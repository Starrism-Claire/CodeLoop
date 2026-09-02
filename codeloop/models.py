from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


TaskStatus = Literal["running", "completed", "failed"]


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LLMResponse:
    tool_calls: list[ToolCall] = field(default_factory=list)
    final_answer: str | None = None

    @property
    def tool_call(self) -> ToolCall | None:
        return self.tool_calls[0] if self.tool_calls else None

    @classmethod
    def tool(cls, name: str, **arguments: Any) -> "LLMResponse":
        return cls(tool_calls=[ToolCall(name=name, arguments=arguments)])

    @classmethod
    def tools(cls, calls: list[ToolCall]) -> "LLMResponse":
        return cls(tool_calls=calls)

    @classmethod
    def final(cls, answer: str) -> "LLMResponse":
        return cls(final_answer=answer)


@dataclass
class ToolResult:
    tool_name: str
    ok: bool
    output: Any = None
    error: str | None = None
    error_type: str | None = None

    def as_observation(self) -> dict[str, Any]:
        return {
            "tool": self.tool_name,
            "ok": self.ok,
            "output": self.output,
            "error": self.error,
            "error_type": self.error_type,
        }


@dataclass
class TaskState:
    current_step: int = 0
    modified_files: set[str] = field(default_factory=set)
    modification_version: int = 0
    has_modified_code: bool = False
    has_validated: bool = False
    recent_actions: list[str] = field(default_factory=list)
    failed_actions: dict[str, int] = field(default_factory=dict)
    task_status: TaskStatus = "running"
    validation_command: str | None = None
    validation_result: str | None = None
    validation_output: str | None = None
    validation_duration_seconds: float | None = None
    last_auto_validation_version: int | None = None
    read_file_versions: dict[str, int] = field(default_factory=dict)
    last_failed_validation_command: str | None = None
    last_failed_validation_version: int | None = None
