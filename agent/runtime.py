from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent.change_manager import ChangeApprovalResult
from agent.model import ModelProvider, ModelResponse
from agent.planner import ChangePlanner
from agent.runner import AgentRunner
from agent.session import AgentSession
from config import PROJECT_ROOT
from reasoning.recorder import ReasoningRecorder
from results.recorder import save_result
from safety.approval import ApprovalDecision, ApprovalManager
from safety.change_gate import ChangeGate
from tools.registry import ToolRegistry, ToolResult


class AgentRuntime:
    """
    Core agent loop.

    High-level flow:

        User task
            ↓
        Model
            ↓
        Thinking / reasoning trace
            ↓
        Tool calls?
         ↙       ↘
       Yes       No
        ↓         ↓
      Safety    Final answer
        ↓
    ┌──────────────────────────────────────┐
    │ SAFE                                 │
    │   → execute immediately             │
    │                                      │
    │ DENIED                               │
    │   → reject execution                │
    │                                      │
    │ REQUIRE_APPROVAL                    │
    │   → split LOCAL / REMOTE operations │
    └──────────────────────────────────────┘
                    ↓
        ┌──────────────────────────────┐
        │ LOCAL PROPOSAL               │
        │ write/edit/git_add/commit    │
        │ run_command                  │
        └──────────────────────────────┘
                    ↓
               user approval
                    ↓
              execute local
                    ↓
        self-review / next model turn
                    ↓
        ┌──────────────────────────────┐
        │ REMOTE PUSH PROPOSAL         │
        │ git_push only                │
        └──────────────────────────────┘
                    ↓
               user approval
                    ↓
                  push
                    ↓
                Model / final

    A git_push requested in the same model response as actual file
    modifications is deferred until the local modification workflow
    has completed. This prevents pushing unvalidated local changes.
    """

    # Actual repository-content modifications.
    # These trigger Phase 12 self-review when test_command is supplied.
    MODIFYING_TOOLS = {
        "write_file",
        "edit_file",
    }

    PUSH_TOOLS = {
        "git_push",
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
        change_planner: ChangePlanner | None = None,
        change_gate: ChangeGate | None = None,
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

        self.change_planner = (
            change_planner
            if change_planner is not None
            else ChangePlanner()
        )

        self.change_gate = (
            change_gate
            if change_gate is not None
            else ChangeGate()
        )

        self._stop_requested = False

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
            3. Feed results back to the model
            4. Allow the model to fix failures
        """

        if session is None:
            session = AgentSession()

        self._stop_requested = False

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
                    user_message=user_message,
                )

                if self._stop_requested:
                    final_answer = (
                        "Execution was cancelled by the user. "
                        "No further proposed changes were executed."
                    )

                    result_path = save_result(
                        content=final_answer,
                        session_id=session.session_id,
                        turn=session.turn,
                    )

                    print(f"[RESULT] {result_path}")

                    return final_answer

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
        user_message: str,
    ) -> bool:
        """
        Process all tool calls from one model response.

        SAFE tools:
            Execute immediately.

        DENIED tools:
            Never execute.

        Local REQUIRE_APPROVAL tools:
            Are grouped into one local ChangeProposal.

        git_push:
            Is separated into its own remote ChangeProposal.

        Returns:
            True when at least one actual file-modifying tool
            completed successfully.
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

        safe_calls: list[Any] = []
        denied_calls: list[Any] = []
        approval_calls: list[Any] = []

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

                self._record_tool_result(
                    session=session,
                    tool_name=tool_name,
                    result=result,
                )

                continue

            print(f"[TOOL REQUEST] {tool_name}")
            print(
                "[ARGS] "
                f"{json.dumps(arguments, default=str)}"
            )

            safety_check = self.safety.check(
                tool_name,
                arguments,
            )

            print(
                f"[SAFETY] {safety_check.decision.value} "
                f"- {safety_check.reason}"
            )

            if safety_check.decision == ApprovalDecision.DENIED:
                denied_calls.append(tool_call)
                continue

            if (
                safety_check.decision
                == ApprovalDecision.REQUIRE_APPROVAL
            ):
                approval_calls.append(tool_call)
                continue

            safe_calls.append(tool_call)

        # ---------------------------------------------------------
        # SAFE TOOLS
        # ---------------------------------------------------------

        changes_made = False

        for tool_call in safe_calls:
            function = tool_call.function

            tool_name = function.name
            arguments = function.arguments

            result = self._execute_tool_direct(
                tool_name=tool_name,
                arguments=arguments,
            )

            if (
                result.success
                and tool_name in self.MODIFYING_TOOLS
            ):
                changes_made = True

            self._record_tool_result(
                session=session,
                tool_name=tool_name,
                result=result,
            )

        # ---------------------------------------------------------
        # DENIED TOOLS
        # ---------------------------------------------------------

        for tool_call in denied_calls:
            function = tool_call.function

            tool_name = function.name
            arguments = function.arguments

            safety_check = self.safety.check(
                tool_name,
                arguments,
            )

            result = ToolResult(
                success=False,
                error=(
                    f"Tool '{tool_name}' was denied by the "
                    f"safety policy: {safety_check.reason}"
                ),
            )

            print(
                f"[SAFETY DENIED] "
                f"{tool_name}: {safety_check.reason}"
            )

            self._record_tool_result(
                session=session,
                tool_name=tool_name,
                result=result,
            )

        if not approval_calls:
            return changes_made

        # ---------------------------------------------------------
        # SPLIT LOCAL / REMOTE APPROVAL OPERATIONS
        # ---------------------------------------------------------

        local_calls: list[Any] = []
        push_calls: list[Any] = []

        for tool_call in approval_calls:
            tool_name = tool_call.function.name

            if tool_name in self.PUSH_TOOLS:
                push_calls.append(tool_call)
            else:
                local_calls.append(tool_call)

        model_summary, model_reason = (
            self._extract_model_proposal(
                response.content or ""
            )
        )

        # ---------------------------------------------------------
        # LOCAL CHANGE PROPOSAL
        # ---------------------------------------------------------

        if local_calls:
            local_proposal = (
                self.change_planner.build_local_proposal(
                    user_message=user_message,
                    tool_calls=local_calls,
                    model_summary=model_summary,
                    model_reason=model_reason,
                )
            )

            if local_proposal is None or local_proposal.is_empty:
                self._withhold_tool_calls(
                    session=session,
                    tool_calls=local_calls,
                    reason=(
                        "The local approval-required operations "
                        "could not be converted into a valid change "
                        "proposal."
                    ),
                )

                # Never continue into a push when the local proposal
                # could not safely be constructed.
                self._withhold_tool_calls(
                    session=session,
                    tool_calls=push_calls,
                    reason=(
                        "The requested push was withheld because "
                        "the preceding local change proposal could "
                        "not be constructed safely."
                    ),
                )

                return changes_made

            (
                local_result,
                local_changes_made,
                local_all_success,
            ) = self._request_and_execute_proposal(
                session=session,
                proposal=local_proposal,
            )

            changes_made = (
                changes_made
                or local_changes_made
            )

            if local_result is None:
                return changes_made

            if local_result.cancelled:
                # Withhold any push requested in the same response.
                self._withhold_tool_calls(
                    session=session,
                    tool_calls=push_calls,
                    reason=(
                        "The requested push was withheld because "
                        "the local change proposal was cancelled."
                    ),
                )

                self._stop_requested = True

                return changes_made

            if local_result.rejected:
                # A rejected local proposal invalidates the same-turn
                # push request. The model must decide what to do next
                # after receiving the rejection reason.
                self._withhold_tool_calls(
                    session=session,
                    tool_calls=push_calls,
                    reason=(
                        "The requested push was withheld because "
                        "the local repository change proposal was "
                        "rejected by the user."
                    ),
                )

                return changes_made

            # Approved local proposal, but one or more operations failed.
            if not local_all_success:
                self._withhold_tool_calls(
                    session=session,
                    tool_calls=push_calls,
                    reason=(
                        "The requested push was withheld because "
                        "one or more local repository operations "
                        "failed."
                    ),
                )

                session.add_message(
                    {
                        "role": "user",
                        "content": (
                            "The local change proposal was approved, "
                            "but one or more local operations failed. "
                            "Do not push yet. Inspect the tool results, "
                            "recover from the failure, and only request "
                            "a push after the local repository state is "
                            "correct."
                        ),
                    }
                )

                return changes_made

            # -----------------------------------------------------
            # IMPORTANT PUSH BOUNDARY
            # -----------------------------------------------------

            if push_calls and local_changes_made:
                # Actual file changes just occurred. Do not push in
                # the same model turn. The run() method will perform
                # Phase 12 self-review after this method returns, and
                # the model can request git_push again on the next turn.
                self._withhold_tool_calls(
                    session=session,
                    tool_calls=push_calls,
                    reason=(
                        "The requested push was deferred because "
                        "local repository modifications were just "
                        "completed. The changes must be validated "
                        "before a remote push."
                    ),
                )

                session.add_message(
                    {
                        "role": "user",
                        "content": (
                            "The local repository changes were completed. "
                            "The git push requested in the same model "
                            "response was deferred. Complete validation "
                            "and review first. Request git_push again "
                            "only when the local changes are ready to "
                            "be sent to the remote repository."
                        ),
                    }
                )

                return changes_made

            # If the local proposal contained only Git staging/commit
            # operations and all succeeded, a push can be proposed now.
            if push_calls:
                return (
                    changes_made
                    or self._handle_push_calls(
                        session=session,
                        user_message=user_message,
                        push_calls=push_calls,
                        model_summary=model_summary,
                        model_reason=model_reason,
                    )
                )

            return changes_made

        # ---------------------------------------------------------
        # PUSH-ONLY RESPONSE
        # ---------------------------------------------------------

        if push_calls:
            return (
                changes_made
                or self._handle_push_calls(
                    session=session,
                    user_message=user_message,
                    push_calls=push_calls,
                    model_summary=model_summary,
                    model_reason=model_reason,
                )
            )

        return changes_made

    def _handle_push_calls(
        self,
        *,
        session: AgentSession,
        user_message: str,
        push_calls: list[Any],
        model_summary: str | None,
        model_reason: str | None,
    ) -> bool:
        """
        Present and execute a dedicated remote-push proposal.

        git_push is never grouped into the local repository-change
        proposal.
        """

        push_proposal = (
            self.change_planner.build_push_proposal(
                user_message=user_message,
                tool_calls=push_calls,
                model_summary=model_summary,
                model_reason=model_reason,
            )
        )

        if push_proposal is None or push_proposal.is_empty:
            self._withhold_tool_calls(
                session=session,
                tool_calls=push_calls,
                reason=(
                    "The remote push request could not be converted "
                    "into a valid push proposal."
                ),
            )

            return False

        print()
        print("=" * 60)
        print("REMOTE PUSH APPROVAL")
        print("=" * 60)

        approval_result, _, all_success = (
            self._request_and_execute_proposal(
                session=session,
                proposal=push_proposal,
            )
        )

        if approval_result is None:
            return False

        if approval_result.cancelled:
            self._stop_requested = True
            return False

        if approval_result.rejected:
            return False

        if not all_success:
            session.add_message(
                {
                    "role": "user",
                    "content": (
                        "The remote push was approved but the push "
                        "operation failed. Inspect the tool result "
                        "before attempting another push."
                    ),
                }
            )

        return False

    def _request_and_execute_proposal(
        self,
        *,
        session: AgentSession,
        proposal: Any,
    ) -> tuple[
        ChangeApprovalResult | None,
        bool,
        bool,
    ]:
        """
        Ask for approval for one proposal and execute it only after
        approval.

        Returns:

            (
                approval_result,
                changes_made,
                all_operations_succeeded,
            )
        """

        if proposal is None or proposal.is_empty:
            return None, False, False

        approval_result = self.change_gate.request_approval(
            proposal
        )

        print(
            f"[CHANGE DECISION] "
            f"{approval_result.decision.value}"
        )

        if approval_result.approved:
            print(
                "[CHANGE PROPOSAL] "
                "Approved. Executing proposed operations..."
            )

            return (
                approval_result,
                *self._execute_proposal(
                    session=session,
                    proposal=proposal,
                ),
            )

        if approval_result.rejected:
            self._handle_change_rejection(
                session=session,
                approval_result=approval_result,
                proposal=proposal,
            )

            return (
                approval_result,
                False,
                False,
            )

        if approval_result.cancelled:
            self._record_cancelled_proposal(
                session=session,
                proposal=proposal,
            )

            print(
                "[CHANGE PROPOSAL] "
                "Cancelled. No proposed changes were executed."
            )

            return (
                approval_result,
                False,
                False,
            )

        # Fail closed.
        self._record_cancelled_proposal(
            session=session,
            proposal=proposal,
        )

        return (
            approval_result,
            False,
            False,
        )

    def _execute_proposal(
        self,
        *,
        session: AgentSession,
        proposal: Any,
    ) -> tuple[bool, bool]:
        """
        Execute every operation in an already-approved proposal.

        The safety policy is rechecked immediately before each actual
        execution.

        Returns:

            (
                changes_made,
                all_operations_succeeded,
            )
        """

        changes_made = False
        all_success = True

        for operation in proposal.operations:
            result = self._execute_approved_tool(
                tool_name=operation.tool_name,
                arguments=operation.arguments,
            )

            if not result.success:
                all_success = False

            if (
                result.success
                and operation.tool_name in self.MODIFYING_TOOLS
            ):
                changes_made = True

            self._record_tool_result(
                session=session,
                tool_name=operation.tool_name,
                result=result,
            )

        return changes_made, all_success

    def _handle_change_rejection(
        self,
        *,
        session: AgentSession,
        approval_result: ChangeApprovalResult,
        proposal: Any,
    ) -> None:
        """
        Handle a rejected change proposal.

        Critical rule:

            Rejected proposals are NEVER executed.

        The rejection reason is sent back to the model so it can:

            - revise the proposal,
            - ask for clarification,
            - or stop.
        """

        print()
        print("=" * 60)
        print(
            "[CHANGE PROPOSAL] "
            "Rejected. None of the proposed operations were executed."
        )
        print("=" * 60)

        for operation in proposal.operations:
            result = ToolResult(
                success=False,
                error=(
                    "Tool execution was withheld because the user "
                    "rejected the proposed changes."
                ),
            )

            self._record_tool_result(
                session=session,
                tool_name=operation.tool_name,
                result=result,
            )

        model_feedback = approval_result.to_model_context()

        print("[MODEL FEEDBACK]")
        print(model_feedback)

        session.add_message(
            {
                "role": "user",
                "content": model_feedback,
            }
        )

    def _record_cancelled_proposal(
        self,
        *,
        session: AgentSession,
        proposal: Any,
    ) -> None:
        """
        Record that a proposal's operations were cancelled without
        execution.
        """

        for operation in proposal.operations:
            result = ToolResult(
                success=False,
                error=(
                    "Execution cancelled by the user. "
                    "The proposed operation was not executed."
                ),
            )

            self._record_tool_result(
                session=session,
                tool_name=operation.tool_name,
                result=result,
            )

    def _withhold_tool_calls(
        self,
        *,
        session: AgentSession,
        tool_calls: list[Any],
        reason: str,
    ) -> None:
        """
        Record that tool calls were intentionally not executed.

        This does not represent a failure of the tool itself.
        The model needs to know the operation was deliberately
        withheld by the runtime.
        """

        for tool_call in tool_calls:
            function = tool_call.function

            result = ToolResult(
                success=False,
                error=reason,
            )

            self._record_tool_result(
                session=session,
                tool_name=function.name,
                result=result,
            )

            print(
                f"[TOOL WITHHELD] "
                f"{function.name}: {reason}"
            )

    def _execute_tool_direct(
        self,
        *,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> ToolResult:
        """
        Execute a tool that has already been classified as SAFE.
        """

        try:
            print(f"[TOOL EXECUTE] {tool_name}")

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

    def _execute_approved_tool(
        self,
        *,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> ToolResult:
        """
        Execute a tool after the user has approved the proposal.

        The low-level safety policy is checked again.

        SAFE and REQUIRE_APPROVAL are executable here.
        REQUIRE_APPROVAL has already been approved through ChangeGate.

        DENIED is always blocked.
        """

        safety_check = self.safety.check(
            tool_name,
            arguments,
        )

        print(
            f"[SAFETY RECHECK] "
            f"{safety_check.decision.value} "
            f"- {safety_check.reason}"
        )

        if safety_check.decision == ApprovalDecision.DENIED:
            result = ToolResult(
                success=False,
                error=(
                    f"Tool '{tool_name}' was denied by the "
                    f"safety policy during final execution check: "
                    f"{safety_check.reason}"
                ),
            )

            print(
                f"[SAFETY DENIED] "
                f"{tool_name}: {safety_check.reason}"
            )

            return result

        return self._execute_tool_direct(
            tool_name=tool_name,
            arguments=arguments,
        )

    def _record_tool_result(
        self,
        *,
        session: AgentSession,
        tool_name: str,
        result: ToolResult,
    ) -> None:
        """
        Record a tool result in the model conversation.
        """

        print(
            f"[TOOL RESULT] "
            f"{'SUCCESS' if result.success else 'FAILED'}"
        )

        if not result.success:
            print(
                f"[TOOL ERROR] "
                f"{result.error or 'Unknown error'}"
            )

        session.add_message(
            {
                "role": "tool",
                "name": tool_name,
                "content": result.as_message(),
            }
        )

    def _extract_model_proposal(
        self,
        content: str,
    ) -> tuple[str | None, str | None]:
        """
        Extract WHAT and WHY from model response content.

        Expected format:

            WHAT:
            ...

            WHY:
            ...

        Files and operations remain derived from structured tool calls.
        """

        if not content.strip():
            return None, None

        what = self._extract_section(
            content,
            "WHAT",
        )

        why = self._extract_section(
            content,
            "WHY",
        )

        return what, why

    @staticmethod
    def _extract_section(
        content: str,
        section_name: str,
    ) -> str | None:
        """
        Extract a named section from model output.
        """

        lines = content.splitlines()

        target = section_name.strip().upper()

        start_index: int | None = None

        for index, line in enumerate(lines):
            normalized = line.strip()

            if normalized.startswith("#"):
                normalized = normalized.lstrip("#").strip()

            if normalized.upper() == f"{target}:":
                start_index = index + 1
                break

        if start_index is None:
            return None

        collected: list[str] = []

        boundary_names = {
            "WHAT",
            "WHY",
            "FILES",
            "OPERATIONS",
        }

        for line in lines[start_index:]:
            normalized = line.strip()

            check_line = normalized

            if check_line.startswith("#"):
                check_line = check_line.lstrip("#").strip()

            upper_line = check_line.upper()

            if (
                ":" in upper_line
                and upper_line.split(":", 1)[0].strip()
                in boundary_names
            ):
                break

            collected.append(line)

        value = "\n".join(collected).strip()

        return value or None

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

    def _execute_tool_with_safety(
        self,
        *,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> ToolResult:
        """
        Phase 10 safety gateway used by internal runner operations.

        Model-requested repository changes use ChangeGate instead.
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
            return self.tools.execute(
                tool_name,
                arguments,
            )

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

    def _request_approval(
        self,
        *,
        tool_name: str,
        arguments: dict[str, Any],
        reason: str,
    ) -> bool:
        """
        Ask the user for approval for runner-internal operations.

        Model-requested repository changes do not use this method.
        They use ChangeGate and structured ChangeProposal objects.
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