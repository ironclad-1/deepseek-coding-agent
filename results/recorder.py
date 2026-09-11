from __future__ import annotations

from datetime import datetime
from pathlib import Path

from config import RESULTS_DIR


def save_result(
    content: str,
    session_id: str,
    turn: int,
) -> Path:
    """
    Save the final agent answer to the .results directory.
    """

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    result_path = (
        RESULTS_DIR
        / f"{timestamp}_{session_id}_turn_{turn:04d}.result"
    )

    result_text = (
        "============================================================\n"
        "AGENT FINAL RESULT\n"
        "============================================================\n\n"
        f"Timestamp: {datetime.now().isoformat()}\n"
        f"Session: {session_id}\n"
        f"Turn: {turn}\n\n"
        "FINAL ANSWER\n"
        "------------------------------------------------------------\n"
        f"{content.strip()}\n"
    )

    result_path.write_text(result_text, encoding="utf-8")

    return result_path