from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from reasoning.formatter import format_reasoning_trace


class ReasoningRecorder:
    """Persist model reasoning traces as .reason files."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)

    def create_trace_file(
        self,
        session_id: str,
        turn: int,
    ) -> Path:
        """Generate a unique .reason file path."""

        timestamp = datetime.now(timezone.utc).strftime(
            "%Y%m%d_%H%M%S_%f"
        )

        filename = (
            f"{timestamp}_{session_id}_turn_{turn:04d}.reason"
        )

        return self.directory / filename

    def save(
        self,
        *,
        model: str,
        session_id: str,
        turn: int,
        user_message: str,
        thinking: str,
    ) -> Path:
        """Format and save a reasoning trace."""

        trace_file = self.create_trace_file(
            session_id=session_id,
            turn=turn,
        )

        formatted_trace = format_reasoning_trace(
            model=model,
            session_id=session_id,
            turn=turn,
            user_message=user_message,
            thinking=thinking,
        )

        trace_file.write_text(
            formatted_trace,
            encoding="utf-8",
        )

        return trace_file