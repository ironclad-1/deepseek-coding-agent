from __future__ import annotations

from pathlib import Path

from tools.registry import ToolResult


DEFAULT_MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB

BINARY_CHECK_SIZE = 4096


def _resolve_path(
    repository_root: Path,
    path: str,
) -> Path:
    """
    Resolve a user/model-provided path and ensure that it remains
    inside the repository root.
    """

    if not isinstance(path, str) or not path.strip():
        raise ValueError("File path must be a non-empty string.")

    root = repository_root.resolve()
    candidate = Path(path)

    if not candidate.is_absolute():
        candidate = root / candidate

    candidate = candidate.resolve()

    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise PermissionError(
            f"Access outside repository is not allowed: {path}"
        ) from exc

    return candidate


def _is_binary_file(path: Path) -> bool:
    """
    Perform a small binary-file check.

    This is intentionally conservative. A file containing a NUL
    byte in its first few KB is treated as binary.
    """

    with path.open("rb") as file:
        sample = file.read(BINARY_CHECK_SIZE)

    return b"\x00" in sample


def read_file(
    repository_root: Path,
    path: str,
    start_line: int | None = None,
    end_line: int | None = None,
    max_size: int = DEFAULT_MAX_FILE_SIZE,
) -> ToolResult:
    """
    Read a text file from inside the repository.

    Lines are 1-based and inclusive.

    Examples:

        read_file(root, "README.md")

        read_file(
            root,
            "src/main.py",
            start_line=10,
            end_line=40,
        )
    """

    try:
        resolved_path = _resolve_path(
            repository_root,
            path,
        )

        if not resolved_path.exists():
            return ToolResult(
                success=False,
                error=f"File does not exist: {path}",
            )

        if not resolved_path.is_file():
            return ToolResult(
                success=False,
                error=f"Path is not a file: {path}",
            )

        file_size = resolved_path.stat().st_size

        if file_size > max_size:
            return ToolResult(
                success=False,
                error=(
                    f"File is too large to read: {path} "
                    f"({file_size} bytes > {max_size} bytes)"
                ),
                metadata={
                    "size": file_size,
                    "max_size": max_size,
                },
            )

        if _is_binary_file(resolved_path):
            return ToolResult(
                success=False,
                error=f"Binary files are not supported: {path}",
            )

        content = resolved_path.read_text(
            encoding="utf-8",
        )

        lines = content.splitlines()

        total_lines = len(lines)

        if start_line is None:
            start_line = 1

        if end_line is None:
            end_line = total_lines

        if start_line < 1:
            return ToolResult(
                success=False,
                error="start_line must be greater than or equal to 1.",
            )

        if end_line < start_line:
            return ToolResult(
                success=False,
                error=(
                    "end_line must be greater than or equal "
                    "to start_line."
                ),
            )

        selected_lines = lines[
            start_line - 1 : end_line
        ]

        numbered_content = "\n".join(
            f"{number}: {line}"
            for number, line in enumerate(
                selected_lines,
                start=start_line,
            )
        )

        relative_path = resolved_path.relative_to(
            repository_root.resolve()
        )

        return ToolResult(
            success=True,
            output=numbered_content,
            metadata={
                "path": str(relative_path),
                "start_line": start_line,
                "end_line": min(end_line, total_lines),
                "total_lines": total_lines,
                "size": file_size,
            },
        )

    except UnicodeDecodeError:
        return ToolResult(
            success=False,
            error=f"File is not valid UTF-8 text: {path}",
        )

    except PermissionError as exc:
        return ToolResult(
            success=False,
            error=str(exc),
        )

    except OSError as exc:
        return ToolResult(
            success=False,
            error=f"Unable to read '{path}': {exc}",
        )

    except Exception as exc:
        return ToolResult(
            success=False,
            error=(
                f"Unexpected error while reading "
                f"'{path}': {type(exc).__name__}: {exc}"
            ),
        )