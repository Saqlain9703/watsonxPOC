# Synthetic account-status tool

[`account_tools.py`](account_tools.py) exposes one read-only ADK tool:
`get_account_status(account_id: str) -> dict`. It requires no external service,
credentials, clock, or third-party runtime package. It is attached only to
`account_billing_agent`.

## Fixed fixture

All rows are synthetic snapshots **as of 2026-09-16 00:00 UTC**. Dates do not
advance with the clock, keeping evaluations reproducible. Do not describe these
records as live data.

| Account ID | Status | Plan | Frequency | Next billing date |
| --- | --- | --- | --- | --- |
| ACC-0001 | active | starter | monthly | 2026-10-01 |
| ACC-0002 | active | growth | monthly | 2026-10-15 |
| ACC-0003 | past_due | growth | monthly | 2026-10-05 |
| ACC-0004 | pending_activation | starter | monthly | null |

The records contain no names, emails, payment details, invoice amounts, or real
account data. They are excluded from the knowledge corpus so account-specific
questions exercise the tool rather than bypassing it through retrieval.

## Result contract

```json
{
  "found": true,
  "error": null,
  "source": "synthetic_account_fixture_v1",
  "as_of": "2026-09-16T00:00:00Z",
  "account": {
    "account_id": "ACC-0002",
    "status": "active",
    "plan": "growth",
    "billing_frequency": "monthly",
    "next_billing_date": "2026-10-15"
  }
}
```

- Malformed input returns `found: false`, `error: INVALID_ACCOUNT_ID`, and
  `account: null`. IDs must match `ACC-[0-9]{4}` exactly; no guessing or coercion.
- A well-formed unknown ID returns `ACCOUNT_NOT_FOUND` with no account data.
- A null `next_billing_date` must not be filled with a guess.
- Results are independent copies; modifying one cannot alter later calls.
- The function returns a dictionary. The ADK wrapper exposes it through
  `get_account_status(account_id="ACC-0002").content` during local tests.

## Import

`make import` handles the full dependency sequence. To import only this tool into
an already activated environment, run from the project root:

```bash
.venv/bin/orchestrate tools import --kind python \
  --file tools/account_tools.py --requirements-file tools/requirements.txt
```

The tool requirements file intentionally has no external packages. Do not send
the root CLI/development requirements file to the tool runtime.

This synthetic fixture performs no ownership checks. A production replacement
would need authenticated account access. It cannot execute subscription changes,
grant eligibility, or process payments. Record fixture/snapshot changes before
freezing a formal ground-truth dataset.
