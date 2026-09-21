PYTHON ?= python3.12
VENV_PYTHON := .venv/bin/python
MANAGE := $(VENV_PYTHON) scripts/manage_agents.py

.PHONY: help setup env validate test knowledge knowledge-status knowledge-status-local render connect models import deploy list import-local models-local list-local

help:
	@echo "setup         Create Python 3.12 venv and install pinned dependencies"
	@echo "env           Create .env from placeholders if it does not exist"
	@echo "validate      Validate agents, KBs, Markdown sources, and the tool offline"
	@echo "test          Run offline validation and deployment-script tests"
	@echo "knowledge     Stage Markdown as supported text uploads (no credentials)"
	@echo "knowledge-status  Verify ingested KBs match the current local sources"
	@echo "render        Render agent YAML and knowledge uploads using WO_AGENT_MODEL"
	@echo "connect       Register/activate the SaaS environment in .env"
	@echo "models        Connect and list tenant models (no model ID needed yet)"
	@echo "import        Import KBs and tool, verify ingestion, then import agent drafts"
	@echo "deploy        Import current YAML, then deploy all three live on SaaS"
	@echo "list          List native agents on the configured SaaS tenant"
	@echo "import-local  Import drafts into a running Developer Edition"
	@echo "models-local  List models on Developer Edition"
	@echo "list-local    List native agents on Developer Edition"

setup:
	$(PYTHON) -m venv .venv
	$(VENV_PYTHON) -m pip install -r requirements.txt

env:
	@test -f .env || (umask 077; cp .env.example .env)

validate:
	$(MANAGE) validate

test:
	bash scripts/smoke_test.sh

knowledge:
	$(MANAGE) knowledge

knowledge-status:
	$(MANAGE) knowledge-status

knowledge-status-local:
	$(MANAGE) knowledge-status --local

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

list-local:
	$(MANAGE) list --local
