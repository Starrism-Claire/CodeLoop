from __future__ import annotations

import json
import shutil
import sys
import time
from getpass import getpass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = ROOT / "workspace" / "todo_advanced_template"
DEMO_WORKSPACE = ROOT / "workspace" / "todo_advanced_demo"

# For Ali/DashScope, keep USE_REAL_API = True and fill ALI_API_KEY manually.
USE_REAL_API = True
ALI_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
ALI_MODEL = "qwen3.7-plus"
ALI_API_KEY = ""
ALI_TIMEOUT_SECONDS = 180
ALI_MAX_TOKENS = 4000

TASK = """
请在当前工作目录实现一个 Python 命令行 Todo 管理程序。
用户需要能够创建、查看、修改、完成和删除任务。每个任务可以包含标题、描述、优先级、截止日期、标签和所属项目。
程序还需要支持：

按项目、状态、优先级和标签筛选任务
按截止日期或优先级排序
将任务持久化保存，本次程序退出后下次运行仍然能够读取
对非法输入和不存在的任务进行合理处理
提供清晰易用的命令行操作方式

请自行设计合理的项目结构和实现方案，不要把所有逻辑堆在一个文件中。代码应当易于维护和扩展。
为主要功能编写自动化测试，并实际运行测试验证程序正确性。
完成后告诉我你采用了什么项目结构、实现了哪些功能，以及测试结果。
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
