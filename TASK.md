# TASK.md

## Current Goal

Implement the first usable version of **CodeLoop** according to `ARCHITECTURE.md` and `AGENTS.md`.

The goal is a minimal but complete coding-agent harness that can:

1. accept a natural-language programming task;
2. inspect the workspace;
3. read and search code;
4. modify code;
5. run commands/tests;
6. observe execution results;
7. continue fixing failures;
8. finish only after successful validation.

## Phase 1 — Core Agent Loop

Implement:

- Agent Controller
- LLM Client
- Context Manager
- Tool Router
- Task State
- Runtime Policy
- Agent Loop
- `MAX_STEPS`
- basic error handling

The LLM must be able to return either:

```text
Tool Call
or
Final Answer
```

Tool results must be added back into the context for the next LLM turn.

## Phase 2 — Tools

Implement these tools:

```text
list_files
read_file
write_file
search_code
apply_patch
run_command
```

Requirements:

- all paths are restricted to `workspace/`;
- `apply_patch` is preferred for existing-file modification;
- `run_command` uses a fixed workspace directory and timeout;
- command results include exit code, stdout, and stderr.

## Phase 3 — Runtime Guarantees

Implement:

- workspace sandbox;
- path traversal protection;
- command timeout;
- repeated-failure detection;
- modification tracking;
- mandatory validation after modification.

If code was modified but no successful validation has occurred, the Agent must not terminate successfully.

## Phase 4 — Observability

Print a readable Agent Trace:

```text
[STEP]
[TOOL CALL]
[TOOL RESULT]
[RUNTIME]
[FINAL]
```

Also support optional local JSONL execution logs.

Logs must never contain secrets.

## Phase 5 — Verification

Create a small example project inside `workspace/` and verify that CodeLoop can autonomously complete a task such as:

```text
Inspect the current project, fix the bug, and run the tests.
If the tests fail, continue debugging until they pass.
```

The expected behavior is:

```text
inspect
→ locate relevant code
→ read
→ modify
→ run tests
→ observe result
→ retry if needed
→ finish
```

## Done Criteria

The MVP is complete only when:

- the Agent can finish a real programming task end-to-end;
- tool execution happens locally;
- tool errors do not crash the Agent;
- modified code is validated before completion;
- unsafe workspace access is blocked;
- infinite loops are bounded;
- the execution process is observable;
- no agent framework or hosted execution tool is used.

Do not add multi-agent systems, RAG, MCP, vector databases, or complex UI before the MVP passes all criteria above.