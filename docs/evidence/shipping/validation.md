# Validation evidence

Validated on 2026-09-17 with Python 3.12 and IBM watsonx Orchestrate ADK 2.16.1.

- Four native agent YAML files loaded through the installed ADK schema.
- All active agents have empty knowledge bases; only Rate Eligibility has a tool.
- The read-only Python tool passed the installed IBM ADK Python-tool parser.
- Nineteen automated tests passed, covering thresholds, input validation,
  deterministic decisions, agent topology, safe rendering, and import ordering.
- The approved threshold and boundary cases passed through the ADK tool wrapper.
- `1200`, `international_heavy`, and `ecommerce` returned Platinum/18% with
  rule `INTL_1000`.
- Invalid input raises a tool error rather than silently returning Standard.
- Both deterministic governance probes returned their documented injected faults.

These checks do not exercise an LLM, tenant collaboration, or Governance metric
sync. Complete the chat and fault-injection cases before publishing live.
