#!/usr/bin/env python3
"""Find native agents whose tool IDs are missing from the active WXO environment."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


ANSI_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def run_cli(arguments: list[str]) -> str:
    executable = shutil.which("orchestrate")
    if not executable:
        raise RuntimeError(
            "The 'orchestrate' command was not found. Activate the evaluation "
            "virtual environment and try again."
        )
    result = subprocess.run(
        [executable, *arguments],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(
            f"Command failed: orchestrate {' '.join(arguments)}\n{detail}"
        )
    return result.stdout


def read_or_run(path: Path | None, arguments: list[str]) -> str:
    if path:
        return path.read_text(encoding="utf-8", errors="replace")
    return run_cli(arguments)


def json_values(text: str):
    """Yield JSON objects from output that may also contain CLI log lines."""
    cleaned = ANSI_ESCAPE.sub("", text.lstrip("\ufeff"))
    decoder = json.JSONDecoder()
    for index, character in enumerate(cleaned):
        if character not in "[{":
            continue
        try:
            value, _ = decoder.raw_decode(cleaned[index:])
        except json.JSONDecodeError:
            continue
        yield value


def parse_agents(text: str) -> list[dict[str, Any]]:
    for value in json_values(text):
        if isinstance(value, dict) and isinstance(value.get("native"), list):
            return value["native"]
        if isinstance(value, list) and all(isinstance(item, dict) for item in value):
            if any("tools" in item and "name" in item for item in value):
                return value
    raise RuntimeError("Could not find the native-agent JSON in CLI output.")


def parse_tools(text: str) -> list[dict[str, Any]]:
    for value in json_values(text):
        if isinstance(value, list) and all(isinstance(item, dict) for item in value):
            if not value or all("id" in item and "name" in item for item in value):
                return value
    raise RuntimeError("Could not find the tool JSON in CLI output.")


def resource_id(value: Any) -> str:
    if isinstance(value, dict):
        value = value.get("id", value.get("tool_id", ""))
    return str(value)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--agents-file",
        type=Path,
        help="Read saved `agents list --verbose` output instead of calling the CLI.",
    )
    parser.add_argument(
        "--tools-file",
        type=Path,
        help="Read saved `tools list --verbose` output instead of calling the CLI.",
    )
    args = parser.parse_args()
    if bool(args.agents_file) != bool(args.tools_file):
        parser.error("Use --agents-file and --tools-file together.")

    try:
        agents = parse_agents(
            read_or_run(
                args.agents_file,
                ["agents", "list", "--kind", "native", "--verbose"],
            )
        )
        tools = parse_tools(
            read_or_run(args.tools_file, ["tools", "list", "--verbose"])
        )
    except (OSError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    known_tool_ids = {resource_id(tool.get("id")) for tool in tools}
    missing: list[tuple[str, str, str]] = []
    for agent in agents:
        for tool in agent.get("tools") or []:
            tool_id = resource_id(tool)
            if tool_id and tool_id not in known_tool_ids:
                missing.append(
                    (
                        str(agent.get("name", "<unknown>")),
                        str(agent.get("id", "<unknown>")),
                        tool_id,
                    )
                )

    print(f"Checked {len(agents)} native agents and {len(tools)} tools.")
    if not missing:
        print("OK: no orphaned native-agent tool references were found.")
        return 0

    headings = ("AGENT NAME", "AGENT ID", "MISSING TOOL ID")
    widths = [
        max(len(headings[index]), *(len(row[index]) for row in missing))
        for index in range(3)
    ]
    print("FOUND: orphaned tool references that can cause evaluation KeyError.")
    print("  ".join(headings[index].ljust(widths[index]) for index in range(3)))
    print("  ".join("-" * width for width in widths))
    for row in missing:
        print("  ".join(row[index].ljust(widths[index]) for index in range(3)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
