from __future__ import annotations
import subprocess
from pathlib import Path
from typing import Sequence
from tools.registry import ToolResult

DEFAULT_TIMEOUT = 30


def _validate_repository(repository_root: Path) -> tuple[Path | None, ToolResult | None]:
    try:
        root = Path(repository_root).resolve()
    except Exception as exc:
        return None, ToolResult(
            success=False,
            error=f"Unable to resolve repository path: {type(exc).__name__}: {exc}",
        )

    if not root.exists():
        return None, ToolResult(
            success=False,
            error=f"Repository does not exist: {root}",
        )

    if not root.is_dir():
        return None, ToolResult(
            success=False,
            error=f"Repository path is not a directory: {root}",
        )

    git_directory = root / ".git"

    if not git_directory.exists():
        return None, ToolResult(
            success=False,
            error=f"Not a Git repository: {root}",
        )

    return root, None


def _run_git(
    repository_root: Path,
    arguments: Sequence[str],
    timeout: int = DEFAULT_TIMEOUT,
) -> ToolResult:
    root, validation_error = _validate_repository(repository_root)

    if validation_error is not None:
        return validation_error

    if not isinstance(timeout, int):
        return ToolResult(
            success=False,
            error="timeout must be an integer.",
        )

    if timeout < 1:
        return ToolResult(
            success=False,
            error="timeout must be greater than or equal to 1 second.",
        )

    command = ["git", *arguments]

    try:
        process = subprocess.run(
            command,
            cwd=root,
            shell=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )

        stdout = process.stdout or ""
        stderr = process.stderr or ""

        return ToolResult(
            success=process.returncode == 0,
            output=stdout.strip(),
            error=(
                None
                if process.returncode == 0
                else stderr.strip()
                or f"Git exited with code {process.returncode}."
            ),
            metadata={
                "command": command,
                "exit_code": process.returncode,
                "cwd": str(root),
                "timeout": timeout,
            },
        )

    except subprocess.TimeoutExpired:
        return ToolResult(
            success=False,
            error=f"Git command timed out after {timeout} seconds.",
            metadata={
                "command": command,
                "cwd": str(root),
                "timeout": timeout,
                "timed_out": True,
            },
        )

    except FileNotFoundError:
        return ToolResult(
            success=False,
            error="Git executable was not found on PATH.",
        )

    except OSError as exc:
        return ToolResult(
            success=False,
            error=f"Unable to execute Git: {exc}",
        )

    except Exception as exc:
        return ToolResult(
            success=False,
            error=(
                f"Unexpected error while executing Git: "
                f"{type(exc).__name__}: {exc}"
            ),
        )


def git_status(
    repository_root: Path,
    timeout: int = DEFAULT_TIMEOUT,
) -> ToolResult:
    return _run_git(
        repository_root,
        ["status", "--short", "--branch"],
        timeout=timeout,
    )


def git_diff(
    repository_root: Path,
    timeout: int = DEFAULT_TIMEOUT,
) -> ToolResult:
    return _run_git(
        repository_root,
        ["diff"],
        timeout=timeout,
    )


def git_log(
    repository_root: Path,
    max_entries: int = 10,
    timeout: int = DEFAULT_TIMEOUT,
) -> ToolResult:
    if not isinstance(max_entries, int):
        return ToolResult(
            success=False,
            error="max_entries must be an integer.",
        )

    if max_entries < 1:
        return ToolResult(
            success=False,
            error="max_entries must be greater than or equal to 1.",
        )

    return _run_git(
        repository_root,
        [
            "log",
            f"-n{max_entries}",
            "--oneline",
            "--decorate",
        ],
        timeout=timeout,
    )


def git_branch(
    repository_root: Path,
    timeout: int = DEFAULT_TIMEOUT,
) -> ToolResult:
    return _run_git(
        repository_root,
        ["branch", "--show-current"],
        timeout=timeout,
    )


def git_remote(
    repository_root: Path,
    timeout: int = DEFAULT_TIMEOUT,
) -> ToolResult:
    return _run_git(
        repository_root,
        ["remote", "-v"],
        timeout=timeout,
    )