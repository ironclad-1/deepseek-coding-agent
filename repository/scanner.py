from __future__ import annotations

import subprocess
from collections import Counter
from pathlib import Path

from repository.context import RepositoryContext


# Directories that normally should not be scanned.
DEFAULT_IGNORED_DIRECTORIES = {
    ".git",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    ".idea",
    ".vscode",
}


# Common project files.
PROJECT_FILE_NAMES = {
    "README",
    "README.md",
    "README.txt",
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "setup.py",
    "setup.cfg",
    "Pipfile",
    "Pipfile.lock",
    "poetry.lock",
    "package.json",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "Cargo.toml",
    "Cargo.lock",
    "go.mod",
    "go.sum",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "CMakeLists.txt",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    ".gitignore",
    ".env.example",
}


# Extensions mapped to language names.
LANGUAGE_MAP = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".c": "C",
    ".h": "C/C++",
    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".cs": "C#",
    ".go": "Go",
    ".rs": "Rust",
    ".rb": "Ruby",
    ".php": "PHP",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".sh": "Shell",
    ".ps1": "PowerShell",
    ".sql": "SQL",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".xml": "XML",
    ".md": "Markdown",
    ".txt": "Text",
}


class RepositoryScanner:
    """
    Scans a local repository and builds a RepositoryContext.
    """

    def __init__(
        self,
        root: str | Path,
        *,
        ignored_directories: set[str] | None = None,
    ) -> None:
        self.root = Path(root).expanduser().resolve()

        self.ignored_directories = (
            set(ignored_directories)
            if ignored_directories is not None
            else DEFAULT_IGNORED_DIRECTORIES.copy()
        )

    def validate(self) -> None:
        """Validate that the root exists and is a directory."""

        if not self.root.exists():
            raise FileNotFoundError(
                f"Repository does not exist: {self.root}"
            )

        if not self.root.is_dir():
            raise NotADirectoryError(
                f"Repository path is not a directory: {self.root}"
            )

    def scan(self) -> RepositoryContext:
        """
        Scan the repository and return its structural context.
        """

        self.validate()

        context = RepositoryContext(
            root=self.root,
            is_git_repository=self._is_git_repository(),
        )

        language_counter: Counter[str] = Counter()
        extension_counter: Counter[str] = Counter()

        for current_path in self._walk():
            relative_path = current_path.relative_to(self.root)

            if current_path.is_dir():
                context.directories.append(relative_path)
                continue

            context.files.append(relative_path)

            extension = current_path.suffix.lower()

            if extension:
                extension_counter[extension] += 1

                language = LANGUAGE_MAP.get(extension)

                if language:
                    language_counter[language] += 1

            if self._is_project_file(current_path):
                context.project_files.append(relative_path)

            if self._is_test_file(current_path):
                context.test_files.append(relative_path)

        context.extensions = dict(
            extension_counter.most_common()
        )

        context.languages = dict(
            language_counter.most_common()
        )

        context.test_directories = self._find_test_directories()

        if context.is_git_repository:
            context.git_info = self._get_git_info()

        return context

    def _walk(self):
        """Walk the repository while skipping ignored directories."""

        for path in self.root.rglob("*"):
            if not self._should_ignore(path):
                yield path

    def _should_ignore(self, path: Path) -> bool:
        """
        Determine whether a path belongs to an ignored directory.
        """

        return any(
            part in self.ignored_directories
            for part in path.parts
        )

    def _is_project_file(self, path: Path) -> bool:
        """Determine whether a file is a known project file."""

        return (
            path.name in PROJECT_FILE_NAMES
            or path.name.upper() == "README"
        )

    def _is_test_file(self, path: Path) -> bool:
        """Determine whether a file appears to be a test file."""

        name = path.name.lower()

        return (
            name.startswith("test_")
            or name.endswith("_test.py")
            or name.endswith(".test.js")
            or name.endswith(".test.ts")
            or name.endswith(".spec.js")
            or name.endswith(".spec.ts")
        )

    def _find_test_directories(self) -> list[Path]:
        """Find directories commonly used for tests."""

        test_directory_names = {
            "test",
            "tests",
            "__tests__",
            "spec",
            "specs",
        }

        directories: list[Path] = []

        for path in self.root.rglob("*"):
            if not path.is_dir():
                continue

            if self._should_ignore(path):
                continue

            if path.name.lower() in test_directory_names:
                directories.append(
                    path.relative_to(self.root)
                )

        return directories

    def _is_git_repository(self) -> bool:
        """Check whether the repository has a Git working tree."""

        result = subprocess.run(
            [
                "git",
                "-C",
                str(self.root),
                "rev-parse",
                "--is-inside-work-tree",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        return (
            result.returncode == 0
            and result.stdout.strip().lower() == "true"
        )

    def _get_git_info(self) -> dict[str, str]:
        """Collect basic Git information."""

        info: dict[str, str] = {}

        commands = {
            "branch": [
                "git",
                "-C",
                str(self.root),
                "branch",
                "--show-current",
            ],
            "status": [
                "git",
                "-C",
                str(self.root),
                "status",
                "--porcelain",
            ],
            "remote": [
                "git",
                "-C",
                str(self.root),
                "remote",
                "-v",
            ],
        }

        for key, command in commands.items():
            try:
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if result.returncode == 0:
                    output = result.stdout.strip()

                    if key == "status":
                        info[key] = (
                            "clean"
                            if not output
                            else "modified"
                        )
                    else:
                        info[key] = output or "none"

                else:
                    info[key] = "unavailable"

            except subprocess.TimeoutExpired:
                info[key] = "timeout"

        return info