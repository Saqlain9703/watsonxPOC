#!/usr/bin/env python3
"""Validate, render, import, and deploy the shipping agents and Python tool."""

import argparse
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
from ibm_watsonx_orchestrate.agent_builder.tools.utils import extract_python_tools
import yaml

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / ".build" / "shipping"
AGENT_NAMES = ("rate_eligibility_agent", "general_enquiry_agent", "response_agent", "supervisor_agent")
MODEL_TOKEN = "${WO_AGENT_MODEL}"
TOOL_PATH = ROOT / "tools" / "rate_eligibility.py"
TOOL_REQUIREMENTS = ROOT / "tools" / "requirements.txt"


def configuration(env_file: Path) -> dict[str, str]:
    values = {k: v for k, v in dotenv_values(env_file, interpolate=False).items() if v is not None}
    return {**values, **os.environ}


def required(config: dict[str, str], key: str) -> str:
    value = config.get(key, "").strip()
    if not value or any(token in value for token in ("<", ">", "${")) or value.lower() in {"placeholder", "changeme", "todo"}:
        raise ValueError(f"Set {key} in .env or your shell; it is missing or still a placeholder.")
    if "\n" in value or "\r" in value:
        raise ValueError(f"{key} must be a single-line value.")
    return value


def validate_document(data: dict, name: str) -> None:
    if not isinstance(data, dict) or data.get("spec_version") != "v1" or data.get("kind") != "native":
        raise ValueError(f"{name}: expected spec_version: v1 and kind: native.")
    if data.get("name") != name:
        raise ValueError(f"{name}: filename and agent name must match.")
    for field in ("description", "instructions", "llm"):
        if not isinstance(data.get(field), str) or not data[field].strip():
            raise ValueError(f"{name}: {field} must be a nonempty string.")
    unknown = set(data) - set(Agent.model_fields) - {"spec_version"}
    if unknown:
        raise ValueError(f"{name}: unknown ADK fields: {', '.join(sorted(unknown))}.")
    Agent.model_validate(data)


def load_agents(directory: Path = ROOT / "agents") -> list[dict]:
    actual = {p.name for p in directory.glob("*.yaml")} | {p.name for p in directory.glob("*.yml")}
    if actual != {f"{name}.yaml" for name in AGENT_NAMES}:
        raise ValueError("agents/ must contain exactly the four shipping POC agents.")
    documents = []
    for name in AGENT_NAMES:
        data = yaml.safe_load((directory / f"{name}.yaml").read_text(encoding="utf-8"))
        validate_document(data, name)
        expected_tools = ["evaluate_rate_eligibility"] if name == "rate_eligibility_agent" else []
        expected_collaborators = list(AGENT_NAMES[:3]) if name == "supervisor_agent" else []
        if data.get("tools") != expected_tools or data.get("knowledge_base") != []:
            raise ValueError(f"{name}: only the rate specialist may have the Python tool; no agent may have knowledge bases.")
        if data.get("collaborators") != expected_collaborators:
            raise ValueError(f"{name}: unexpected collaborator graph.")
        if data["llm"] != MODEL_TOKEN:
            raise ValueError(f"{name}: configure WO_AGENT_MODEL through .env, not the YAML.")
        documents.append(data)
    return documents


def validate_rate_tool(
    tool_path: Path = TOOL_PATH,
    requirements_path: Path = TOOL_REQUIREMENTS,
):
    if not tool_path.is_file() or not requirements_path.is_file():
        raise ValueError("The Python rate tool and tools/requirements.txt are required.")
    tools = extract_python_tools(
        file=str(tool_path),
        requirements_file=str(requirements_path),
        log_requirements_path=False,
    )
    if len(tools) != 1 or tools[0].__tool_spec__.name != "evaluate_rate_eligibility":
        raise ValueError("Expected exactly one Python tool named evaluate_rate_eligibility.")
    spec = tools[0].__tool_spec__.model_dump(mode="json")
    if spec.get("permission") != "read_only":
        raise ValueError("evaluate_rate_eligibility must remain read-only.")
    required_inputs = {"monthly_volume", "destination_mix", "business_type"}
    if set(spec["input_schema"]["required"]) != required_inputs:
        raise ValueError("The Python rate tool must require all three eligibility inputs.")
    return tools[0]


def render(config: dict[str, str], output: Path = BUILD) -> list[Path]:
    documents = load_agents()
    validate_rate_tool()
    model = required(config, "WO_AGENT_MODEL")
    if not re.fullmatch(r"[A-Za-z0-9_.:-]+(?:/[A-Za-z0-9_.:-]+)+", model):
        raise ValueError("WO_AGENT_MODEL must be a provider/model ID from `make models`.")
    files = []
    for data in documents:
        data["llm"] = model
        path = output / "agents" / f"{data['name']}.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        Agent.from_spec(str(path))
        files.append(path)
    print(f"Rendered 4 agents in {output}; validated the Python tool at {TOOL_PATH}.")
    return files


def run_cli(*args: str) -> None:
    if os.name == "nt":
        venv_executables = (
            ROOT / ".venv" / "Scripts" / "orchestrate.exe",
            ROOT / ".venv" / "Scripts" / "orchestrate",
        )
    else:
        venv_executables = (ROOT / ".venv" / "bin" / "orchestrate",)
    executable = next((path for path in venv_executables if path.is_file()), None)
    binary = str(executable) if executable else shutil.which("orchestrate")
    if not binary:
        raise ValueError("IBM ADK is missing. Run `make setup` first.")
    display = list(args)
    if "--api-key" in display:
        display[display.index("--api-key") + 1] = "<redacted>"
    print("+ orchestrate " + shlex.join(display), flush=True)
    result = subprocess.run([binary, *args], cwd=ROOT, check=False)
    if result.returncode:
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
    if auth_type not in {"ibm_iam", "mcsp", "mcsp_v1", "mcsp_v2", "cpd"}:
        raise ValueError("WO_ENV_TYPE must identify IBM Cloud, AWS SaaS, or IBM Software Hub/CPD.")
    from ibm_watsonx_orchestrate.cli.config import Config
    existing = Config().read("environments", name)
    if existing:
        if existing.get("wxo_url", "").rstrip("/") != url or existing.get("auth_type") != auth_type:
            raise ValueError(f"Environment {name} has different URL/auth settings. Choose a new WO_ENV_NAME or update its CLI registration.")
    else:
        run_cli("env", "add", "--name", name, "--url", url, "--type", auth_type)
    activation_args = ["env", "activate", name, "--api-key", key]
    if auth_type == "cpd":
        activation_args.extend(("--username", required(config, "WO_USERNAME")))
    skip_version_check = config.get("WO_SKIP_VERSION_CHECK", "").strip().lower()
    if skip_version_check:
        if skip_version_check not in {"true", "false"}:
            raise ValueError("WO_SKIP_VERSION_CHECK must be true or false when set.")
        activation_args.append(
            "--skip-version-check" if skip_version_check == "true" else "--enable-version-check"
        )
    run_cli(*activation_args)
    if Config().read("context", "active_environment") != name:
        raise RuntimeError("The requested environment did not become active; stopping.")


def import_resources(
    files: list[Path],
    tool_path: Path = TOOL_PATH,
    requirements_path: Path = TOOL_REQUIREMENTS,
) -> None:
    run_cli(
        "tools", "import", "--kind", "python", "--file", str(tool_path),
        "--requirements-file", str(requirements_path),
    )
    for path in files:
        run_cli("agents", "import", "--file", str(path))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate", "render", "connect", "models", "import", "deploy", "list"))
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    parser.add_argument("--local", action="store_true", help="Target a running Developer Edition environment.")
    args = parser.parse_args()
    try:
        if args.command == "validate":
            load_agents()
            validate_rate_tool()
            print("Validated 4 native agents, no knowledge bases, and the Python tool with the IBM ADK.")
            print("This is schema validation, not a runtime routing or LLM-quality test.")
            return 0
        if args.command == "deploy" and args.local:
            raise ValueError("Developer Edition supports drafts only; use import --local.")
        config = configuration(args.env_file)
        if args.command == "render":
            render(config)
            return 0
        files = render(config) if args.command in {"import", "deploy"} else []
        connect(config, args.local)
        if args.command in {"import", "deploy"}:
            import_resources(files)
        if args.command == "deploy":
            for name in AGENT_NAMES:
                run_cli("agents", "deploy", "--name", name)
        if args.command == "models":
            run_cli("models", "list")
        elif args.command in {"import", "deploy", "list"}:
            run_cli("agents", "list", "--kind", "native")
        return 0
    except (ValueError, RuntimeError, OSError, yaml.YAMLError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
