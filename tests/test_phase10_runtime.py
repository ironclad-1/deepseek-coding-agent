from __future__ import annotations

import builtins
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import agent.runtime as runtime_module
from agent.model import ModelResponse
from agent.runtime import AgentRuntime
from tools.registry import Tool, ToolRegistry


@dataclass
class FakeFunction:
    name: str
    arguments: dict[str, Any]


@dataclass
class FakeToolCall:
    function: FakeFunction


class FakeRecorder:
    def save(
        self,
        *,
        model: str,
        session_id: str,
        turn: int,
        user_message: str,
        thinking: str,
    ) -> Path:
        return Path(f"fake_reasoning_turn_{turn}.reason")


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def make_tool_response(
    tool_name: str,
    arguments: dict[str, Any],
) -> ModelResponse:
    return ModelResponse(
        model="test-model",
        thinking="test reasoning",
        content="",
        tool_calls=[
            FakeToolCall(
                function=FakeFunction(
                    name=tool_name,
                    arguments=arguments,
                )
            )
        ],
        raw=None,
    )


def make_final_response(content: str) -> ModelResponse:
    return ModelResponse(
        model="test-model",
        thinking="test reasoning",
        content=content,
        tool_calls=None,
        raw=None,
    )


def build_runtime(
    execution_counts: dict[str, int],
) -> AgentRuntime:
    tools = ToolRegistry()

    def fake_read_file(path: str):
        execution_counts["read_file"] += 1
        from tools.registry import ToolResult

        return ToolResult(
            success=True,
            output=f"Read: {path}",
        )

    def fake_write_file(
        path: str,
        content: str,
    ):
        execution_counts["write_file"] += 1
        from tools.registry import ToolResult

        return ToolResult(
            success=True,
            output=f"Wrote: {path}",
        )

    def fake_run_command(command: str):
        execution_counts["run_command"] += 1
        from tools.registry import ToolResult

        return ToolResult(
            success=True,
            output=f"Executed: {command}",
        )

    tools.register(
        Tool(
            name="read_file",
            description="Read a file.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                    },
                },
                "required": ["path"],
            },
            function=fake_read_file,
        )
    )

    tools.register(
        Tool(
            name="write_file",
            description="Write a file.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                    },
                    "content": {
                        "type": "string",
                    },
                },
                "required": ["path", "content"],
            },
            function=fake_write_file,
        )
    )

    tools.register(
        Tool(
            name="run_command",
            description="Run a command.",
            parameters={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                    },
                },
                "required": ["command"],
            },
            function=fake_run_command,
        )
    )

    return AgentRuntime(
        model=object(),
        tools=tools,
        recorder=FakeRecorder(),
        max_turns=5,
    )


def run_with_responses(
    runtime: AgentRuntime,
    responses: list[ModelResponse],
) -> str:
    response_iterator = iter(responses)

    def fake_call_model(session: Any) -> ModelResponse:
        try:
            return next(response_iterator)
        except StopIteration as exc:
            raise AssertionError(
                "Runtime requested more model responses than expected."
            ) from exc

    runtime._call_model = fake_call_model
    return runtime.run("Execute the test task.")


def main() -> None:
    print("=" * 60)
    print("PHASE 10 — RUNTIME SAFETY TEST")
    print("=" * 60)

    original_input = builtins.input
    original_save_result = runtime_module.save_result

    runtime_module.save_result = (
        lambda content, session_id, turn: Path(
            f"fake_result_turn_{turn}.result"
        )
    )

    try:
        with tempfile.TemporaryDirectory(
            prefix="phase10_runtime_"
        ):

            print("\n1. SAFE tool executes automatically...")

            execution_counts = {
                "read_file": 0,
                "write_file": 0,
                "run_command": 0,
            }

            runtime = build_runtime(execution_counts)

            def unexpected_input(prompt: str = "") -> str:
                raise AssertionError(
                    "SAFE tool unexpectedly requested approval."
                )

            builtins.input = unexpected_input

            answer = run_with_responses(
                runtime,
                [
                    make_tool_response(
                        "read_file",
                        {
                            "path": "test.txt",
                        },
                    ),
                    make_final_response(
                        "Safe tool completed."
                    ),
                ],
            )

            check(
                execution_counts["read_file"] == 1,
                "SAFE read_file was not executed exactly once.",
            )

            check(
                execution_counts["write_file"] == 0,
                "Unexpected write_file execution.",
            )

            check(
                execution_counts["run_command"] == 0,
                "Unexpected run_command execution.",
            )

            check(
                answer == "Safe tool completed.",
                "Unexpected final answer.",
            )

            print("✓ SAFE tool executed exactly once")
            print("✓ SAFE tool did not request approval")

            print("\n2. Approval-required tool executes after approval...")

            execution_counts = {
                "read_file": 0,
                "write_file": 0,
                "run_command": 0,
            }

            runtime = build_runtime(execution_counts)

            def approve(prompt: str = "") -> str:
                return "y"

            builtins.input = approve

            answer = run_with_responses(
                runtime,
                [
                    make_tool_response(
                        "write_file",
                        {
                            "path": "approved.txt",
                            "content": "approved",
                        },
                    ),
                    make_final_response(
                        "Approved tool completed."
                    ),
                ],
            )

            check(
                execution_counts["write_file"] == 1,
                "Approved write_file was not executed exactly once.",
            )

            check(
                answer == "Approved tool completed.",
                "Unexpected final answer after approval.",
            )

            print("✓ Approval was requested")
            print("✓ Approved tool executed exactly once")

            print("\n3. Rejected approval prevents execution...")

            execution_counts = {
                "read_file": 0,
                "write_file": 0,
                "run_command": 0,
            }

            runtime = build_runtime(execution_counts)

            def reject(prompt: str = "") -> str:
                return "n"

            builtins.input = reject

            answer = run_with_responses(
                runtime,
                [
                    make_tool_response(
                        "write_file",
                        {
                            "path": "rejected.txt",
                            "content": "should not run",
                        },
                    ),
                    make_final_response(
                        "Rejected tool completed."
                    ),
                ],
            )

            check(
                execution_counts["write_file"] == 0,
                "Rejected write_file was executed.",
            )

            check(
                answer == "Rejected tool completed.",
                "Unexpected final answer after rejection.",
            )

            print("✓ Approval was requested")
            print("✓ Rejected tool was NOT executed")

            print("\n4. DENIED commands never reach the tool...")

            denied_commands = [
                "powershell Get-ChildItem",
                "powershell.exe Get-ChildItem",
                "cmd.exe /c dir",
                "cmd /c dir",
                "del test.txt",
                "erase test.txt",
                "rmdir test_folder",
                "rd test_folder",
                "format C:",
                "shutdown /s",
                "restart-computer",
                "remove-item test.txt",
            ]

            for command in denied_commands:
                execution_counts = {
                    "read_file": 0,
                    "write_file": 0,
                    "run_command": 0,
                }

                runtime = build_runtime(execution_counts)

                def unexpected_denied_input(
                    prompt: str = "",
                ) -> str:
                    raise AssertionError(
                        f"DENIED command requested approval: {command}"
                    )

                builtins.input = unexpected_denied_input

                run_with_responses(
                    runtime,
                    [
                        make_tool_response(
                            "run_command",
                            {
                                "command": command,
                            },
                        ),
                        make_final_response(
                            "Denied command handled."
                        ),
                    ],
                )

                check(
                    execution_counts["run_command"] == 0,
                    f"DENIED command was executed: {command}",
                )

                print(
                    f"✓ DENIED and not executed: {command}"
                )

            print("\n5. Unknown executable is denied...")

            execution_counts = {
                "read_file": 0,
                "write_file": 0,
                "run_command": 0,
            }

            runtime = build_runtime(execution_counts)

            builtins.input = unexpected_denied_input

            run_with_responses(
                runtime,
                [
                    make_tool_response(
                        "run_command",
                        {
                            "command": "unknown_executable test",
                        },
                    ),
                    make_final_response(
                        "Unknown executable denied."
                    ),
                ],
            )

            check(
                execution_counts["run_command"] == 0,
                "Unknown executable reached the tool.",
            )

            print("✓ Unknown executable was not executed")

            print("\n6. Unknown tool is denied...")

            execution_counts = {
                "read_file": 0,
                "write_file": 0,
                "run_command": 0,
            }

            runtime = build_runtime(execution_counts)

            builtins.input = unexpected_denied_input

            run_with_responses(
                runtime,
                [
                    make_tool_response(
                        "unknown_tool",
                        {},
                    ),
                    make_final_response(
                        "Unknown tool denied."
                    ),
                ],
            )

            check(
                execution_counts["read_file"] == 0,
                "Unknown tool caused read_file execution.",
            )

            check(
                execution_counts["write_file"] == 0,
                "Unknown tool caused write_file execution.",
            )

            check(
                execution_counts["run_command"] == 0,
                "Unknown tool caused run_command execution.",
            )

            print("✓ Unknown tool was not executed")

            print("\n7. Approved command reaches the tool exactly once...")

            execution_counts = {
                "read_file": 0,
                "write_file": 0,
                "run_command": 0,
            }

            runtime = build_runtime(execution_counts)

            def approve_command(prompt: str = "") -> str:
                return "yes"

            builtins.input = approve_command

            answer = run_with_responses(
                runtime,
                [
                    make_tool_response(
                        "run_command",
                        {
                            "command": "python test.py",
                        },
                    ),
                    make_final_response(
                        "Approved command completed."
                    ),
                ],
            )

            check(
                execution_counts["run_command"] == 1,
                "Approved command was not executed exactly once.",
            )

            check(
                answer == "Approved command completed.",
                "Unexpected final answer.",
            )

            print("✓ Approval was requested")
            print("✓ Approved command executed exactly once")

    finally:
        builtins.input = original_input
        runtime_module.save_result = original_save_result

    print("\n" + "=" * 60)
    print("PHASE 10 RUNTIME TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()