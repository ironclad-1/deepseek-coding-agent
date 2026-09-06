from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RepositoryContext:
    """
    Structural information discovered about a repository.
    """

    root: Path
    is_git_repository: bool = False

    files: list[Path] = field(default_factory=list)
    directories: list[Path] = field(default_factory=list)

    extensions: dict[str, int] = field(default_factory=dict)
    languages: dict[str, int] = field(default_factory=dict)

    project_files: list[Path] = field(default_factory=list)
    test_files: list[Path] = field(default_factory=list)
    test_directories: list[Path] = field(default_factory=list)

    git_info: dict[str, str] = field(default_factory=dict)

    def file_count(self) -> int:
        """Return the number of discovered files."""
        return len(self.files)

    def directory_count(self) -> int:
        """Return the number of discovered directories."""
        return len(self.directories)

    def _display_path(self, path: Path) -> str:
        """
        Convert a stored repository path into a display-friendly
        relative path.

        The scanner normally stores paths relative to the repository
        root. This method also safely handles absolute paths.
        """

        if path.is_absolute():
            try:
                return str(path.relative_to(self.root))
            except ValueError:
                return str(path)

        return str(path)

    def summary(self) -> str:
        """Return a human-readable repository summary."""

        lines = [
            "============================================================",
            "REPOSITORY SUMMARY",
            "============================================================",
            f"Root              : {self.root}",
            f"Git repository    : {self.is_git_repository}",
            f"Files             : {self.file_count()}",
            f"Directories       : {self.directory_count()}",
            "",
            "LANGUAGES",
            "------------------------------------------------------------",
        ]

        if self.languages:
            for language, count in sorted(
                self.languages.items(),
                key=lambda item: item[1],
                reverse=True,
            ):
                lines.append(
                    f"{language:<18}: {count}"
                )
        else:
            lines.append("None detected")

        lines.extend(
            [
                "",
                "PROJECT FILES",
                "------------------------------------------------------------",
            ]
        )

        if self.project_files:
            for path in self.project_files:
                lines.append(
                    self._display_path(path)
                )
        else:
            lines.append("None detected")

        lines.extend(
            [
                "",
                "TEST FILES",
                "------------------------------------------------------------",
            ]
        )

        if self.test_files:
            for path in self.test_files:
                lines.append(
                    self._display_path(path)
                )
        else:
            lines.append("None detected")

        lines.extend(
            [
                "",
                "TEST DIRECTORIES",
                "------------------------------------------------------------",
            ]
        )

        if self.test_directories:
            for path in self.test_directories:
                lines.append(
                    self._display_path(path)
                )
        else:
            lines.append("None detected")

        if self.git_info:
            lines.extend(
                [
                    "",
                    "GIT",
                    "------------------------------------------------------------",
                ]
            )

            for key, value in self.git_info.items():
                lines.append(
                    f"{key:<18}: {value}"
                )

        return "\n".join(lines)