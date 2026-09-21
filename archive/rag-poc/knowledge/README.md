# Onboarding knowledge bases

The canonical sources are **12 Markdown documents**, six per domain, for the
fictional **Northstar Workspace** service. All policies, limits, and examples
are synthetic POC content. They describe neither IBM policy nor a real business.
The document IDs remain stable so answers can be checked against specific sources.

## Account and Billing

| ID | Source | Subject |
| --- | --- | --- |
| AB-001 | [Account setup](docs/account_billing/ab_001_account_setup.md) | Activation prerequisites; invitation expiry. |
| AB-002 | [Billing cycles](docs/account_billing/ab_002_billing_cycles.md) | Activation-based start, renewals, change effective dates. |
| AB-003 | [Payment methods](docs/account_billing/ab_003_payment_methods.md) | Supported cards, USD, failed-payment retries. |
| AB-004 | [Invoices](docs/account_billing/ab_004_invoices.md) | Invoice access and limits of the lookup tool. |
| AB-005 | [Refund policy](docs/account_billing/ab_005_refunds_policy.md) | Duplicate-charge refund review and a 7-business-day window. |
| AB-006 | [Subscription changes](docs/account_billing/ab_006_subscription_changes.md) | Plan changes, cancellation, and a conflicting 14-business-day refund window. |

## Product and Policy

| ID | Source | Subject |
| --- | --- | --- |
| PP-001 | [Product overview](docs/product_policy/pp_001_product_overview.md) | Checklist capabilities and export contents. |
| PP-002 | [Plans and limits](docs/product_policy/pp_002_plans_and_limits.md) | Starter/Growth member and workspace limits. |
| PP-003 | [Onboarding eligibility](docs/product_policy/pp_003_onboarding_eligibility.md) | Business requirements and supported regions. |
| PP-004 | [Annual billing eligibility](docs/product_policy/pp_004_annual_billing_eligibility.md) | Active Growth accounts; conditional approval. |
| PP-005 | [Service levels](docs/product_policy/pp_005_service_levels.md) | Availability and first-response targets. |
| PP-006 | [Data and terms](docs/product_policy/pp_006_data_and_terms.md) | Terms acceptance, export, and retention. |

## Build and import

```bash
make knowledge    # Offline; no model or credentials required
make validate
# After configuring the tenant and model in .env:
make import       # KBs -> readiness check -> account tool -> agents
make knowledge-status
```

IBM documents `.txt` uploads but does not list `.md` in the built-in knowledge
upload formats. `make knowledge` stages byte-for-byte UTF-8 text copies in
`.build/knowledge/documents/`, preserving Markdown headings and all source text.
It writes two ADK YAML manifests and a SHA-256 source map to
`.build/knowledge/manifest.json`. No PDF conversion dependency is needed.

**Import the rendered `.build/knowledge/*.yaml` files.** The YAML files in this
directory are source manifests with Markdown paths relative to this directory.
Rendered paths are relative to the rendered YAML file, as the ADK expects.

Upload names include a hash of the source content. A changed source gets a new
upload name, allowing the readiness check to detect an old ingested version.
Old generated copies may remain on disk but are not included in the import
manifest. Edit Markdown sources, then rebuild; do not edit the generated copies.

Re-import updates the two named KBs to this corpus. In the pinned ADK, files not
in the new manifest are removed from those KBs. Keep these KB names dedicated to
the POC. A failed import does not automatically roll back previous resources.

## What Orchestrate handles automatically

For these built-in knowledge bases, no custom embedding service, vector database,
or retrieval function is required. The sequence is:

1. **Import the knowledge base.** Our script stages the Markdown as supported text
   files and runs the ADK import. Orchestrate ingests the documents, creates their
   embeddings using the configured model, and indexes them in built-in Milvus.
2. **Wait for ingestion.** The helper checks that both indexes are ready and contain
   the current source files before importing agents.
3. **Attach by name.** The specialist's `knowledge_base` field references its
   imported KB. This reference connects the agent to knowledge; it does not upload
   documents by itself.
4. **Retrieve at runtime.** In our dynamic mode, the agent issues a search when it
   needs domain evidence. Orchestrate searches the index and returns relevant
   content; the specialist uses it to answer with citations. Greetings and
   account-tool-only questions need not search the policy corpus.

`generation.enabled: false` disables the knowledge base's separate answer-generation
step. It does **not** disable embedding or retrieval: the native specialist agent
still generates the answer. Changes to Markdown require another build/import;
there is no automatic watch or synchronization from this local directory.

Custom retrieval code would be needed if we chose a custom-search backend instead
of the built-in index. Tenant entitlements, successful ingestion, and runtime
retrieval quality still need verification on the configured environment.

## Retrieval settings

Both knowledge bases use the built-in index and the documented default embedding
model, `ibm/slate-125m-english-rtrvr-v2`. Confirm availability during tenant ingestion.
Dynamic mode (`query_source: Agent`, generation disabled) lets each specialist
retrieve evidence and compose its own answer. The configured document limit is
5 and all available citations are shown.

The plan's low retrieval/response confidence thresholds are omitted: IBM documents
those controls as ignored in dynamic mode. Do not claim they are enforced. Inspect
retrieved passages and citations in the tenant to establish actual coverage.

## Deliberate governance cases

- **Single-source facts:** invitation expiry (AB-001), Starter member limit
  (PP-002), and retention window (PP-006) each have a specific source.
- **Conflict:** AB-005 says 7 business days and AB-006 says 14 business days for
  the same approved duplicate-charge refund. Both are current and have equal
  authority. Correct behavior reports both with citations and leaves the conflict
  unresolved. This is intentional; do not silently fix it.
- **Missing information:** no source provides an enterprise-plan price or a
  disaster-recovery recovery-time objective. The agent should say it lacks that
  information, not infer a price or confuse a support target with recovery time.
- **Two-domain answer:** annual billing needs PP-004's eligibility rule and
  AB-002's timing rule. A named-account question also needs the account tool.

This README and test expectations are excluded from ingestion. Only the
explicitly listed domain documents enter the knowledge bases.

Sources for the integration format:
[IBM knowledge-base creation](https://developer.watson-orchestrate.ibm.com/knowledge_base/build_kb),
[IBM knowledge-base import](https://developer.watson-orchestrate.ibm.com/knowledge_base/deploy_kb),
and the installed ADK 2.16.1 schema and CLI.
