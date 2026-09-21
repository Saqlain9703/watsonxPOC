# Agent handoff contracts

These JSON shapes are prompt-level contracts. watsonx Orchestrate does not
validate them as a deterministic workflow, so runtime traces must confirm them.

## Routing

| Customer intent | Specialist |
| --- | --- |
| Tier, discount, eligibility, price, or quote | `rate_eligibility_agent` |
| General shipping concept, packaging, or terminology | `general_enquiry_agent` |
| Mixed rate and general request | Rate agent; list the general part as unanswered |

The supervisor passes the original request, relevant customer context, exact
specialist name, a short routing reason, and the complete specialist result to
`response_agent`.

## Rate specialist result

```json
{
  "status": "completed | needs_clarification | tool_error | unsupported",
  "extracted_inputs": {},
  "missing_fields": [],
  "tool_result": null,
  "draft_answer": "...",
  "unanswered_parts": []
}
```

`tool_result` must be the unmodified successful Python-tool response. It stays `null`
when inputs are incomplete or the tool fails.

## General specialist result

```json
{
  "status": "completed | needs_clarification | wrong_route | unsupported",
  "answer": "...",
  "assumptions": [],
  "uncertainties": [],
  "unanswered_parts": [],
  "grounding": "none_model_reasoning"
}
```

## Response reviewer result

```json
{
  "review_status": "approved | needs_clarification | blocked | partial",
  "route_ok": true,
  "completeness": "complete | incomplete",
  "issues": [],
  "customer_answer": "Final customer-facing text"
}
```

The supervisor relays `customer_answer` unchanged. If routing or evidence is
invalid, the reviewer withholds the unsupported result and asks for clarification
or explains the limitation.
