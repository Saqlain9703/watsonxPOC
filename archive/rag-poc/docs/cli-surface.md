# Verified ADK CLI surface

Verified locally on **2026-09-16**, Python **3.12.13**,
`ibm-watsonx-orchestrate==2.16.1`. `orchestrate --version` reported ADK 2.16.1.
All help commands below returned exit code 0. No tenant credentials were used.

## Commands used by this scaffold

| Purpose | Verified spelling / flags |
| --- | --- |
| Version and root help | `orchestrate --version`, `orchestrate --help` |
| Register remote environment | `orchestrate env add --name NAME --url URL --type TYPE` |
| Authenticate/activate remote | `orchestrate env activate NAME --api-key KEY` |
| Activate Developer Edition | `orchestrate env activate local` |
| List environments | `orchestrate env list` |
| List tenant models | `orchestrate models list` (`--raw`, `--all` also available) |
| Import a draft | `orchestrate agents import --file FILE` (`-f` alias) |
| List native agents | `orchestrate agents list --kind native` (`--verbose` for details) |
| Deploy a live agent | `orchestrate agents deploy --name NAME` |
| Start local services with telemetry | `orchestrate server start --env-file .env --with-ibm-telemetry` |
| Start local chat UI | `orchestrate chat start` |

The remote helper selects the configured environment explicitly before listing,
importing, or deploying. Dependencies are imported/deployed before the supervisor.
`env add` prompts when a registration exists; the helper reuses a matching
registration and stops on a URL/auth mismatch.

## Group help inspected for later phases

The following command groups all exist and their `--help` commands were run:

```text
agents
tools
knowledge-bases
evaluations
observability
controls
env
```

Only group availability is established for later-phase commands. Their
subcommands, flags, schemas, and tenant behavior must be verified when used.
Raw help captures from this session are in ignored `.build/cli-help/`.

## Corrections to the supplied examples

- The installed auth type enum is `ibm_iam|mcsp|mcsp_v1|mcsp_v2|cpd|k8s`.
  `--type local` is invalid. Use the built-in `local` environment instead.
- The knowledge command is `knowledge-bases`, with a hyphen.
- Native agent YAML uses the modern `react_core` style. The older examples'
  `default` and `react` styles are deprecated in current IBM documentation.
- Every `starter_prompts.prompts` item requires an `id`. The supplied example
  omitted it; the installed `Agent.from_spec` rejected that example until fixed.
- YAML is loaded through `yaml.safe_load`; `${WO_AGENT_MODEL}` is not expanded by
  the ADK. The project renderer substitutes only the parsed `llm` field.
- `env add --iam-url` appears in online docs, but is absent from this installed
  CLI's options. The helper does not pass that unsupported flag.
- Draft import and live deployment are separate commands. Developer Edition
  supports drafts only.

## Offline schema validation

The validator uses `ibm_watsonx_orchestrate.agent_builder.agents.Agent` and the
ADK's `Agent.from_spec` for rendered files. It also checks names, unknown top-level
fields, the expected collaborator graph, and exact tool/knowledge dependencies.
Templates allow the model placeholder; rendering and
remote operations require configured values.

## Knowledge and tools increment

These subcommand help pages were also verified against installed ADK 2.16.1:

| Purpose | Verified command |
| --- | --- |
| Import knowledge documents | `orchestrate knowledge-bases import --file FILE` |
| Inspect full ingestion status | `orchestrate knowledge-bases status --name NAME --verbose` |
| Import Python tool | `orchestrate tools import --kind python --file tools/account_tools.py --requirements-file tools/requirements.txt` |

KB paths resolve relative to the YAML file's directory in the installed CLI.
Both source and rendered definitions validate with `KnowledgeBase.from_spec`;
source paths use Markdown and rendered paths use supported text uploads. The
tool schema is materialized through the ADK decorator before remote work.

The pinned ADK's KB importer polls `built_in_index_status` for up to 1,200 seconds.
Error and timeout paths can return without a failing exit code. The project
therefore uses `KnowledgeBaseClient.get_by_names` and `status` after import to
require exactly one matching KB, `built_in_index_status: ready`, and expected
`documents[].metadata.original_file_name` values. Names include content hashes
so stale document versions cannot satisfy the check.

The manifests use dynamic knowledge mode and all citations. Confidence thresholds
from the plan are not claimed as active; see [knowledge settings](../knowledge/README.md#retrieval-settings)
and [IBM KB modes](https://developer.watson-orchestrate.ibm.com/knowledge_base/build_kb).

Sources:

- [IBM native agents](https://developer.watson-orchestrate.ibm.com/agents/build_agent)
- [IBM importing and deploying agents](https://developer.watson-orchestrate.ibm.com/agents/import_agent)
- [IBM environment setup](https://developer.watson-orchestrate.ibm.com/environment/initiate_environment)
- [IBM agent styles](https://developer.watson-orchestrate.ibm.com/agents/agent_styles)
- Installed ADK 2.16.1 help and Python schema/source.
