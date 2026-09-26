from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from git.operations import (
    git_branch,
    git_diff,
    git_log,
    git_remote,
    git_status,
)


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run_git(repository_root: Path, *arguments: str) -> None:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repository_root,
        shell=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Git command failed: {' '.join(arguments)}\n"
            f"STDOUT: {result.stdout}\n"
            f"STDERR: {result.stderr}"
        )


def prepare_repository(repository_root: Path) -> None:
    run_git(repository_root, "init")
    run_git(repository_root, "branch", "-M", "main")
    run_git(repository_root, "config", "user.name", "Phase 11 Test")
    run_git(repository_root, "config", "user.email", "phase11@test.local")

    readme = repository_root / "README.md"
    readme.write_text(
        "# Phase 11 Test Repository\n"
        "Git operations test.\n",
        encoding="utf-8",
    )

    run_git(repository_root, "add", "README.md")
    run_git(
        repository_root,
        "commit",
        "-m",
        "Initial Phase 11 test commit",
    )

    run_git(
        repository_root,
        "remote",
        "add",
        "origin",
        "https://example.com/phase11-test.git",
    )


def main() -> None:
    print("=" * 60)
    print("PHASE 11 — GIT OPERATIONS TEST")
    print("=" * 60)

    with tempfile.TemporaryDirectory(
        prefix="phase11_git_"
    ) as temp_dir:
        repository_root = Path(temp_dir)

        print("\n1. Preparing temporary Git repository...")
        prepare_repository(repository_root)

        check(
            (repository_root / ".git").exists(),
            "Git repository was not initialized.",
        )

        print("✓ Temporary Git repository created")

        print("\n2. Checking Git status on a clean repository...")
        result = git_status(repository_root)

        check(
            result.success,
            result.error or "git_status failed.",
        )

        check(
            "## main" in result.output,
            "Expected main branch was not reported.",
        )

        print("✓ git_status works on clean repository")
        print(f"  {result.output}")

        print("\n3. Checking current branch...")
        result = git_branch(repository_root)

        check(
            result.success,
            result.error or "git_branch failed.",
        )

        check(
            result.output.strip() == "main",
            "Current branch should be main.",
        )

        print("✓ git_branch works")

        print("\n4. Checking Git log...")
        result = git_log(
            repository_root,
            max_entries=5,
        )

        check(
            result.success,
            result.error or "git_log failed.",
        )

        check(
            "Initial Phase 11 test commit" in result.output,
            "Initial commit was not found in git log.",
        )

        print("✓ git_log works")

        print("\n5. Checking Git remote...")
        result = git_remote(repository_root)

        check(
            result.success,
            result.error or "git_remote failed.",
        )

        check(
            "origin" in result.output,
            "Origin remote was not found.",
        )

        check(
            "https://example.com/phase11-test.git"
            in result.output,
            "Expected remote URL was not found.",
        )

        print("✓ git_remote works")

        print("\n6. Creating an untracked file...")
        untracked_file = repository_root / "untracked.txt"

        untracked_file.write_text(
            "This file is untracked.\n",
            encoding="utf-8",
        )

        result = git_status(repository_root)

        check(
            result.success,
            result.error or "git_status failed.",
        )

        check(
            "?? untracked.txt" in result.output,
            "Untracked file was not reported.",
        )

        print("✓ git_status detects untracked files")

        print("\n7. Modifying a tracked file...")
        readme = repository_root / "README.md"

        readme.write_text(
            "# Phase 11 Test Repository\n"
            "Git operations test.\n"
            "This line was added during the test.\n",
            encoding="utf-8",
        )

        result = git_diff(repository_root)

        check(
            result.success,
            result.error or "git_diff failed.",
        )

        check(
            "This line was added during the test."
            in result.output,
            "Expected modified line was not found in git diff.",
        )

        check(
            "README.md" in result.output,
            "README.md was not shown in git diff.",
        )

        print("✓ git_diff detects tracked-file changes")

        print("\n8. Checking status after modifications...")
        result = git_status(repository_root)

        check(
            result.success,
            result.error or "git_status failed.",
        )

        check(
            "README.md" in result.output,
            "Modified README.md was not reported.",
        )

        check(
            "?? untracked.txt" in result.output,
            "Untracked file disappeared from status.",
        )

        print("✓ git_status reports tracked and untracked changes")

        print("\n9. Checking git_log entry limit...")
        result = git_log(
            repository_root,
            max_entries=1,
        )

        check(
            result.success,
            result.error or "git_log with limit failed.",
        )

        log_lines = [
            line
            for line in result.output.splitlines()
            if line.strip()
        ]

        check(
            len(log_lines) <= 1,
            "git_log returned more entries than requested.",
        )

        print("✓ git_log respects max_entries")

        print("\n10. Rejecting a non-Git repository...")
        non_git_root = Path(
            tempfile.mkdtemp(prefix="phase11_non_git_")
        )

        result = git_status(non_git_root)

        check(
            not result.success,
            "Non-Git directory should not be accepted.",
        )

        check(
            "not a git repository" in (result.error or "").lower(),
            "Expected non-Git repository error.",
        )

        print("✓ Non-Git repository is rejected")

        print("\n11. Checking repository is not modified by read-only operations...")

        status_before = subprocess.run(
            ["git", "status", "--short"],
            cwd=repository_root,
            shell=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        ).stdout.strip()

        git_status(repository_root)
        git_diff(repository_root)
        git_log(repository_root)
        git_branch(repository_root)
        git_remote(repository_root)

        status_after = subprocess.run(
            ["git", "status", "--short"],
            cwd=repository_root,
            shell=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        ).stdout.strip()

        check(
            status_before == status_after,
            "Read-only Git operations changed repository state.",
        )

        print("✓ Read-only Git operations do not modify repository state")

    print("\n" + "=" * 60)
    print("PHASE 11 GIT OPERATIONS TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()