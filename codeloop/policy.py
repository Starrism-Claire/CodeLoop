from __future__ import annotations

import os
import re
from pathlib import Path

from .models import TaskState, ToolCall


class PolicyError(ValueError):
    pass


class RuntimePolicy:
    def __init__(
        self,
        workspace: str | Path,
        max_steps: int = 30,
        command_timeout: int = 10,
        max_tool_output_chars: int = 12000,
        repeated_failure_limit: int = 2,
    ) -> None:
        self.workspace = Path(workspace).resolve()
        self.max_steps = max_steps
        self.command_timeout = command_timeout
        self.max_tool_output_chars = max_tool_output_chars
        self.repeated_failure_limit = repeated_failure_limit

    def ensure_workspace(self) -> None:
        self.workspace.mkdir(parents=True, exist_ok=True)

    def resolve_workspace_path(self, user_path: str | None = ".") -> Path:
        raw = user_path or "."
        candidate = (self.workspace / raw).resolve()
        if candidate != self.workspace and self.workspace not in candidate.parents:
            raise PolicyError(f"path escapes workspace: {raw}")
        return candidate

    def relative_path(self, path: Path) -> str:
        return path.resolve().relative_to(self.workspace).as_posix()

    def validate_tool_call(self, call: ToolCall) -> None:
        allowed = {"list_files", "read_file", "write_file", "search_code", "apply_patch", "run_command"}
        if call.name not in allowed:
            raise PolicyError(f"unknown tool: {call.name}")

        if call.name in {"list_files", "read_file", "write_file"}:
            self.resolve_workspace_path(call.arguments.get("path", "."))

        if call.name == "apply_patch":
            self._validate_patch_paths(str(call.arguments.get("patch", "")))

        if call.name == "run_command":
            self.validate_command(str(call.arguments.get("command", "")))

    def validate_command(self, command: str) -> None:
        if not command.strip():
            raise PolicyError("empty command")
        lowered = command.lower()
        dangerous = [
            "rm ",
            "del ",
            "rmdir ",
            "remove-item",
            "format ",
            "shutdown",
            "curl ",
            "wget ",
            "invoke-webrequest",
            "start-process",
        ]
        if any(token in lowered for token in dangerous):
            raise PolicyError(f"dangerous command rejected: {command}")
        if re.search(r"(\|\|\s*true|\bor\s+true\b)", lowered):
            raise PolicyError("commands may not hide failures with || true")
        if re.search(r"(^|[\\/\s])\.\.([\\/\s]|$)", command):
            raise PolicyError("commands may not reference parent paths")
        if re.search(r"\b(cd|pushd|popd)\b", lowered):
            raise PolicyError("directory-changing commands are not allowed")
        if re.match(r"\s*(cat|head|tail|more|type|get-content)\b", lowered):
            raise PolicyError("use read_file instead of shell commands to read files")

    def is_validation_command(self, command: str) -> bool:
        lowered = command.lower().strip()
        validation_patterns = [
            r"(^|\s)pytest(\s|$)",
            r"(^|\s)python(?:3)?\s+-m\s+pytest(\s|$)",
            r"(^|\s)python(?:3)?\s+-m\s+unittest(\s|$)",
            r"(^|\s)python(?:3)?\s+-c\s+",
            r"(^|\s)npm\s+test(\s|$)",
            r"(^|\s)npm\s+run\s+test(\s|$)",
            r"(^|\s)cargo\s+test(\s|$)",
            r"(^|\s)go\s+test(\s|$)",
        ]
        return any(re.search(pattern, lowered) for pattern in validation_patterns)

    def check_step_limit(self, state: TaskState) -> None:
        if state.current_step >= self.max_steps:
            raise PolicyError(f"MAX_STEPS reached ({self.max_steps})")

    def can_terminate(self, state: TaskState) -> tuple[bool, str]:
        if state.has_modified_code and not state.has_validated:
            return False, "Code was modified, but no successful validation has run yet."
        return True, "ok"

    def record_action_result(self, state: TaskState, call: ToolCall, ok: bool, signature: str) -> str | None:
        state.recent_actions.append(signature)
        state.recent_actions = state.recent_actions[-10:]
        if ok:
            state.failed_actions.pop(signature, None)
            return None
        state.failed_actions[signature] = state.failed_actions.get(signature, 0) + 1
        if state.failed_actions[signature] >= self.repeated_failure_limit:
            return (
                f"Repeated failure detected for {call.name}. Inspect the error_type/message, "
                "read relevant files if needed, and change the tool arguments before retrying."
            )
        return None

    def truncate(self, value: str) -> tuple[str, bool]:
        if len(value) <= self.max_tool_output_chars:
            return value, False
        return value[: self.max_tool_output_chars] + "\n...[truncated]", True

    def _validate_patch_paths(self, patch: str) -> None:
        for line in patch.splitlines():
            for marker in ("*** Add File: ", "*** Update File: ", "*** Delete File: "):
                if line.startswith(marker):
                    self.resolve_workspace_path(line[len(marker) :].strip())


def default_workspace() -> Path:
    return Path(os.environ.get("CODELOOP_WORKSPACE", "workspace")).resolve()
