# CPD evaluation recovery and metrics runbook

Use these steps from Windows PowerShell at the repository root. They avoid the
dataset generation and recording commands; the ten JSON cases under
`evaluation/manual_supervisor_dataset` are already evaluation-ready.

## 1. Start with a clean evaluation environment

The current IBM ADK release still installs evaluation framework 1.5.2, which is
the version used to validate this dataset. Create a new environment so earlier
manual package edits cannot affect the run:

```powershell
py -3.12 -m venv evalenv
.\evalenv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install "ibm-watsonx-orchestrate[agentops]==2.17.0"
orchestrate --version
```

## 2. Activate the CPD environment

List the registered environments, then activate the CPD environment that holds
the deployed agents:

```powershell
orchestrate env list
orchestrate env activate <CPD_ENVIRONMENT_NAME>
```

For a private or self-signed CPD certificate, register the environment with its
CA certificate where possible:

```powershell
orchestrate env add --name cpd-eval --url "<CPD_INSTANCE_URL>" --type cpd --verify "C:\path\cpd-ca.pem"
orchestrate env activate cpd-eval
```

For a trusted internal test instance where certificate verification must be
disabled, use `--insecure` when adding the environment and set the PowerShell
environment variable with `$env:` syntax:

```powershell
$env:WO_SSL_VERIFY = "false"
orchestrate env add --name cpd-eval --url "<CPD_INSTANCE_URL>" --type cpd --insecure
orchestrate env activate cpd-eval
```

Use exactly one CPD credential method when prompted: password or API key.

## 3. Detect the UUID `KeyError` before evaluating

Run the repository diagnostic instead of parsing CLI JSON in PowerShell:

```powershell
python .\scripts\diagnose_evaluation_resources.py
```

The evaluator reads every native agent and tool before opening the dataset. In
evaluation framework 1.5.2, any agent tool UUID absent from the tools endpoint
causes a bare `KeyError('<uuid>')`. The diagnostic prints the owning agent.

If it prints `OK`, continue to step 5. If it prints `FOUND`, use step 4.

## 4. Repair the agent printed by the diagnostic

If the agent is obsolete and safe to discard, remove only that named agent:

```powershell
orchestrate agents remove --name <AGENT_NAME> --kind native
```

If the agent must remain, re-import it from its source definition after importing
its tool. Re-importing without deleting may preserve the stale UUID, so remove
the affected agent first. If it is `rate_eligibility_agent`, the supervisor also
holds its collaborator ID. Recreate both from the repository:

```powershell
orchestrate agents remove --name supervisor_agent --kind native
orchestrate agents remove --name rate_eligibility_agent --kind native
python .\scripts\manage_agents.py deploy --env-file .\.env
```

Run the diagnostic again. Do not start the evaluation until it prints `OK`:

```powershell
python .\scripts\diagnose_evaluation_resources.py
```

Removing and recreating an agent gives it a new internal ID. Update any external
monitoring or governance association that used the previous ID.

## 5. Run one smoke case

```powershell
orchestrate evaluations evaluate `
  --test-paths .\evaluation\manual_supervisor_dataset\RATE-001.json `
  --output-dir .\evaluation\output\supervisor_smoke
```

The `provider_config` deprecation warning is not a failure. A successful smoke
run writes message and metric artifacts below the output directory.

## 6. Run all ten cases

```powershell
orchestrate evaluations evaluate `
  --test-paths .\evaluation\manual_supervisor_dataset `
  --output-dir .\evaluation\output\manual_supervisor
```

The directory is `evaluation`, singular. Do not pass the CSV to `evaluate`.

## 7. Open the metrics

Find and display the generated aggregate metrics:

```powershell
$summary = Get-ChildItem `
  .\evaluation\output\manual_supervisor `
  -Recurse `
  -Filter summary_metrics.csv |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1

$summary.FullName
Import-Csv $summary.FullName | Format-Table -AutoSize
```

Per-case metric JSON and conversation traces are under the same output tree:

```powershell
Get-ChildItem .\evaluation\output\manual_supervisor -Recurse -Filter *.metrics.json
Get-ChildItem .\evaluation\output\manual_supervisor\messages -Filter *.messages.json
```

If the UUID error remains after the diagnostic prints `OK`, capture the actual
traceback to distinguish a different `KeyError`:

```powershell
orchestrate --debug evaluations evaluate `
  --test-paths .\evaluation\manual_supervisor_dataset\RATE-001.json `
  --output-dir .\evaluation\output\debug 2>&1 |
  Tee-Object .\evaluation\output\evaluation-debug.log
```
