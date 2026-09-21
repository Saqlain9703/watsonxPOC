#!/usr/bin/env python3
"""Validate agent templates offline, then render/import/deploy with the IBM ADK."""

import argparse
import importlib.util
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
from urllib.parse import urlparse

from dotenv import dotenv_values
from ibm_watsonx_orchestrate.agent_builder.agents import Agent
import yaml

from knowledge_assets import KB_NAMES, assert_knowledge_ready, build_knowledge, load_knowledge

ROOT = Path(__file__).resolve().parents[1]
AGENT_NAMES = (
    "account_billing_agent",
    "product_policy_agent",
    "onboarding_supervisor",
)
MODEL_TOKEN = "${WO_AGENT_MODEL}"
AGENT_DEPENDENCIES = {
    "account_billing_agent": (["get_account_status"], ["account_billing_kb"]),
    "product_policy_agent": ([], ["product_policy_kb"]),
    "onboarding_supervisor": ([], []),
}


def configuration(env_file: Path) -> dict[str, str]:
    # Do not source a shell file or expand arbitrary environment variables.
    values = {k: v for k, v in dotenv_values(env_file, interpolate=False).items() if v is not None}
    return {**values, **os.environ}  # Explicit shell variables take precedence.


def required(config: dict[str, str], key: str) -> str:
    value = config.get(key, "").strip()
    if not value or any(token in value for token in ("<", ">", "${")) or value.lower() in {
        "placeholder", "changeme", "todo",
    }:
        raise ValueError(f"Set {key} in .env or your shell; it is missing or still a placeholder.")
    if "\n" in value or "\r" in value:
        raise ValueError(f"{key} must be a single-line value.")
    return value


def validate_document(data: dict, name: str) -> None:
    if not isinstance(data, dict):
        raise ValueError(f"{name}: expected a YAML mapping.")
    if data.get("spec_version") != "v1" or data.get("kind") != "native":
        raise ValueError(f"{name}: requires spec_version: v1 and kind: native.")
    if data.get("name") != name:
        raise ValueError(f"{name}: filename and agent name must match.")
    for field in ("description", "instructions", "llm"):
        if not isinstance(data.get(field), str) or not data[field].strip():
            raise ValueError(f"{name}: {field} must be a nonempty string.")
    # Pydantic otherwise ignores some unknown fields, hiding misspelled YAML keys.
    unknown = set(data) - set(Agent.model_fields) - {"spec_version"}
    if unknown:
        raise ValueError(f"{name}: unknown ADK fields: {', '.join(sorted(unknown))}.")
    Agent.model_validate(data)


def load_agents(directory: Path = ROOT / "agents") -> list[dict]:
    expected = {f"{name}.yaml" for name in AGENT_NAMES}
    actual = {p.name for p in directory.glob("*.yaml")} | {p.name for p in directory.glob("*.yml")}
    if actual != expected:
        raise ValueError("agents/ must contain exactly the three POC agent YAML files.")
    documents = []
    for name in AGENT_NAMES:
        path = directory / f"{name}.yaml"
        data = yaml.safe_load(path.read_text())
        validate_document(data, name)
        expected_tools, expected_knowledge = AGENT_DEPENDENCIES[name]
        if data.get("tools", []) != expected_tools or data.get("knowledge_base", []) != expected_knowledge:
            raise ValueError(f"{name}: tools/knowledge_base must match the declared POC dependencies.")
        collaborators = data.get("collaborators", [])
        wanted = list(AGENT_NAMES[:2]) if name == AGENT_NAMES[-1] else []
        if collaborators != wanted:
            raise ValueError(f"{name}: collaborators must be {wanted} in dependency order.")
        if data["llm"] != MODEL_TOKEN:
            raise ValueError(f"{name}: keep llm as {MODEL_TOKEN}; configure the model in .env.")
        documents.append(data)
    return documents


def render_agents(config: dict[str, str], output: Path = ROOT / ".build" / "agents") -> list[Path]:
    documents = load_agents()
    model = required(config, "WO_AGENT_MODEL")
    if not re.fullmatch(r"[A-Za-z0-9_.:-]+(?:/[A-Za-z0-9_.:-]+)+", model):
        raise ValueError("WO_AGENT_MODEL must be a provider/model ID from `make models`.")
    for data in documents:
        # Replace the parsed scalar, never interpolate raw YAML or credentials.
        data["llm"] = model
        validate_document(data, data["name"])
    output.mkdir(parents=True, exist_ok=True)
    files = []
    for data in documents:
        path = output / f"{data['name']}.yaml"
        path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
        Agent.from_spec(str(path))  # Same file loader used by the ADK.
        files.append(path)
    print(f"Rendered and ADK-validated {len(files)} agent files in {output}.")
    return files


def run_cli(*args: str) -> None:
    executable = ROOT / ".venv" / "bin" / "orchestrate"
    binary = str(executable) if executable.is_file() else shutil.which("orchestrate")
    if not binary:
        raise ValueError("IBM ADK is missing. Run `make setup` first.")
    display = list(args)
    if "--api-key" in display:
        display[display.index("--api-key") + 1] = "<redacted>"
    print("+ orchestrate " + shlex.join(display), flush=True)
    result = subprocess.run([binary, *args], cwd=ROOT, check=False)
    if result.returncode:
        # CalledProcessError includes argv (and potentially the API key).
        raise RuntimeError(f"Orchestrate {' '.join(display[:2])} failed (exit {result.returncode}).")


def connect(config: dict[str, str], local: bool = False) -> None:
    if local:
        run_cli("env", "activate", "local")
        return
    name = required(config, "WO_ENV_NAME")
    url = required(config, "WO_INSTANCE_URL").rstrip("/")
    key = required(config, "WO_API_KEY")
    auth_type = required(config, "WO_ENV_TYPE")
    if name == "local" or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", name):
        raise ValueError("WO_ENV_NAME must be a remote environment name, e.g. poc-saas.")
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("WO_INSTANCE_URL must be the HTTPS service instance URL from API details.")
    if auth_type not in {"ibm_iam", "mcsp", "mcsp_v1", "mcsp_v2"}:
        raise ValueError("This scaffold supports IBM Cloud/AWS SaaS; see docs/open-questions.md for CPD.")

    from ibm_watsonx_orchestrate.cli.config import Config

    # Reuse a matching registration without the CLI's interactive update prompt.
    existing = Config().read("environments", name)
    if existing:
        if existing.get("wxo_url", "").rstrip("/") != url or existing.get("auth_type") != auth_type:
            raise ValueError(
                f"Environment {name} has different URL/auth settings. Choose a new WO_ENV_NAME "
                "or update that registration with `orchestrate env add`."
            )
    else:
        run_cli("env", "add", "--name", name, "--url", url, "--type", auth_type)
    run_cli("env", "activate", name, "--api-key", key)
    if Config().read("context", "active_environment") != name:
        raise RuntimeError("The requested environment did not become active; stopping.")


def import_agents(files: list[Path]) -> None:
    for path in files:  # Collaborators are already first in the validated order.
        run_cli("agents", "import", "--file", str(path))


def validate_account_tool() -> None:
    spec = importlib.util.spec_from_file_location("poc_account_tools", ROOT / "tools" / "account_tools.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    tool_spec = module.get_account_status.__tool_spec__
    if tool_spec.name != "get_account_status":
        raise ValueError("Account tool name does not match the agent dependency.")
    # Materialize the ADK schema to catch annotation/docstring problems locally.
    tool_spec.model_dump_json()
    if not (ROOT / "tools" / "requirements.txt").is_file():
        raise ValueError("tools/requirements.txt is required for Python-tool import.")


def check_knowledge_ready(files: list[Path]) -> None:
    from ibm_watsonx_orchestrate.client.knowledge_bases.knowledge_base_client import KnowledgeBaseClient
    from ibm_watsonx_orchestrate.client.utils import instantiate_client

    assert_knowledge_ready(instantiate_client(KnowledgeBaseClient), files)


def import_dependencies(knowledge_files: list[Path]) -> None:
    for path in knowledge_files:
        run_cli("knowledge-bases", "import", "--file", str(path))
    # The pinned ADK sometimes returns normally after an ingestion error/timeout.
    # Inspect structured status and content-derived filenames before continuing.
    check_knowledge_ready(knowledge_files)
    run_cli("tools", "import", "--kind", "python", "--file", str(ROOT / "tools" / "account_tools.py"),
            "--requirements-file", str(ROOT / "tools" / "requirements.txt"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate", "knowledge", "knowledge-status", "render", "connect", "models", "import", "deploy", "list"))
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    parser.add_argument("--local", action="store_true", help="Target the built-in Developer Edition environment.")
    args = parser.parse_args()
    try:
        if args.command == "validate":
            load_agents()
            knowledge = load_knowledge()
            validate_account_tool()
            print(f"Validated 3 agents, 2 knowledge bases, {sum(len(k['documents']) for k in knowledge)} Markdown sources, and 1 Python tool with the IBM ADK.")
            print("Model placeholders are allowed here; runtime behavior and tenant access are not tested.")
            return 0
        if args.command == "knowledge":
            build_knowledge()
            return 0
        if args.command == "deploy" and args.local:
            raise ValueError("Developer Edition supports drafts only. Use import --local.")
        config = configuration(args.env_file)
        if args.command == "render":
            render_agents(config)
            build_knowledge()
            validate_account_tool()
            return 0
        files = render_agents(config) if args.command in {"import", "deploy"} else []
        knowledge_files = []
        if args.command in {"import", "deploy", "knowledge-status"}:
            knowledge_files = build_knowledge()
            validate_account_tool()
        connect(config, args.local)
        if args.command in {"import", "deploy"}:
            import_dependencies(knowledge_files)
            import_agents(files)
        if args.command == "knowledge-status":
            check_knowledge_ready(knowledge_files)
            return 0
        if args.command == "deploy":
            for name in AGENT_NAMES:
                run_cli("agents", "deploy", "--name", name)
        if args.command == "models":
            run_cli("models", "list")
        elif args.command in {"import", "deploy", "list"}:
            run_cli("agents", "list", "--kind", "native")
        print("Command completed. Use docs/smoke-tests.md to verify routing after import/deployment.")
        return 0
    except (ValueError, RuntimeError, OSError, yaml.YAMLError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
