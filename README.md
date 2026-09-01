# CodeLoop

CodeLoop is a lightweight local coding-agent harness. It lets an LLM propose tool calls, while the local runtime executes file operations, patching, shell commands, validation, logging, and termination control.

The project intentionally avoids Agent Frameworks and Agent SDKs. The agent loop, context handling, tool router, runtime policy, error handling, and local tool execution are implemented directly in this repository.

## Features

- Local agent loop with bounded steps
- OpenAI-compatible LLM client
- Deterministic demo LLM client for tests and simple demos
- Workspace-restricted tools
- Tool routing for:
  - `list_files`
  - `read_file`
  - `write_file`
  - `search_code`
  - `apply_patch`
  - `run_command`
- Runtime validation after code changes
- Explicit validation command detection
- Trace logging for tool calls, results, validation, and final status

## Project Layout

```text
CodeLoop/
  codeloop/                 Core runtime package
    config.py               LLM config loading
    context.py              Agent context management
    controller.py           Agent loop and termination control
    llm.py                  Demo and OpenAI-compatible LLM clients
    models.py               Shared runtime data models
    policy.py               Workspace and command safety policy
    router.py               Tool execution router
    tools.py                Local tool implementations
  tests/                    Runtime behavior tests
  workspace/                Sandboxed task workspaces and demos
    run_demo.py             Editable demo runner
  run.py                    General CLI entrypoint
```

## Requirements

- Python 3.11+
- No third-party runtime dependency is required by CodeLoop itself
- `pytest` is used for the repository test suite

## Run Tests

```powershell
cd F:\CodeLoop
pytest -q
```

Expected result:

```text
19 passed
```

## General Usage

Use `run.py` for ordinary coding-agent tasks:

```powershell
python run.py -t "Fix the bug in the current project and run the tests." -w workspace/my_project --llm demo
```

Use an OpenAI-compatible API:

```powershell
python run.py -t "Implement the requested feature and run tests." -w workspace/my_project --llm openai --config codeloop_config.json
```

The config file format is:

```json
{
  "llm": {
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "api_key": "your_api_key_here",
    "model": "qwen3.7-plus",
    "timeout": 180,
    "temperature": 0,
    "max_tokens": 4000
  }
}
```

Do not commit real API keys. Keep local secrets in ignored config files.

## Demo Runner

`workspace/run_demo.py` is a convenience script for repeatedly testing one demo task.

Current demo directories:

```python
TEMPLATE_DIR = ROOT / "workspace" / "todo_advanced_template"
DEMO_WORKSPACE = ROOT / "workspace" / "todo_advanced_demo"
```

Meaning:

- `TEMPLATE_DIR` is the clean starting point copied before each run
- `DEMO_WORKSPACE` is the runtime workspace where the agent edits files

Run it with:

```powershell
python workspace/run_demo.py
```

After a run, the trace log is saved at:

```text
workspace/todo_advanced_demo/codeloop-trace.jsonl
```

## Safety Model

CodeLoop restricts file and command operations to the configured workspace. The LLM does not directly execute filesystem or shell actions. It can only propose tool calls; the local runtime validates and executes those calls.

Any code modification must be followed by real validation before the controller can mark the task completed.

## Notes

- `ARCHITECTURE.md`, `AGENTS.md`, and `TASK.md` are project guidance documents for building CodeLoop itself.
- They are not automatically required as context for every coding task handled by the agent.
- For repeatable demos, keep a clean template directory and let the agent work only in the copied demo workspace.
