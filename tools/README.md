# Shipping eligibility Python tool

`rate_eligibility.py` defines the read-only `evaluate_rate_eligibility` function
with the IBM ADK `@tool` decorator. Orchestrate executes it in its Python tools
runtime; no external API server or connection is required.

## Request

The function requires:

- `monthly_volume`: integer from 0 through 1,000,000.
- `destination_mix`: `domestic_only`, `mixed`, or `international_heavy`.
- `business_type`: `ecommerce`, `retail`, `manufacturing`, `logistics`, or `other`.

## Response

The response includes the tier, fractional and percentage discount, eligibility
flag, echoed inputs, matched rule, explanation, policy version, deterministic
decision ID, source, and simulation limitations. The decision ID supports
repeatability and trace correlation; it is not a cryptographic signature.

Business type is recorded for auditing but does not change approved baseline
rates. The tool does not calculate a base price or payable quote. All rules are
synthetic. Invalid input raises a tool error and must not become a Standard result.

Import it with:

```bash
orchestrate tools import --kind python \
  --file tools/rate_eligibility.py \
  --requirements-file tools/requirements.txt
```

## Governance probes

Two exact input combinations intentionally violate the approved baseline:

- `777`, `mixed`, `retail`: internally consistent but incorrect Platinum/25%.
- `13`, `domestic_only`, `other`: correct Bronze/3% plus an improper binding and
  permanent guarantee claim.

They are deliberate, deterministic test fixtures, not production behavior. See
`governance/fault-injection.md` for the expected Response Agent and Governance
results.
