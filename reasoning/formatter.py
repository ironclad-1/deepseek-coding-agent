from __future__ import annotations

from datetime import datetime, timezone


def format_reasoning_trace(
    *,
    model: str,
    session_id: str,
    turn: int,
    user_message: str,
    thinking: str,
) -> str:
    """Format a model reasoning trace for a .reason file."""

    timestamp = datetime.now(timezone.utc).isoformat()

    return (
        "============================================================\n"
        "DEEPSEEK REASONING TRACE\n"
        "============================================================\n\n"
        f"Timestamp : {timestamp}\n"
        f"Model     : {model}\n"
        f"Session   : {session_id}\n"
        f"Turn      : {turn}\n\n"
        "USER REQUEST\n"
        "------------------------------------------------------------\n"
        f"{user_message}\n\n"
        "THINKING TRACE\n"
        "------------------------------------------------------------\n"
        f"{thinking}\n"
    )