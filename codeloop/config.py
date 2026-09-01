from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class LLMConfig:
    provider: str = "openai"
    base_url: str | None = None
    api_key: str | None = None
    model: str | None = None
    timeout: int = 60
    temperature: float | None = 0
    max_tokens: int | None = 1200
    reasoning_effort: str | None = None


def load_llm_config(path: str | Path | None = "codeloop_config.json") -> LLMConfig:
    if path is None:
        return LLMConfig()

    config_path = Path(path)
    if not config_path.exists():
        return LLMConfig()

    data = json.loads(config_path.read_text(encoding="utf-8"))
    llm_data = data.get("llm", data)
    if not isinstance(llm_data, dict):
        raise ValueError("LLM config must be a JSON object")

    allowed = {"provider", "base_url", "api_key", "model", "timeout", "temperature", "max_tokens", "reasoning_effort"}
    unknown = set(llm_data) - allowed
    if unknown:
        raise ValueError(f"Unknown LLM config keys: {sorted(unknown)}")

    return LLMConfig(**_without_none(llm_data))


def _without_none(data: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in data.items() if value is not None}
