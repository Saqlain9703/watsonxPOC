"""Offline checks for the scaffold and operations that will later write to a tenant."""

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, call, patch

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import manage_agents as manage


class AgentScaffoldTests(unittest.TestCase):
    def test_templates_load_with_adk_and_correct_graph(self):
        documents = manage.load_agents()
        self.assertEqual([d["name"] for d in documents], list(manage.AGENT_NAMES))

    def test_unresolved_model_cannot_render(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "agents"
            for model in ("", "<supported-provider/model-id>", "${WO_AGENT_MODEL}"):
                with self.subTest(model=model), self.assertRaisesRegex(ValueError, "WO_AGENT_MODEL"):
                    manage.render_agents({"WO_AGENT_MODEL": model}, target)
            self.assertFalse(target.exists())

    def test_rendered_yaml_round_trips_without_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = {"WO_AGENT_MODEL": "watsonx/test/model", "WO_API_KEY": "test-only-secret"}
            with redirect_stdout(StringIO()):
                paths = manage.render_agents(config, Path(tmp))
            for path in paths:
                text = path.read_text()
                data = yaml.safe_load(text)
                self.assertEqual(data["llm"], "watsonx/test/model")
                self.assertNotIn("test-only-secret", text)
                self.assertNotIn(manage.MODEL_TOKEN, text)

    def test_model_value_cannot_inject_yaml(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                manage.render_agents({"WO_AGENT_MODEL": "watsonx/model\ntools: [unexpected]"}, Path(tmp))

    def test_unknown_adk_field_is_rejected(self):
        document = manage.load_agents()[0]
        document["collaborator"] = ["unknown_agent"]
        with self.assertRaisesRegex(ValueError, "unknown ADK fields"):
            manage.validate_document(document, document["name"])

    def test_reverse_collaboration_edge_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "agents"
            shutil.copytree(manage.ROOT / "agents", directory)
            path = directory / "account_billing_agent.yaml"
            data = yaml.safe_load(path.read_text())
            data["collaborators"] = ["onboarding_supervisor"]
            path.write_text(yaml.safe_dump(data))
            with self.assertRaisesRegex(ValueError, "collaborators"):
                manage.load_agents(directory)

    def test_unregistered_tool_reference_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "agents"
            shutil.copytree(manage.ROOT / "agents", directory)
            path = directory / "account_billing_agent.yaml"
            data = yaml.safe_load(path.read_text())
            data["tools"] = ["missing_tool"]
            path.write_text(yaml.safe_dump(data))
            with self.assertRaisesRegex(ValueError, "dependencies"):
                manage.load_agents(directory)

    def test_dotenv_is_data_and_shell_overrides_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = Path(tmp) / ".env"
            env.write_text('WO_AGENT_MODEL="file/model"\nWO_API_KEY="$(echo never-execute)"\n')
            with patch.dict(manage.os.environ, {"WO_AGENT_MODEL": "shell/model"}, clear=True):
                config = manage.configuration(env)
            self.assertEqual(config["WO_AGENT_MODEL"], "shell/model")
            self.assertEqual(config["WO_API_KEY"], "$(echo never-execute)")

    def test_missing_credentials_prevent_any_cli_call(self):
        with patch.object(manage, "run_cli") as cli:
            with self.assertRaisesRegex(ValueError, "WO_INSTANCE_URL"):
                manage.connect({"WO_ENV_NAME": "poc-saas", "WO_INSTANCE_URL": "<placeholder>"})
            cli.assert_not_called()

    def test_import_stops_at_first_failure(self):
        files = [Path(name + ".yaml") for name in manage.AGENT_NAMES]
        with patch.object(manage, "run_cli", side_effect=[None, RuntimeError("import failed")]) as cli:
            with self.assertRaises(RuntimeError):
                manage.import_agents(files)
        self.assertEqual(cli.call_args_list, [
            call("agents", "import", "--file", str(files[0])),
            call("agents", "import", "--file", str(files[1])),
        ])

    def test_api_key_is_redacted_on_cli_failure(self):
        output = StringIO()
        with patch.object(subprocess, "run", return_value=Mock(returncode=1)), redirect_stdout(output):
            with self.assertRaises(RuntimeError) as error:
                manage.run_cli("env", "activate", "poc-saas", "--api-key", "test-only-secret")
        self.assertNotIn("test-only-secret", output.getvalue() + str(error.exception))
        self.assertIn("<redacted>", output.getvalue())

    def test_deploy_imports_then_publishes_in_dependency_order(self):
        files = [Path(name + ".yaml") for name in manage.AGENT_NAMES]
        knowledge = [Path(name + ".yaml") for name in manage.KB_NAMES]
        with patch.object(sys, "argv", ["manage_agents.py", "deploy"]), \
             patch.object(manage, "configuration", return_value={}), \
             patch.object(manage, "render_agents", return_value=files), \
             patch.object(manage, "build_knowledge", return_value=knowledge), \
             patch.object(manage, "validate_account_tool"), \
             patch.object(manage, "check_knowledge_ready") as ready, \
             patch.object(manage, "connect") as connect, \
             patch.object(manage, "run_cli") as cli, redirect_stdout(StringIO()):
            self.assertEqual(manage.main(), 0)
        connect.assert_called_once_with({}, False)
        ready.assert_called_once_with(knowledge)
        self.assertEqual(cli.call_args_list, [
            *[call("knowledge-bases", "import", "--file", str(path)) for path in knowledge],
            call("tools", "import", "--kind", "python", "--file", str(manage.ROOT / "tools/account_tools.py"),
                 "--requirements-file", str(manage.ROOT / "tools/requirements.txt")),
            *[call("agents", "import", "--file", str(path)) for path in files],
            *[call("agents", "deploy", "--name", name) for name in manage.AGENT_NAMES],
            call("agents", "list", "--kind", "native"),
        ])

    def test_not_ready_knowledge_stops_before_tools_or_agents(self):
        knowledge = [Path(name + ".yaml") for name in manage.KB_NAMES]
        with patch.object(manage, "check_knowledge_ready", side_effect=RuntimeError("not ready")), \
             patch.object(manage, "run_cli") as cli:
            with self.assertRaisesRegex(RuntimeError, "not ready"):
                manage.import_dependencies(knowledge)
        self.assertEqual(cli.call_args_list, [
            call("knowledge-bases", "import", "--file", str(path)) for path in knowledge
        ])


if __name__ == "__main__":
    unittest.main()
