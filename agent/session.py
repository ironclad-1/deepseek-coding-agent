from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass
class AgentSession:
    """
    Stores the state of one agent task.

    A session contains the conversation history, model-turn count,
    and number of tools executed during the task.
    """

    session_id: str = field(default_factory=lambda: uuid4().hex)
    messages: list[dict[str, Any]] = field(default_factory=list)
    turn: int = 0
    tool_calls: int = 0

    def add_message(self, message: dict[str, Any]) -> None:
        """Add a message to the conversation history."""
        self.messages.append(message)

    def next_turn(self) -> int:
        """Increment and return the next model turn number."""
        self.turn += 1
        return self.turn