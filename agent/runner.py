from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Any
from tools.registry import ToolResult


@dataclass
class TestRunResult:
    __test__ = False
    command: str
    success: bool
    output: str = ""
    error: str | None = None
    exit_code: int | None = None
    timed_out: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReviewResult:
    success: bool
    diff: str = ""
    has_changes: bool = False
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    tests_passed: bool
    diff_available: bool
    test_result: TestRunResult | None = None
    review_result: ReviewResult | None = None
    error: str | None = None


class AgentRunner:
    """
    Deterministic validation runner for Phase 12.

    Responsibilities:

        Run tests
        Capture test output
        Capture exit status
        Detect timeouts
        Inspect Git diff
        Return structured validation results

    The runner does not decide whether a command is safe.
    Command approval remains the responsibility of the safety layer
    and AgentRuntime.
    """

    def __init__(
        self,
        *,
        repository_root: Path,
        command_executor: Callable[..., ToolResult],
        diff_provider: Callable[..., ToolResult],
    ) -> None:
        self.repository_root = Path(
            repository_root
        ).resolve()

        self.command_executor = command_executor
        self.diff_provider = diff_provider

    def run_tests(
        self,
        command: str,
        *,
        timeout: int = 30,
    ) -> TestRunResult:
        """
        Execute a test command through the supplied command executor.
        """

        if not isinstance(command, str) or not command.strip():
            return TestRunResult(
                command=command if isinstance(command, str) else "",
                success=False,
                error="Test command must be a non-empty string.",
            )

        try:
            result = self.command_executor(
                command=command,
                timeout=timeout,
            )

        except Exception as exc:
            return TestRunResult(
                command=command,
                success=False,
                error=(
                    f"Test execution failed unexpectedly: "
                    f"{type(exc).__name__}: {exc}"
                ),
            )

        if not isinstance(result, ToolResult):
            return TestRunResult(
                command=command,
                success=False,
                error="Command executor must return ToolResult.",
            )

        metadata = dict(result.metadata)

        exit_code = metadata.get(
            "exit_code"
        )

        timed_out = bool(
            metadata.get(
                "timed_out",
                False,
            )
        )

        return TestRunResult(
            command=command,
            success=result.success,
            output=result.output,
            error=result.error,
            exit_code=exit_code,
            timed_out=timed_out,
            metadata=metadata,
        )

    def review_diff(self) -> ReviewResult:
        """
        Retrieve the current Git diff for review.
        """

        try:
            result = self.diff_provider()

        except Exception as exc:
            return ReviewResult(
                success=False,
                error=(
                    f"Git diff retrieval failed unexpectedly: "
                    f"{type(exc).__name__}: {exc}"
                ),
            )

        if not isinstance(result, ToolResult):
            return ReviewResult(
                success=False,
                error="Diff provider must return ToolResult.",
            )

        diff = result.output or ""

        return ReviewResult(
            success=result.success,
            diff=diff,
            has_changes=bool(
                diff.strip()
            ),
            error=result.error,
            metadata=dict(
                result.metadata
            ),
        )

    def validate(
        self,
        *,
        test_command: str,
        timeout: int = 30,
    ) -> ValidationResult:
        """
        Run tests and inspect the Git diff.

        This is one deterministic validation cycle:

            Test → Capture result → Review diff
        """

        test_result = self.run_tests(
            test_command,
            timeout=timeout,
        )

        review_result = self.review_diff()

        if not test_result.success:
            return ValidationResult(
                tests_passed=False,
                diff_available=review_result.has_changes,
                test_result=test_result,
                review_result=review_result,
                error=test_result.error,
            )

        if not review_result.success:
            return ValidationResult(
                tests_passed=True,
                diff_available=False,
                test_result=test_result,
                review_result=review_result,
                error=review_result.error,
            )

        return ValidationResult(
            tests_passed=True,
            diff_available=review_result.has_changes,
            test_result=test_result,
            review_result=review_result,
        )

    def format_test_feedback(
        self,
        result: TestRunResult,
    ) -> str:
        """
        Convert a test result into concise feedback suitable for
        sending back to the model.
        """

        lines = [
            "TEST RESULT",
            "-----------",
            f"Command: {result.command}",
            f"Success: {result.success}",
        ]

        if result.exit_code is not None:
            lines.append(
                f"Exit code: {result.exit_code}"
            )

        if result.timed_out:
            lines.append(
                "Status: timed out"
            )

        if result.output:
            lines.extend(
                [
                    "",
                    "OUTPUT:",
                    result.output,
                ]
            )

        if result.error:
            lines.extend(
                [
                    "",
                    "ERROR:",
                    result.error,
                ]
            )

        return "\n".join(lines)

    def format_review_feedback(
        self,
        result: ReviewResult,
    ) -> str:
        """
        Convert a Git diff review into concise model feedback.
        """

        lines = [
            "GIT DIFF REVIEW",
            "----------------",
            f"Success: {result.success}",
            f"Changes detected: {result.has_changes}",
        ]

        if result.diff:
            lines.extend(
                [
                    "",
                    "DIFF:",
                    result.diff,
                ]
            )

        if result.error:
            lines.extend(
                [
                    "",
                    "ERROR:",
                    result.error,
                ]
            )

        return "\n".join(lines)