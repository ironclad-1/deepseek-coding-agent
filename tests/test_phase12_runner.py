from __future__ import annotations

from pathlib import Path

from agent.runner import AgentRunner, ReviewResult, TestRunResult
from tools.registry import ToolResult


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    print("=" * 60)
    print("PHASE 12 — AGENT RUNNER TEST")
    print("=" * 60)

    repository_root = Path(".").resolve()

    print("\n1. Successful test execution...")

    executed_commands: list[str] = []

    def successful_executor(
        *,
        command: str,
        timeout: int,
    ) -> ToolResult:
        executed_commands.append(command)

        return ToolResult(
            success=True,
            output="2 passed in 0.15s",
            metadata={
                "command": [command],
                "exit_code": 0,
                "timeout": timeout,
            },
        )

    def successful_diff_provider() -> ToolResult:
        return ToolResult(
            success=True,
            output="",
            metadata={
                "exit_code": 0,
            },
        )

    runner = AgentRunner(
        repository_root=repository_root,
        command_executor=successful_executor,
        diff_provider=successful_diff_provider,
    )

    result = runner.run_tests(
        "pytest",
        timeout=30,
    )

    check(
        isinstance(result, TestRunResult),
        "run_tests did not return TestRunResult.",
    )

    check(
        result.success,
        "Successful test command should return success=True.",
    )

    check(
        result.exit_code == 0,
        "Successful test should have exit code 0.",
    )

    check(
        "2 passed" in result.output,
        "Test output was not captured.",
    )

    check(
        result.timed_out is False,
        "Successful test should not be marked as timed out.",
    )

    check(
        executed_commands == ["pytest"],
        "Test command was not passed to the executor correctly.",
    )

    print("✓ Successful test execution works")
    print("✓ Test output is captured")
    print("✓ Exit code is captured")

    print("\n2. Failed test execution...")

    def failed_executor(
        *,
        command: str,
        timeout: int,
    ) -> ToolResult:
        return ToolResult(
            success=False,
            output="FAILED tests/test_app.py::test_greet",
            error="1 failed, 2 passed",
            metadata={
                "command": [command],
                "exit_code": 1,
                "timeout": timeout,
            },
        )

    runner = AgentRunner(
        repository_root=repository_root,
        command_executor=failed_executor,
        diff_provider=successful_diff_provider,
    )

    result = runner.run_tests(
        "pytest tests/",
        timeout=45,
    )

    check(
        not result.success,
        "Failed test command should return success=False.",
    )

    check(
        result.exit_code == 1,
        "Failed test should preserve exit code 1.",
    )

    check(
        "FAILED" in result.output,
        "Failed test output was not captured.",
    )

    check(
        result.error == "1 failed, 2 passed",
        "Test error was not captured correctly.",
    )

    print("✓ Failed test execution works")
    print("✓ Failure output is captured")
    print("✓ Failure exit code is captured")

    print("\n3. Timed-out test execution...")

    def timeout_executor(
        *,
        command: str,
        timeout: int,
    ) -> ToolResult:
        return ToolResult(
            success=False,
            output="Command timed out after 5 seconds.",
            error="Command timed out after 5 seconds.",
            metadata={
                "command": [command],
                "timeout": timeout,
                "timed_out": True,
            },
        )

    runner = AgentRunner(
        repository_root=repository_root,
        command_executor=timeout_executor,
        diff_provider=successful_diff_provider,
    )

    result = runner.run_tests(
        "pytest",
        timeout=5,
    )

    check(
        not result.success,
        "Timed-out test should return success=False.",
    )

    check(
        result.timed_out,
        "Timed-out test should have timed_out=True.",
    )

    check(
        "timed out" in result.output.lower(),
        "Timeout output was not captured.",
    )

    print("✓ Timeout detection works")
    print("✓ Timeout status is preserved")

    print("\n4. Unexpected command executor failure...")

    def crashing_executor(
        *,
        command: str,
        timeout: int,
    ) -> ToolResult:
        raise RuntimeError("executor crashed")

    runner = AgentRunner(
        repository_root=repository_root,
        command_executor=crashing_executor,
        diff_provider=successful_diff_provider,
    )

    result = runner.run_tests(
        "pytest",
    )

    check(
        not result.success,
        "Unexpected executor failure should return success=False.",
    )

    check(
        "executor crashed" in (result.error or ""),
        "Unexpected executor error was not preserved.",
    )

    print("✓ Unexpected executor failures are handled")

    print("\n5. Invalid empty test command...")

    result = runner.run_tests(
        "",
    )

    check(
        not result.success,
        "Empty test command should fail.",
    )

    check(
        result.error
        == "Test command must be a non-empty string.",
        "Incorrect empty-command error.",
    )

    print("✓ Empty test command is rejected")

    print("\n6. Successful Git diff review with no changes...")

    def no_changes_diff_provider() -> ToolResult:
        return ToolResult(
            success=True,
            output="",
            metadata={
                "exit_code": 0,
            },
        )

    runner = AgentRunner(
        repository_root=repository_root,
        command_executor=successful_executor,
        diff_provider=no_changes_diff_provider,
    )

    result = runner.review_diff()

    check(
        isinstance(result, ReviewResult),
        "review_diff did not return ReviewResult.",
    )

    check(
        result.success,
        "Successful diff review should return success=True.",
    )

    check(
        not result.has_changes,
        "Empty diff should report has_changes=False.",
    )

    check(
        result.diff == "",
        "Empty diff should return an empty diff string.",
    )

    print("✓ Empty Git diff is handled correctly")

    print("\n7. Git diff review with changes...")

    expected_diff = (
        "diff --git a/app.py b/app.py\n"
        "--- a/app.py\n"
        "+++ b/app.py\n"
        "@@ -1 +1 @@\n"
        "-return 'Hello'\n"
        "+return 'Hello, world'\n"
    )

    def changed_diff_provider() -> ToolResult:
        return ToolResult(
            success=True,
            output=expected_diff,
            metadata={
                "exit_code": 0,
            },
        )

    runner = AgentRunner(
        repository_root=repository_root,
        command_executor=successful_executor,
        diff_provider=changed_diff_provider,
    )

    result = runner.review_diff()

    check(
        result.success,
        "Successful diff review should return success=True.",
    )

    check(
        result.has_changes,
        "Non-empty diff should report has_changes=True.",
    )

    check(
        result.diff == expected_diff,
        "Git diff content was not preserved.",
    )

    print("✓ Git diff with changes is captured")
    print("✓ Change detection works")

    print("\n8. Git diff provider failure...")

    def failed_diff_provider() -> ToolResult:
        return ToolResult(
            success=False,
            error="Not a Git repository.",
        )

    runner = AgentRunner(
        repository_root=repository_root,
        command_executor=successful_executor,
        diff_provider=failed_diff_provider,
    )

    result = runner.review_diff()

    check(
        not result.success,
        "Failed diff provider should return success=False.",
    )

    check(
        result.error == "Not a Git repository.",
        "Diff provider error was not preserved.",
    )

    check(
        not result.has_changes,
        "Failed diff review should not report changes.",
    )

    print("✓ Git diff provider failures are handled")

    print("\n9. Invalid diff provider return type...")

    def invalid_diff_provider() -> str:
        return "invalid"

    runner = AgentRunner(
        repository_root=repository_root,
        command_executor=successful_executor,
        diff_provider=invalid_diff_provider,
    )

    result = runner.review_diff()

    check(
        not result.success,
        "Invalid diff provider result should fail.",
    )

    check(
        result.error == "Diff provider must return ToolResult.",
        "Incorrect invalid-provider error.",
    )

    print("✓ Invalid diff provider results are rejected")

    print("\n10. Complete validation cycle with passing tests...")

    def passing_executor(
        *,
        command: str,
        timeout: int,
    ) -> ToolResult:
        return ToolResult(
            success=True,
            output="3 passed in 0.20s",
            metadata={
                "command": [command],
                "exit_code": 0,
                "timeout": timeout,
            },
        )

    def changed_diff() -> ToolResult:
        return ToolResult(
            success=True,
            output=(
                "diff --git a/app.py b/app.py\n"
                "+return 'Hello, world'\n"
            ),
            metadata={
                "exit_code": 0,
            },
        )

    runner = AgentRunner(
        repository_root=repository_root,
        command_executor=passing_executor,
        diff_provider=changed_diff,
    )

    validation = runner.validate(
        test_command="pytest tests/",
        timeout=60,
    )

    check(
        validation.tests_passed,
        "Passing tests should produce tests_passed=True.",
    )

    check(
        validation.diff_available,
        "Non-empty diff should produce diff_available=True.",
    )

    check(
        validation.test_result is not None,
        "Validation should contain test_result.",
    )

    check(
        validation.review_result is not None,
        "Validation should contain review_result.",
    )

    check(
        validation.test_result.success,
        "Contained test result should be successful.",
    )

    check(
        validation.review_result.has_changes,
        "Contained review result should detect changes.",
    )

    check(
        validation.error is None,
        "Successful validation should not have an error.",
    )

    print("✓ Complete passing validation cycle works")

    print("\n11. Complete validation cycle with failed tests...")

    def failing_executor_for_validation(
        *,
        command: str,
        timeout: int,
    ) -> ToolResult:
        return ToolResult(
            success=False,
            output="1 failed, 2 passed",
            error="Tests failed.",
            metadata={
                "command": [command],
                "exit_code": 1,
                "timeout": timeout,
            },
        )

    runner = AgentRunner(
        repository_root=repository_root,
        command_executor=failing_executor_for_validation,
        diff_provider=changed_diff,
    )

    validation = runner.validate(
        test_command="pytest tests/",
        timeout=60,
    )

    check(
        not validation.tests_passed,
        "Failed tests should produce tests_passed=False.",
    )

    check(
        validation.test_result is not None,
        "Failed validation should contain test_result.",
    )

    check(
        validation.review_result is not None,
        "Failed validation should still contain review_result.",
    )

    check(
        validation.diff_available,
        "Available diff should still be reported after test failure.",
    )

    check(
        validation.error == "Tests failed.",
        "Validation should preserve test failure error.",
    )

    print("✓ Failed validation cycle works")
    print("✓ Diff is still available after test failure")

    print("\n12. Validation with failed Git diff review...")

    runner = AgentRunner(
        repository_root=repository_root,
        command_executor=passing_executor,
        diff_provider=failed_diff_provider,
    )

    validation = runner.validate(
        test_command="pytest tests/",
    )

    check(
        validation.tests_passed,
        "Passing tests should remain tests_passed=True.",
    )

    check(
        not validation.diff_available,
        "Failed diff review should report diff_available=False.",
    )

    check(
        validation.review_result is not None,
        "Validation should contain failed review result.",
    )

    check(
        validation.error == "Not a Git repository.",
        "Diff review error was not preserved.",
    )

    print("✓ Failed diff validation is handled")

    print("\n13. Test feedback formatting...")

    test_result = TestRunResult(
        command="pytest tests/",
        success=False,
        output="FAILED test_example",
        error="1 failed",
        exit_code=1,
        timed_out=False,
    )

    feedback = runner.format_test_feedback(
        test_result
    )

    check(
        "TEST RESULT" in feedback,
        "Test feedback heading is missing.",
    )

    check(
        "pytest tests/" in feedback,
        "Test command is missing from feedback.",
    )

    check(
        "Exit code: 1" in feedback,
        "Exit code is missing from feedback.",
    )

    check(
        "FAILED test_example" in feedback,
        "Test output is missing from feedback.",
    )

    check(
        "1 failed" in feedback,
        "Test error is missing from feedback.",
    )

    print("✓ Test feedback formatting works")

    print("\n14. Git diff feedback formatting...")

    review_result = ReviewResult(
        success=True,
        diff=expected_diff,
        has_changes=True,
    )

    feedback = runner.format_review_feedback(
        review_result
    )

    check(
        "GIT DIFF REVIEW" in feedback,
        "Git diff feedback heading is missing.",
    )

    check(
        "Changes detected: True" in feedback,
        "Change status is missing from feedback.",
    )

    check(
        "return 'Hello, world'" in feedback,
        "Git diff content is missing from feedback.",
    )

    print("✓ Git diff feedback formatting works")

    print("\n" + "=" * 60)
    print("PHASE 12 RUNNER TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()