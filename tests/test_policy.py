from pathlib import Path

import pytest

from codeloop.models import TaskState
from codeloop.policy import PolicyError, RuntimePolicy


def test_rejects_path_traversal(tmp_path: Path):
    policy = RuntimePolicy(tmp_path / "workspace")

    with pytest.raises(PolicyError):
        policy.resolve_workspace_path("../outside.txt")


def test_rejects_unsafe_command(tmp_path: Path):
    policy = RuntimePolicy(tmp_path / "workspace")

    with pytest.raises(PolicyError):
        policy.validate_command("python ../outside.py")


def test_rejects_shell_file_reading_commands(tmp_path: Path):
    policy = RuntimePolicy(tmp_path / "workspace")

    with pytest.raises(PolicyError):
        policy.validate_command("cat app.py")

    with pytest.raises(PolicyError):
        policy.validate_command("type app.py")


def test_rejects_commands_that_hide_failures(tmp_path: Path):
    policy = RuntimePolicy(tmp_path / "workspace")

    with pytest.raises(PolicyError):
        policy.validate_command("python -m unittest test_app -v || true")


def test_identifies_validation_commands(tmp_path: Path):
    policy = RuntimePolicy(tmp_path / "workspace")

    assert policy.is_validation_command("python -m unittest test_app -v")
    assert policy.is_validation_command("pytest -q")
    assert policy.is_validation_command('python -c "assert True"')
    assert not policy.is_validation_command("type test_app.py")


def test_requires_validation_after_modification(tmp_path: Path):
    policy = RuntimePolicy(tmp_path / "workspace")
    state = TaskState(has_modified_code=True, has_validated=False)

    allowed, reason = policy.can_terminate(state)

    assert allowed is False
    assert "validation" in reason
