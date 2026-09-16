from __future__ import annotations

import shlex
import subprocess
from pathlib import Path
from typing import Sequence

from tools.registry import ToolResult

DEFAULT_TIMEOUT = 30
MAX_TIMEOUT = 120

ALLOWED_COMMANDS = {
    "python",
    "python.exe",
    "py",
    "py.exe",
    "pytest",
    "pytest.exe",
    "git",
    "git.exe",
    "pip",
    "pip.exe",
}

BLOCKED_COMMANDS = {
    "del",
    "erase",
    "rd",
    "rmdir",
    "format",
    "shutdown",
    "restart-computer",
    "stop-computer",
    "remove-item",
    "set-content",
    "add-content",
    "invoke-expression",
    "iex",
    "start-process",
}


def _parse_command(command: str | Sequence[str]) -> list[str]:
    if isinstance(command, str):
        if not command.strip():
            raise ValueError("Command must be a non-empty string.")
        return shlex.split(command, posix=False)

    if isinstance(command, Sequence) and not isinstance(command, (str, bytes)):
        parts = [str(part) for part in command]
        if not parts:
            raise ValueError("Command must contain at least one argument.")
        return parts

    raise TypeError("Command must be a string or sequence of arguments.")


def _validate_command(parts: list[str]) -> None:
    executable = Path(parts[0]).name.lower()

    if executable in BLOCKED_COMMANDS:
        raise PermissionError(
            f"Command is blocked for safety: {executable}"
        )

    if executable not in ALLOWED_COMMANDS:
        raise PermissionError(
            f"Command is not allowed: {executable}. "
            f"Allowed commands: {', '.join(sorted(ALLOWED_COMMANDS))}"
        )

    lowered_parts = [part.lower() for part in parts]

    dangerous_patterns = {
        "&&",
        "||",
        ";",
        "|",
        ">",
        ">>",
        "<",
        "2>",
        "2>>",
        "powershell",
        "cmd.exe",
        "cmd",
        "start",
        "curl",
        "wget",
        "invoke-webrequest",
        "invoke-restmethod",
    }

    for part in lowered_parts:
        if part in dangerous_patterns:
            raise PermissionError(
                f"Shell chaining or external command execution is not allowed: {part}"
            )


def run_command(
    repository_root: Path,
    command: str | Sequence[str],
    timeout: int = DEFAULT_TIMEOUT,
) -> ToolResult:
    """
    Execute one allowed command inside the repository.

    The command must use an executable from ALLOWED_COMMANDS.
    Shell execution is disabled.
    """
    try:
        if not isinstance(repository_root, Path):
            repository_root = Path(repository_root)

        repository_root = repository_root.resolve()

        if not repository_root.exists():
            return ToolResult(
                success=False,
                error=f"Repository root does not exist: {repository_root}",
            )

        if not repository_root.is_dir():
            return ToolResult(
                success=False,
                error=f"Repository root is not a directory: {repository_root}",
            )

        if not isinstance(timeout, int):
            return ToolResult(
                success=False,
                error="timeout must be an integer.",
            )

        if timeout < 1:
            return ToolResult(
                success=False,
                error="timeout must be greater than or equal to 1 second.",
            )

        timeout = min(timeout, MAX_TIMEOUT)

        parts = _parse_command(command)
        _validate_command(parts)

        process = subprocess.run(
            parts,
            cwd=repository_root,
            shell=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )

        stdout = process.stdout or ""
        stderr = process.stderr or ""

        output_parts = [
            f"Command: {' '.join(parts)}",
            f"Exit code: {process.returncode}",
        ]

        if stdout:
            output_parts.append(f"STDOUT:\n{stdout}")

        if stderr:
            output_parts.append(f"STDERR:\n{stderr}")

        return ToolResult(
            success=process.returncode == 0,
            output="\n\n".join(output_parts),
            error=(
                None
                if process.returncode == 0
                else f"Command exited with code {process.returncode}."
            ),
            metadata={
                "command": parts,
                "exit_code": process.returncode,
                "timeout": timeout,
                "cwd": str(repository_root),
            },
        )

    except ValueError as exc:
        return ToolResult(
            success=False,
            error=str(exc),
        )

    except TypeError as exc:
        return ToolResult(
            success=False,
            error=str(exc),
        )

    except PermissionError as exc:
        return ToolResult(
            success=False,
            error=str(exc),
        )

    except FileNotFoundError:
        return ToolResult(
            success=False,
            error=f"Command executable not found: {command}",
        )

    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""

        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")

        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")

        return ToolResult(
            success=False,
            output=(
                f"Command timed out after {timeout} seconds."
                + (f"\n\nSTDOUT:\n{stdout}" if stdout else "")
                + (f"\n\nSTDERR:\n{stderr}" if stderr else "")
            ),
            error=f"Command timed out after {timeout} seconds.",
            metadata={
                "command": _parse_command(command),
                "timeout": timeout,
                "cwd": str(repository_root),
                "timed_out": True,
            },
        )

    except OSError as exc:
        return ToolResult(
            success=False,
            error=f"Unable to execute command: {exc}",
        )

    except Exception as exc:
        return ToolResult(
            success=False,
            error=(
                f"Unexpected error while executing command: "
                f"{type(exc).__name__}: {exc}"
            ),
        )