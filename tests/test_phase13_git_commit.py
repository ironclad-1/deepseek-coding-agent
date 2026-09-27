from __future__ import annotations

from types import SimpleNamespace

import agent.runtime as runtime_module
from agent.model import ModelResponse
from agent.runtime import AgentRuntime
from safety.approval import ApprovalManager
from tools.registry import ToolResult


class FakeModel:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def chat(
        self,
        messages,
        *,
        think,
        stream,
        tools,
    ):
        self.calls.append(
            {
                "messages": list(messages),
                "think": think,
                "stream": stream,
                "tools": tools,
            }
        )

        if not self.responses:
            raise AssertionError(
                "FakeModel received an unexpected extra call."
            )

        return self.responses.pop(0)


class FakeTools:
    def __init__(self):
        self.executed = []

    def schemas(self):
        return []

    def execute(
        self,
        tool_name,
        arguments,
    ):
        self.executed.append(
            {
                "tool_name": tool_name,
                "arguments": arguments,
            }
        )

        return ToolResult(
            success=True,
            output=f"{tool_name} executed successfully.",
        )


class FakeRecorder:
    def save(
        self,
        *,
        model,
        session_id,
        turn,
        user_message,
        thinking,
    ):
        return f"fake-reason-{turn}.reason"


def make_tool_call(
    tool_name: str,
    arguments: dict,
):
    return SimpleNamespace(
        function=SimpleNamespace(
            name=tool_name,
            arguments=arguments,
        )
    )


def make_model_response(
    *,
    content: str = "",
    tool_calls=None,
):
    return ModelResponse(
        model="fake-model",
        thinking="test thinking",
        content=content,
        tool_calls=tool_calls or [],
        raw={},
    )


def create_runtime(
    model,
    tools,
    *,
    max_turns: int = 5,
):
    return AgentRuntime(
        model=model,
        tools=tools,
        recorder=FakeRecorder(),
        safety=ApprovalManager(),
        max_turns=max_turns,
    )


def test_git_add_requires_change_proposal_approval(
    monkeypatch,
):
    tools = FakeTools()

    git_add_call = make_tool_call(
        "git_add",
        {
            "paths": [
                "agent/runtime.py",
                "agent/planner.py",
            ],
        },
    )

    first_response = make_model_response(
        content=(
            "WHAT:\n"
            "Stage the Phase 13 implementation files.\n\n"
            "WHY:\n"
            "The completed changes need to be staged for the "
            "next Git workflow step."
        ),
        tool_calls=[git_add_call],
    )

    second_response = make_model_response(
        content="The requested files were staged.",
    )

    model = FakeModel(
        [
            first_response,
            second_response,
        ]
    )

    runtime = create_runtime(
        model=model,
        tools=tools,
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _: "y",
    )

    monkeypatch.setattr(
        runtime_module,
        "save_result",
        lambda **kwargs: "fake-result.txt",
    )

    result = runtime.run(
        "Stage the Phase 13 implementation files.",
    )

    assert result == "The requested files were staged."

    assert len(tools.executed) == 1

    assert (
        tools.executed[0]["tool_name"]
        == "git_add"
    )

    assert tools.executed[0]["arguments"]["paths"] == [
        "agent/runtime.py",
        "agent/planner.py",
    ]


def test_rejected_git_add_is_never_executed(
    monkeypatch,
):
    tools = FakeTools()

    git_add_call = make_tool_call(
        "git_add",
        {
            "paths": [
                "agent/runtime.py",
            ],
        },
    )

    first_response = make_model_response(
        content=(
            "WHAT:\n"
            "Stage agent/runtime.py.\n\n"
            "WHY:\n"
            "The change is ready to be staged."
        ),
        tool_calls=[git_add_call],
    )

    second_response = make_model_response(
        content=(
            "Understood. I will not stage any files."
        ),
    )

    model = FakeModel(
        [
            first_response,
            second_response,
        ]
    )

    runtime = create_runtime(
        model=model,
        tools=tools,
    )

    responses = iter(
        [
            "n",
            "Do not stage anything yet.",
        ]
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _: next(responses),
    )

    monkeypatch.setattr(
        runtime_module,
        "save_result",
        lambda **kwargs: "fake-result.txt",
    )

    result = runtime.run(
        "Stage agent/runtime.py.",
    )

    assert result == (
        "Understood. I will not stage any files."
    )

    # Critical assertion:
    # rejected git_add must never reach the tool layer.
    assert tools.executed == []

    second_call_messages = model.calls[1]["messages"]

    rejection_messages = [
        message
        for message in second_call_messages
        if (
            message.get("role") == "user"
            and "rejected" in message.get(
                "content",
                "",
            ).lower()
        )
    ]

    assert rejection_messages

    rejection_text = rejection_messages[-1]["content"]

    assert (
        "Do not stage anything yet."
        in rejection_text
    )


def test_git_commit_requires_change_proposal_approval(
    monkeypatch,
):
    tools = FakeTools()

    git_commit_call = make_tool_call(
        "git_commit",
        {
            "message": "Complete Phase 13 approval workflow",
        },
    )

    first_response = make_model_response(
        content=(
            "WHAT:\n"
            "Create the Phase 13 Git commit.\n\n"
            "WHY:\n"
            "The approved implementation is ready to be "
            "recorded in Git history."
        ),
        tool_calls=[git_commit_call],
    )

    second_response = make_model_response(
        content=(
            "The Phase 13 commit was created."
        ),
    )

    model = FakeModel(
        [
            first_response,
            second_response,
        ]
    )

    runtime = create_runtime(
        model=model,
        tools=tools,
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _: "y",
    )

    monkeypatch.setattr(
        runtime_module,
        "save_result",
        lambda **kwargs: "fake-result.txt",
    )

    result = runtime.run(
        "Create a commit for the approved Phase 13 changes.",
    )

    assert result == (
        "The Phase 13 commit was created."
    )

    assert len(tools.executed) == 1

    assert (
        tools.executed[0]["tool_name"]
        == "git_commit"
    )

    assert (
        tools.executed[0]["arguments"]["message"]
        == "Complete Phase 13 approval workflow"
    )


def test_git_add_and_git_commit_share_one_change_approval(
    monkeypatch,
):
    tools = FakeTools()

    git_add_call = make_tool_call(
        "git_add",
        {
            "paths": [
                "agent/runtime.py",
                "agent/change_manager.py",
                "safety/change_gate.py",
            ],
        },
    )

    git_commit_call = make_tool_call(
        "git_commit",
        {
            "message": "Add Phase 13 change approval workflow",
        },
    )

    first_response = make_model_response(
        content=(
            "WHAT:\n"
            "Stage the Phase 13 implementation and create its "
            "Git commit.\n\n"
            "WHY:\n"
            "The completed changes need to be staged and recorded "
            "in Git history."
        ),
        tool_calls=[
            git_add_call,
            git_commit_call,
        ],
    )

    second_response = make_model_response(
        content=(
            "The Phase 13 changes were staged and committed."
        ),
    )

    model = FakeModel(
        [
            first_response,
            second_response,
        ]
    )

    runtime = create_runtime(
        model=model,
        tools=tools,
    )

    approval_count = 0

    def approve_once(_):
        nonlocal approval_count

        approval_count += 1

        return "y"

    monkeypatch.setattr(
        "builtins.input",
        approve_once,
    )

    monkeypatch.setattr(
        runtime_module,
        "save_result",
        lambda **kwargs: "fake-result.txt",
    )

    result = runtime.run(
        "Stage the Phase 13 changes and commit them.",
    )

    assert result == (
        "The Phase 13 changes were staged and committed."
    )

    # One human approval for the entire coherent Git operation set.
    assert approval_count == 1

    assert len(tools.executed) == 2

    assert [
        call["tool_name"]
        for call in tools.executed
    ] == [
        "git_add",
        "git_commit",
    ]

    assert (
        tools.executed[1]["arguments"]["message"]
        == "Add Phase 13 change approval workflow"
    )