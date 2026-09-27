from __future__ import annotations

from types import SimpleNamespace

import agent.runtime as runtime_module
from agent.model import ModelResponse
from agent.runtime import AgentRuntime
from agent.session import AgentSession
from config import PROJECT_ROOT
from reasoning.recorder import ReasoningRecorder
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

    def execute(self, tool_name, arguments):
        self.executed.append(
            {
                "tool_name": tool_name,
                "arguments": arguments,
            }
        )

        return ToolResult(
            success=True,
            output="Fake tool executed.",
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


def test_rejected_change_is_never_executed_and_reason_reaches_model(
    monkeypatch,
):
    tools = FakeTools()

    edit_call = make_tool_call(
        "edit_file",
        {
            "path": "calculator.py",
            "old_text": "return a - b",
            "new_text": "return a + b",
        },
    )

    first_response = make_model_response(
        content=(
            "WHAT:\n"
            "Add the addition operation.\n\n"
            "WHY:\n"
            "The current implementation only supports subtraction."
        ),
        tool_calls=[edit_call],
    )

    second_response = make_model_response(
        content=(
            "Understood. I will not make any changes. "
            "I will stop here."
        ),
    )

    model = FakeModel(
        [
            first_response,
            second_response,
        ]
    )

    runtime = AgentRuntime(
        model=model,
        tools=tools,
        recorder=FakeRecorder(),
        safety=ApprovalManager(),
        repository_root=PROJECT_ROOT,
        max_turns=5,
    )

    responses = iter(
        [
            "n",
            "Do not make any changes. I only wanted inspection.",
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
        "Add an addition operation to the calculator.",
    )

    assert result == (
        "Understood. I will not make any changes. "
        "I will stop here."
    )

    # Critical safety assertion:
    # the rejected edit_file must never have reached the tool layer.
    assert tools.executed == []

    # The model must receive the user's actual rejection reason.
    second_call_messages = model.calls[1]["messages"]

    rejection_messages = [
        message
        for message in second_call_messages
        if message.get("role") == "user"
        and "rejected" in message.get("content", "").lower()
    ]

    assert rejection_messages

    rejection_text = rejection_messages[-1]["content"]

    assert (
        "Do not make any changes"
        in rejection_text
    )

    assert (
        "I only wanted inspection"
        in rejection_text
    )


def test_approved_change_is_executed(monkeypatch):
    tools = FakeTools()

    write_call = make_tool_call(
        "write_file",
        {
            "path": "hello.txt",
            "content": "hello",
            "overwrite": False,
        },
    )

    first_response = make_model_response(
        content=(
            "WHAT:\n"
            "Create hello.txt.\n\n"
            "WHY:\n"
            "The user requested the file."
        ),
        tool_calls=[write_call],
    )

    second_response = make_model_response(
        content="The requested file was created successfully.",
    )

    model = FakeModel(
        [
            first_response,
            second_response,
        ]
    )

    runtime = AgentRuntime(
        model=model,
        tools=tools,
        recorder=FakeRecorder(),
        safety=ApprovalManager(),
        repository_root=PROJECT_ROOT,
        max_turns=5,
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
        "Create hello.txt containing hello.",
    )

    assert result == (
        "The requested file was created successfully."
    )

    assert len(tools.executed) == 1
    assert tools.executed[0]["tool_name"] == "write_file"

    assert (
        tools.executed[0]["arguments"]["path"]
        == "hello.txt"
    )


def test_multiple_approval_required_changes_use_one_approval(
    monkeypatch,
):
    tools = FakeTools()

    edit_call = make_tool_call(
        "edit_file",
        {
            "path": "calculator.py",
            "old_text": "return a - b",
            "new_text": "return a + b",
        },
    )

    write_call = make_tool_call(
        "write_file",
        {
            "path": "tests/test_calculator.py",
            "content": "def test_add(): pass",
        },
    )

    first_response = make_model_response(
        content=(
            "WHAT:\n"
            "Add the addition implementation and its regression test.\n\n"
            "WHY:\n"
            "The requested functionality is missing."
        ),
        tool_calls=[
            edit_call,
            write_call,
        ],
    )

    second_response = make_model_response(
        content="Both requested changes were completed.",
    )

    model = FakeModel(
        [
            first_response,
            second_response,
        ]
    )

    runtime = AgentRuntime(
        model=model,
        tools=tools,
        recorder=FakeRecorder(),
        safety=ApprovalManager(),
        repository_root=PROJECT_ROOT,
        max_turns=5,
    )

    input_count = 0

    def approve_once(_):
        nonlocal input_count
        input_count += 1
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
        "Add addition support and a regression test.",
    )

    assert result == (
        "Both requested changes were completed."
    )

    # One ChangeGate approval for the coherent proposal.
    assert input_count == 1

    # Both approved operations execute.
    assert len(tools.executed) == 2

    assert [
        call["tool_name"]
        for call in tools.executed
    ] == [
        "edit_file",
        "write_file",
    ]