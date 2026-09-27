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


def make_runtime(
    model,
    tools,
):
    return AgentRuntime(
        model=model,
        tools=tools,
        recorder=FakeRecorder(),
        safety=ApprovalManager(),
        max_turns=5,
    )


def test_local_changes_and_push_require_separate_approvals(
    monkeypatch,
):
    tools = FakeTools()

    write_call = make_tool_call(
        "write_file",
        {
            "path": "workspace/test.txt",
            "content": "test",
        },
    )

    push_call = make_tool_call(
        "git_push",
        {
            "remote": "origin",
            "branch": "main",
        },
    )

    first_response = make_model_response(
        content=(
            "WHAT:\n"
            "Create the requested file and push the completed "
            "repository changes.\n\n"
            "WHY:\n"
            "The task requires both the local change and the "
            "remote update."
        ),
        tool_calls=[
            write_call,
            push_call,
        ],
    )

    second_response = make_model_response(
        content=(
            "The local change is complete. "
            "The push was deferred until validation."
        ),
    )

    model = FakeModel(
        [
            first_response,
            second_response,
        ]
    )

    runtime = make_runtime(
        model,
        tools,
    )

    approvals = iter(
        [
            "y",
        ]
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _: next(approvals),
    )

    monkeypatch.setattr(
        runtime_module,
        "save_result",
        lambda **kwargs: "fake-result.txt",
    )

    result = runtime.run(
        "Create the file and push the changes.",
    )

    assert result == (
        "The local change is complete. "
        "The push was deferred until validation."
    )

    # Only the local write executes.
    assert [
        call["tool_name"]
        for call in tools.executed
    ] == [
        "write_file",
    ]


def test_push_only_gets_its_own_approval(
    monkeypatch,
):
    tools = FakeTools()

    push_call = make_tool_call(
        "git_push",
        {
            "remote": "origin",
            "branch": "main",
        },
    )

    first_response = make_model_response(
        content=(
            "WHAT:\n"
            "Push the current branch to origin.\n\n"
            "WHY:\n"
            "The completed commit is ready to be sent remotely."
        ),
        tool_calls=[push_call],
    )

    second_response = make_model_response(
        content="The branch was pushed successfully.",
    )

    model = FakeModel(
        [
            first_response,
            second_response,
        ]
    )

    runtime = make_runtime(
        model,
        tools,
    )

    approvals = iter(["y"])

    monkeypatch.setattr(
        "builtins.input",
        lambda _: next(approvals),
    )

    monkeypatch.setattr(
        runtime_module,
        "save_result",
        lambda **kwargs: "fake-result.txt",
    )

    result = runtime.run(
        "Push the completed commit to origin/main.",
    )

    assert result == (
        "The branch was pushed successfully."
    )

    assert [
        call["tool_name"]
        for call in tools.executed
    ] == [
        "git_push",
    ]


def test_rejected_push_is_not_executed(
    monkeypatch,
):
    tools = FakeTools()

    push_call = make_tool_call(
        "git_push",
        {
            "remote": "origin",
            "branch": "main",
        },
    )

    first_response = make_model_response(
        content=(
            "WHAT:\n"
            "Push the completed branch to origin.\n\n"
            "WHY:\n"
            "The user requested the repository to be published."
        ),
        tool_calls=[push_call],
    )

    second_response = make_model_response(
        content=(
            "Understood. I will not push the repository."
        ),
    )

    model = FakeModel(
        [
            first_response,
            second_response,
        ]
    )

    runtime = make_runtime(
        model,
        tools,
    )

    approvals = iter(
        [
            "n",
            "Do not push anything yet.",
        ]
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _: next(approvals),
    )

    monkeypatch.setattr(
        runtime_module,
        "save_result",
        lambda **kwargs: "fake-result.txt",
    )

    result = runtime.run(
        "Push the repository to origin.",
    )

    assert result == (
        "Understood. I will not push the repository."
    )

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
        "Do not push anything yet."
        in rejection_text
    )


def test_rejected_local_change_also_withholds_same_turn_push(
    monkeypatch,
):
    tools = FakeTools()

    write_call = make_tool_call(
        "write_file",
        {
            "path": "workspace/test.txt",
            "content": "test",
        },
    )

    push_call = make_tool_call(
        "git_push",
        {
            "remote": "origin",
            "branch": "main",
        },
    )

    first_response = make_model_response(
        content=(
            "WHAT:\n"
            "Create the requested file and push it.\n\n"
            "WHY:\n"
            "The task requests the local file and remote update."
        ),
        tool_calls=[
            write_call,
            push_call,
        ],
    )

    second_response = make_model_response(
        content=(
            "Understood. I will not make or push any changes."
        ),
    )

    model = FakeModel(
        [
            first_response,
            second_response,
        ]
    )

    runtime = make_runtime(
        model,
        tools,
    )

    approvals = iter(
        [
            "n",
            "Do not make or push any changes.",
        ]
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _: next(approvals),
    )

    monkeypatch.setattr(
        runtime_module,
        "save_result",
        lambda **kwargs: "fake-result.txt",
    )

    result = runtime.run(
        "Create the file and push the changes.",
    )

    assert result == (
        "Understood. I will not make or push any changes."
    )

    # Neither write_file nor git_push executes.
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
        "Do not make or push any changes."
        in rejection_text
    )