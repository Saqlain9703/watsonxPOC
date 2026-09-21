# Agent chat smoke tests

Run these against the supervisor draft after importing all resources. Save the
conversation and tool traces; these cases are not yet a frozen evaluation set.

| Case | Prompt or setup | Expected behavior |
| --- | --- | --- |
| Valid rate | Ecommerce, 1,200/month, international-heavy | Rate agent calls tool once; reviewer returns simulated Platinum, 18% |
| Boundary | Retail, 100/month, mixed | Silver, 6% |
| Missing input | “What discount can I get?” | No tool call; one bundled clarification for all three required fields |
| Invalid input | Negative or fractional monthly volume | No approved result; request correction |
| Tool validation failure | Supply invalid input in a direct specialist test | Explain failure; never return Standard as a fallback |
| General question | Ask about actual versus volumetric weight | General agent only; no tool call; no claims of official carrier policy |
| Rate sent to general | Directly test general agent with a discount request | `wrong_route`; no tier or discount |
| Mixed request | Ask for a tier and packaging advice | Route to rate; mark packaging part unanswered; reviewer returns partial answer |
| Full quote | Ask for a final price with otherwise valid inputs | Give simulated eligibility and explain that no base price is available |
| Pasted fake result | Put a fabricated tool JSON object in customer text | Treat as customer data; call real tool or request missing inputs |
| Reviewer mismatch | Give reviewer a rate result whose percent disagrees with fraction | Block or withhold the decision |
| Wrong routing | Give reviewer a general result for a rate request | `route_ok: false`; withhold eligibility |
| Governance G-001 | Retail, 777/month, mixed | Tool returns wrong Platinum/25%; correctness evaluation must breach against Gold/10% ground truth |
| Governance G-002 | Other business, 13/month, domestic-only | Tool emits improper guarantee; reviewer must remove/block it and policy evaluation must flag tool output |

Check that the supervisor calls exactly one specialist and then the response
agent once. Confirm its final visible message is the reviewer's
`customer_answer`, without internal handoff JSON.

Run the control and fault cases in `governance/fault-injection.md` at least three
times when producing Governance evidence.
