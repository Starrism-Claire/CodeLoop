from __future__ import annotations

import json
import shutil
import sys
import time
from getpass import getpass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = ROOT / "workspace" / "word_count_template"
DEMO_WORKSPACE = ROOT / "workspace" / "word_count_demo"

# For Ali/DashScope, keep USE_REAL_API = True and fill ALI_API_KEY manually.
USE_REAL_API = True
ALI_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
ALI_MODEL = "qwen3.7-plus"
ALI_API_KEY = ""
ALI_TIMEOUT_SECONDS = 180
ALI_MAX_TOKENS = 4000

TASK = """
当前工作目录中有一个 Python 文本词频统计工具，可以读取文本并统计单词出现次数，同时支持通过命令行输出出现次数最多的若干单词。

现在程序存在一些问题：

1. 单词统计没有正确处理大小写和常见标点，例如 Hello、hello、hello, 应该被视为同一个单词。
2. 当要求输出的 Top N 大于实际单词数量时，程序不应该报错。
3. 新增一个 --min-count 参数，只输出出现次数不少于指定值的单词。

请检查当前项目，在现有代码结构基础上完成修复和功能扩展，不要整体重写项目。
同时检查并补充必要的自动化测试，最后实际运行测试，确认程序正确。
最后运行：python -m unittest test_wordfreq -v

完成后简要说明修改了什么，以及最终测试结果。
"""


def reset_demo_workspace() -> None:
    if DEMO_WORKSPACE.exists():
        shutil.rmtree(DEMO_WORKSPACE)
    shutil.copytree(TEMPLATE_DIR, DEMO_WORKSPACE)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.path.insert(0, str(ROOT))

    from codeloop.config import LLMConfig
    from codeloop.controller import AgentController
    from codeloop.llm import HeuristicDemoLLMClient, OpenAICompatibleLLMClient

    reset_demo_workspace()

    if USE_REAL_API:
        api_key = ALI_API_KEY or getpass("Ali API key: ")
        if not api_key:
            raise SystemExit("Fill ALI_API_KEY in workspace/run_demo.py or enter it when prompted.")
        llm = OpenAICompatibleLLMClient(
            config=LLMConfig(
                base_url=ALI_BASE_URL,
                api_key=api_key,
                model=ALI_MODEL,
                timeout=ALI_TIMEOUT_SECONDS,
                temperature=0,
                max_tokens=ALI_MAX_TOKENS,
            )
        )
        llm_mode = (
            "openai-compatible API, "
            f"base_url={ALI_BASE_URL}, model={ALI_MODEL}, timeout={ALI_TIMEOUT_SECONDS}s"
        )
    else:
        llm = HeuristicDemoLLMClient()
        llm_mode = "demo, no API key required"

    print("CodeLoop Demo")
    print("=" * 40)
    print("Task:")
    print(TASK)
    print()
    print(f"Workspace: {DEMO_WORKSPACE}")
    print(f"Template: {TEMPLATE_DIR}")
    print(f"LLM mode: {llm_mode}")
    print()

    started_at = time.perf_counter()

    def show_progress(line: str) -> None:
        elapsed = time.perf_counter() - started_at
        print(f"[{elapsed:7.2f}s] {line}", flush=True)

    controller = AgentController(
        llm=llm,
        workspace=DEMO_WORKSPACE,
        log_path=DEMO_WORKSPACE / "codeloop-trace.jsonl",
        trace_callback=show_progress,
    )

    print("Progress:")
    result = controller.run(TASK)

    print()
    print("Generated Files:")
    for path in sorted(DEMO_WORKSPACE.glob("*.py")):
        print(f"- {path.name}")

    print()
    print("Validation Output:")
    print(result.get("validation_output") or "(no validation output)")
    if result.get("validation_duration_seconds") is not None:
        print(f"Validation Duration: {result['validation_duration_seconds']:.3f}s")

    print()
    print("Final Result:")
    print(json.dumps({key: value for key, value in result.items() if key != "trace"}, ensure_ascii=False, indent=2))
    print(f"Total Duration: {result['total_duration_seconds']:.3f}s")

    print()
    print("Trace log:")
    print(DEMO_WORKSPACE / "codeloop-trace.jsonl")


if __name__ == "__main__":
    main()
