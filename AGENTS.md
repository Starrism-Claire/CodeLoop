# AGENTS.md

## Project

Build **CodeLoop**, a lightweight coding-agent harness.

Follow `ARCHITECTURE.md` as the authoritative architecture. Do not redesign the system unless explicitly requested.

## Core Constraints

- Do not use any agent framework or agent SDK.
- Implement Agent Loop, Context, Tool Routing, Runtime Control, Error Handling, and termination logic locally.
- LLMs may only propose tool calls; local runtime executes all filesystem and shell operations.
- All file operations must remain inside `workspace/`.
- Shell commands must use timeout and safety checks.
- Prefer `apply_patch` for modifying existing files; use `write_file` mainly for file creation or justified full replacement.
- Any code modification must be followed by real execution or test validation before successful completion.
- Tool errors must be returned to the LLM as observations instead of crashing the Agent.
- Enforce `MAX_STEPS` and repeated-failure detection.
- Keep model-provider-specific code isolated in the LLM client.
- Never hard-code API keys or secrets. Read them from environment variables or ignored local config files.

## Engineering Rules

- Keep the implementation simple, modular, and easy to explain.
- Avoid unnecessary multi-agent systems, RAG, MCP, vector databases, or complex UI.
- Add or update tests for important runtime behavior.
- Run relevant tests after changes.
- Do not make unrelated refactors.
- Preserve clear Agent Trace / logging for tool calls, results, validation, and final status.

## Priority

```text
correctness
> safety
> verifiability
> simplicity
> extra features
```