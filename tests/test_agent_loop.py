from pathlib import Path

from codeloop import AgentController, LLMResponse, ScriptedLLMClient, ToolCall


def test_agent_completes_read_modify_test_loop(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "calculator.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    (workspace / "test_calculator.py").write_text(
        "from calculator import add\n\n\ndef test_adds_two_numbers():\n    assert add(2, 3) == 5\n",
        encoding="utf-8",
    )
    llm = ScriptedLLMClient(
        [
            LLMResponse.tool("list_files"),
            LLMResponse.tool("search_code", pattern="return a - b", include="*.py"),
            LLMResponse.tool("read_file", path="calculator.py"),
            LLMResponse.tool(
                "apply_patch",
                patch="""*** Begin Patch
*** Update File: calculator.py
@@
 def add(a, b):
-    return a - b
+    return a + b
*** End Patch""",
            ),
            LLMResponse.tool("run_command", command="pytest -q"),
            LLMResponse.final("Fixed and validated."),
        ]
    )

    result = AgentController(llm=llm, workspace=workspace).run("Fix the bug and run tests.")

    assert result["status"] == "completed"
    assert result["modified_files"] == ["calculator.py"]
    assert result["validation_result"] == "passed"
    assert "return a + b" in (workspace / "calculator.py").read_text(encoding="utf-8")


def test_agent_rejects_final_before_validation_then_continues(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "app.py").write_text("value = 1\n", encoding="utf-8")
    llm = ScriptedLLMClient(
        [
            LLMResponse.tool(
                "apply_patch",
                patch="""*** Begin Patch
*** Update File: app.py
@@
-value = 1
+value = 2
*** End Patch""",
            ),
            LLMResponse.final("Done."),
            LLMResponse.tool("run_command", command="python -c \"import app; assert app.value == 2\""),
            LLMResponse.final("Done after validation."),
        ]
    )

    result = AgentController(llm=llm, workspace=workspace).run("Change value.")

    assert result["status"] == "completed"
    assert any("no successful validation" in line for line in result["trace"])


def test_agent_stops_at_max_steps(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    llm = ScriptedLLMClient([LLMResponse.tool("list_files") for _ in range(5)])

    result = AgentController(llm=llm, workspace=workspace, max_steps=2).run("Loop forever.")

    assert result["status"] == "failed"
    assert any("MAX_STEPS" in line for line in result["trace"])


def test_agent_reports_repeated_failures(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    llm = ScriptedLLMClient(
        [
            LLMResponse.tool("read_file", path="missing.py"),
            LLMResponse.tool("read_file", path="missing.py"),
            LLMResponse.tool("read_file", path="missing.py"),
            LLMResponse.final("Could not fix."),
        ]
    )

    result = AgentController(llm=llm, workspace=workspace).run("Read a missing file repeatedly.")

    assert any("Repeated failure detected" in line for line in result["trace"])


def test_controller_blocks_duplicate_read_file_without_changes(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "app.py").write_text("value = 1\n", encoding="utf-8")
    llm = ScriptedLLMClient(
        [
            LLMResponse.tool("read_file", path="app.py"),
            LLMResponse.tool("read_file", path="app.py"),
            LLMResponse.final("Done."),
        ]
    )

    result = AgentController(llm=llm, workspace=workspace).run("Inspect app.py.")

    assert result["status"] == "completed"
    assert any("duplicate_read" in line for line in result["trace"])


def test_controller_blocks_duplicate_validation_without_code_change(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "test_app.py").write_text(
        "import unittest\n\n"
        "class AppTests(unittest.TestCase):\n"
        "    def test_fail(self):\n"
        "        self.assertEqual(1, 2)\n",
        encoding="utf-8",
    )
    llm = ScriptedLLMClient(
        [
            LLMResponse.tool("run_command", command="python -m unittest test_app -v"),
            LLMResponse.tool("run_command", command="python -m unittest test_app -v"),
            LLMResponse.final("Done."),
        ]
    )

    result = AgentController(llm=llm, workspace=workspace).run("Run tests.")

    assert result["status"] == "completed"
    assert any("duplicate_validation" in line for line in result["trace"])


def test_controller_guides_recovery_to_source_after_validation_failure(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "app.py").write_text("def value():\n    return 1\n", encoding="utf-8")
    (workspace / "test_app.py").write_text(
        "import unittest\n"
        "from app import value\n\n"
        "class AppTests(unittest.TestCase):\n"
        "    def test_value(self):\n"
        "        self.assertEqual(value(), 2)\n",
        encoding="utf-8",
    )
    llm = ScriptedLLMClient(
        [
            LLMResponse.tool("run_command", command="python -m unittest test_app -v"),
            LLMResponse.tool("read_file", path="test_app.py"),
            LLMResponse.tool("read_file", path="app.py"),
            LLMResponse.final("Done."),
        ]
    )

    result = AgentController(llm=llm, workspace=workspace).run("Fix failing tests.")

    assert result["status"] == "completed"
    assert any("validation_recovery_error" in line for line in result["trace"])
    assert any("[TOOL CALL] read_file {'path': 'app.py'}" in line for line in result["trace"])


def test_demo_agent_creates_calculator_project_from_scratch(tmp_path: Path):
    from codeloop.llm import HeuristicDemoLLMClient

    workspace = tmp_path / "workspace"
    task = (
        "在当前工作目录下实现一个 calculator.py，包含 add/sub/mul/div 四个函数，"
        "div 遇到除以 0 要抛出 ValueError；再写一个 test_calculator.py 用标准库 unittest "
        "覆盖这四个函数（含除零场景），最后运行测试，确保全部通过，把最终测试输出展示出来。"
    )

    result = AgentController(llm=HeuristicDemoLLMClient(), workspace=workspace).run(task)

    assert result["status"] == "completed"
    assert result["modified_files"] == ["calculator.py", "test_calculator.py"]
    assert result["validation_command"] == "python -m unittest -v"
    assert "test_div_by_zero_raises_value_error" in result["validation_output"]
    assert "def div" in (workspace / "calculator.py").read_text(encoding="utf-8")
    assert "assertRaises(ValueError)" in (workspace / "test_calculator.py").read_text(encoding="utf-8")


def test_agent_executes_batched_tools_and_auto_finalizes_after_validation(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    llm = ScriptedLLMClient(
        [
            LLMResponse.tools(
                [
                    ToolCall("write_file", {"path": "app.py", "content": "value = 2\n"}),
                    ToolCall("run_command", {"command": "python -c \"import app; assert app.value == 2\""}),
                ]
            ),
            LLMResponse.final("This should not be needed."),
        ]
    )

    result = AgentController(llm=llm, workspace=workspace).run("Create and validate app.py.")

    assert result["status"] == "completed"
    assert result["total_agent_steps"] == 1
    assert result["validation_result"] == "passed"
    assert any("controller after successful validation" in line for line in result["trace"])


def test_agent_pauses_batch_after_failure_for_recovery(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    llm = ScriptedLLMClient(
        [
            LLMResponse.tools(
                [
                    ToolCall("read_file", {"path": "missing.py"}),
                    ToolCall("write_file", {"path": "should_not_exist.py", "content": "bad = True\n"}),
                ]
            ),
            LLMResponse.tool("write_file", path="fixed.py", content="ok = True\n"),
            LLMResponse.tool("run_command", command="python -c \"import fixed; assert fixed.ok\""),
        ]
    )

    result = AgentController(llm=llm, workspace=workspace).run("Recover from a failed first action.")

    assert result["status"] == "completed"
    assert not (workspace / "should_not_exist.py").exists()
    assert any("Batch paused" in line for line in result["trace"])


def test_agent_reports_llm_errors_without_traceback(tmp_path: Path):
    class FailingLLM:
        def next_response(self, messages, tool_schemas):
            raise RuntimeError("LLM request timed out after 1s")

    workspace = tmp_path / "workspace"
    result = AgentController(llm=FailingLLM(), workspace=workspace).run("Do work.")

    assert result["status"] == "failed"
    assert any("LLM request timed out" in line for line in result["trace"])


def test_controller_runs_explicit_validation_after_unvalidated_final(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    llm = ScriptedLLMClient(
        [
            LLMResponse.tool(
                "write_file",
                path="test_app.py",
                content=(
                    "import unittest\n\n"
                    "class AppTests(unittest.TestCase):\n"
                    "    def test_ok(self):\n"
                    "        self.assertTrue(True)\n"
                ),
            ),
            LLMResponse.final("Done."),
        ]
    )

    result = AgentController(llm=llm, workspace=workspace).run(
        "Create a test file and finally run: python -m unittest test_app -v"
    )

    assert result["status"] == "completed"
    assert result["validation_command"] == "python -m unittest test_app -v"
    assert any("Auto-running validation command" in line for line in result["trace"])


def test_controller_replaces_guessed_validation_with_user_command(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    llm = ScriptedLLMClient(
        [
            LLMResponse.tools(
                [
                    ToolCall("write_file", {"path": "test_todo.py", "content": "import unittest\n"}),
                    ToolCall("run_command", {"command": "python3 -m unittest test_todo -v"}),
                ]
            ),
        ]
    )

    result = AgentController(llm=llm, workspace=workspace).run(
        "Create tests. Finally run: python -m unittest test_todo -v"
    )

    assert result["validation_command"] == "python -m unittest test_todo -v"
    assert any("Replacing validation command" in line for line in result["trace"])


def test_controller_does_not_treat_file_display_as_validation(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "test_app.py").write_text(
        "import unittest\n\n"
        "class AppTests(unittest.TestCase):\n"
        "    def test_ok(self):\n"
        "        self.assertTrue(True)\n",
        encoding="utf-8",
    )
    llm = ScriptedLLMClient(
        [
            LLMResponse.tool("run_command", command="type test_app.py"),
            LLMResponse.tool("run_command", command="python -m unittest test_app -v"),
        ]
    )

    result = AgentController(llm=llm, workspace=workspace).run("Run the tests.")

    assert result["status"] == "completed"
    assert result["validation_command"] == "python -m unittest test_app -v"
    assert any("use read_file instead" in line for line in result["trace"])


def test_controller_infers_unittest_command_for_natural_language_task(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "test_dijkstra.py").write_text(
        "import unittest\n\n"
        "class DijkstraTests(unittest.TestCase):\n"
        "    def test_ok(self):\n"
        "        self.assertTrue(True)\n",
        encoding="utf-8",
    )
    llm = ScriptedLLMClient(
        [
            LLMResponse.tool("write_file", path="dijkstra.py", content="value = 1\n"),
            LLMResponse.final("Fixed."),
        ]
    )

    result = AgentController(llm=llm, workspace=workspace).run(
        "这个项目里的 Dijkstra 最短路径实现好像有问题，帮我检查并修复一下。修好后把相关测试跑通，并告诉我测试结果。"
    )

    assert result["status"] == "completed"
    assert result["validation_command"] == "python -m unittest test_dijkstra -v"
    assert any("Auto-running validation command" in line for line in result["trace"])
