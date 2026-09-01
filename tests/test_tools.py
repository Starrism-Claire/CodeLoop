from pathlib import Path

from codeloop.models import TaskState, ToolCall
from codeloop.policy import RuntimePolicy
from codeloop.router import ToolRouter


def test_tool_errors_are_observations(tmp_path: Path):
    router = ToolRouter(RuntimePolicy(tmp_path / "workspace"))
    state = TaskState()

    result = router.execute(ToolCall("read_file", {"path": "missing.py"}), state)

    assert result.ok is False
    assert result.error


def test_apply_patch_modifies_only_workspace_file(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "app.py").write_text("def value():\n    return 1\n", encoding="utf-8")
    router = ToolRouter(RuntimePolicy(workspace))
    state = TaskState()

    result = router.execute(
        ToolCall(
            "apply_patch",
            {
                "patch": """*** Begin Patch
*** Update File: app.py
@@
 def value():
-    return 1
+    return 2
*** End Patch"""
            },
        ),
        state,
    )

    assert result.ok is True
    assert (workspace / "app.py").read_text(encoding="utf-8") == "def value():\n    return 2\n"
    assert state.has_modified_code is True
    assert state.has_validated is False
