from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent.model import ModelProvider, ModelResponse
from agent.runner import AgentRunner
from agent.session import AgentSession
from config import PROJECT_ROOT
from reasoning.recorder import ReasoningRecorder
from results.recorder import save_result
from safety.approval import ApprovalDecision, ApprovalManager
from tools.registry import ToolRegistry, ToolResult


class AgentRuntime:
    """
    Core agent loop.

    Flow:

        User
          ↓
        Model
          ↓
        Thinking
          ↓
        Tool call?
        ↙       ↘
      Yes       No
       ↓         ↓
    Safety    Final answer
       ↓
    Approval?
    ↙      ↘
   Yes      No
   ↓         ↓
 Execute   Reject
   ↓         ↓
 Result ←────┘
   ↓
 Model
   ↓
 Changes made?
   ↓
 Self-review
   ├── Run tests
   └── Review git diff
   ↓
 Feed results to model
   ↓
 repeat
    """

    MODIFYING_TOOLS = {
        "write_file",
        "edit_file",
    }

    def __init__(
        self,
        model: ModelProvider,
        tools: ToolRegistry,
        recorder: ReasoningRecorder,
        *,
        max_turns: int = 20,
        safety: ApprovalManager | None = None,
        repository_root: Path | None = None,
    ) -> None:
        self.model = model
        self.tools = tools
        self.recorder = recorder
        self.max_turns = max_turns
        self.safety = safety or ApprovalManager()

        self.repository_root = (
            repository_root.resolve()
            if repository_root is not None
            else PROJECT_ROOT.resolve()
        )

        self.runner = AgentRunner(
            repository_root=self.repository_root,
            command_executor=self._run_runner_command,
            diff_provider=self._review_runner_diff,
        )

    def run(
        self,
        user_message: str,
        *,
        session: AgentSession | None = None,
        test_command: str | None = None,
        test_timeout: int = 30,
    ) -> str:
        """
        Run an agent task until the model produces a final answer.

        When test_command is supplied, successful file modifications
        trigger the Phase 12 self-review cycle:

            1. Run tests
            2. Review git diff
            3. Feed the results back to the model
            4. Allow the model to fix failures
        """

        if session is None:
            session = AgentSession()

        session.add_message(
            {
                "role": "user",
                "content": user_message,
            }
        )

        for _ in range(self.max_turns):
            turn = session.next_turn()

            print(f"\n[MODEL TURN {turn}]")
            print("-" * 60)

            response = self._call_model(session)

            self._record_reasoning(
                session=session,
                user_message=user_message,
                response=response,
                turn=turn,
            )

            if response.tool_calls:
                changes_made = self._handle_tool_calls(
                    session=session,
                    response=response,
                )

                if changes_made and test_command:
                    self._run_self_review(
                        session=session,
                        test_command=test_command,
                        test_timeout=test_timeout,
                    )

                continue

            final_answer = response.content.strip()

            if final_answer:
                result_path = save_result(
                    content=final_answer,
                    session_id=session.session_id,
                    turn=session.turn,
                )

                print(f"[RESULT] {result_path}")

                return final_answer

            print(
                "[MODEL] Empty response received; retrying..."
            )

            session.add_message(
                {
                    "role": "user",
                    "content": (
                        "Continue the task. Use the available tools as "
                        "required and provide a final answer when finished."
                    ),
                }
            )

        raise RuntimeError(
            f"Agent exceeded maximum turn limit ({self.max_turns})."
        )

    def _call_model(
        self,
        session: AgentSession,
    ) -> ModelResponse:
        """
        Send the current conversation to the model.
        """

        response = self.model.chat(
            session.messages,
            think=True,
            stream=False,
            tools=self.tools.schemas(),
        )

        if not isinstance(response, ModelResponse):
            raise RuntimeError(
                "Expected ModelResponse from ModelProvider."
            )

        return response

    def _record_reasoning(
        self,
        *,
        session: AgentSession,
        user_message: str,
        response: ModelResponse,
        turn: int,
    ) -> None:
        """
        Save the model-provided thinking trace.
        """

        trace_file = self.recorder.save(
            model=response.model,
            session_id=session.session_id,
            turn=turn,
            user_message=user_message,
            thinking=response.thinking,
        )

        print(f"[REASONING] {trace_file}")

    def _handle_tool_calls(
        self,
        *,
        session: AgentSession,
        response: ModelResponse,
    ) -> bool:
        """
        Check safety for every tool requested by the model,
        request user approval when necessary, and execute
        only permitted tools.

        Returns True when at least one modifying tool completed
        successfully.
        """

        assistant_tool_calls: list[dict[str, Any]] = []

        for tool_call in response.tool_calls:
            function = tool_call.function

            assistant_tool_calls.append(
                {
                    "function": {
                        "name": function.name,
                        "arguments": function.arguments,
                    }
                }
            )

        session.add_message(
            {
                "role": "assistant",
                "content": response.content or "",
                "tool_calls": assistant_tool_calls,
            }
        )

        changes_made = False

        for tool_call in response.tool_calls:
            function = tool_call.function

            tool_name = function.name
            arguments = function.arguments

            if not isinstance(arguments, dict):
                result = ToolResult(
                    success=False,
                    error=(
                        f"Arguments for tool '{tool_name}' "
                        "must be a dictionary."
                    ),
                )

                print(
                    f"[TOOL ERROR] {result.error}"
                )

                session.add_message(
                    {
                        "role": "tool",
                        "name": tool_name,
                        "content": result.as_message(),
                    }
                )

                continue

            print(f"[TOOL] {tool_name}")
            print(
                "[ARGS] "
                f"{json.dumps(arguments, default=str)}"
            )

            result = self._execute_tool_with_safety(
                tool_name=tool_name,
                arguments=arguments,
            )

            if (
                result.success
                and tool_name in self.MODIFYING_TOOLS
            ):
                changes_made = True

            session.add_message(
                {
                    "role": "tool",
                    "name": tool_name,
                    "content": result.as_message(),
                }
            )

        return changes_made

    def _execute_tool_with_safety(
        self,
        *,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> ToolResult:
        """
        Central Phase 10 safety gateway.

        Every tool execution, including Phase 12 runner operations,
        must pass through this method.
        """

        safety_check = self.safety.check(
            tool_name,
            arguments,
        )

        print(
            f"[SAFETY] {safety_check.decision.value} "
            f"- {safety_check.reason}"
        )

        if safety_check.decision == ApprovalDecision.DENIED:
            result = ToolResult(
                success=False,
                error=(
                    f"Tool '{tool_name}' was denied by the "
                    f"safety policy: {safety_check.reason}"
                ),
            )

            print(
                f"[SAFETY DENIED] {safety_check.reason}"
            )

            return result

        if (
            safety_check.decision
            == ApprovalDecision.REQUIRE_APPROVAL
        ):
            approved = self._request_approval(
                tool_name=tool_name,
                arguments=arguments,
                reason=safety_check.reason,
            )

            if not approved:
                result = ToolResult(
                    success=False,
                    error=(
                        f"User denied execution of tool "
                        f"'{tool_name}'."
                    ),
                )

                print(
                    f"[APPROVAL] User denied: {tool_name}"
                )

                return result

            print(
                f"[APPROVAL] User approved: {tool_name}"
            )

        try:
            result = self.tools.execute(
                tool_name,
                arguments,
            )

            return result

        except Exception as exc:
            result = ToolResult(
                success=False,
                error=(
                    f"Tool '{tool_name}' failed: "
                    f"{type(exc).__name__}: {exc}"
                ),
            )

            print(
                f"[TOOL ERROR] {result.error}"
            )

            return result

        finally:
            print()

    def _run_runner_command(
        self,
        *,
        command: str,
        timeout: int = 30,
    ) -> ToolResult:
        """
        Execute a Phase 12 test command through the
        Phase 10 safety layer.
        """

        return self._execute_tool_with_safety(
            tool_name="run_command",
            arguments={
                "command": command,
                "timeout": timeout,
            },
        )

    def _review_runner_diff(self) -> ToolResult:
        """
        Obtain git diff through the Phase 10 safety gateway.
        """

        return self._execute_tool_with_safety(
            tool_name="git_diff",
            arguments={},
        )

    def _run_self_review(
        self,
        *,
        session: AgentSession,
        test_command: str,
        test_timeout: int,
    ) -> None:
        """
        Run the Phase 12 validation cycle after file modifications.
        """

        print()
        print("=" * 60)
        print("PHASE 12 SELF-REVIEW")
        print("=" * 60)

        validation = self.runner.validate(
            test_command=test_command,
            timeout=test_timeout,
        )

        test_feedback = self.runner.format_test_feedback(
            validation.test_result
        )

        review_feedback = self.runner.format_review_feedback(
            validation.review_result
        )

        print("[SELF-REVIEW]")
        print(test_feedback)
        print(review_feedback)

        feedback_parts = [
            "Phase 12 self-review has completed.",
            "",
            test_feedback,
            "",
            review_feedback,
        ]

        if validation.error:
            feedback_parts.extend(
                [
                    "",
                    f"Validation error: {validation.error}",
                ]
            )

        if validation.tests_passed:
            feedback_parts.extend(
                [
                    "",
                    (
                        "Tests passed. Review the diff and continue "
                        "the task. Make further changes only if required."
                    ),
                ]
            )
        else:
            feedback_parts.extend(
                [
                    "",
                    (
                        "Tests failed. Inspect the failure output, "
                        "identify the cause, make the necessary fixes, "
                        "and run the tests again."
                    ),
                ]
            )

        session.add_message(
            {
                "role": "user",
                "content": "\n".join(feedback_parts),
            }
        )

    def _request_approval(
        self,
        *,
        tool_name: str,
        arguments: dict[str, Any],
        reason: str,
    ) -> bool:
        """
        Ask the user for approval before executing a
        tool classified as requiring approval.
        """

        print()
        print("=" * 60)
        print("APPROVAL REQUIRED")
        print("=" * 60)
        print(f"Tool: {tool_name}")
        print(f"Reason: {reason}")
        print(
            "Arguments: "
            f"{json.dumps(arguments, indent=2, default=str)}"
        )
        print("=" * 60)

        while True:
            response = input(
                "Approve this tool execution? [y/n]: "
            ).strip().lower()

            if response in {"y", "yes"}:
                return True

            if response in {"n", "no"}:
                return False

            print("Please enter 'y' or 'n'.")