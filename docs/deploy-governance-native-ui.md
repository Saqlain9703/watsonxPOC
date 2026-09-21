# Deploy, govern, and use the shipping agents

This runbook covers the SaaS POC path: deploy the four watsonx Orchestrate
agents, enable and verify monitoring, connect them to watsonx.governance, and use
the IBM native chat and dashboard interfaces.

## Platform compatibility

Orchestrate operational analytics and watsonx.governance onboarding are separate
capabilities. Orchestrate can automatically collect conversations, tokens,
latency, failures, feedback, traces, and sampled evaluations without an agent
being registered in Governance. Seeing those values under **Analyze** does not
prove that Governance monitoring or metric synchronization is configured.

IBM's public compatibility documentation currently excludes standard
on-premises deployments from the new Analytics and direct Governance-monitoring
experiences. However, privately hosted, preview, internal, or differently
packaged tenants can expose Analytics, as the target POC tenant does. Treat the
tenant UI as evidence that operational analytics is enabled, then verify
Governance integration separately by checking for a Governance asset/use case,
monitoring status, and a working Governance dashboard link.

If the tenant has operational analytics but no supported Governance connection,
collect chat transcripts, ADK evaluation output, and exported traces, then
register the governed agent and evidence manually or build a separate dashboard.
To demonstrate IBM's native automatic metrics synchronization and Governance
dashboard, use a deployment combination listed as supported for that feature or
obtain written confirmation that the tenant has it enabled.

## Current status

| Agent | YAML/ADK valid | Monitoring enabled in tenant | Linked in Governance |
| --- | --- | --- | --- |
| `rate_eligibility_agent` | Yes | Not yet verified | Not yet configured |
| `general_enquiry_agent` | Yes | Not yet verified | Not yet configured |
| `response_agent` | Yes | Not yet verified | Not yet configured |
| `supervisor_agent` | Yes | Not yet verified | Not yet configured |

`monitoring_enabled` is not an agent YAML property. Monitoring is tenant state
that is enabled after import, when each agent has an ID. The repository currently
contains environment placeholders, so it cannot query or change tenant state.
Do not treat monitoring as enabled until the GET verification below returns
`"monitoring_enabled": true` for every agent.

## 1. Prerequisites

- A watsonx Orchestrate SaaS instance and API key.
- A supported chat model in that tenant.
- Python tool execution enabled for the Orchestrate tenant/plan.
- A watsonx.governance subscription with Governance Console access.
- Orchestrate Agent Builder/Admin access and Governance owner/MRG permissions.
- Agent monitoring and Orchestrate metric synchronization available in the
  selected platform and region.

Copy `.env.example` to `.env` and replace these placeholders:

```dotenv
WO_INSTANCE_URL="https://<orchestrate-instance-api-base>"
WO_API_KEY="<orchestrate-api-key>"
WO_ENV_NAME="poc-saas"
WO_ENV_TYPE="ibm_iam"
WO_AGENT_MODEL="<provider/model-id-returned-by-make-models>"
```

Do not commit `.env`.

## 2. Validate and import drafts

From the project root:

```bash
make validate
make test
make models
```

Set `WO_AGENT_MODEL` to a model ID returned by `make models`, then run:

```bash
make render
make import
```

The helper imports resources in dependency order:

1. `evaluate_rate_eligibility` Python tool
2. Rate Eligibility Agent
3. General Enquiry Agent
4. Response Agent
5. Supervisor Agent

Confirm all four agent records and capture their IDs:

```bash
.venv/bin/orchestrate agents list --kind native --verbose
```

## 3. Test with native Orchestrate Chat

1. Open the watsonx Orchestrate instance.
2. Open **Orchestrate Chat** or the Supervisor draft preview.
3. Select `supervisor_agent` as the conversation agent.
4. Run at least these prompts:
   - `We ship 1200 parcels per month, mostly internationally, and we are an ecommerce business. What tier and discount qualify?`
   - `What is the difference between actual and volumetric weight?`
   - `What discount can my business get?`
5. Confirm the first prompt calls the eligibility tool and returns simulated
   Platinum/18%, the second uses General Enquiry without a tool, and the third
   asks for the three missing eligibility inputs.
6. Inspect the trace to confirm one specialist is selected and Response Agent
   reviews the result before the Supervisor returns the final answer.
7. Run governance probes G-001 and G-002 from
   `governance/fault-injection.md` and preserve both raw tool output and final
   response for evaluation.

Use the full cases in `docs/smoke-tests.md` before publishing.

## 4. Enable monitoring for every agent

> This section does not apply to on-premises/CPD. Do not treat a successful CPD
> agent deployment as evidence that native Governance monitoring is available.

Use the four IDs returned by `agents list --verbose`. The monitoring API requires
a bearer token accepted by the Orchestrate instance; obtain it using the tenant's
documented IBM Cloud IAM or AWS SaaS authentication flow. Keep it in a temporary
shell variable and never add it to this repository.

For each agent ID, enable monitoring:

```bash
curl --request POST \
  "<WO_INSTANCE_URL>/v1/orchestrate/monitoring/agents/<AGENT_ID>/status" \
  --header "Authorization: Bearer <WO_BEARER_TOKEN>" \
  --header "Content-Type: application/json" \
  --data '{"enable": true}'
```

Expected response:

```json
{
  "monitoring_enabled": true,
  "wxg_metrics_url": "..."
}
```

Then verify each agent independently:

```bash
curl --request GET \
  "<WO_INSTANCE_URL>/v1/orchestrate/monitoring/agents/<AGENT_ID>/status" \
  --header "Authorization: Bearer <WO_BEARER_TOKEN>"
```

Record the result for all four names. The monitoring gate passes only when every
GET response contains `"monitoring_enabled": true`. Repeat this verification
after publishing. Enabling monitoring does not itself generate metrics; run chat
traffic or evaluations so that executions exist to measure.

API references:

- [Set agent monitoring](https://developer.watson-orchestrate.ibm.com/apis/governance-monitoring/setup-agent-monitoring)
- [Get agent monitoring status](https://developer.watson-orchestrate.ibm.com/apis/governance-monitoring/get-agent-monitoring-details)

## 5. Publish the agents

After the draft chat tests pass:

```bash
make deploy
make list
```

`make deploy` re-renders and imports the current source, then deploys the three
supporting agents before the Supervisor. It is a live SaaS action. Open native
Orchestrate Chat, select `supervisor_agent`, and repeat the core smoke cases.

## 6. Connect watsonx.governance

> Use this automatic platform-connection flow only for a deployment combination
> listed as supported by the current IBM documentation. It is not the native
> integration path for the CPD environment used in this POC session.

### Software Hub/OpenPages access

An **Enabled** watsonx.governance tile in the Software Hub service catalog means
the software is installed. It does not grant a user access to its OpenPages
instance. If Governance console redirects to OpenPages and reports that the user
is not authorized, a platform/OpenPages administrator must:

1. Open **Services > Instances** and locate the instance whose name contains
   `openpages`.
2. Select **Manage access**, add the user, and grant the `OpenPagesUser` service
   role.
3. Add the user to the Governance inventory used for AI use cases.
4. Assign the appropriate OpenPages profile and application permissions. Use
   `watsonx.governance MRG Master` only when the user needs its broad
   administrative/model-risk permissions.
5. Confirm that post-installation setup enabled IBM OpenPages integration and
   associated it with the intended inventory.

The user's Software Hub platform API key does not bypass these permissions.
After access is granted, the platform API key can be exchanged for a bearer
token and the documented OpenPages REST API V2 can return authorized governance
objects and metadata as JSON.

OpenPages JSON and Orchestrate telemetry are different sources. OpenPages does
not contain Orchestrate conversation metrics unless a supported synchronization
connection or a custom ingestion process writes those records. For this CPD POC,
export Orchestrate traces separately, compute the required metrics, and either
display them in a custom dashboard or write approved summaries/evidence to
governance objects through the OpenPages API.

An administrator completes the platform connection once:

1. Open watsonx.governance **Governance Console**.
2. Go to **Integrations → Agent Platforms**.
3. Add the watsonx Orchestrate instance and authenticate it.
4. Enable the integration and confirm that its status is **Active**.

Then govern this POC:

1. Create or open a use case such as `Shipping Customer Assistance POC`.
2. Move it to the **Risk Assessment** workflow stage if the standard workflow is
   in use; this exposes **Related Assets**.
3. Under **Related Assets → Agents**, click **Import**.
4. Select the connected Orchestrate instance.
5. Import all four agents and make `supervisor_agent` the primary customer-facing
   asset in the use-case documentation.
6. Set an evaluation results sync interval. Use on-demand sync while validating
   drafts and a daily, weekly, or monthly interval for production.
7. Run the initial sync and check the scheduler/job result for failures.

References:

- [Associate Orchestrate agents with a use case](https://www.ibm.com/docs/en/watsonx/saas?topic=cases-associating-agents)
- [Configure Orchestrate metric synchronization](https://www.ibm.com/docs/en/watsonx/saas?topic=console-configuring-metrics-synchronization-watsonx-orchestrate-agents)

## 7. Configure governance evidence and thresholds

In each imported agent's task view:

1. Confirm build-time metrics are present after draft evaluation/sync.
2. For live agents, confirm production metrics appear after executions and the
   scheduled collection job runs.
3. Review the metric list supplied by the tenant. It can include answer quality,
   tool quality, transaction completion, and LLM-as-a-judge metrics.
4. Configure correctness ground truth for G-001 and a policy criterion that
   prohibits binding or permanent commercial commitments for G-002.
5. Define business thresholds for the metrics used by this POC.
6. Record an owner and remediation action for a threshold breach.
7. Preserve evaluation dates, agent versions, thresholds, and pass/breach results
   as the POC evidence pack.

Useful POC measures include routing accuracy, eligibility tool accuracy, input
accuracy, answer relevance/correctness, transaction completion, latency, and the
rate at which Response Agent blocks inconsistent results. Some domain-specific
measures require a curated evaluation set rather than automatic runtime metrics.

## 8. Use the native Governance dashboard

1. Open Governance Console with the profile assigned to this use case.
2. Open the `Shipping Customer Assistance POC` use case to see its four linked
   agents, risks, controls, evidence, and workflow status.
3. Open an agent task view to inspect build and production metrics and their
   history.
4. Add dashboard charts for the synchronized metrics and threshold status. At a
   minimum show answer quality, tool quality, transaction completion, and current
   breaches when those metrics are available in the tenant.
5. Add the use case or relevant canvas as a dashboard favorite if that feature is
   enabled for the Governance profile.

Governance synchronization is scheduled evidence collection, not a live chat
screen. Use Orchestrate Chat and traces for individual conversations; use the
Governance dashboard for aggregated quality, controls, evidence, and breaches.

## Completion checklist

- [ ] The Python tool passes ADK validation and imports successfully.
- [ ] Four agents and the Python tool are imported.
- [ ] Draft smoke cases pass through `supervisor_agent`.
- [ ] Monitoring POST succeeds for all four agent IDs.
- [ ] Monitoring GET returns `true` for all four agent IDs.
- [ ] All four agents are associated with the Governance use case.
- [ ] Initial metric sync completes successfully.
- [ ] G-001 produces a correctness breach against Gold/10% ground truth.
- [ ] G-002 records the tool-policy violation and verifies final-response filtering.
- [ ] Thresholds and breach owners are configured.
- [ ] Native Orchestrate Chat works with the Supervisor.
- [ ] Native Governance dashboard displays synchronized metrics.
- [ ] Live deployment is followed by another monitoring and smoke-test check.
