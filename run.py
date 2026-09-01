from __future__ import annotations

import argparse
import json
from pathlib import Path

from codeloop.config import load_llm_config
from codeloop.controller import AgentController
from codeloop.llm import HeuristicDemoLLMClient, OpenAICompatibleLLMClient


def main() -> None:
    parser = argparse.ArgumentParser(description="Run CodeLoop against the current workspace.")
    parser.add_argument("-t", "--task", required=True, help="Natural-language programming task.")
    parser.add_argument("-w", "--workspace", default="workspace/current", help="Sandbox workspace directory.")
    parser.add_argument("--llm", choices=["demo", "openai"], default="demo")
    parser.add_argument("--model", default=None)
    parser.add_argument("--config", default="codeloop_config.json")
    parser.add_argument("--log", default=None)
    args = parser.parse_args()

    config = load_llm_config(args.config)
    llm = HeuristicDemoLLMClient() if args.llm == "demo" else OpenAICompatibleLLMClient(model=args.model, config=config)
    result = AgentController(llm=llm, workspace=Path(args.workspace), log_path=args.log).run(args.task)

    for line in result["trace"]:
        print(line)
    print(json.dumps({key: value for key, value in result.items() if key != "trace"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
