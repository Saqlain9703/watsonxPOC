PYTHON ?= python3.12
VENV_PYTHON := .venv/bin/python
MANAGE := $(VENV_PYTHON) scripts/manage_agents.py

.PHONY: help setup env validate test render connect models import deploy list import-local models-local

help:
	@echo "setup          Create venv and install pinned project dependencies"
	@echo "env            Create placeholder .env if it does not exist"
	@echo "validate       Validate 4 agents and the Python tool offline"
	@echo "test           Run offline ADK/schema and Python-tool tests"
	@echo "render         Render agent YAML from configured placeholders"
	@echo "models         Connect and list tenant models"
	@echo "import         Import Python tool, 3 supporting agents, then supervisor as drafts"
	@echo "deploy         Re-import current files, then publish 4 agents live on SaaS"
	@echo "list           List native agents on the configured SaaS tenant"
	@echo "import-local   Import drafts into a running Developer Edition"

setup:
	$(PYTHON) -m venv .venv
	$(VENV_PYTHON) -m pip install -r requirements.txt

env:
	@test -f .env || (umask 077; cp .env.example .env)

validate:
	$(MANAGE) validate

test:
	bash scripts/smoke_test.sh

render:
	$(MANAGE) render

connect:
	$(MANAGE) connect

models:
	$(MANAGE) models

import:
	bash scripts/import_all.sh

deploy:
	$(MANAGE) deploy

list:
	$(MANAGE) list

import-local:
	bash scripts/import_all.sh --local

models-local:
	$(MANAGE) models --local
