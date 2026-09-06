from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from repository.scanner import (
    DEFAULT_IGNORED_DIRECTORIES,
    RepositoryScanner,
)

from tools.registry import ToolResult

BINARY_CHECK_SIZE = 4096
DEFAULT_MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB
DEFAULT_MAX_RESULTS = 100


@dataclass
class SearchMatch:
    """One repository search match."""

    path: Path
    line_number: int
    line: str

    def format(self, repository_root: Path) -> str:
        """Format the match for the agent/model."""

        relative_path = self.path.relative_to(repository_root)

        return (
            f"{relative_path}:{self.line_number}: "
            f"{self.line.strip()}"
        )


class RepositorySearch:
    """Search text content throughout a repository."""

    def __init__(
        self,
        repository_root: str | Path,
        *,
        ignored_directories: set[str] | None = None,
        max_file_size: int = DEFAULT_MAX_FILE_SIZE,
    ) -> None:
        self.repository_root = Path(
            repository_root
        ).expanduser().resolve()

        self.ignored_directories = (
            set(ignored_directories)
            if ignored_directories is not None
            else DEFAULT_IGNORED_DIRECTORIES.copy()
        )

        self.max_file_size = max_file_size

        self.scanner = RepositoryScanner(
            self.repository_root,
            ignored_directories=self.ignored_directories,
        )

    def search(
        self,
        query: str,
        *,
        case_sensitive: bool = False,
        max_results: int = DEFAULT_MAX_RESULTS,
    ) -> ToolResult:
        """
        Search repository files for a text query.

        Returns matching file paths, line numbers, and lines.
        """

        try:
            self._validate()

            if not isinstance(query, str) or not query.strip():
                return ToolResult(
                    success=False,
                    error="Search query must be a non-empty string.",
                )

            if max_results < 1:
                return ToolResult(
                    success=False,
                    error="max_results must be at least 1.",
                )

            matches: list[SearchMatch] = []

            for path in self._iter_files():

                if len(matches) >= max_results:
                    break

                if not self._is_searchable_file(path):
                    continue

                file_size = path.stat().st_size

                if file_size > self.max_file_size:
                    continue

                try:
                    with path.open(
                        "r",
                        encoding="utf-8",
                        errors="strict",
                    ) as file:
                        for line_number, line in enumerate(
                            file,
                            start=1,
                        ):
                            haystack = (
                                line
                                if case_sensitive
                                else line.lower()
                            )

                            needle = (
                                query
                                if case_sensitive
                                else query.lower()
                            )

                            if needle in haystack:
                                matches.append(
                                    SearchMatch(
                                        path=path,
                                        line_number=line_number,
                                        line=line.rstrip("\n\r"),
                                    )
                                )

                            if len(matches) >= max_results:
                                break

                except (UnicodeDecodeError, OSError):
                    continue

            output = "\n".join(
                match.format(self.repository_root)
                for match in matches
            )

            if not output:
                output = f"No matches found for: {query}"

            return ToolResult(
                success=True,
                output=output,
                metadata={
                    "query": query,
                    "match_count": len(matches),
                    "max_results": max_results,
                    "case_sensitive": case_sensitive,
                },
            )

        except Exception as exc:
            return ToolResult(
                success=False,
                error=(
                    f"Search failed: "
                    f"{type(exc).__name__}: {exc}"
                ),
            )

    def _validate(self) -> None:
        """Validate the repository root."""

        if not self.repository_root.exists():
            raise FileNotFoundError(
                f"Repository does not exist: "
                f"{self.repository_root}"
            )

        if not self.repository_root.is_dir():
            raise NotADirectoryError(
                f"Repository path is not a directory: "
                f"{self.repository_root}"
            )

    def _iter_files(self) -> Iterator[Path]:
        """Yield searchable files."""

        for path in self.repository_root.rglob("*"):
            if not path.is_file():
                continue

            if self._should_ignore(path):
                continue

            yield path

    def _should_ignore(self, path: Path) -> bool:
        """Check whether a path belongs to an ignored directory."""

        return any(
            part in self.ignored_directories
            for part in path.relative_to(
                self.repository_root
            ).parts
        )

    @staticmethod
    def _is_searchable_file(path: Path) -> bool:
        """Check whether a file appears to be text."""

        try:
            with path.open("rb") as file:
                sample = file.read(BINARY_CHECK_SIZE)

            return b"\x00" not in sample

        except OSError:
            return False