#!/usr/bin/env python3
"""Apply or restore the evaluation-framework orphan-tool workaround."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


ORIGINAL = "agent_tools = [tool_id2name[id] for id in agent_tool_ids]"
PATCHED = (
    "agent_tools = [\n"
    "                tool_id2name[id]\n"
    "                for id in agent_tool_ids\n"
    "                if id in tool_id2name\n"
    "            ]"
)
BACKUP_SUFFIX = ".watsonxpoc-backup"


def resource_map_path() -> Path:
    try:
        import agentops.resource_map as resource_map
    except ImportError as exc:
        raise RuntimeError(
            "The evaluation framework is not installed in this Python environment. "
            "Activate the evaluation virtual environment first."
        ) from exc
    return Path(resource_map.__file__).resolve()


def apply(path: Path, backup: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if PATCHED in text:
        print(f"Already patched: {path}")
        return
    if ORIGINAL not in text:
        raise RuntimeError(
            "The expected evaluation-framework code was not found. Do not patch "
            f"this version manually: {path}"
        )
    if not backup.exists():
        shutil.copy2(path, backup)
    path.write_text(text.replace(ORIGINAL, PATCHED, 1), encoding="utf-8")
    print(f"Patched: {path}")
    print(f"Backup:  {backup}")
    print("Orphaned tool IDs will be ignored while building the evaluation resource map.")


def restore(path: Path, backup: Path) -> None:
    if not backup.exists():
        raise RuntimeError(f"Backup not found; nothing to restore: {backup}")
    shutil.copy2(backup, path)
    backup.unlink()
    print(f"Restored: {path}")


def status(path: Path, backup: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if PATCHED in text:
        state = "patched"
    elif ORIGINAL in text:
        state = "original"
    else:
        state = "unknown version"
    print(f"Status: {state}")
    print(f"File:   {path}")
    print(f"Backup: {backup} ({'present' if backup.exists() else 'absent'})")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("apply", "restore", "status"))
    args = parser.parse_args()
    try:
        path = resource_map_path()
        backup = Path(str(path) + BACKUP_SUFFIX)
        if args.action == "apply":
            apply(path, backup)
        elif args.action == "restore":
            restore(path, backup)
        else:
            status(path, backup)
    except (OSError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
