# CodeLoop Architecture

## 1. System Goal

CodeLoop is a lightweight coding-agent harness.

The LLM is responsible for reasoning and proposing actions.
The runtime is responsible for controlling, validating, executing, observing, and recording those actions.

Core principle:

```text
LLM proposes actions.
Runtime decides whether actions are allowed.
Tools interact with the real environment.
Execution results are returned to the LLM.
The loop continues until the task is safely completed.
```

The system must implement the agent runtime itself and must not depend on an external agent framework.

------

## 2. High-Level Architecture

```text
                         User Task
                            │
                            ▼
                   ┌─────────────────┐
                   │ Agent Controller│
                   └───────┬─────────┘
                           │
              ┌────────────┼──────────────┐
              ▼            ▼              ▼
       Context Manager   Task State    Runtime Policy
              │            │              │
              └────────────┼──────────────┘
                           ▼
                      LLM Client
                           │
                     Tool Call
                           │
                           ▼
                     Tool Router
                           │
          ┌────────────────┼─────────────────┐
          ▼                ▼                 ▼
      File Tools        Code Tools        Shell Tool
          │                │                 │
   list/read        search/apply_patch   run_command
          │                │                 │
          └────────────────┼─────────────────┘
                           ▼
                       Workspace
                           │
                    Tool Result
                           │
                           ▼
                    Runtime Check
                           │
                     Context Update
                           │
                           └────→ Next LLM Turn
```

------

## 3. Core Components

### Agent Controller

The central orchestrator of the system.

Responsibilities:

- receive the user task;
- initialize task state and context;
- call the LLM;
- parse tool calls;
- dispatch tools through the Tool Router;
- collect tool results;
- update context and task state;
- enforce runtime rules;
- control iteration and termination.

The Agent Controller owns the main Agent Loop.

------

### Context Manager

Maintains the short-term memory visible to the LLM.

It stores:

- system prompt;
- original user task;
- assistant messages;
- tool calls;
- tool results;
- recent execution errors;
- relevant code and execution context.

Context must remain bounded. Large tool outputs may be truncated or summarized when necessary.

------

### Task State

Stores deterministic execution state outside the LLM.

Recommended state:

```text
current_step
modified_files
has_modified_code
has_validated
recent_actions
failed_actions
task_status
```

Task State is used by the runtime to make decisions that must not depend only on the LLM.

------

### Runtime Policy

Provides deterministic constraints around model behavior.

Responsibilities:

- enforce maximum Agent steps;
- restrict filesystem access to the workspace;
- reject invalid or unsafe paths;
- enforce command timeout;
- restrict dangerous commands;
- limit tool output size;
- detect repeated failed actions;
- require validation after code modification;
- decide whether the Agent is allowed to terminate.

The runtime must never blindly trust an LLM-generated action.

------

### LLM Client

The only component responsible for communicating with the model API.

Input:

```text
Context
Tool Schemas
```

Output:

```text
Tool Call
or
Final Answer
```

The LLM Client must not directly execute files, commands, or tools.

The model provider should be replaceable without changing the Agent Controller.

------

### Tool Router

Maps an LLM tool call to the corresponding local implementation.

Example:

```text
list_files    -> File Tool
read_file     -> File Tool
search_code   -> Code Tool
apply_patch   -> Code Tool
write_file    -> File Tool
run_command   -> Shell Tool
```

Before execution, arguments must pass Runtime Policy checks.

After execution, results must be normalized before returning to the LLM.

------

## 4. Tools

### File Tools

#### `list_files`

Inspect files and directories inside the workspace.

#### `read_file`

Read the contents of a file inside the workspace.

#### `write_file`

Create a new file or replace a file when full-file writing is explicitly appropriate.

All paths must remain inside the workspace.

------

### Code Tools

#### `search_code`

Search the project by:

- function name;
- class name;
- variable name;
- keyword;
- text pattern.

Its purpose is to locate relevant code before reading many files.

#### `apply_patch`

Perform localized code modification.

Prefer `apply_patch` over rewriting an existing file because it:

- minimizes modification scope;
- reduces accidental code deletion;
- produces a clear diff;
- makes changes easier to review.

------

### Shell Tool

#### `run_command`

Execute commands inside the workspace.

Typical uses:

```text
pytest
python main.py
npm test
compiler commands
git diff
```

It must return structured execution information:

```text
command
exit_code
stdout
stderr
timeout_status
```

Commands must use a fixed workspace working directory and a timeout.

------

## 5. Agent Loop

The main execution model is:

```text
Reason
  ↓
Act
  ↓
Observe
  ↓
Reason
  ↓
...
```

Concrete control flow:

```text
1. Receive User Task
2. Add task to Context
3. Call LLM
4. If LLM returns Tool Call:
      validate action
      execute tool
      collect result
      update Task State
      update Context
      continue loop
5. If LLM returns Final Answer:
      run Runtime Check
6. If Runtime Check passes:
      finish
7. Otherwise:
      inject runtime feedback
      continue loop
```

Tool errors are observations, not fatal Agent failures.

Errors should be returned to the LLM so it can choose another strategy.

------

## 6. Mandatory Runtime Invariants

The following rules must always hold.

### Workspace Isolation

The Agent may only read or modify files inside the configured workspace.

Path traversal such as:

```text
../
../../
```

must not allow access outside the workspace.

------

### Validation After Modification

If the Agent executes:

```text
write_file
apply_patch
```

then:

```text
has_modified_code = true
has_validated = false
```

Before successful termination, the Agent must perform an appropriate execution or test.

Only after successful validation may:

```text
has_validated = true
```

If the LLM attempts to finish before validation, the Runtime must reject termination and request validation.

------

### Loop Protection

The Agent must have:

```text
MAX_STEPS
command timeout
repeated-action detection
repeated-failure detection
```

Repeated identical failed actions should produce runtime feedback instructing the model to change strategy.

------

### Tool Execution Boundary

The LLM never directly performs filesystem or shell operations.

The execution path is always:

```text
LLM
↓
Tool Call
↓
Tool Router
↓
Runtime Policy
↓
Local Tool
↓
Tool Result
↓
Context
↓
LLM
```

------

## 7. Observability

Every Agent run should produce a visible execution trace.

Recommended trace:

```text
[STEP 1]
[TOOL CALL] list_files

[STEP 2]
[TOOL CALL] search_code

[STEP 3]
[TOOL CALL] read_file

[STEP 4]
[TOOL CALL] apply_patch

[STEP 5]
[TOOL CALL] run_command
[RESULT] tests passed

[FINAL]
Task completed
```

The same execution information may also be persisted locally as structured JSONL logs.

Logs must never contain API keys, authorization headers, or other secrets.

------

## 8. Final Result

A successful task should return a concise structured summary containing:

```text
status
modified files
main changes
validation command
validation result
total Agent steps
```

Example:

```text
Task completed successfully.

Modified:
- calculator.py

Changes:
- Fixed divide() implementation.

Validation:
- pytest
- 3 tests passed

Steps:
6
```

------

## 9. Design Philosophy

CodeLoop should remain a single-agent system.

Do not introduce unnecessary:

```text
multi-agent orchestration
RAG
vector databases
MCP
planner agents
reviewer agents
complex web UI
```

unless they are explicitly required later.

Priority order:

```text
correct Agent Loop
> deterministic Runtime control
> reliable Tool execution
> validation
> error recovery
> observability
> extra features
```

CodeLoop is not primarily a code-generation wrapper.

It is a lightweight Harness that converts an LLM's probabilistic decisions into controlled, observable, executable, and verifiable software-engineering actions.