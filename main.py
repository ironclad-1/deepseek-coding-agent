from __future__ import annotations

from agent.model import ModelProvider
from agent.planner import ChangePlanner
from agent.runtime import AgentRuntime
from config import PROJECT_ROOT, REASONING_DIR
from git.operations import (
    git_add,
    git_branch,
    git_commit,
    git_diff,
    git_log,
    git_push,
    git_remote,
    git_status,
)
from reasoning.recorder import ReasoningRecorder
from safety.approval import ApprovalManager
from safety.change_gate import ChangeGate
from tools.filesystem import edit_file, read_file, write_file
from tools.registry import Tool, ToolRegistry
from tools.search import search_repo
from tools.terminal import run_command


REPOSITORY_ROOT = PROJECT_ROOT


def build_tool_registry() -> ToolRegistry:
    """
    Build the complete tool registry used by the agent.
    """

    tools = ToolRegistry()

    # ---------------------------------------------------------
    # Repository search
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # File reading
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # File creation
    # ---------------------------------------------------------

    tools.register(
        Tool(
            name="write_file",
            description=(
                "Create a UTF-8 text file inside the repository. "
                "Existing files are protected unless overwrite is enabled. "
                "This operation requires user approval."
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
                    "content": {
                        "type": "string",
                        "description": (
                            "Complete UTF-8 content to write."
                        ),
                    },
                    "overwrite": {
                        "type": "boolean",
                        "description": (
                            "Whether an existing file may be replaced."
                        ),
                    },
                },
                "required": ["path", "content"],
            },
            function=(
                lambda path,
                content,
                overwrite=False: write_file(
                    REPOSITORY_ROOT,
                    path,
                    content,
                    overwrite=overwrite,
                )
            ),
        )
    )

    # ---------------------------------------------------------
    # File editing
    # ---------------------------------------------------------

    tools.register(
        Tool(
            name="edit_file",
            description=(
                "Edit a UTF-8 text file by replacing exactly one "
                "occurrence of old_text with new_text. "
                "This operation requires user approval."
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
                    "old_text": {
                        "type": "string",
                        "description": (
                            "Exact text to replace. "
                            "Must occur exactly once."
                        ),
                    },
                    "new_text": {
                        "type": "string",
                        "description": (
                            "Replacement text."
                        ),
                    },
                },
                "required": [
                    "path",
                    "old_text",
                    "new_text",
                ],
            },
            function=(
                lambda path,
                old_text,
                new_text: edit_file(
                    REPOSITORY_ROOT,
                    path,
                    old_text,
                    new_text,
                )
            ),
        )
    )

    # ---------------------------------------------------------
    # Command execution
    # ---------------------------------------------------------

    tools.register(
        Tool(
            name="run_command",
            description=(
                "Run one allowed command inside the repository and "
                "return its stdout, stderr, exit code, and execution "
                "result. Command execution requires user approval."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": (
                            "Command to execute. Allowed executables "
                            "include python, py, pytest, git, and pip."
                        ),
                    },
                    "timeout": {
                        "type": "integer",
                        "description": (
                            "Maximum execution time in seconds."
                        ),
                    },
                },
                "required": ["command"],
            },
            function=(
                lambda command,
                timeout=30: run_command(
                    REPOSITORY_ROOT,
                    command,
                    timeout=timeout,
                )
            ),
        )
    )

    # =========================================================
    # Git — read-only operations
    # =========================================================

    tools.register(
        Tool(
            name="git_status",
            description=(
                "Show the current Git branch and working-tree status."
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
                "Show unstaged changes in the Git repository."
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
                "Show recent Git commits."
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
            function=(
                lambda max_entries=10: git_log(
                    REPOSITORY_ROOT,
                    max_entries=max_entries,
                )
            ),
        )
    )

    tools.register(
        Tool(
            name="git_branch",
            description=(
                "Show the current Git branch."
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
                "Show configured Git remotes."
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

    # =========================================================
    # Git — Phase 13 modifying operations
    # =========================================================

    tools.register(
        Tool(
            name="git_add",
            description=(
                "Stage explicitly selected files or directories "
                "in the Git repository. This changes the Git index "
                "and requires user approval."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "paths": {
                        "type": "array",
                        "items": {
                            "type": "string",
                        },
                        "minItems": 1,
                        "description": (
                            "Repository-relative files or directories "
                            "to stage."
                        ),
                    },
                    "timeout": {
                        "type": "integer",
                        "description": (
                            "Maximum execution time in seconds."
                        ),
                    },
                },
                "required": ["paths"],
            },
            function=(
                lambda paths,
                timeout=30: git_add(
                    REPOSITORY_ROOT,
                    paths,
                    timeout=timeout,
                )
            ),
        )
    )

    tools.register(
        Tool(
            name="git_commit",
            description=(
                "Create a Git commit from the currently staged changes. "
                "This changes repository history and requires user "
                "approval. Files must be staged separately with git_add."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": (
                            "Commit message describing the staged changes."
                        ),
                    },
                    "timeout": {
                        "type": "integer",
                        "description": (
                            "Maximum execution time in seconds."
                        ),
                    },
                },
                "required": ["message"],
            },
            function=(
                lambda message,
                timeout=30: git_commit(
                    REPOSITORY_ROOT,
                    message,
                    timeout=timeout,
                )
            ),
        )
    )

    # =========================================================
    # Git — Phase 14 remote push
    # =========================================================

    tools.register(
        Tool(
            name="git_push",
            description=(
                "Push a local Git branch to a configured remote "
                "repository. If no branch is specified, the current "
                "branch is used. This sends commits outside the local "
                "repository and requires separate explicit user approval."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "remote": {
                        "type": "string",
                        "description": (
                            "Configured Git remote name, usually origin."
                        ),
                    },
                    "branch": {
                        "type": "string",
                        "description": (
                            "Local branch to push. If omitted, the "
                            "current branch is used."
                        ),
                    },
                    "timeout": {
                        "type": "integer",
                        "description": (
                            "Maximum execution time in seconds."
                        ),
                    },
                },
                "required": [],
            },
            function=(
                lambda remote="origin",
                branch=None,
                timeout=30: git_push(
                    REPOSITORY_ROOT,
                    remote=remote,
                    branch=branch,
                    timeout=timeout,
                )
            ),
        )
    )

    return tools


def main() -> None:
    print("=" * 60)
    print("DEEPSEEK LOCAL CODING AGENT")
    print("=" * 60)

    print(f"Repository: {REPOSITORY_ROOT}")
    print(f"Reasoning directory: {REASONING_DIR}")

    # ---------------------------------------------------------
    # Model
    # ---------------------------------------------------------

    model = ModelProvider()

    print("\nChecking Ollama...")
    model.check_connection()
    print("✓ Ollama connection successful")

    print(f"Checking model: {model.model}...")

    if not model.check_model():
        raise RuntimeError(
            f"Model '{model.model}' is not installed."
        )

    print("✓ Model available")

    # ---------------------------------------------------------
    # Tools
    # ---------------------------------------------------------

    tools = build_tool_registry()

    print(
        f"✓ Registered tools: {tools.names()}"
    )

    # ---------------------------------------------------------
    # Reasoning recorder
    # ---------------------------------------------------------

    recorder = ReasoningRecorder(
        REASONING_DIR
    )

    # ---------------------------------------------------------
    # Phase 10 safety policy
    # ---------------------------------------------------------

    safety = ApprovalManager()

    print("✓ Safety policy initialized")

    # ---------------------------------------------------------
    # Phase 13 change proposal system
    # ---------------------------------------------------------

    change_planner = ChangePlanner()
    change_gate = ChangeGate()

    print("✓ Change proposal system initialized")

    # ---------------------------------------------------------
    # Agent runtime
    # ---------------------------------------------------------

    runtime = AgentRuntime(
        model=model,
        tools=tools,
        recorder=recorder,
        safety=safety,
        change_planner=change_planner,
        change_gate=change_gate,
        max_turns=20,
        repository_root=REPOSITORY_ROOT,
    )

    print("✓ Agent runtime initialized")

    # ---------------------------------------------------------
    # User task
    # ---------------------------------------------------------

    print()
    user_message = input("Task: ").strip()

    if not user_message:
        raise ValueError(
            "Task cannot be empty."
        )

    answer = runtime.run(
        user_message
    )

    # ---------------------------------------------------------
    # Final answer
    # ---------------------------------------------------------

    print()
    print("=" * 60)
    print("FINAL ANSWER")
    print("=" * 60)
    print(answer)


if __name__ == "__main__":
    main()