from __future__ import annotations

import json

from .models import TaskState, ToolCall, ToolResult
from .policy import PolicyError, RuntimePolicy
from .tools import LocalTools


class ToolRouter:
    def __init__(self, policy: RuntimePolicy, tools: LocalTools | None = None) -> None:
        self.policy = policy
        self.tools = tools or LocalTools(policy)

    def execute(self, call: ToolCall, state: TaskState) -> ToolResult:
        try:
            self.policy.validate_tool_call(call)
            method = getattr(self.tools, call.name)
            result = method(**call.arguments)
        except PolicyError as exc:
            result = ToolResult(call.name, False, error=str(exc), error_type="policy_error")
        except TypeError as exc:
            result = ToolResult(call.name, False, error=f"invalid arguments: {exc}", error_type="invalid_arguments")
        except Exception as exc:
            result = ToolResult(call.name, False, error=str(exc), error_type="tool_error")

        self._update_state(call, result, state)
        return result

    def _update_state(self, call: ToolCall, result: ToolResult, state: TaskState) -> None:
        if result.ok and call.name == "read_file" and "path" in call.arguments:
            state.read_file_versions[str(call.arguments["path"])] = state.modification_version

        if result.ok and call.name in {"write_file", "apply_patch"}:
            state.has_modified_code = True
            state.has_validated = False
            state.modification_version += 1
            if call.name == "write_file" and "path" in call.arguments:
                state.modified_files.add(str(call.arguments["path"]))
            if call.name == "apply_patch" and isinstance(result.output, dict):
                for path in result.output.get("changed_files", []):
                    state.modified_files.add(str(path))

        if call.name == "run_command" and result.ok:
            command = str(call.arguments.get("command", ""))
            state.validation_command = str(call.arguments.get("command", ""))
            if self.policy.is_validation_command(command):
                state.has_validated = True
                state.validation_result = "passed"
                state.last_failed_validation_command = None
                state.last_failed_validation_version = None
            else:
                state.validation_result = None
            state.validation_output = _command_output_text(result.output)
            state.validation_duration_seconds = _command_duration(result.output)
        elif call.name == "run_command":
            state.validation_command = str(call.arguments.get("command", ""))
            state.validation_result = "failed"
            state.validation_output = _command_output_text(result.output)
            state.validation_duration_seconds = _command_duration(result.output)
            if self.policy.is_validation_command(state.validation_command):
                state.last_failed_validation_command = state.validation_command
                state.last_failed_validation_version = state.modification_version


def _command_output_text(output: object) -> str | None:
    if not isinstance(output, dict):
        return None
    stdout = str(output.get("stdout") or "")
    stderr = str(output.get("stderr") or "")
    return (stdout + stderr).strip()


def _command_duration(output: object) -> float | None:
    if not isinstance(output, dict):
        return None
    value = output.get("duration_seconds")
    return float(value) if value is not None else None


def action_signature(call: ToolCall) -> str:
    return json.dumps({"name": call.name, "arguments": call.arguments}, sort_keys=True, ensure_ascii=False)
