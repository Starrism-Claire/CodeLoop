from __future__ import annotations

import json
import re
import time
from collections.abc import Callable
from pathlib import Path

from .context import ContextManager
from .llm import LLMClient, tool_schemas
from .models import TaskState, ToolCall, ToolResult
from .policy import PolicyError, RuntimePolicy
from .router import ToolRouter, action_signature


class AgentController:
    def __init__(
        self,
        llm: LLMClient,
        workspace: str | Path = "workspace",
        max_steps: int = 30,
        log_path: str | Path | None = None,
        trace_callback: Callable[[str], None] | None = None,
        auto_finalize_after_validation: bool = True,
    ) -> None:
        self.policy = RuntimePolicy(workspace=workspace, max_steps=max_steps)
        self.router = ToolRouter(self.policy)
        self.llm = llm
        self.log_path = Path(log_path) if log_path else None
        self.trace_callback = trace_callback
        self.auto_finalize_after_validation = auto_finalize_after_validation

    def run(self, task: str) -> dict:
        context = ContextManager(task)
        state = TaskState()
        trace: list[str] = []
        started_at = time.perf_counter()
        explicit_validation_command = _extract_validation_command(task)
        validation_command = explicit_validation_command or self._infer_validation_command()

        def emit(line: str) -> None:
            trace.append(line)
            if self.trace_callback:
                self.trace_callback(line)

        while state.task_status == "running":
            try:
                self.policy.check_step_limit(state)
            except PolicyError as exc:
                state.task_status = "failed"
                emit(f"[RUNTIME] {exc}")
                break

            state.current_step += 1
            emit(f"[STEP {state.current_step}]")
            llm_started_at = time.perf_counter()
            emit("[LLM CALL] requesting next action")
            try:
                response = self.llm.next_response(context.snapshot(), tool_schemas())
            except Exception as exc:
                state.task_status = "failed"
                emit(f"[LLM ERROR] {exc}")
                break
            emit(f"[LLM RESULT] received in {time.perf_counter() - llm_started_at:.3f}s")

            if response.tool_calls:
                batch_failed = False
                for call in response.tool_calls:
                    call = self._normalize_validation_call(call, state, explicit_validation_command, emit)
                    emit(f"[TOOL CALL] {call.name} {call.arguments}")
                    context.add_assistant_tool_call(call.name, call.arguments)
                    result = self._runtime_guard(call, state) or self.router.execute(call, state)
                    emit(f"[TOOL RESULT] ok={result.ok}")
                    context.add_tool_result(result.as_observation())
                    feedback = self.policy.record_action_result(state, call, result.ok, action_signature(call))
                    if feedback:
                        emit(f"[RUNTIME] {feedback}")
                        context.add_runtime_feedback(feedback)
                    self._write_log(state, call.name, result.as_observation())

                    if not result.ok:
                        batch_failed = True
                        failure_feedback = _failure_feedback(result)
                        emit(f"[RUNTIME] {failure_feedback}")
                        context.add_runtime_feedback(failure_feedback)
                        emit("[RUNTIME] Batch paused after failed tool result.")
                        break

                    if self.auto_finalize_after_validation and call.name == "run_command":
                        if not self.policy.is_validation_command(str(call.arguments.get("command", ""))):
                            emit("[RUNTIME] Command succeeded but is not a validation command; continuing.")
                            context.add_runtime_feedback(
                                "The command succeeded, but it was not a test or validation command. "
                                "Run the required validation command before finishing."
                            )
                            continue
                        allowed, reason = self.policy.can_terminate(state)
                        if allowed:
                            state.task_status = "completed"
                            emit("[FINAL] Task completed by controller after successful validation")
                            break
                        emit(f"[RUNTIME] {reason}")
                        context.add_runtime_feedback(reason)
                validation_command = explicit_validation_command or validation_command or self._infer_validation_command()
                if not batch_failed and state.task_status != "completed" and state.has_modified_code and not state.has_validated:
                    if self._run_validation(validation_command, state, context, emit):
                        continue
                continue

            final_answer = response.final_answer or ""
            context.add_assistant_final(final_answer)
            validation_command = explicit_validation_command or validation_command or self._infer_validation_command()
            if state.has_modified_code and not state.has_validated:
                if self._run_validation(validation_command, state, context, emit):
                    continue
            allowed, reason = self.policy.can_terminate(state)
            if allowed:
                state.task_status = "completed"
                emit("[FINAL] Task completed")
                break
            emit(f"[RUNTIME] {reason}")
            context.add_runtime_feedback(reason)

        if state.task_status != "completed":
            emit("[FINAL] Task failed")

        summary = {
            "status": state.task_status,
            "modified_files": sorted(state.modified_files),
            "main_changes": self._main_changes(state),
            "validation_command": state.validation_command,
            "validation_result": state.validation_result,
            "validation_output": state.validation_output,
            "validation_duration_seconds": state.validation_duration_seconds,
            "total_agent_steps": state.current_step,
            "total_duration_seconds": round(time.perf_counter() - started_at, 3),
            "trace": trace,
        }
        return summary

    def _main_changes(self, state: TaskState) -> str:
        if state.modified_files:
            return "Modified " + ", ".join(sorted(state.modified_files)) + "."
        return "No files modified."

    def _normalize_validation_call(
        self,
        call,
        state: TaskState,
        validation_command: str | None,
        emit: Callable[[str], None],
    ):
        if (
            call.name == "run_command"
            and validation_command
            and state.has_modified_code
            and str(call.arguments.get("command", "")).strip() != validation_command
        ):
            emit(f"[RUNTIME] Replacing validation command with selected command: {validation_command}")
            return ToolCall(name="run_command", arguments={"command": validation_command})
        return call

    def _run_validation(
        self,
        validation_command: str | None,
        state: TaskState,
        context: ContextManager,
        emit: Callable[[str], None],
    ) -> bool:
        if not validation_command:
            return False
        if state.last_auto_validation_version == state.modification_version:
            return False
        emit(f"[RUNTIME] Auto-running validation command: {validation_command}")
        state.last_auto_validation_version = state.modification_version
        call = ToolCall(name="run_command", arguments={"command": validation_command})
        result = self._runtime_guard(call, state) or self.router.execute(call, state)
        emit(f"[TOOL CALL] run_command {call.arguments}")
        emit(f"[TOOL RESULT] ok={result.ok}")
        context.add_tool_result(result.as_observation())
        self._write_log(state, "run_command", result.as_observation())
        if result.ok and self.auto_finalize_after_validation:
            allowed, reason = self.policy.can_terminate(state)
            if allowed:
                state.task_status = "completed"
                emit("[FINAL] Task completed by controller after successful validation")
            else:
                emit(f"[RUNTIME] {reason}")
                context.add_runtime_feedback(reason)
        elif not result.ok:
            emit("[RUNTIME] Auto-validation failed; requesting LLM repair.")
        return True

    def _infer_validation_command(self) -> str | None:
        tests = sorted(self.policy.workspace.glob("test_*.py"))
        if len(tests) == 1:
            return f"python -m unittest {tests[0].stem} -v"
        if len(tests) > 1:
            return "python -m unittest discover -v"
        return None

    def _runtime_guard(self, call: ToolCall, state: TaskState) -> ToolResult | None:
        if call.name == "read_file":
            path = str(call.arguments.get("path", ""))
            if state.read_file_versions.get(path) == state.modification_version:
                return ToolResult(
                    "read_file",
                    False,
                    error=(
                        f"{path} has already been read and no file changes happened since then. "
                        "Use the existing context, search_code, or read a changed/relevant source file."
                    ),
                    error_type="duplicate_read",
                )
            if self._after_failed_validation_without_modification(state) and not _is_relevant_source_file(path):
                return ToolResult(
                    "read_file",
                    False,
                    error=(
                        "After validation failed, read relevant source files rather than rereading tests "
                        "or unrelated files. Use the validation output to locate the failing implementation."
                    ),
                    error_type="validation_recovery_error",
                )

        if call.name == "run_command":
            command = str(call.arguments.get("command", "")).strip()
            if (
                self.policy.is_validation_command(command)
                and state.last_failed_validation_command == command
                and state.last_failed_validation_version == state.modification_version
            ):
                return ToolResult(
                    "run_command",
                    False,
                    error=(
                        "The same validation command already failed and no code has changed since then. "
                        "Inspect the failure output and modify relevant source files before rerunning validation."
                    ),
                    error_type="duplicate_validation",
                )
        return None

    def _after_failed_validation_without_modification(self, state: TaskState) -> bool:
        return (
            state.validation_result == "failed"
            and state.last_failed_validation_version == state.modification_version
        )

    def _write_log(self, state: TaskState, tool_name: str, observation: dict) -> None:
        if not self.log_path:
            return
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "step": state.current_step,
            "tool": tool_name,
            "observation": observation,
            "modified_files": sorted(state.modified_files),
            "has_validated": state.has_validated,
        }
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _extract_validation_command(task: str) -> str | None:
    commands = re.findall(r"python(?:3)?\s+-m\s+unittest(?:\s+[^\n`。；;]*)?", task)
    if commands:
        return _clean_command(commands[-1])
    commands = re.findall(r"pytest(?:\s+[^\n`。；;]*)?", task)
    if commands:
        return _clean_command(commands[-1])
    return None


def _clean_command(command: str) -> str:
    return command.strip().strip("`").strip()


def _failure_feedback(result) -> str:
    observation = result.as_observation()
    error_type = observation.get("error_type") or "tool_error"
    message = observation.get("error") or "tool failed"
    output = observation.get("output")
    stderr = ""
    if isinstance(output, dict):
        stderr = str(output.get("stderr") or "").strip()
    if stderr:
        return f"Tool failed: error_type={error_type}; message={message}; stderr={stderr}"
    return f"Tool failed: error_type={error_type}; message={message}"


def _is_relevant_source_file(path: str) -> bool:
    normalized = path.replace("\\", "/")
    name = Path(normalized).name
    if not normalized.endswith(".py"):
        return False
    if name.startswith("test_") or name.endswith("_test.py") or "/tests/" in normalized:
        return False
    return True
