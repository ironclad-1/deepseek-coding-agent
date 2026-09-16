from __future__ import annotations
from pathlib import Path
from tools.registry import ToolResult

DEFAULT_MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB
BINARY_CHECK_SIZE = 4096

def _resolve_path(repository_root: Path, path: str) -> Path:
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
        raise PermissionError(f"Access outside repository is not allowed: {path}") from exc
    return candidate

def _is_binary_file(path: Path) -> bool:
    """
    Perform a small binary-file check.
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
    """
    try:
        resolved_path = _resolve_path(repository_root, path)
        if not resolved_path.exists():
            return ToolResult(success=False, error=f"File does not exist: {path}")
        if not resolved_path.is_file():
            return ToolResult(success=False, error=f"Path is not a file: {path}")
        file_size = resolved_path.stat().st_size
        if file_size > max_size:
            return ToolResult(
                success=False,
                error=f"File is too large to read: {path} ({file_size} bytes > {max_size} bytes)",
                metadata={"size": file_size, "max_size": max_size},
            )
        if _is_binary_file(resolved_path):
            return ToolResult(success=False, error=f"Binary files are not supported: {path}")
        content = resolved_path.read_text(encoding="utf-8")
        lines = content.splitlines()
        total_lines = len(lines)
        if start_line is None:
            start_line = 1
        if end_line is None:
            end_line = total_lines
        if start_line < 1:
            return ToolResult(success=False, error="start_line must be greater than or equal to 1.")
        if end_line < start_line:
            return ToolResult(success=False, error="end_line must be greater than or equal to start_line.")
        selected_lines = lines[start_line - 1:end_line]
        numbered_content = "\n".join(
            f"{number}: {line}"
            for number, line in enumerate(selected_lines, start=start_line)
        )
        relative_path = resolved_path.relative_to(repository_root.resolve())
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
        return ToolResult(success=False, error=f"File is not valid UTF-8 text: {path}")
    except PermissionError as exc:
        return ToolResult(success=False, error=str(exc))
    except OSError as exc:
        return ToolResult(success=False, error=f"Unable to read '{path}': {exc}")
    except Exception as exc:
        return ToolResult(
            success=False,
            error=f"Unexpected error while reading '{path}': {type(exc).__name__}: {exc}",
        )

def write_file(
    repository_root: Path,
    path: str,
    content: str,
    overwrite: bool = False,
    max_size: int = DEFAULT_MAX_FILE_SIZE,
) -> ToolResult:
    """
    Create a UTF-8 text file inside the repository.
    Existing files are protected unless overwrite=True.
    """
    try:
        resolved_path = _resolve_path(repository_root, path)
        if not isinstance(content, str):
            return ToolResult(success=False, error="File content must be a string.")
        content_size = len(content.encode("utf-8"))
        if content_size > max_size:
            return ToolResult(
                success=False,
                error=f"File content is too large: {path} ({content_size} bytes > {max_size} bytes)",
                metadata={"size": content_size, "max_size": max_size},
            )
        if resolved_path.exists():
            if not resolved_path.is_file():
                return ToolResult(success=False, error=f"Path is not a file: {path}")
            if not overwrite:
                return ToolResult(
                    success=False,
                    error=f"File already exists: {path}. Set overwrite=True to replace it.",
                )
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_path.write_text(content, encoding="utf-8")
        relative_path = resolved_path.relative_to(repository_root.resolve())
        return ToolResult(
            success=True,
            output=f"File {'overwritten' if overwrite and resolved_path.exists() else 'created'}: {relative_path}",
            metadata={
                "path": str(relative_path),
                "size": content_size,
                "lines": len(content.splitlines()),
                "overwritten": overwrite,
            },
        )
    except PermissionError as exc:
        return ToolResult(success=False, error=str(exc))
    except OSError as exc:
        return ToolResult(success=False, error=f"Unable to write '{path}': {exc}")
    except Exception as exc:
        return ToolResult(
            success=False,
            error=f"Unexpected error while writing '{path}': {type(exc).__name__}: {exc}",
        )

def edit_file(
    repository_root: Path,
    path: str,
    old_text: str,
    new_text: str,
    max_size: int = DEFAULT_MAX_FILE_SIZE,
) -> ToolResult:
    """
    Replace exactly one occurrence of old_text with new_text.
    The edit is rejected when old_text is missing or occurs more than once.
    """
    try:
        resolved_path = _resolve_path(repository_root, path)
        if not resolved_path.exists():
            return ToolResult(success=False, error=f"File does not exist: {path}")
        if not resolved_path.is_file():
            return ToolResult(success=False, error=f"Path is not a file: {path}")
        file_size = resolved_path.stat().st_size
        if file_size > max_size:
            return ToolResult(
                success=False,
                error=f"File is too large to edit: {path} ({file_size} bytes > {max_size} bytes)",
                metadata={"size": file_size, "max_size": max_size},
            )
        if _is_binary_file(resolved_path):
            return ToolResult(success=False, error=f"Binary files are not supported: {path}")
        if not isinstance(old_text, str) or not old_text:
            return ToolResult(success=False, error="old_text must be a non-empty string.")
        if not isinstance(new_text, str):
            return ToolResult(success=False, error="new_text must be a string.")
        content = resolved_path.read_text(encoding="utf-8")
        occurrence_count = content.count(old_text)
        if occurrence_count == 0:
            return ToolResult(
                success=False,
                error=f"Exact old_text was not found in file: {path}",
            )
        if occurrence_count > 1:
            return ToolResult(
                success=False,
                error=(
                    f"Exact old_text occurs {occurrence_count} times in file: {path}. "
                    "The edit was not applied because the match is ambiguous."
                ),
                metadata={"occurrences": occurrence_count},
            )
        updated_content = content.replace(old_text, new_text, 1)
        updated_size = len(updated_content.encode("utf-8"))
        if updated_size > max_size:
            return ToolResult(
                success=False,
                error=f"Edited file would exceed maximum size: {path} ({updated_size} bytes > {max_size} bytes)",
                metadata={"size": updated_size, "max_size": max_size},
            )
        resolved_path.write_text(updated_content, encoding="utf-8")
        relative_path = resolved_path.relative_to(repository_root.resolve())
        return ToolResult(
            success=True,
            output=f"File edited: {relative_path}",
            metadata={
                "path": str(relative_path),
                "replacements": 1,
                "old_text_length": len(old_text),
                "new_text_length": len(new_text),
                "size": updated_size,
            },
        )
    except UnicodeDecodeError:
        return ToolResult(success=False, error=f"File is not valid UTF-8 text: {path}")
    except PermissionError as exc:
        return ToolResult(success=False, error=str(exc))
    except OSError as exc:
        return ToolResult(success=False, error=f"Unable to edit '{path}': {exc}")
    except Exception as exc:
        return ToolResult(
            success=False,
            error=f"Unexpected error while editing '{path}': {type(exc).__name__}: {exc}",
        )