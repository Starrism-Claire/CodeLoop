from __future__ import annotations

import fnmatch
import subprocess
import time
from pathlib import Path
from typing import Any

from .models import ToolResult
from .policy import RuntimePolicy


class LocalTools:
    def __init__(self, policy: RuntimePolicy) -> None:
        self.policy = policy
        self.policy.ensure_workspace()

    def list_files(self, path: str = ".", recursive: bool = True) -> ToolResult:
        try:
            root = self.policy.resolve_workspace_path(path)
            if not root.exists():
                return ToolResult("list_files", False, error=f"path not found: {path}")
            if root.is_file():
                return ToolResult("list_files", True, output=[self.policy.relative_path(root)])
            pattern = "**/*" if recursive else "*"
            files = sorted(
                self.policy.relative_path(p) + ("/" if p.is_dir() else "")
                for p in root.glob(pattern)
                if not any(part.startswith(".") for part in p.relative_to(self.policy.workspace).parts)
            )
            return ToolResult("list_files", True, output=files)
        except Exception as exc:
            return ToolResult("list_files", False, error=str(exc))

    def read_file(self, path: str) -> ToolResult:
        try:
            target = self.policy.resolve_workspace_path(path)
            if not target.is_file():
                return ToolResult("read_file", False, error=f"not a file: {path}")
            return ToolResult("read_file", True, output=target.read_text(encoding="utf-8"))
        except Exception as exc:
            return ToolResult("read_file", False, error=str(exc))

    def write_file(self, path: str, content: str) -> ToolResult:
        try:
            target = self.policy.resolve_workspace_path(path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return ToolResult("write_file", True, output={"path": self.policy.relative_path(target), "bytes": len(content)})
        except Exception as exc:
            return ToolResult("write_file", False, error=str(exc))

    def search_code(self, pattern: str, path: str = ".", include: str = "*", max_matches: int = 50) -> ToolResult:
        try:
            root = self.policy.resolve_workspace_path(path)
            matches: list[dict[str, Any]] = []
            files = [root] if root.is_file() else [p for p in root.rglob("*") if p.is_file()]
            for file_path in files:
                rel = self.policy.relative_path(file_path)
                if not fnmatch.fnmatch(file_path.name, include):
                    continue
                try:
                    lines = file_path.read_text(encoding="utf-8").splitlines()
                except UnicodeDecodeError:
                    continue
                for idx, line in enumerate(lines, start=1):
                    if pattern in line:
                        matches.append({"path": rel, "line": idx, "text": line})
                        if len(matches) >= max_matches:
                            return ToolResult("search_code", True, output={"matches": matches, "truncated": True})
            return ToolResult("search_code", True, output={"matches": matches, "truncated": False})
        except Exception as exc:
            return ToolResult("search_code", False, error=str(exc))

    def apply_patch(self, patch: str) -> ToolResult:
        try:
            changed = apply_unified_patch(self.policy, patch)
            return ToolResult("apply_patch", True, output={"changed_files": changed})
        except Exception as exc:
            return ToolResult("apply_patch", False, error=str(exc))

    def run_command(self, command: str, timeout: int | None = None) -> ToolResult:
        try:
            self.policy.validate_command(command)
            started_at = time.perf_counter()
            completed = subprocess.run(
                command,
                cwd=self.policy.workspace,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout or self.policy.command_timeout,
            )
            duration_seconds = time.perf_counter() - started_at
            stdout, stdout_truncated = self.policy.truncate(completed.stdout)
            stderr, stderr_truncated = self.policy.truncate(completed.stderr)
            return ToolResult(
                "run_command",
                completed.returncode == 0,
                output={
                    "command": command,
                    "exit_code": completed.returncode,
                    "stdout": stdout,
                    "stderr": stderr,
                    "timeout": False,
                    "truncated": stdout_truncated or stderr_truncated,
                    "duration_seconds": round(duration_seconds, 3),
                },
            )
        except subprocess.TimeoutExpired as exc:
            return ToolResult(
                "run_command",
                False,
                output={"command": command, "exit_code": None, "stdout": exc.stdout or "", "stderr": exc.stderr or "", "timeout": True},
                error="command timed out",
            )
        except Exception as exc:
            return ToolResult("run_command", False, error=str(exc))


def apply_unified_patch(policy: RuntimePolicy, patch: str) -> list[str]:
    lines = patch.splitlines()
    if not lines or lines[0] != "*** Begin Patch" or lines[-1] != "*** End Patch":
        raise ValueError("patch must start with *** Begin Patch and end with *** End Patch")

    changed: list[str] = []
    index = 1
    while index < len(lines) - 1:
        line = lines[index]
        if line.startswith("*** Add File: "):
            rel = line.removeprefix("*** Add File: ").strip()
            index += 1
            new_lines: list[str] = []
            while index < len(lines) - 1 and not lines[index].startswith("*** "):
                if not lines[index].startswith("+"):
                    raise ValueError("add file lines must start with +")
                new_lines.append(lines[index][1:])
                index += 1
            target = policy.resolve_workspace_path(rel)
            if target.exists():
                raise ValueError(f"file already exists: {rel}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            changed.append(rel)
            continue

        if line.startswith("*** Delete File: "):
            rel = line.removeprefix("*** Delete File: ").strip()
            target = policy.resolve_workspace_path(rel)
            if not target.is_file():
                raise ValueError(f"file not found: {rel}")
            target.unlink()
            changed.append(rel)
            index += 1
            continue

        if line.startswith("*** Update File: "):
            rel = line.removeprefix("*** Update File: ").strip()
            target = policy.resolve_workspace_path(rel)
            original = target.read_text(encoding="utf-8")
            content_lines = original.splitlines()
            trailing_newline = original.endswith("\n")
            index += 1
            while index < len(lines) - 1 and lines[index].startswith("@@"):
                index += 1
                old_block: list[str] = []
                new_block: list[str] = []
                while index < len(lines) - 1 and not lines[index].startswith("@@") and not lines[index].startswith("*** "):
                    patch_line = lines[index]
                    if patch_line.startswith(" "):
                        old_block.append(patch_line[1:])
                        new_block.append(patch_line[1:])
                    elif patch_line.startswith("-"):
                        old_block.append(patch_line[1:])
                    elif patch_line.startswith("+"):
                        new_block.append(patch_line[1:])
                    elif patch_line == "":
                        old_block.append("")
                        new_block.append("")
                    else:
                        raise ValueError(f"invalid patch line: {patch_line}")
                    index += 1
                position = _find_block(content_lines, old_block)
                if position < 0:
                    raise ValueError(f"hunk not found in {rel}")
                content_lines = content_lines[:position] + new_block + content_lines[position + len(old_block) :]
            final = "\n".join(content_lines) + ("\n" if trailing_newline else "")
            target.write_text(final, encoding="utf-8")
            changed.append(rel)
            continue

        raise ValueError(f"unknown patch operation: {line}")

    return changed


def _find_block(lines: list[str], block: list[str]) -> int:
    if not block:
        return 0
    for index in range(0, len(lines) - len(block) + 1):
        if lines[index : index + len(block)] == block:
            return index
    return -1
