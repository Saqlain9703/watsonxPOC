# Local validation of the initial agents

Date: 2026-09-16. Python 3.12.13; IBM watsonx Orchestrate ADK 2.16.1.

## Completed

- All three source YAML files validate using the installed IBM `Agent` schema.
- Rendered files round-trip through `Agent.from_spec` using a synthetic model
  string for the offline test. This is not a model-availability check.
- `make test`: **11 tests passed**. Checks cover the collaborator graph, unknown
  fields, unresolved placeholders, rendered YAML, dotenv handling, secret
  redaction in helper output/errors, stopping after an import failure, and
  dependency ordering for import and live deployment.
- `make import` and `make render` with the provided placeholders stop with
  `Set WO_AGENT_MODEL in .env or your shell; it is missing or still a placeholder.`
  No environment registration or tenant operation is reached.
- Shell wrappers pass `bash -n`; Python scripts pass bytecode compilation.
- CLI help was verified as described in `docs/cli-surface.md`.

The deployment-order tests mock the CLI; they do not publish agents.

## Awaiting environment configuration

- Supported model selection on the actual tenant.
- Draft import and live deployment.
- Runtime first-route accuracy, completeness fallback, and collaborator call
  limits, using `docs/smoke-tests.md`.
- Developer Edition startup and telemetry, if the local path is used.

The implementation plan's runtime exit gates are not yet passed. Add actual
tenant screenshots/traces here after running the initial checks.
