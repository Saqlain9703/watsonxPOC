# Manual supervisor evaluation dataset

This directory contains ten hand-authored ADK 2.x ground-truth cases. Pass the
directory directly to `orchestrate evaluations evaluate`; do not run
`evaluations generate` or `evaluations record` first.

Each JSON file contains:

- `agent`: deployed agent name (`supervisor_agent`)
- `starting_sentence`: first simulated customer message
- `story`: context supplied to the evaluation user simulator
- `max_user_turns`: one turn for these deterministic cases
- `goals`: expected call and response order as a directed graph
- `goal_details`: expected collaborator calls, eligibility-tool arguments, and
  final reference response

`{"IGNORE": null}` intentionally ignores dynamic collaborator-handoff arguments.
The eligibility tool arguments remain exact and are evaluated.

## Included cases

| Case | Expected behavior |
| --- | --- |
| RATE-001 | Platinum / 18% |
| RATE-002 | Gold / 10% |
| RATE-003 | Silver / 6% |
| RATE-004 | Bronze / 3% |
| CLAR-001 | Ask for all missing eligibility inputs; no eligibility tool call |
| GEN-002 | Route actual-versus-volumetric-weight question to general enquiry |
| GEN-003 | Route packaging question to general enquiry |
| QUOTE-001 | Return simulated eligibility and explain that no final price is available |
| G-001 | Deliberate correctness probe; Gold / 10% is ground truth while the tool returns Platinum / 25% |
| G-002 | Reviewer must remove the tool's binding/permanent guarantee claim |

## Run

```bash
orchestrate evaluations evaluate \
  --test-paths evaluation/manual_supervisor_dataset \
  --output-dir evaluation/output/manual_supervisor
```

For PowerShell, replace each trailing `\` with a backtick.

For CPD setup, UUID `KeyError` recovery, a one-case smoke run, and commands to
open `summary_metrics.csv`, follow
[`docs/cpd-evaluation-recovery.md`](../../docs/cpd-evaluation-recovery.md).
