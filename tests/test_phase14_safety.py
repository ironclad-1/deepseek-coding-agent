from __future__ import annotations

from safety.approval import (
    ApprovalDecision,
    ApprovalManager,
)


def test_git_push_requires_approval():
    manager = ApprovalManager()

    result = manager.check(
        "git_push",
        {
            "remote": "origin",
            "branch": "main",
        },
    )

    assert result.decision == ApprovalDecision.REQUIRE_APPROVAL

    assert (
        "remote repository"
        in result.reason.lower()
    )

    assert (
        "approval"
        in result.reason.lower()
    )


def test_git_push_is_not_safe():
    manager = ApprovalManager()

    result = manager.check(
        "git_push",
        {},
    )

    assert result.decision != ApprovalDecision.SAFE


def test_git_add_still_requires_approval():
    manager = ApprovalManager()

    result = manager.check(
        "git_add",
        {
            "paths": [
                "agent/runtime.py",
            ],
        },
    )

    assert result.decision == ApprovalDecision.REQUIRE_APPROVAL


def test_git_commit_still_requires_approval():
    manager = ApprovalManager()

    result = manager.check(
        "git_commit",
        {
            "message": "Complete Phase 13",
        },
    )

    assert result.decision == ApprovalDecision.REQUIRE_APPROVAL


def test_read_only_git_tools_remain_safe():
    manager = ApprovalManager()

    safe_tools = [
        "git_status",
        "git_diff",
        "git_log",
        "git_branch",
        "git_remote",
    ]

    for tool_name in safe_tools:
        result = manager.check(
            tool_name,
            {},
        )

        assert result.decision == ApprovalDecision.SAFE, (
            f"{tool_name} should remain SAFE, "
            f"got {result.decision.value}"
        )