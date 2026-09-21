# Open questions and limitations

Resolve these before a live SaaS deployment:

- Which Orchestrate tenant URL, environment type, and supported model ID will be used?
- Does the target tenant plan support the required Python tools runtime capacity?
- Are the synthetic rate thresholds and zero-volume behavior accepted for the demo?
- Should business type affect future rates, or remain audit metadata only?
- What trace retention and review criteria will be used for the POC demo?
- Which Governance metric or custom evaluator will grade the two controlled tool
  faults, and what pass/breach thresholds will be approved?

The routing and JSON handoffs are enforced through agent instructions, not a
workflow engine or typed runtime contract. The Response Agent can identify
inconsistency and missing support, but it cannot independently prove that an
ungrounded general answer is factually correct or authenticate copied tool data.
