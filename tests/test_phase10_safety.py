from __future__ import annotations

from safety.approval import ApprovalDecision, ApprovalManager


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    print("=" * 60)
    print("PHASE 10 — SAFETY POLICY TEST")
    print("=" * 60)

    safety = ApprovalManager()

    print("\n1. Read-only tools are safe...")
    result = safety.check("read_file", {"path": "app.py"})
    check(
        result.decision == ApprovalDecision.SAFE,
        "read_file should be SAFE",
    )
    check(
        result.allowed,
        "read_file should be allowed",
    )
    print("✓ read_file is SAFE")

    result = safety.check("search_repo", {"query": "hello"})
    check(
        result.decision == ApprovalDecision.SAFE,
        "search_repo should be SAFE",
    )
    print("✓ search_repo is SAFE")

    print("\n2. File modification tools require approval...")
    result = safety.check(
        "write_file",
        {
            "path": "test.py",
            "content": "print('hello')",
        },
    )
    check(
        result.decision == ApprovalDecision.REQUIRE_APPROVAL,
        "write_file should require approval",
    )
    check(
        result.requires_approval,
        "write_file should report requires_approval=True",
    )
    print("✓ write_file requires approval")

    result = safety.check(
        "edit_file",
        {
            "path": "app.py",
            "old_text": "Hello",
            "new_text": "Hi",
        },
    )
    check(
        result.decision == ApprovalDecision.REQUIRE_APPROVAL,
        "edit_file should require approval",
    )
    print("✓ edit_file requires approval")

    print("\n3. Safe Git commands are allowed...")
    result = safety.check(
        "run_command",
        {
            "command": "git status",
        },
    )
    check(
        result.decision == ApprovalDecision.SAFE,
        "git status should be SAFE",
    )
    print("✓ git status is SAFE")

    result = safety.check(
        "run_command",
        {
            "command": "git diff",
        },
    )
    check(
        result.decision == ApprovalDecision.SAFE,
        "git diff should be SAFE",
    )
    print("✓ git diff is SAFE")

    result = safety.check(
        "run_command",
        {
            "command": "git log",
        },
    )
    check(
        result.decision == ApprovalDecision.SAFE,
        "git log should be SAFE",
    )
    print("✓ git log is SAFE")

    print("\n4. Executable commands require approval...")
    result = safety.check(
        "run_command",
        {
            "command": "python test.py",
        },
    )
    check(
        result.decision == ApprovalDecision.REQUIRE_APPROVAL,
        "python command should require approval",
    )
    print("✓ python execution requires approval")

    result = safety.check(
        "run_command",
        {
            "command": "pytest",
        },
    )
    check(
        result.decision == ApprovalDecision.REQUIRE_APPROVAL,
        "pytest should require approval",
    )
    print("✓ pytest requires approval")

    result = safety.check(
        "run_command",
        {
            "command": "pip install requests",
        },
    )
    check(
        result.decision == ApprovalDecision.REQUIRE_APPROVAL,
        "pip should require approval",
    )
    print("✓ pip requires approval")

    print("\n5. Dangerous commands are denied...")
    result = safety.check(
        "run_command",
        {
            "command": "powershell Get-ChildItem",
        },
    )
    check(
        result.decision == ApprovalDecision.DENIED,
        "PowerShell should be DENIED",
    )
    check(
        result.denied,
        "PowerShell should report denied=True",
    )
    print("✓ PowerShell is DENIED")

    result = safety.check(
        "run_command",
        {
            "command": "cmd.exe /c dir",
        },
    )
    check(
        result.decision == ApprovalDecision.DENIED,
        "cmd.exe should be DENIED",
    )
    print("✓ cmd.exe is DENIED")

    result = safety.check(
        "run_command",
        {
            "command": "del test.txt",
        },
    )
    check(
        result.decision == ApprovalDecision.DENIED,
        "del should be DENIED",
    )
    print("✓ del is DENIED")

    print("\n6. Unknown tools are denied...")
    result = safety.check(
        "unknown_tool",
        {},
    )
    check(
        result.decision == ApprovalDecision.DENIED,
        "Unknown tools should be DENIED",
    )
    print("✓ Unknown tools are DENIED")

    print("\n7. Invalid input is denied...")
    result = safety.check(
        "",
        {},
    )
    check(
        result.decision == ApprovalDecision.DENIED,
        "Empty tool name should be DENIED",
    )
    print("✓ Empty tool name is DENIED")

    result = safety.check(
        "run_command",
        {},
    )
    check(
        result.decision == ApprovalDecision.DENIED,
        "Missing command should be DENIED",
    )
    print("✓ Missing command is DENIED")

    result = safety.check(
        "run_command",
        {
            "command": "",
        },
    )
    check(
        result.decision == ApprovalDecision.DENIED,
        "Empty command should be DENIED",
    )
    print("✓ Empty command is DENIED")

    print("\n8. Safety status properties...")
    safe_result = safety.check(
        "read_file",
        {
            "path": "README.md",
        },
    )

    approval_result = safety.check(
        "edit_file",
        {
            "path": "app.py",
            "old_text": "A",
            "new_text": "B",
        },
    )

    denied_result = safety.check(
        "unknown_tool",
        {},
    )

    check(
        safe_result.allowed,
        "SAFE result should have allowed=True",
    )
    check(
        not safe_result.requires_approval,
        "SAFE result should not require approval",
    )
    check(
        not safe_result.denied,
        "SAFE result should not be denied",
    )

    check(
        not approval_result.allowed,
        "Approval-required result should not be allowed automatically",
    )
    check(
        approval_result.requires_approval,
        "Approval-required result should have requires_approval=True",
    )
    check(
        not approval_result.denied,
        "Approval-required result should not be denied",
    )

    check(
        not denied_result.allowed,
        "Denied result should not be allowed",
    )
    check(
        not denied_result.requires_approval,
        "Denied result should not require approval",
    )
    check(
        denied_result.denied,
        "Denied result should have denied=True",
    )

    print("✓ Safety status properties work")

    print("\n" + "=" * 60)
    print("PHASE 10 SAFETY TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()