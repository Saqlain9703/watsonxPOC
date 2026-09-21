#!/usr/bin/env bash
# Offline schema and Python-tool tests. Live review cases are in docs/smoke-tests.md.
set -euo pipefail
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"
"$PROJECT_ROOT/.venv/bin/python" scripts/manage_agents.py validate
"$PROJECT_ROOT/.venv/bin/python" -m unittest discover -s tests -v
