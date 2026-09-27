from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from git.operations import git_push


def run_git(
    cwd: Path,
    *arguments: str,
) -> subprocess.CompletedProcess[str]:
    """
    Run a real Git command for test setup/verification.
    """

    return subprocess.run(
        ["git", *arguments],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )


def configure_git_identity(
    repository: Path,
) -> None:
    run_git(
        repository,
        "config",
        "user.name",
        "Phase 14 Test User",
    )

    run_git(
        repository,
        "config",
        "user.email",
        "phase14@example.com",
    )


def create_source_repository(
    root: Path,
) -> Path:
    repository = root / "source"

    repository.mkdir()

    run_git(
        repository,
        "-c",
        "init.defaultBranch=main",
        "init",
    )

    configure_git_identity(repository)

    test_file = repository / "hello.txt"
    test_file.write_text(
        "Phase 14 push test\n",
        encoding="utf-8",
    )

    run_git(
        repository,
        "add",
        "--",
        "hello.txt",
    )

    run_git(
        repository,
        "commit",
        "-m",
        "Initial commit",
    )

    return repository


def create_bare_remote(
    root: Path,
) -> Path:
    remote = root / "remote.git"

    run_git(
        root,
        "init",
        "--bare",
        remote.name,
    )

    return remote


def test_git_push_default_remote_and_current_branch(
    tmp_path,
):
    source = create_source_repository(tmp_path)
    remote = create_bare_remote(tmp_path)

    run_git(
        source,
        "remote",
        "add",
        "origin",
        str(remote),
    )

    result = git_push(
        source,
    )

    assert result.success is True
    assert result.error is None

    head = run_git(
        source,
        "rev-parse",
        "HEAD",
    ).stdout.strip()

    remote_head = run_git(
        remote,
        "rev-parse",
        "refs/heads/main",
    ).stdout.strip()

    assert remote_head == head


def test_git_push_explicit_branch(
    tmp_path,
):
    source = create_source_repository(tmp_path)
    remote = create_bare_remote(tmp_path)

    run_git(
        source,
        "remote",
        "add",
        "upstream",
        str(remote),
    )

    result = git_push(
        source,
        remote="upstream",
        branch="main",
    )

    assert result.success is True
    assert result.error is None

    source_head = run_git(
        source,
        "rev-parse",
        "HEAD",
    ).stdout.strip()

    remote_head = run_git(
        remote,
        "rev-parse",
        "refs/heads/main",
    ).stdout.strip()

    assert remote_head == source_head


def test_git_push_rejects_unconfigured_remote(
    tmp_path,
):
    source = create_source_repository(tmp_path)
    remote = create_bare_remote(tmp_path)

    result = git_push(
        source,
        remote="upstream",
    )

    assert result.success is False
    assert result.error is not None
    assert "not configured" in result.error.lower()

    # The remote repository must remain untouched.
    refs_result = subprocess.run(
        [
            "git",
            "--git-dir",
            str(remote),
            "show-ref",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    assert refs_result.stdout.strip() == ""


def test_git_push_rejects_invalid_remote(
    tmp_path,
):
    source = create_source_repository(tmp_path)

    result = git_push(
        source,
        remote="--force",
    )

    assert result.success is False
    assert result.error is not None
    assert "begin with '-'" in result.error


def test_git_push_rejects_invalid_branch(
    tmp_path,
):
    source = create_source_repository(tmp_path)
    remote = create_bare_remote(tmp_path)

    run_git(
        source,
        "remote",
        "add",
        "origin",
        str(remote),
    )

    result = git_push(
        source,
        branch="does-not-exist",
    )

    assert result.success is False
    assert result.error is not None
    assert "does not exist" in result.error.lower()


def test_git_push_rejects_option_like_branch(
    tmp_path,
):
    source = create_source_repository(tmp_path)
    remote = create_bare_remote(tmp_path)

    run_git(
        source,
        "remote",
        "add",
        "origin",
        str(remote),
    )

    result = git_push(
        source,
        branch="--force",
    )

    assert result.success is False
    assert result.error is not None
    assert "begin with '-'" in result.error


def test_git_push_rejects_nonexistent_repository(
    tmp_path,
):
    missing_repository = tmp_path / "missing"

    result = git_push(
        missing_repository,
    )

    assert result.success is False
    assert result.error is not None
    assert "does not exist" in result.error.lower()


def test_git_push_rejects_non_git_directory(
    tmp_path,
):
    non_git_directory = tmp_path / "not-a-repository"
    non_git_directory.mkdir()

    result = git_push(
        non_git_directory,
    )

    assert result.success is False
    assert result.error is not None
    assert "not a git repository" in result.error.lower()