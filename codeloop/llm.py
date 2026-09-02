from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any

from .config import LLMConfig
from .models import LLMResponse, ToolCall


class LLMClient(ABC):
    @abstractmethod
    def next_response(self, messages: list[dict], tool_schemas: list[dict]) -> LLMResponse:
        raise NotImplementedError


class ScriptedLLMClient(LLMClient):
    """Deterministic LLM double for tests and local demos."""

    def __init__(self, responses: Iterable[LLMResponse]) -> None:
        self._responses = list(responses)
        self._index = 0

    def next_response(self, messages: list[dict], tool_schemas: list[dict]) -> LLMResponse:
        if self._index >= len(self._responses):
            return LLMResponse.final("No scripted responses remain.")
        response = self._responses[self._index]
        self._index += 1
        return response


class HeuristicDemoLLMClient(LLMClient):
    """Tiny local demo policy that exercises the runtime without external APIs."""

    def __init__(self) -> None:
        self.step = 0
        self.mode: str | None = None

    def next_response(self, messages: list[dict], tool_schemas: list[dict]) -> LLMResponse:
        self.step += 1
        task_text = " ".join(str(message.get("content", "")) for message in messages if message.get("role") == "user")
        if self.mode is None:
            lowered = task_text.lower()
            if "calculator.py" in lowered and "unittest" in lowered and "div" in lowered:
                self.mode = "calculator_from_scratch"
            else:
                self.mode = "fix_sample"

        if self.mode == "calculator_from_scratch":
            return self._calculator_from_scratch_response()

        return self._fix_sample_response()

    def _fix_sample_response(self) -> LLMResponse:
        if self.step == 1:
            return LLMResponse.tool("list_files")
        if self.step == 2:
            return LLMResponse.tool("search_code", pattern="return a - b", include="*.py")
        if self.step == 3:
            return LLMResponse.tool("read_file", path="calculator.py")
        if self.step == 4:
            return LLMResponse.tool(
                "apply_patch",
                patch="""*** Begin Patch
*** Update File: calculator.py
@@
 def add(a, b):
-    return a - b
+    return a + b
*** End Patch""",
            )
        if self.step == 5:
            return LLMResponse.tool("run_command", command="pytest -q")
        return LLMResponse.final("Fixed the calculator bug and validated with tests.")

    def _calculator_from_scratch_response(self) -> LLMResponse:
        if self.step == 1:
            return LLMResponse.tools(
                [
                    ToolCall(
                        name="write_file",
                        arguments={
                            "path": "calculator.py",
                            "content": """def add(a, b):
    return a + b


def sub(a, b):
    return a - b


def mul(a, b):
    return a * b


def div(a, b):
    if b == 0:
        raise ValueError("division by zero")
    return a / b
""",
                        },
                    ),
                    ToolCall(
                        name="write_file",
                        arguments={
                            "path": "test_calculator.py",
                            "content": """import unittest

from calculator import add, div, mul, sub


class CalculatorTests(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(2, 3), 5)

    def test_sub(self):
        self.assertEqual(sub(7, 4), 3)

    def test_mul(self):
        self.assertEqual(mul(3, 4), 12)

    def test_div(self):
        self.assertEqual(div(8, 2), 4)

    def test_div_by_zero_raises_value_error(self):
        with self.assertRaises(ValueError):
            div(1, 0)


if __name__ == "__main__":
    unittest.main()
""",
                        },
                    ),
                    ToolCall(name="run_command", arguments={"command": "python -m unittest -v"}),
                ]
            )
        return LLMResponse.final("Implemented calculator.py, added unittest coverage, and validated all tests.")


class OpenAICompatibleLLMClient(LLMClient):
    """Minimal OpenAI-compatible chat completions client.

    This is intentionally only an LLM client. It parses proposed tool calls but
    never executes them; the controller still routes every action locally.
    """

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: int | None = None,
        config: LLMConfig | None = None,
    ) -> None:
        config = config or LLMConfig()
        self.model = model or config.model or os.environ.get("CODELOOP_MODEL") or os.environ.get("OPENAI_MODEL") or "gpt-4o-mini"
        self.api_key = api_key or config.api_key or os.environ.get("OPENAI_API_KEY")
        self.base_url = (base_url or config.base_url or os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
        self.timeout = timeout if timeout is not None else config.timeout
        self.temperature = config.temperature
        self.max_tokens = config.max_tokens
        self.reasoning_effort = config.reasoning_effort
        if not self.api_key:
            raise ValueError("api_key is required in codeloop_config.json or OPENAI_API_KEY")

    def next_response(self, messages: list[dict], tool_schemas: list[dict]) -> LLMResponse:
        body = {
            "model": self.model,
            "messages": _to_openai_messages(messages),
            "tools": tool_schemas,
            "tool_choice": "auto",
        }
        if self.temperature is not None:
            body["temperature"] = self.temperature
        if self.max_tokens is not None:
            body["max_tokens"] = self.max_tokens
        if self.reasoning_effort is not None:
            body["reasoning_effort"] = self.reasoning_effort
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"LLM request failed: HTTP {exc.code}: {details}") from exc
        except (TimeoutError, socket.timeout) as exc:
            raise RuntimeError(f"LLM request timed out after {self.timeout}s") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"LLM request failed: {exc.reason}") from exc

        message = payload["choices"][0]["message"]
        tool_calls = message.get("tool_calls") or []
        if tool_calls:
            calls: list[ToolCall] = []
            for raw_call in tool_calls:
                function = raw_call["function"]
                arguments = json.loads(function.get("arguments") or "{}")
                calls.append(ToolCall(name=function["name"], arguments=arguments))
            return LLMResponse.tools(calls)
        return LLMResponse.final(message.get("content") or "")


def tool_schemas() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": "list_files",
                "description": "List files inside workspace.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "default": "."},
                        "recursive": {"type": "boolean", "default": True},
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read a UTF-8 file inside workspace.",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "Create or replace a UTF-8 file inside workspace.",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                    "required": ["path", "content"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search_code",
                "description": "Search source text inside workspace.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string"},
                        "path": {"type": "string", "default": "."},
                        "include": {"type": "string", "default": "*"},
                        "max_matches": {"type": "integer", "default": 50},
                    },
                    "required": ["pattern"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "apply_patch",
                "description": (
                    "Apply a localized patch inside workspace. Use only CodeLoop patch format, not git diff. "
                    "Example: *** Begin Patch\\n*** Update File: app.py\\n@@\\n-old\\n+new\\n*** End Patch"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {"patch": {"type": "string"}},
                    "required": ["patch"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "run_command",
                "description": (
                    "Run a safe command in the workspace. Use this for tests/builds/program runs. "
                    "Do not read files with cat/head/tail/more/type/Get-Content; use read_file. "
                    "Do not cd elsewhere or use || true. If the user gives a validation command, use it exactly."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {"command": {"type": "string"}, "timeout": {"type": "integer"}},
                    "required": ["command"],
                },
            },
        },
    ]


def _to_openai_messages(messages: list[dict[str, Any]]) -> list[dict[str, str]]:
    converted: list[dict[str, str]] = []
    for message in messages:
        role = message.get("role", "user")
        if role == "runtime":
            converted.append({"role": "user", "content": f"Runtime feedback:\n{message.get('content', '')}"})
        elif role == "tool":
            converted.append({"role": "user", "content": f"Tool observation:\n{message.get('content', '')}"})
        elif "tool_call" in message:
            converted.append({"role": "assistant", "content": f"Proposed tool call: {message['tool_call']}"})
        elif role in {"system", "user", "assistant"}:
            converted.append({"role": role, "content": str(message.get("content", ""))})
    return converted
