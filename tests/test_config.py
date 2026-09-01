from pathlib import Path

from codeloop.config import load_llm_config
from codeloop.llm import OpenAICompatibleLLMClient


def test_loads_llm_config_file(tmp_path: Path):
    config_path = tmp_path / "codeloop_config.json"
    config_path.write_text(
        """
{
  "llm": {
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "api_key": "test-key",
    "model": "qwen-plus",
    "timeout": 30
  }
}
""",
        encoding="utf-8",
    )

    config = load_llm_config(config_path)

    assert config.base_url == "https://dashscope.aliyuncs.com/compatible-mode/v1"
    assert config.api_key == "test-key"
    assert config.model == "qwen-plus"
    assert config.timeout == 30


def test_openai_client_prefers_config_values():
    config = load_llm_config(None)
    client = OpenAICompatibleLLMClient(
        config=config.__class__(
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            api_key="test-key",
            model="qwen-plus",
        )
    )

    assert client.base_url == "https://dashscope.aliyuncs.com/compatible-mode/v1"
    assert client.api_key == "test-key"
    assert client.model == "qwen-plus"
