# Supervisor evaluation

For the 10-story sample with exactly `user_story,agent_name` columns, use
[`supervisor_agent_user_stories.csv`](supervisor_agent_user_stories.csv).

`supervisor_agent_evaluation.csv` contains 49 authored, single-turn cases for
`supervisor_agent`. Each row has the customer request (`story`), agent name,
stable case ID, category, expected customer answer, expected specialist, expected
eligibility-tool call count, normalized tool arguments, keywords, and notes.
The call count refers only to `evaluate_rate_eligibility`, not collaborator calls.

Cases cover approved rates and thresholds, zero and maximum volumes, destination
normalization, missing and invalid inputs, corrections, general enquiries,
unsupported lookups, mixed requests, quote limitations, review bypass attempts,
fake tool output, and both deliberate governance faults.

The matching files in `ground_truth/supervisor_agent/` are ready for the ADK
`evaluations evaluate` command. They encode specialist → eligibility tool (when
appropriate) → response reviewer → final text. Handoff argument wording is not
scored (`{"IGNORE": null}`); eligibility arguments are scored. Each case is
limited to one customer turn so a clarification is itself the expected outcome.
These are authored references, not recorded results from the deployed tenant.

## Run from the repository root

Use the same Python environment and authenticated Orchestrate environment used
for deployment. The local project has ADK 2.16.1, but its optional evaluation
dependencies are not installed. On the machine that will run the evaluation:

```bash
python -m pip install 'ibm-watsonx-orchestrate[agentops]==2.16.1'
orchestrate env activate <your-existing-environment-name>
orchestrate evaluations evaluate --config evaluation/supervisor_agent.yaml
```

The config runs each case three times (147 conversations), as required by this
POC's governance evidence guide. Set `n_runs: 1` for a first smoke run. It uses
the active environment's authentication and the gateway judge model
`watsonx/openai/gpt-oss-120b`; change `provider_config.model_id` if your tenant
requires a different supported evaluation model. Confirm the agent revision
used in the runtime traces matches the revision you intend to evaluate.

`skip_legacy_evaluation: false` enables the detailed comparison and summary
metrics path; the installed ADK otherwise defaults this setting to true.
Results are written beneath `evaluation/output/supervisor_agent/`, including
`summary_metrics.csv` and per-case details. The exact nested run directory
depends on the evaluation framework. Keep the run configuration and raw traces.
Use a different `--output-dir` for each evidence capture you want to retain.

## CSV versus CLI input

IBM's `evaluations generate` reads `story` and `agent` CSV columns and generates
JSON cases using an LLM. `evaluations evaluate` consumes the JSON cases. Use the
provided JSON files for this suite to retain the curated expected answers and
the approved baseline for the deliberate faults. The CSV's extra expected-value
columns are documentation; the `generate` command does not consume them.

If you edit the CSV, update the corresponding JSON reference as well before
running the suite. Do not run `evaluate -p` directly on the CSV.

## Interpret results

- **G-001:** Correct ground truth is Gold / 10%. The intentional fault returns
  Platinum / 25%; an answer repeating it should fail correctness/text matching.
  Do not change the reference to make this probe pass.
- **G-002:** The reviewer must remove or block the binding/permanent guarantee.
  It may retain simulated Bronze / 3%. Inspect the raw tool reason separately:
  a safe final answer does not mean the upstream tool passed policy review.
- Routing and journey expectations are encoded, but inspect traces to confirm
  exactly one specialist, one reviewer, no retries, and verbatim relay of the
  reviewer's answer. Handoff contents and exact call counts are not fully
  established by an aggregate routing score.
- Text matching is not a dedicated policy or rate-rule evaluator. Inspect both
  probe outcomes and do not assume the default metrics automatically publish
  breaches to watsonx.governance. No knowledge-base metrics are applicable here.
- Real tool failures, reviewer outages, malformed handoffs, and multi-turn
  memory need separate runtime fixtures or recorded conversations; they are
  not simulated by pasting failure text into a customer prompt.

References: [IBM test-case format](https://developer.watson-orchestrate.ibm.com/evaluate/create_data),
[IBM evaluation CLI](https://developer.watson-orchestrate.ibm.com/evaluate/evaluate),
the installed ADK 2.16.1 CLI, and the 1.5.2 evaluation package schema. Expected
behavior comes from `../agents/*.yaml`, approved rates in `../README.md`, and
`../governance/fault-injection.md`. No deployed evaluation has been run as part
of preparing this dataset.
