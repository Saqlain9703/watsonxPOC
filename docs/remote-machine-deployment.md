# Deploy the shipping POC from another machine

This runbook covers the first remote phase: obtain watsonx Orchestrate SaaS
credentials, configure this project, import the Python tool and four agents as
drafts, test the customer entry point, and publish the agents.

## What must be configured

Five active values are needed for SaaS. IBM Software Hub/CPD also needs the
login username:

| Variable | Source | Example / choice |
| --- | --- | --- |
| `WO_INSTANCE_URL` | Orchestrate **Settings > API details** | Copy the complete service instance URL |
| `WO_API_KEY` | Generate from the same **API details** page | Copy it immediately and store it securely |
| `WO_ENV_NAME` | You choose this local CLI alias | `shipping-poc` |
| `WO_ENV_TYPE` | Hosting platform | `ibm_iam` for IBM Cloud; `mcsp` for AWS SaaS; `cpd` for Software Hub/CPD |
| `WO_USERNAME` | CPD user profile/login | Required only when `WO_ENV_TYPE="cpd"` |
| `WO_AGENT_MODEL` | Output of `orchestrate models list` | Use one complete provider/model ID shown by the tenant |

The `WATSONX_*` and `WXG_*` values in `.env.example` belong to the later
Governance integration phase. Leave those placeholders unchanged for this
deployment.

## 1. Transfer the project safely

Do not transfer `.venv`, `.env`, `.build`, `__pycache__`, or `.pyc` files. In
particular, do not put an API key in the zip file. Create `.env` only on the
machine that can reach the Orchestrate tenant.

A virtual environment copied from macOS/Linux cannot run on Windows and causes
`[WinError 193] %1 is not a valid Win32 application`. If `.venv` was copied,
delete it on the destination machine and recreate it there.

The active project needs these paths:

```text
agents/
tools/
scripts/
tests/
docs/
governance/
.env.example
Makefile
requirements.txt
README.md
```

The `archive/` directory contains retired API and RAG versions and is not needed
for deployment.

## 2. Find the Orchestrate URL and authentication credential

On the machine where watsonx Orchestrate is open:

1. Sign in to the watsonx Orchestrate tenant.
2. Select the user/profile icon in the upper-right corner.
3. Select **Settings**.
4. Open the **API details** tab.
5. Copy the complete **Service instance URL**. This is `WO_INSTANCE_URL`; do
   not shorten it to the browser's host name.

For IBM Cloud or AWS SaaS:

6. Select **Generate API key** on the Orchestrate API details page.
7. For an IBM Cloud tenant, the page opens IBM Cloud IAM. Select
   **Create**, enter a recognizable name such as `shipping-poc-adk`, and copy
   the generated key.
8. For an AWS SaaS tenant, generate and copy the key directly from the
   API details page. AWS tenant keys cannot be retrieved later, so save it in a
   password manager.

For IBM Cloud, use the key generated through this Orchestrate page. IBM warns
against using credentials from the IBM Cloud resource page for this ADK login.

For IBM Software Hub/Cloud Pak for Data, the credential is different:

1. Return to the parent **IBM Software Hub** page rather than Orchestrate's API
   details page.
2. Select the profile icon, then **Profile and settings**.
3. Open **API key**, select **Generate new key**, then **Generate**.
4. Copy the key immediately. This Software Hub platform key is `WO_API_KEY`.
5. Copy the exact Software Hub username shown in the same profile. This is
   `WO_USERNAME`; it might differ from the user's email or display name.

An IBM IAM key or an Orchestrate SaaS key cannot be substituted for the
Software Hub platform key in the CPD authentication flow.

Choose the authentication type:

- IBM Cloud hosted tenant: `WO_ENV_TYPE="ibm_iam"`
- AWS hosted SaaS tenant: `WO_ENV_TYPE="mcsp"`; the ADK tries MCSP v2 and then
  v1 automatically
- IBM Software Hub/Cloud Pak for Data: `WO_ENV_TYPE="cpd"` and set
  `WO_USERNAME` to the username used to sign in

## 3. Create the Python environment

Open the unzipped project folder in VS Code, then open its integrated terminal.
Python 3.12 is the tested version.

### macOS or Linux

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

### Windows PowerShell

Use WSL if available because the included Makefile and shell smoke-test script
use Bash. Native PowerShell can still run the deployment helper directly:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

If PowerShell blocks activation, invoke `.\.venv\Scripts\python.exe` in place
of `python` in the commands below and ensure the venv `Scripts` directory is on
`PATH` so the helper can find `orchestrate.exe`.

## 4. Fill `.env`

Open `.env` in VS Code and replace only the active deployment values first:

```dotenv
WO_INSTANCE_URL="https://copy-the-complete-value-from-api-details"
WO_API_KEY="copy-the-generated-key"
WO_ENV_NAME="shipping-poc"
WO_ENV_TYPE="ibm_iam"
WO_USERNAME="<required-only-for-cpd>"
WO_SKIP_VERSION_CHECK="false"
WO_AGENT_MODEL="<supported-provider/model-id>"
```

Use `mcsp` instead of `ibm_iam` for AWS SaaS. For a Software Hub/CPD URL, use
`cpd` and fill `WO_USERNAME`. Keep `.env` local: it is already ignored by the
project, and the deployment helper redacts the API key from its own command log.

Leave `WO_AGENT_MODEL` as a placeholder for the next step. All other placeholder
variables may also remain unchanged.

## 5. Connect and select a tenant-supported model

With the virtual environment active, run:

```bash
python scripts/manage_agents.py models
```

This command registers the environment, authenticates with the API key, and
runs `orchestrate models list`. Copy one complete model ID from the output into
`WO_AGENT_MODEL` in `.env`. Choose a chat model supported by `react_core` and
native tool calling. The full tenant output is authoritative; do not invent or
shorten the ID.

Run the connection check again after editing `.env`:

```bash
python scripts/manage_agents.py models
```

Remote CLI authentication expires after about two hours. The helper activates
the environment on every remote command, so rerunning it renews the session.

## 6. Validate locally before uploading

On macOS, Linux, or WSL:

```bash
make validate
make test
make render
```

On native PowerShell:

```powershell
python scripts/manage_agents.py validate
python -m unittest discover -s tests -v
python scripts/manage_agents.py render
```

`render` substitutes the selected model into copies under `.build/shipping`.
Credentials are never written into the agent YAML files.

## 7. Import drafts into Orchestrate

Import the tool and agents without publishing them:

```bash
python scripts/manage_agents.py import
```

The helper imports resources in this dependency order:

1. Python tool `evaluate_rate_eligibility`
2. `rate_eligibility_agent`
3. `general_enquiry_agent`
4. `response_agent`
5. `supervisor_agent`

The tool is uploaded from `tools/rate_eligibility.py`; it is not an API and
requires no URL, tunnel, or Orchestrate connection object.

## 8. Test the draft in the Orchestrate UI

In the Orchestrate UI:

1. Open the agent builder or agent management area.
2. Find `supervisor_agent` and open its draft/preview chat.
3. Test a general request:
   `What is the difference between volumetric weight and actual weight?`
4. Test a rate request:
   `We ship 1200 parcels monthly, mostly international, and run an ecommerce business. What tier and discount apply?`
5. Test missing fields:
   `What shipping discount can my business get?`
6. Confirm the rate path invokes `evaluate_rate_eligibility`, the general path
   does not invoke it, and both paths pass through `response_agent` before the
   final reply.

Use the additional cases in `docs/smoke-tests.md`, including the two deliberate
Governance fault probes, before publishing.

## 9. Publish all four agents

After the draft checks pass, publish the current files:

```bash
python scripts/manage_agents.py deploy
python scripts/manage_agents.py list
```

`deploy` reimports the tool and agent definitions, then publishes all four
agents. The final list should include:

```text
rate_eligibility_agent
general_enquiry_agent
response_agent
supervisor_agent
```

## Primary chat agent

`supervisor_agent` is the only customer entry point. Select it in native
Orchestrate Chat. It classifies the request, delegates to exactly one specialist,
sends the complete specialist result to `response_agent`, and returns the
reviewed answer.

The other three agents must be deployed because they are collaborators, but a
customer should not start a chat with them directly.

## Common failures

- **401/403 during activation:** generate a current key from Orchestrate
  **Settings > API details** and confirm it belongs to the same tenant as the
  service instance URL.
- **Wrong authentication flow:** use `ibm_iam` for IBM Cloud and `mcsp` for AWS
  SaaS. URLs hosted on Software Hub/CPD use `cpd` and require `WO_USERNAME`.
- **Existing environment has a different URL:** choose a new `WO_ENV_NAME`, or
  remove the old CLI alias with `orchestrate env remove -n <old-name>`.
- **Model validation or import fails:** rerun `python scripts/manage_agents.py
  models` and copy an exact available model ID.
- **An upload partially succeeds:** rerun `import`; matching tool and agent names
  are updated.
- **CPD certificate verification fails:** obtain the cluster root/intermediate CA
  bundle in PEM format from the platform administrator and update the CLI
  environment with `orchestrate env add ... --type cpd --verify <ca.pem>`. For
  an isolated POC only, the ADK also supports `--insecure`; update the existing
  environment when prompted. These options belong on `env add`, not on
  `models list` or `env activate`.
- **Python tool import fails while contacting `pypi.org`:** activate with
  `orchestrate env activate <name> --skip-version-check` and set
  `WO_SKIP_VERSION_CHECK="true"`. This skips the local ADK release lookup; it
  does not remove the ADK version from the uploaded tool requirements.
