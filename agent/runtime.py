from __future__ import annotations

import json
from typing import Any

from agent.model import ModelProvider, ModelResponse
from agent.session import AgentSession
from reasoning.recorder import ReasoningRecorder
from tools.registry import ToolRegistry
from results.recorder import save_result


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
    Tool      Final answer
       ↓
    Result
       ↓
     Model
       ↓
     repeat
    """

    def __init__(
        self,
        model: ModelProvider,
        tools: ToolRegistry,
        recorder: ReasoningRecorder,
        *,
        max_turns: int = 20,
    ) -> None:
        self.model = model
        self.tools = tools
        self.recorder = recorder
        self.max_turns = max_turns

    def run(
        self,
        user_message: str,
        *,
        session: AgentSession | None = None,
    ) -> str:
        """
        Run an agent task until the model produces a final answer.
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
                self._handle_tool_calls(
                    session=session,
                    response=response,
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
    ) -> None:
        """
        Execute every tool requested by the model and add the
        resulting messages to the conversation.
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

        # Record the assistant message that requested the tools.
        session.add_message(
            {
                "role": "assistant",
                "content": response.content or "",
                "tool_calls": assistant_tool_calls,
            }
        )

        for tool_call in response.tool_calls:
            function = tool_call.function

            tool_name = function.name
            arguments = function.arguments

            if not isinstance(arguments, dict):
                raise RuntimeError(
                    f"Arguments for tool '{tool_name}' must be a dictionary."
                )

            print(f"[TOOL] {tool_name}")
            print(
                "[ARGS] "
                f"{json.dumps(arguments, default=str)}"
            )

            try:
                result = self.tools.execute(
                    tool_name,
                    arguments,
                )

                session.tool_calls += 1

            except Exception as exc:
                result = (
                    f"Tool '{tool_name}' failed: "
                    f"{type(exc).__name__}: {exc}"
                )

                print(f"[TOOL ERROR] {result}")

            else:
                print(f"[RESULT] {result}")

            # Return the tool result to the model.
            session.add_message(
                {
                    "role": "tool",
                    "name": tool_name,
                    "content": result.as_message(),
                }
            )