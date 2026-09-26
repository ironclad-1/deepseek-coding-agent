from __future__ import annotations
import subprocess
from pathlib import Path
from agent.model import ModelProvider
from agent.runtime import AgentRuntime
from config import REASONING_DIR
from reasoning.recorder import ReasoningRecorder
from tools.filesystem import read_file
from tools.registry import Tool, ToolRegistry
from tools.search import search_repo
from git.operations import git_status, git_diff, git_log, git_branch, git_remote

REPOSITORY_ROOT = Path(
    r"C:\Users\kinga\Desktop\Try_rag\AgentTestRepos\phase11-agent-test"
)


def _run_git(*arguments: str) -> None:
    result = subprocess.run(
        ["git", *arguments],
        cwd=REPOSITORY_ROOT,
        shell=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Git command failed: {' '.join(arguments)}\n"
            f"STDOUT: {result.stdout}\n"
            f"STDERR: {result.stderr}"
        )


def _prepare_test_repository() -> None:
    REPOSITORY_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not (REPOSITORY_ROOT / ".git").exists():
        _run_git("init")
        _run_git("branch", "-M", "main")
        _run_git("config", "user.name", "Phase 11 Test")
        _run_git(
            "config",
            "user.email",
            "phase11@test.local",
        )

    readme_path = REPOSITORY_ROOT / "README.md"

    readme_path.write_text(
        "# Phase 11 Test Repository\n"
        "This repository is used to test Git integration.\n",
        encoding="utf-8",
    )

    app_path = REPOSITORY_ROOT / "app.py"

    app_path.write_text(
        "def greet():\n"
        "    return 'Hello'\n",
        encoding="utf-8",
    )

    _run_git("add", "README.md", "app.py")

    commit_check = subprocess.run(
        [
            "git",
            "rev-parse",
            "--verify",
            "HEAD",
        ],
        cwd=REPOSITORY_ROOT,
        shell=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if commit_check.returncode != 0:
        _run_git(
            "commit",
            "-m",
            "Initial Phase 11 test commit",
        )

    remote_check = subprocess.run(
        [
            "git",
            "remote",
            "get-url",
            "origin",
        ],
        cwd=REPOSITORY_ROOT,
        shell=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if remote_check.returncode != 0:
        _run_git(
            "remote",
            "add",
            "origin",
            "https://example.com/phase11-test.git",
        )

    readme_path.write_text(
        "# Phase 11 Test Repository\n"
        "This repository is used to test Git integration.\n"
        "This is an uncommitted Phase 11 test change.\n",
        encoding="utf-8",
    )


def main() -> None:
    print("=" * 60)
    print("PHASE 11 — REAL MODEL GIT INTEGRATION TEST")
    print("=" * 60)

    _prepare_test_repository()

    print(
        f"\nRepository: {REPOSITORY_ROOT}"
    )

    model = ModelProvider()

    print("\nChecking Ollama...")
    model.check_connection()
    print("✓ Ollama connection successful")

    print(
        f"Checking model: {model.model}..."
    )

    if not model.check_model():
        raise RuntimeError(
            f"Model '{model.model}' is not installed."
        )

    print("✓ Model available")

    tools = ToolRegistry()

    tools.register(
        Tool(
            name="search_repo",
            description=(
                "Search the repository for a text query. "
                "Returns matching files, line numbers, and lines."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Text to search for in the repository."
                        ),
                    },
                    "case_sensitive": {
                        "type": "boolean",
                        "description": (
                            "Whether the search should be case-sensitive."
                        ),
                    },
                    "max_results": {
                        "type": "integer",
                        "description": (
                            "Maximum number of search results."
                        ),
                    },
                },
                "required": ["query"],
            },
            function=(
                lambda query,
                case_sensitive=False,
                max_results=100: search_repo(
                    REPOSITORY_ROOT,
                    query,
                    case_sensitive=case_sensitive,
                    max_results=max_results,
                )
            ),
        )
    )

    tools.register(
        Tool(
            name="read_file",
            description=(
                "Read a text file from inside the repository. "
                "Returns numbered lines."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": (
                            "Repository-relative path of the file."
                        ),
                    },
                    "start_line": {
                        "type": "integer",
                        "description": (
                            "First line to read, starting at 1."
                        ),
                    },
                    "end_line": {
                        "type": "integer",
                        "description": (
                            "Last line to read, inclusive."
                        ),
                    },
                },
                "required": ["path"],
            },
            function=(
                lambda path,
                start_line=None,
                end_line=None: read_file(
                    REPOSITORY_ROOT,
                    path,
                    start_line=start_line,
                    end_line=end_line,
                )
            ),
        )
    )

    tools.register(
        Tool(
            name="git_status",
            description=(
                "Show the current Git branch and working-tree status. "
                "This is a read-only Git operation."
            ),
            parameters={
                "type": "object",
                "properties": {},
            },
            function=lambda: git_status(
                REPOSITORY_ROOT
            ),
        )
    )

    tools.register(
        Tool(
            name="git_diff",
            description=(
                "Show the current unstaged Git diff. "
                "This is a read-only Git operation."
            ),
            parameters={
                "type": "object",
                "properties": {},
            },
            function=lambda: git_diff(
                REPOSITORY_ROOT
            ),
        )
    )

    tools.register(
        Tool(
            name="git_log",
            description=(
                "Show recent Git commits. "
                "This is a read-only Git operation."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "max_entries": {
                        "type": "integer",
                        "description": (
                            "Maximum number of commits to return."
                        ),
                    },
                },
            },
            function=lambda max_entries=10: git_log(
                REPOSITORY_ROOT,
                max_entries=max_entries,
            ),
        )
    )

    tools.register(
        Tool(
            name="git_branch",
            description=(
                "Show the current Git branch. "
                "This is a read-only Git operation."
            ),
            parameters={
                "type": "object",
                "properties": {},
            },
            function=lambda: git_branch(
                REPOSITORY_ROOT
            ),
        )
    )

    tools.register(
        Tool(
            name="git_remote",
            description=(
                "Show the configured Git remotes. "
                "This is a read-only Git operation."
            ),
            parameters={
                "type": "object",
                "properties": {},
            },
            function=lambda: git_remote(
                REPOSITORY_ROOT
            ),
        )
    )

    print(
        f"✓ Registered tools: {tools.names()}"
    )

    recorder = ReasoningRecorder(
        REASONING_DIR
    )

    print(
        f"✓ Reasoning directory: {REASONING_DIR}"
    )

    runtime = AgentRuntime(
        model=model,
        tools=tools,
        recorder=recorder,
        max_turns=15,
    )

    print(
        "✓ Agent runtime initialized"
    )

    prompt = (
        "Work only inside this repository. "
        "This is a Phase 11 Git integration test. "
        "First use search_repo to find the greet function. "
        "Then use read_file on app.py. "
        "After that, you MUST use each of these five Git tools: "
        "git_status, git_branch, git_log, git_remote, and git_diff. "
        "Use each Git tool at least once. "
        "Do not modify any files and do not use write_file, "
        "edit_file, or run_command. "
        "Inspect the results from all five Git tools and then "
        "provide a final summary containing the current branch, "
        "working-tree status, recent commit information, "
        "configured remote, and the current diff."
    )

    print(
        "\nStarting Phase 11 real-model Git task...\n"
    )

    answer = runtime.run(prompt)

    print()
    print("=" * 60)
    print("FINAL ANSWER")
    print("=" * 60)
    print(answer)

    print()
    print("=" * 60)
    print("VERIFYING GIT INTEGRATION RESULTS")
    print("=" * 60)

    status_result = git_status(
        REPOSITORY_ROOT
    )

    branch_result = git_branch(
        REPOSITORY_ROOT
    )

    log_result = git_log(
        REPOSITORY_ROOT,
        max_entries=10,
    )

    remote_result = git_remote(
        REPOSITORY_ROOT
    )

    diff_result = git_diff(
        REPOSITORY_ROOT
    )

    if not status_result.success:
        raise AssertionError(
            status_result.error
            or "git_status verification failed."
        )

    if not branch_result.success:
        raise AssertionError(
            branch_result.error
            or "git_branch verification failed."
        )

    if not log_result.success:
        raise AssertionError(
            log_result.error
            or "git_log verification failed."
        )

    if not remote_result.success:
        raise AssertionError(
            remote_result.error
            or "git_remote verification failed."
        )

    if not diff_result.success:
        raise AssertionError(
            diff_result.error
            or "git_diff verification failed."
        )

    if branch_result.output.strip() != "main":
        raise AssertionError(
            "Expected current branch to be main."
        )

    if "README.md" not in status_result.output:
        raise AssertionError(
            "Expected README.md modification was not found."
        )

    if "Initial Phase 11 test commit" not in log_result.output:
        raise AssertionError(
            "Initial Phase 11 commit was not found."
        )

    if "origin" not in remote_result.output:
        raise AssertionError(
            "Origin remote was not found."
        )

    if "uncommitted Phase 11 test change" not in diff_result.output:
        raise AssertionError(
            "Expected README.md change was not found in git diff."
        )

    print(
        "✓ git_status returned the expected working-tree state"
    )

    print(
        "✓ git_branch returned main"
    )

    print(
        "✓ git_log returned the test commit"
    )

    print(
        "✓ git_remote returned origin"
    )

    print(
        "✓ git_diff returned the expected uncommitted change"
    )

    print()
    print("=" * 60)
    print("PHASE 11 GIT INTEGRATION TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()