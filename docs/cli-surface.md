# CLI and schema notes

The helper uses the installed watsonx Orchestrate ADK and CLI.

- Agent templates use the native `v1` schema and `react_core` style.
- The active Python tool uses the ADK `@tool` decorator and read-only permission.
- The renderer replaces only `${WO_AGENT_MODEL}`.
- The Python tool import runs before supporting agents; the supervisor imports last.
- Draft import and live deployment are separate commands.
- Live deployment is refused for Developer Edition.

Useful commands:

```bash
make validate
make test
make render
make import
make deploy
```

`make import` creates or updates drafts. `make deploy` re-imports the same source
and then publishes all four agents in dependency order. The Python tool executes
inside the Orchestrate tools runtime.
