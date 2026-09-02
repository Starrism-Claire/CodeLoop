# CodeLoop

CodeLoop 是轻量级本地编程智能体实验项目。它不使用 Agent Framework 或 Agent SDK，而是在本地实现 Agent Loop、Context、Tool Router、运行策略、错误处理、终止控制和工具执行。LLM 只提出工具调用，具体动作由本地 Runtime 执行。

## 运行

进入项目目录：

```bash
cd F:\CodeLoop
```

运行测试：

```bash
pytest -q
```

通用任务：

```bash
python run.py -t "修复当前项目的问题并运行测试" -w workspace/my_project --llm demo
```

OpenAI 兼容 API：

```bash
python run.py -t "完成指定编程任务并运行测试" -w workspace/my_project --llm openai --config codeloop_config.json
```

内置 demo：

```bash
python workspace/run_demo.py
```

## 特色

### 核心设计理念

CodeLoop 采用明确的职责分离：**LLM 提议 → Runtime 验证 → 工具执行 → 结果反馈**

- LLM 仅提出工具调用建议，不能直接操作文件或执行命令
- Runtime（本地运行时）负责所有决策：安全验证、约束检查、执行控制
- 每个工具调用都经过 Runtime Policy 检查，确保安全性
- 代码修改后必须验证通过才能标记任务完成

### 分层架构

| 层级     | 模块            | 职责                           |
| -------- | --------------- | ------------------------------ |
| 控制层   | Controller      | 主循环编排，状态管理，决策协调 |
| 上下文层 | Context & State | 短期记忆维护，执行状态追踪     |
| 决策层   | Policy & LLM    | 运行时约束，LLM 推理           |
| 工具层   | Router & Tools  | 工具路由，执行实现             |
| 执行层   | Workspace       | 真实环境交互（受限）           |

### 功能工具

- 支持 `list_files`、`read_file`、`write_file`、`search_code`、`apply_patch`、`run_command`
- 所有文件和命令操作限制在 `workspace/` 内
- 命令执行带超时和安全检查

### 运行时保障

- 支持一次 LLM 响应中连续执行多个工具调用
- 修改代码后强制执行验证（如运行测试）
- 验证通过后由 Controller 自动标记任务完成
- 检测重复失败的工具调用，防止无限循环
- 完整的 Agent Trace 记录，可追踪每一步的耗时和结果

## 说明

`workspace/` 用于放置 demo、模板和任务目录，也可以把已有项目放到这里，再在 `run_demo.py` 中填写任务说明并配置 API 后运行。`codeloop_config.json` 可保存本地 LLM 配置，但不要提交真实 API key。`AGENTS.md`、`Architecture.md` 和 `TASK.md` 是搭建辅助文档，不是普通任务必须读取的上下文。
