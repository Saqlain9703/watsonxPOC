"""Offline schema, dependency, rendering, and fail-before-import checks."""

from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import Mock, call, patch

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import manage_agents as manage


class ShippingAssetTests(unittest.TestCase):
    def test_four_agents_load_with_the_native_adk_schema(self):
        agents = manage.load_agents()
        self.assertEqual(len(agents), 4)
        self.assertTrue(all(a["knowledge_base"] == [] for a in agents))
        self.assertEqual(agents[-1]["collaborators"], list(manage.AGENT_NAMES[:3]))

    def test_old_rag_assets_are_archived_and_excluded(self):
        self.assertTrue((ROOT / "archive/rag-poc/knowledge/account_billing_kb.yaml").is_file())
        self.assertFalse((ROOT / "knowledge").exists())
        self.assertFalse((ROOT / "tools/account_tools.py").exists())

    def test_general_agent_cannot_gain_tools_or_knowledge(self):
        for field, value in (("tools", ["evaluate_rate_eligibility"]), ("knowledge_base", ["old_kb"])):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                directory = Path(tmp) / "agents"
                shutil.copytree(ROOT / "agents", directory)
                path = directory / "general_enquiry_agent.yaml"
                data = yaml.safe_load(path.read_text()); data[field] = value
                path.write_text(yaml.safe_dump(data))
                with self.assertRaisesRegex(ValueError, "only the rate"):
                    manage.load_agents(directory)

    def test_response_agent_cannot_introduce_a_collaboration_loop(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "agents"; shutil.copytree(ROOT / "agents", directory)
            path = directory / "response_agent.yaml"
            data = yaml.safe_load(path.read_text()); data["collaborators"] = ["supervisor_agent"]
            path.write_text(yaml.safe_dump(data))
            with self.assertRaisesRegex(ValueError, "collaborator graph"):
                manage.load_agents(directory)

    def test_python_tool_imports_with_actual_adk_parser(self):
        tool = manage.validate_rate_tool()
        spec = tool.__tool_spec__.model_dump(mode="json")
        self.assertEqual(spec["name"], "evaluate_rate_eligibility")
        self.assertEqual(spec["permission"], "read_only")
        self.assertEqual(spec["binding"]["python"]["function"],
                         "rate_eligibility:evaluate_rate_eligibility")

    def test_render_substitutes_only_model(self):
        config = {"WO_AGENT_MODEL": "watsonx/offline-model", "WO_API_KEY": "never-serialize-this"}
        with tempfile.TemporaryDirectory() as tmp, redirect_stdout(StringIO()):
            files = manage.render(config, Path(tmp))
            self.assertEqual(len(files), 4)
            for path in files:
                self.assertNotIn("${", path.read_text())
                self.assertNotIn(config["WO_API_KEY"], path.read_text())

    def test_placeholder_preflight_never_creates_files(self):
        for config in ({}, {"WO_AGENT_MODEL": "<placeholder>"}):
            with self.subTest(config=config), tempfile.TemporaryDirectory() as tmp:
                output = Path(tmp) / "out"
                with self.assertRaises(ValueError):
                    manage.render(config, output)
                self.assertFalse(output.exists())

    def test_imports_tool_before_agents_and_supervisor_last(self):
        files = [Path(name + ".yaml") for name in manage.AGENT_NAMES]
        tool = Path("rate_eligibility.py")
        requirements = Path("requirements.txt")
        with patch.object(manage, "run_cli") as cli:
            manage.import_resources(files, tool, requirements)
        self.assertEqual(cli.call_args_list, [
            call("tools", "import", "--kind", "python", "--file", str(tool),
                 "--requirements-file", str(requirements)),
            *[call("agents", "import", "--file", str(p)) for p in files],
        ])

    def test_tool_import_failure_stops_all_agent_imports(self):
        with patch.object(manage, "run_cli", side_effect=RuntimeError("tool failed")) as cli:
            with self.assertRaises(RuntimeError):
                manage.import_resources(
                    [Path(n + ".yaml") for n in manage.AGENT_NAMES],
                    Path("tool.py"), Path("requirements.txt"),
                )
        self.assertEqual(cli.call_count, 1)

    def test_deploy_is_separate_and_in_dependency_order(self):
        files = [Path(n + ".yaml") for n in manage.AGENT_NAMES]
        with patch.object(sys, "argv", ["manage_agents.py", "deploy"]), \
             patch.object(manage, "configuration", return_value={}), \
             patch.object(manage, "render", return_value=files), \
             patch.object(manage, "connect") as connect, patch.object(manage, "run_cli") as cli:
            self.assertEqual(manage.main(), 0)
        connect.assert_called_once_with({}, False)
        deployments = [c for c in cli.call_args_list if c.args[:2] == ("agents", "deploy")]
        self.assertEqual(deployments, [call("agents", "deploy", "--name", n) for n in manage.AGENT_NAMES])

    def test_local_live_deployment_is_rejected(self):
        with patch.object(sys, "argv", ["manage_agents.py", "deploy", "--local"]), \
             patch.object(manage, "connect") as connect, redirect_stderr(StringIO()):
            self.assertEqual(manage.main(), 1)
        connect.assert_not_called()

    def test_api_key_is_redacted_from_helper_output_and_errors(self):
        output = StringIO()
        with patch.object(manage.subprocess, "run", return_value=Mock(returncode=1)), redirect_stdout(output):
            with self.assertRaises(RuntimeError) as error:
                manage.run_cli("env", "activate", "poc-saas", "--api-key", "test-only-secret")
        self.assertNotIn("test-only-secret", output.getvalue() + str(error.exception))


if __name__ == "__main__":
    unittest.main()
