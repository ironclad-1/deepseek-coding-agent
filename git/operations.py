from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Sequence

from tools.registry import ToolResult


DEFAULT_TIMEOUT = 30


def _validate_repository(
    repository_root: Path,
) -> tuple[Path | None, ToolResult | None]:
    try:
        root = Path(repository_root).resolve()
    except Exception as exc:
        return None, ToolResult(
            success=False,
            error=(
                f"Unable to resolve repository path: "
                f"{type(exc).__name__}: {exc}"
            ),
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


def _validate_paths(
    repository_root: Path,
    paths: Sequence[str | Path],
) -> tuple[Path | None, list[str] | None, ToolResult | None]:
    root, validation_error = _validate_repository(repository_root)

    if validation_error is not None:
        return None, None, validation_error

    if isinstance(paths, (str, Path)):
        return None, None, ToolResult(
            success=False,
            error="paths must be a sequence of file or directory paths.",
        )

    if not paths:
        return None, None, ToolResult(
            success=False,
            error="At least one path must be provided.",
        )

    relative_paths: list[str] = []

    for raw_path in paths:
        if not isinstance(raw_path, (str, Path)):
            return None, None, ToolResult(
                success=False,
                error="Every path must be a string or Path.",
            )

        path_text = str(raw_path).strip()

        if not path_text:
            return None, None, ToolResult(
                success=False,
                error="Paths cannot be empty.",
            )

        try:
            candidate = (root / path_text).resolve()

            candidate.relative_to(root)
        except ValueError:
            return None, None, ToolResult(
                success=False,
                error=(
                    f"Path is outside the repository: "
                    f"{path_text}"
                ),
            )
        except Exception as exc:
            return None, None, ToolResult(
                success=False,
                error=(
                    f"Unable to resolve path '{path_text}': "
                    f"{type(exc).__name__}: {exc}"
                ),
            )

        if candidate == root / ".git":
            return None, None, ToolResult(
                success=False,
                error="The .git directory cannot be staged.",
            )

        relative_path = candidate.relative_to(root).as_posix()

        if not relative_path:
            return None, None, ToolResult(
                success=False,
                error="The repository root cannot be staged directly.",
            )

        relative_paths.append(relative_path)

    return root, relative_paths, None


def _validate_remote(
    repository_root: Path,
    remote: str,
) -> tuple[Path | None, str | None, ToolResult | None]:
    """
    Validate that the requested remote is a configured Git remote.

    Pushes are intentionally limited to configured remote names rather
    than accepting arbitrary URLs.
    """

    if not isinstance(remote, str):
        return None, None, ToolResult(
            success=False,
            error="remote must be a string.",
        )

    remote = remote.strip()

    if not remote:
        return None, None, ToolResult(
            success=False,
            error="remote cannot be empty.",
        )

    if remote.startswith("-"):
        return None, None, ToolResult(
            success=False,
            error="remote cannot begin with '-'.",
        )

    if any(character.isspace() for character in remote):
        return None, None, ToolResult(
            success=False,
            error="remote cannot contain whitespace.",
        )

    root, validation_error = _validate_repository(
        repository_root,
    )

    if validation_error is not None:
        return None, None, validation_error

    assert root is not None

    remote_result = _run_git(
        root,
        ["remote"],
    )

    if not remote_result.success:
        return None, None, remote_result

    configured_remotes = [
        line.strip()
        for line in remote_result.output.splitlines()
        if line.strip()
    ]

    if remote not in configured_remotes:
        return None, None, ToolResult(
            success=False,
            error=(
                f"Git remote '{remote}' is not configured. "
                f"Configured remotes: "
                f"{', '.join(configured_remotes) or '(none)'}"
            ),
        )

    return root, remote, None


def _validate_branch(
    repository_root: Path,
    branch: str,
) -> tuple[Path | None, str | None, ToolResult | None]:
    """
    Validate that the requested branch is a valid local branch.
    """

    if not isinstance(branch, str):
        return None, None, ToolResult(
            success=False,
            error="branch must be a string.",
        )

    branch = branch.strip()

    if not branch:
        return None, None, ToolResult(
            success=False,
            error="branch cannot be empty.",
        )

    if branch.startswith("-"):
        return None, None, ToolResult(
            success=False,
            error="branch cannot begin with '-'.",
        )

    root, validation_error = _validate_repository(
        repository_root,
    )

    if validation_error is not None:
        return None, None, validation_error

    assert root is not None

    # Ask Git to validate the branch name rather than trying to
    # reproduce Git's complete ref-format rules ourselves.
    format_result = _run_git(
        root,
        [
            "check-ref-format",
            "--branch",
            branch,
        ],
    )

    if not format_result.success:
        return None, None, ToolResult(
            success=False,
            error=(
                f"Invalid Git branch name '{branch}': "
                f"{format_result.error or 'invalid branch name'}"
            ),
        )

    # Confirm that the branch actually exists locally.
    branch_result = _run_git(
        root,
        [
            "show-ref",
            "--verify",
            "--quiet",
            f"refs/heads/{branch}",
        ],
    )

    if not branch_result.success:
        return None, None, ToolResult(
            success=False,
            error=(
                f"Local Git branch does not exist: {branch}"
            ),
        )

    return root, branch, None


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


def git_add(
    repository_root: Path,
    paths: Sequence[str | Path],
    timeout: int = DEFAULT_TIMEOUT,
) -> ToolResult:
    """
    Stage explicitly specified files or directories.

    This operation changes the Git index but does not create a commit.
    Paths must remain inside the repository.
    """

    root, relative_paths, validation_error = _validate_paths(
        repository_root,
        paths,
    )

    if validation_error is not None:
        return validation_error

    assert root is not None
    assert relative_paths is not None

    return _run_git(
        root,
        [
            "add",
            "--",
            *relative_paths,
        ],
        timeout=timeout,
    )


def git_commit(
    repository_root: Path,
    message: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> ToolResult:
    """
    Create a Git commit from currently staged changes.

    This operation does not stage files automatically.
    Files must first be staged through git_add().
    """

    if not isinstance(message, str):
        return ToolResult(
            success=False,
            error="Commit message must be a string.",
        )

    message = message.strip()

    if not message:
        return ToolResult(
            success=False,
            error="Commit message cannot be empty.",
        )

    root, validation_error = _validate_repository(
        repository_root,
    )

    if validation_error is not None:
        return validation_error

    assert root is not None

    return _run_git(
        root,
        [
            "commit",
            "-m",
            message,
        ],
        timeout=timeout,
    )


def git_push(
    repository_root: Path,
    remote: str = "origin",
    branch: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> ToolResult:
    """
    Push a local Git branch to a configured remote.

    If branch is omitted, the current branch is used.

    Safety properties:
        - Repository must be valid.
        - Remote must already be configured.
        - Remote cannot be an arbitrary URL.
        - Branch must be a valid local branch.
        - No shell is used.
    """

    if not isinstance(remote, str):
        return ToolResult(
            success=False,
            error="remote must be a string.",
        )

    remote = remote.strip()

    root, validated_remote, remote_error = _validate_remote(
        repository_root,
        remote,
    )

    if remote_error is not None:
        return remote_error

    assert root is not None
    assert validated_remote is not None

    if branch is None:
        current_branch_result = git_branch(
            root,
            timeout=timeout,
        )

        if not current_branch_result.success:
            return current_branch_result

        branch = current_branch_result.output.strip()

        if not branch:
            return ToolResult(
                success=False,
                error=(
                    "Cannot push because the repository is in "
                    "a detached HEAD state with no current branch."
                ),
            )

    root, validated_branch, branch_error = _validate_branch(
        root,
        branch,
    )

    if branch_error is not None:
        return branch_error

    assert root is not None
    assert validated_branch is not None

    return _run_git(
        root,
        [
            "push",
            validated_remote,
            validated_branch,
        ],
        timeout=timeout,
    )