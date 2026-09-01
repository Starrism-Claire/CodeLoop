from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import load_llm_config
from .controller import AgentController
from .llm import HeuristicDemoLLMClient, OpenAICompatibleLLMClient


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the CodeLoop MVP harness.")
    parser.add_argument("task", nargs="?", default="Inspect the project, fix the bug, and run the tests.")
    parser.add_argument("--workspace", default="workspace/sample_project")
    parser.add_argument("--log", default=None)
    parser.add_argument("--reset-sample", action="store_true", help="Reset the bundled sample project to its buggy state before running.")
    parser.add_argument("--llm", choices=["demo", "openai"], default="demo")
    parser.add_argument("--model", default=None)
    parser.add_argument("--config", default="codeloop_config.json")
    args = parser.parse_args()

    workspace = Path(args.workspace)
    if args.reset_sample:
        workspace.mkdir(parents=True, exist_ok=True)
        (workspace / "calculator.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
        (workspace / "test_calculator.py").write_text(
            "from calculator import add\n\n\n"
            "def test_adds_two_numbers():\n"
            "    assert add(2, 3) == 5\n",
            encoding="utf-8",
        )

    llm_config = load_llm_config(args.config)
    llm = HeuristicDemoLLMClient() if args.llm == "demo" else OpenAICompatibleLLMClient(model=args.model, config=llm_config)
    controller = AgentController(
        llm=llm,
        workspace=workspace,
        log_path=args.log,
    )
    result = controller.run(args.task)
    for line in result["trace"]:
        print(line)
    print(json.dumps({k: v for k, v in result.items() if k != "trace"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
