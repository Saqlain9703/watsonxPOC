# Knowledge and tool implementation checks

Date: 2026-09-16. Python 3.12.13; IBM watsonx Orchestrate ADK 2.16.1.

## Completed locally

- `make validate`: three agent templates, two knowledge-base definitions,
  12 Markdown sources, and the account tool validate successfully.
- `make knowledge`: stages both KBs with 12 text uploads and a SHA-256 manifest.
- `make test`: **27 tests passed**. Coverage includes deterministic account
  results, invalid/unknown IDs, null dates, independent response copies, ADK tool
  schema, agent dependencies, source fidelity, repeatable builds, path checks,
  dependency ordering, and stopping on incomplete or stale ingestion.
- The account tool was called locally through its actual ADK wrapper.
  ACC-0002 returned active/Growth/monthly and next billing date 2026-10-15.
- The KB import/status and Python tool import CLI flags were verified with
  installed help. The source schemas and rendered KB files load through the ADK.
- All 12 rendered upload paths resolve through the ADK's own relative-path helper;
  agent rendering was checked using a temporary synthetic model ID. Shell syntax,
  Python compilation, and local documentation links also pass.

Only synthetic account fixtures and authored POC policy were used. Deployment
order/readiness tests use mock clients. No credentials are required for these
checks, and environment placeholders remain untouched.

## Still requires the configured tenant

Actual file ingestion, embedding availability, Python-tool execution in the
remote runtime, citation rendering, first routing, completeness fallback, and
conflict/refusal behavior. No tenant import or deployment occurred in this
increment. The implementation plan's runtime gates have not passed.

Use `docs/smoke-tests.md` for prompts, expected answers, and evidence capture.
The Markdown originals and `.build/knowledge/manifest.json` identify the exact
source corpus to retain with a future runtime evaluation.
