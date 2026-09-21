# Open questions and implementation decisions

## Current increment

1. **Which model is available on the tenant?** `WO_AGENT_MODEL` remains a
   placeholder. Use `make models` after configuring credentials; choose a model
   with native function calling and `react_core` support. A valid YAML model
   string does not establish availability, entitlement, or inference success.
2. **Single agent versus three agents.** The Word prototype proposes one agent
   with two lookup tools. The implementation plan explicitly changes that to
   three collaborators plus a later account tool. This increment follows the
   plan's three-agent topology to make routing observable.
3. **Call limits are prompt rules.** Native YAML does not give this scaffold a
   deterministic per-collaborator call budget. Verify the one-call-per-specialist
   behavior in traces. A hard guarantee would need an explicit workflow later.
4. **Retrieval and tool behavior await a tenant check.** The two KBs, Markdown
   corpus, and synthetic account tool are attached. Verify citations and policy
   answers in the runtime. Unsupported questions should still refuse.
5. **Style migration.** IBM now deprecates `default` and `react`. Use `react_core`
   in all three files; ADK 2.16.1 accepts it and serializes it as
   `react_intrinsic` for the backend. Tenant compatibility still needs testing.
6. **Reasoning visibility is not tracing.** `hide_reasoning: false` retains the
   plan's UI setting. It does not enable telemetry or guarantee access to a
   model's internal reasoning. Use actual collaborator/tool spans as evidence.
7. **Tenant authentication.** The helper supports IBM Cloud and AWS SaaS API-key
   authentication. CPD/on-premises and Kubernetes authentication require a
   separate configuration path. No tenant type has been verified yet.
8. **CLI/docs mismatch for IAM URL.** Online docs show `env add --iam-url`, but
   ADK 2.16.1's installed `env add --help` does not expose it. If this tenant
   needs a custom IAM endpoint, resolve the supported registration path before
   using the helper. Do not silently guess a command flag.
9. **No runtime gate passed yet.** Agent import, deployment, route traces, and
   local Developer Edition startup await environment settings. Offline schema
   validation and mocked CLI tests are recorded separately from runtime evidence.
10. **Markdown upload compatibility.** Markdown is the authoring format. IBM
    lists `.txt` but not `.md` among built-in upload formats, so the renderer
    stages unchanged UTF-8 text copies. Hashes map uploads back to source documents.
11. **Dynamic knowledge mode.** `query_source: Agent` and disabled generation let
    the specialist compose from retrieved content. IBM says only the document
    limit and citation count apply among the generation/search settings in this
    mode; the plan's low confidence thresholds are therefore omitted.
12. **Ingestion status versus CLI success.** ADK 2.16.1 KB polling can return on
    error or timeout. The helper separately requires a ready index and the exact
    content-derived upload names before importing agents. This status check is
    based on installed client code and still needs a real tenant run.
13. **Embedding availability.** The KBs use the documented built-in default
    `ibm/slate-125m-english-rtrvr-v2`; confirm tenant support through ingestion.
    A tenant needing another model can change `vector_index` in both KB files.
14. **Deliberate conflict.** AB-005 and AB-006 disagree on refund processing time.
    Both are current with no precedence rule. Test explicit document-ID and
    natural-language queries; missing contradictory evidence is a coverage gap.
15. **Mock account scope.** The lookup is a fixed synthetic snapshot with no real
    account authorization or business-system connection. Records are excluded
    from KBs so tool-call evaluation remains meaningful.

## Later phases

- Confirm watsonx.governance monitoring availability, tenant linkage, API paths,
  metrics, and thresholds before implementing that integration.
- Add PII/runtime controls explicitly; prompt rules do not demonstrate control
  enforcement. Use synthetic data for source documents and account-tool records.
- Freeze hand-corrected evaluation cases after retrieval/tool behavior works.
  Compare multiple runs and independently check governance results.

Sources: supplied implementation plan and Word prototype;
[IBM agent styles](https://developer.watson-orchestrate.ibm.com/agents/agent_styles);
[IBM environment documentation](https://developer.watson-orchestrate.ibm.com/environment/initiate_environment);
the installed ADK source and CLI help recorded in [cli-surface.md](cli-surface.md).
