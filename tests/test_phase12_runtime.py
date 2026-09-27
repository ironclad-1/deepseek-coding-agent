from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from agent.model import ModelResponse
from agent.runtime import AgentRuntime
from agent.session import AgentSession
from reasoning.recorder import ReasoningRecorder
from tools.registry import Tool, ToolRegistry, ToolResult


class FakeModel:
    """
    Scripted model used to test AgentRuntime without Ollama.
    """

    def __init__(self, responses: list[ModelResponse]) -> None:
        self.responses = responses
        self.calls: list[list[dict[str, Any]]] = []

    def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        think: bool = True,
        stream: bool = False,
        tools: list[dict[str, Any]] | None = None,
    ) -> ModelResponse:
        self.calls.append(list(messages))

        if not self.responses:
            raise RuntimeError("FakeModel has no more responses.")

        return self.responses.pop(0)


class FakeRecorder:
    """
    Minimal recorder used by the runtime tests.
    """

    def save(
        self,
        *,
        model: str,
        session_id: str,
        turn: int,
        user_message: str,
        thinking: str,
    ) -> str:
        return f".reason/{session_id}-{turn}.reason"


def make_tool_call(
    name: str,
    arguments: dict[str, Any],
) -> Any:
    """
    Create an object matching the runtime's expected tool-call structure.
    """

    return SimpleNamespace(
        function=SimpleNamespace(
            name=name,
            arguments=arguments,
        )
    )


def make_response(
    *,
    content: str = "",
    tool_calls: list[Any] | None = None,
    thinking: str = "test reasoning",
) -> ModelResponse:
    """
    Create a ModelResponse for the scripted model.
    """

    return ModelResponse(
        model="fake-model",
        thinking=thinking,
        content=content,
        tool_calls=tool_calls or [],
        raw={},
    )


def build_registry(
    *,
    write_file_impl,
    run_command_impl,
    git_diff_impl,
) -> ToolRegistry:
    """
    Build the tools required by the Phase 12 runtime tests.
    """

    registry = ToolRegistry()

    registry.register(
        Tool(
            name="write_file",
            description="Write a file.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                    "overwrite": {"type": "boolean"},
                },
                "required": [
                    "path",
                    "content",
                ],
            },
            function=write_file_impl,
        )
    )

    registry.register(
        Tool(
            name="run_command",
            description="Run a command.",
            parameters={
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "timeout": {"type": "integer"},
                },
                "required": [
                    "command",
                ],
            },
            function=run_command_impl,
        )
    )

    registry.register(
        Tool(
            name="git_diff",
            description="Show git diff.",
            parameters={
                "type": "object",
                "properties": {},
            },
            function=git_diff_impl,
        )
    )

    return registry


def build_runtime(
    *,
    model: FakeModel,
    registry: ToolRegistry,
    repository_root: Path,
    max_turns: int = 10,
) -> AgentRuntime:
    """
    Build the real AgentRuntime using the Phase 12 implementation.
    """

    return AgentRuntime(
        model=model,
        tools=registry,
        recorder=FakeRecorder(),
        max_turns=max_turns,
        repository_root=repository_root,
    )


def test_phase12_runtime_tests_pass_and_review_diff(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Verify:

        write_file
            ↓
        approval
            ↓
        file changes
            ↓
        AgentRunner
            ↓
        run_command
            ↓
        approval
            ↓
        successful tests
            ↓
        git_diff
            ↓
        model receives self-review feedback
            ↓
        final answer
    """

    execution_log: list[tuple[str, dict[str, Any]]] = []

    def write_file_impl(**kwargs: Any) -> ToolResult:
        execution_log.append(("write_file", kwargs))

        path = tmp_path / kwargs["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            kwargs["content"],
            encoding="utf-8",
        )

        return ToolResult(
            success=True,
            output=f"Wrote {path}",
        )

    def run_command_impl(**kwargs: Any) -> ToolResult:
        execution_log.append(("run_command", kwargs))

        return ToolResult(
            success=True,
            output="1 passed in 0.02s",
            metadata={
                "exit_code": 0,
            },
        )

    def git_diff_impl(**kwargs: Any) -> ToolResult:
        execution_log.append(("git_diff", kwargs))

        return ToolResult(
            success=True,
            output="diff --git a/app.py b/app.py\n+fixed line",
        )

    registry = build_registry(
        write_file_impl=write_file_impl,
        run_command_impl=run_command_impl,
        git_diff_impl=git_diff_impl,
    )

    model = FakeModel(
        [
            make_response(
                thinking="I need to modify app.py.",
                tool_calls=[
                    make_tool_call(
                        "write_file",
                        {
                            "path": "app.py",
                            "content": "fixed code",
                        },
                    )
                ],
            ),
            make_response(
                thinking="The tests passed and the diff is clean.",
                content="The fix was completed and the tests passed.",
            ),
        ]
    )

    runtime = build_runtime(
        model=model,
        registry=registry,
        repository_root=tmp_path,
    )

    approvals = iter(["y", "y"])

    monkeypatch.setattr(
        "builtins.input",
        lambda _: next(approvals),
    )

    session = AgentSession()

    result = runtime.run(
        "Fix app.py.",
        session=session,
        test_command="pytest",
    )

    assert result == (
        "The fix was completed and the tests passed."
    )

    assert (tmp_path / "app.py").read_text(
        encoding="utf-8"
    ) == "fixed code"

    assert [entry[0] for entry in execution_log] == [
        "write_file",
        "run_command",
        "git_diff",
    ]

    assert len(model.calls) == 2

    final_model_messages = model.calls[1]

    feedback_text = "\n".join(
        str(message.get("content", ""))
        for message in final_model_messages
    )

    assert "Phase 12 self-review has completed." in feedback_text
    assert "Tests passed." in feedback_text
    assert "diff --git" in feedback_text


def test_phase12_runtime_tests_fail_and_feedback_reaches_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Verify:

        write_file
            ↓
        self-review
            ↓
        tests fail
            ↓
        failure feedback reaches model
            ↓
        model performs another edit
            ↓
        second self-review
            ↓
        tests pass
            ↓
        final answer
    """

    execution_log: list[tuple[str, dict[str, Any]]] = []
    test_runs = 0

    def write_file_impl(**kwargs: Any) -> ToolResult:
        execution_log.append(("write_file", kwargs))

        path = tmp_path / kwargs["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            kwargs["content"],
            encoding="utf-8",
        )

        return ToolResult(
            success=True,
            output=f"Wrote {path}",
        )

    def run_command_impl(**kwargs: Any) -> ToolResult:
        nonlocal test_runs

        execution_log.append(("run_command", kwargs))

        test_runs += 1

        if test_runs == 1:
            return ToolResult(
                success=False,
                output="",
                error="AssertionError: expected 2 but got 3",
                metadata={
                    "exit_code": 1,
                },
            )

        return ToolResult(
            success=True,
            output="1 passed in 0.03s",
            metadata={
                "exit_code": 0,
            },
        )

    def git_diff_impl(**kwargs: Any) -> ToolResult:
        execution_log.append(("git_diff", kwargs))

        return ToolResult(
            success=True,
            output=(
                "diff --git a/app.py b/app.py\n"
                "+corrected line"
            ),
        )

    registry = build_registry(
        write_file_impl=write_file_impl,
        run_command_impl=run_command_impl,
        git_diff_impl=git_diff_impl,
    )

    model = FakeModel(
        [
            make_response(
                thinking="I will make the initial change.",
                tool_calls=[
                    make_tool_call(
                        "write_file",
                        {
                            "path": "app.py",
                            "content": "first version",
                        },
                    )
                ],
            ),
            make_response(
                thinking="The tests failed, so I need to fix app.py.",
                tool_calls=[
                    make_tool_call(
                        "write_file",
                        {
                            "path": "app.py",
                            "content": "corrected version",
                        },
                    )
                ],
            ),
            make_response(
                thinking="The second test run passed.",
                content="The issue was fixed and the tests now pass.",
            ),
        ]
    )

    runtime = build_runtime(
        model=model,
        registry=registry,
        repository_root=tmp_path,
        max_turns=10,
    )

    approvals = iter(
        [
            "y",  # first write_file
            "y",  # first run_command
            "y",  # second write_file
            "y",  # second run_command
        ]
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _: next(approvals),
    )

    session = AgentSession()

    result = runtime.run(
        "Fix app.py and make the tests pass.",
        session=session,
        test_command="pytest",
    )

    assert result == (
        "The issue was fixed and the tests now pass."
    )

    assert (
        tmp_path / "app.py"
    ).read_text(encoding="utf-8") == "corrected version"

    assert test_runs == 2

    assert [entry[0] for entry in execution_log] == [
        "write_file",
        "run_command",
        "git_diff",
        "write_file",
        "run_command",
        "git_diff",
    ]

    assert len(model.calls) == 3

    first_review_messages = model.calls[1]
    second_review_messages = model.calls[2]

    first_feedback = "\n".join(
        str(message.get("content", ""))
        for message in first_review_messages
    )

    second_feedback = "\n".join(
        str(message.get("content", ""))
        for message in second_review_messages
    )

    assert "Tests failed." in first_feedback
    assert "AssertionError: expected 2 but got 3" in first_feedback

    assert "Tests passed." in second_feedback


def test_phase12_runtime_runner_command_uses_safety(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Verify that AgentRunner test commands do not bypass
    the Phase 10 approval layer.
    """

    execution_log: list[str] = []

    def run_command_impl(**kwargs: Any) -> ToolResult:
        execution_log.append(kwargs["command"])

        return ToolResult(
            success=True,
            output="tests passed",
            metadata={
                "exit_code": 0,
            },
        )

    def git_diff_impl(**kwargs: Any) -> ToolResult:
        return ToolResult(
            success=True,
            output="",
        )

    def write_file_impl(**kwargs: Any) -> ToolResult:
        path = tmp_path / kwargs["path"]
        path.write_text(
            kwargs["content"],
            encoding="utf-8",
        )

        return ToolResult(
            success=True,
            output="written",
        )

    registry = build_registry(
        write_file_impl=write_file_impl,
        run_command_impl=run_command_impl,
        git_diff_impl=git_diff_impl,
    )

    model = FakeModel(
        [
            make_response(
                tool_calls=[
                    make_tool_call(
                        "write_file",
                        {
                            "path": "app.py",
                            "content": "print('ok')",
                        },
                    )
                ]
            ),
            make_response(
                content="Done.",
            ),
        ]
    )

    runtime = build_runtime(
        model=model,
        registry=registry,
        repository_root=tmp_path,
    )

    requested_tools: list[str] = []

    original_check = runtime.safety.check

    def recording_check(
        tool_name: str,
        arguments: dict[str, Any],
    ):
        requested_tools.append(tool_name)
        return original_check(tool_name, arguments)

    monkeypatch.setattr(
        runtime.safety,
        "check",
        recording_check,
    )

    approvals = iter(
        [
            "y",  # write_file
            "y",  # run_command
        ]
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _: next(approvals),
    )

    runtime.run(
        "Create app.py.",
        session=AgentSession(),
        test_command="pytest",
    )

    assert requested_tools == [
        "write_file",
        "write_file",
        "run_command",
        "git_diff",
    ]

    assert execution_log == ["pytest"]


def test_phase12_runtime_runner_does_not_execute_rejected_test_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Verify that rejecting the test command prevents execution.
    """

    executed = False

    def write_file_impl(**kwargs: Any) -> ToolResult:
        path = tmp_path / kwargs["path"]
        path.write_text(
            kwargs["content"],
            encoding="utf-8",
        )

        return ToolResult(
            success=True,
            output="written",
        )

    def run_command_impl(**kwargs: Any) -> ToolResult:
        nonlocal executed
        executed = True

        return ToolResult(
            success=True,
            output="should never run",
        )

    def git_diff_impl(**kwargs: Any) -> ToolResult:
        return ToolResult(
            success=True,
            output="",
        )

    registry = build_registry(
        write_file_impl=write_file_impl,
        run_command_impl=run_command_impl,
        git_diff_impl=git_diff_impl,
    )

    model = FakeModel(
        [
            make_response(
                tool_calls=[
                    make_tool_call(
                        "write_file",
                        {
                            "path": "app.py",
                            "content": "print('ok')",
                        },
                    )
                ]
            ),
            make_response(
                content="Finished.",
            ),
        ]
    )

    runtime = build_runtime(
        model=model,
        registry=registry,
        repository_root=tmp_path,
    )

    approvals = iter(
        [
            "y",  # approve write_file
            "n",  # reject run_command
        ]
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _: next(approvals),
    )

    runtime.run(
        "Create app.py.",
        session=AgentSession(),
        test_command="pytest",
    )

    assert executed is False


def test_phase12_runtime_without_test_command_keeps_phase10_behavior(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Verify backward compatibility with Phase 10.

    A file modification without test_command must not automatically
    trigger Phase 12 self-review.
    """

    execution_log: list[str] = []

    def write_file_impl(**kwargs: Any) -> ToolResult:
        execution_log.append("write_file")

        path = tmp_path / kwargs["path"]
        path.write_text(
            kwargs["content"],
            encoding="utf-8",
        )

        return ToolResult(
            success=True,
            output="written",
        )

    def run_command_impl(**kwargs: Any) -> ToolResult:
        execution_log.append("run_command")

        return ToolResult(
            success=True,
            output="should not run",
        )

    def git_diff_impl(**kwargs: Any) -> ToolResult:
        execution_log.append("git_diff")

        return ToolResult(
            success=True,
            output="should not run",
        )

    registry = build_registry(
        write_file_impl=write_file_impl,
        run_command_impl=run_command_impl,
        git_diff_impl=git_diff_impl,
    )

    model = FakeModel(
        [
            make_response(
                tool_calls=[
                    make_tool_call(
                        "write_file",
                        {
                            "path": "app.py",
                            "content": "print('hello')",
                        },
                    )
                ]
            ),
            make_response(
                content="File created.",
            ),
        ]
    )

    runtime = build_runtime(
        model=model,
        registry=registry,
        repository_root=tmp_path,
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _: "y",
    )

    result = runtime.run(
        "Create app.py.",
        session=AgentSession(),
    )

    assert result == "File created."

    assert execution_log == [
        "write_file",
    ]