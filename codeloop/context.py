from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


SYSTEM_PROMPT = """You are CodeLoop's coding agent.
The runtime executes tools; you only propose tool calls or provide a final answer.

General workflow:
- For an existing project or bug-fix task, inspect the workspace, read the relevant
  source and tests, make the smallest correct change, then run validation.
- For a new-file task in an empty workspace, skip unnecessary pre-inspection when
  the goal is clear; create the needed source and tests, then validate.
- Prefer apply_patch for localized edits to existing files. Use write_file for new
  files or intentional full-file replacement.
- apply_patch only accepts this exact format:
  *** Begin Patch
  *** Update File: path/to/file.py
  @@
  -old line
  +new line
  *** End Patch
  Do not use git diff format such as ---/+++.
- Use read_file to inspect files. Do not use run_command with cat, head, tail,
  more, type, or Get-Content for file reading.
- Commands run in the workspace by default. Do not cd elsewhere, and do not use
  || true or similar constructs that hide failures.
- If later actions do not depend on earlier observations, return multiple tool
  calls in one response so they can run in order.
- If the user gives an exact validation command, use it exactly.
- If no validation command is given, choose the most relevant local test command
  from the project files and task context.
- After any code change, do not finish until validation has passed.
- If a tool or test fails, use the observed error output to change strategy and fix
  the issue before validating again.
- Do not repeat read_file for the same file unless code changed after the last
  read. Reuse the context already provided.
- If validation failed, do not rerun the same validation command until you have
  changed code. Inspect the failing source files and patch them first.
- After validation failure, avoid rereading test files without a specific reason;
  use the failure output to inspect the relevant implementation files.

Keep actions scoped to the requested task and the workspace."""


@dataclass
class ContextManager:
    user_task: str
    max_messages: int = 16
    max_observation_chars: int = 2000
    messages: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.messages.append({"role": "system", "content": SYSTEM_PROMPT})
        self.messages.append({"role": "user", "content": self.user_task})

    def add_assistant_tool_call(self, name: str, arguments: dict[str, Any]) -> None:
        self._append({"role": "assistant", "tool_call": {"name": name, "arguments": _compact_arguments(arguments)}})

    def add_assistant_final(self, answer: str) -> None:
        self._append({"role": "assistant", "content": answer})

    def add_runtime_feedback(self, message: str) -> None:
        self._append({"role": "runtime", "content": message})

    def add_tool_result(self, result: dict[str, Any]) -> None:
        text = json.dumps(result, ensure_ascii=False, indent=2)
        if len(text) > self.max_observation_chars:
            text = text[: self.max_observation_chars] + "\n...[truncated]"
        self._append({"role": "tool", "content": text})

    def snapshot(self) -> list[dict[str, Any]]:
        return list(self.messages)

    def _append(self, message: dict[str, Any]) -> None:
        self.messages.append(message)
        if len(self.messages) > self.max_messages:
            self.messages = [self.messages[0], self.messages[1], *self.messages[-(self.max_messages - 2) :]]


def _compact_arguments(arguments: dict[str, Any]) -> dict[str, Any]:
    compacted: dict[str, Any] = {}
    for key, value in arguments.items():
        if key in {"content", "patch"} and isinstance(value, str):
            compacted[key] = f"<{len(value)} chars>"
        else:
            compacted[key] = value
    return compacted
