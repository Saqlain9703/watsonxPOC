#!/usr/bin/env bash
# Offline validation only. Live chat checks are documented separately.
set -euo pipefail
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
"$PROJECT_ROOT/.venv/bin/python" "$PROJECT_ROOT/scripts/manage_agents.py" validate
"$PROJECT_ROOT/.venv/bin/python" -m unittest discover -s "$PROJECT_ROOT/tests" -v
