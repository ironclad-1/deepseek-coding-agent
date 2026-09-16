from __future__ import annotations
from pathlib import Path
from agent.model import ModelProvider
from agent.runtime import AgentRuntime
from config import REASONING_DIR
from reasoning.recorder import ReasoningRecorder
from tools.filesystem import edit_file, read_file, write_file
from tools.registry import Tool, ToolRegistry
from tools.search import search_repo
from tools.terminal import run_command

REPOSITORY_ROOT = Path(r"C:\Users\kinga\Desktop\Try_rag\AgentTestRepos\phase9-agent-test")

def _prepare_test_repository() -> None:
    REPOSITORY_ROOT.mkdir(parents=True, exist_ok=True)
    (REPOSITORY_ROOT / "README.md").write_text(
        "# Phase 9 Test Repository\n\n"
        "This repository is used to test command execution.\n",
        encoding="utf-8",
    )
    (REPOSITORY_ROOT / "app.py").write_text(
        "def greet():\n"
        "    return 'Hello'\n",
        encoding="utf-8",
    )

def main() -> None:
    print("=" * 60)
    print("PHASE 9 — END-TO-END COMMAND EXECUTION INTEGRATION TEST")
    print("=" * 60)

    _prepare_test_repository()

    print(f"\nRepository: {REPOSITORY_ROOT}")

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
                        "description": "Text to search for in the repository.",
                    },
                    "case_sensitive": {
                        "type": "boolean",
                        "description": "Whether the search should be case-sensitive.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of search results.",
                    },
                },
                "required": ["query"],
            },
            function=lambda query, case_sensitive=False, max_results=100: (
                search_repo(
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
                        "description": "Repository-relative path of the file.",
                    },
                    "start_line": {
                        "type": "integer",
                        "description": "First line to read, starting at 1.",
                    },
                    "end_line": {
                        "type": "integer",
                        "description": "Last line to read, inclusive.",
                    },
                },
                "required": ["path"],
            },
            function=lambda path, start_line=None, end_line=None: (
                read_file(
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
            name="write_file",
            description=(
                "Create a UTF-8 text file inside the repository. "
                "Existing files are protected unless overwrite is enabled."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Repository-relative path of the file.",
                    },
                    "content": {
                        "type": "string",
                        "description": "Complete UTF-8 content to write.",
                    },
                    "overwrite": {
                        "type": "boolean",
                        "description": "Whether an existing file may be replaced.",
                    },
                },
                "required": ["path", "content"],
            },
            function=lambda path, content, overwrite=False: (
                write_file(
                    REPOSITORY_ROOT,
                    path,
                    content,
                    overwrite=overwrite,
                )
            ),
        )
    )

    tools.register(
        Tool(
            name="edit_file",
            description=(
                "Edit a UTF-8 text file by replacing exactly one occurrence "
                "of old_text with new_text. The edit fails if old_text is "
                "missing or occurs more than once."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Repository-relative path of the file.",
                    },
                    "old_text": {
                        "type": "string",
                        "description": "Exact text to replace. Must occur exactly once.",
                    },
                    "new_text": {
                        "type": "string",
                        "description": "Replacement text.",
                    },
                },
                "required": ["path", "old_text", "new_text"],
            },
            function=lambda path, old_text, new_text: (
                edit_file(
                    REPOSITORY_ROOT,
                    path,
                    old_text,
                    new_text,
                )
            ),
        )
    )

    tools.register(
        Tool(
            name="run_command",
            description=(
                "Run one allowed command inside the repository and return "
                "its stdout, stderr, exit code, and execution result."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": (
                            "Command to execute. Allowed executables include "
                            "python, py, pytest, git, and pip."
                        ),
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Maximum execution time in seconds.",
                    },
                },
                "required": ["command"],
            },
            function=lambda command, timeout=30: (
                run_command(
                    REPOSITORY_ROOT,
                    command,
                    timeout=timeout,
                )
            ),
        )
    )

    print(f"✓ Registered tools: {tools.names()}")

    recorder = ReasoningRecorder(REASONING_DIR)

    print(f"✓ Reasoning directory: {REASONING_DIR}")

    runtime = AgentRuntime(
        model=model,
        tools=tools,
        recorder=recorder,
        max_turns=12,
    )

    print("✓ Agent runtime initialized")

    prompt = (
        "Work only inside this repository. "
        "First use search_repo to find the greet function. "
        "Then use read_file on app.py. "
        "Create a new file named phase9_test.py using write_file. "
        "The file must contain Python code that prints exactly "
        "'Phase 9 command execution works'. "
        "Then use edit_file to change the return value in app.py "
        "from 'Hello' to 'Hello, world'. "
        "Then use run_command to execute the command "
        "'python phase9_test.py'. "
        "Inspect the command result and confirm that the expected "
        "message was printed. "
        "Finally use read_file on app.py and phase9_test.py to verify "
        "the final files. "
        "Do not use any tools other than the available repository tools. "
        "After verification, explain what you changed and what command "
        "was executed."
    )

    print("\nStarting Phase 9 real repository task...\n")

    answer = runtime.run(prompt)

    print()
    print("=" * 60)
    print("FINAL ANSWER")
    print("=" * 60)
    print(answer)

    print()
    print("=" * 60)
    print("VERIFYING FILESYSTEM AND COMMAND RESULTS")
    print("=" * 60)

    app_path = REPOSITORY_ROOT / "app.py"
    new_file_path = REPOSITORY_ROOT / "phase9_test.py"

    if not app_path.exists():
        raise AssertionError("app.py was not found.")

    if not new_file_path.exists():
        raise AssertionError("phase9_test.py was not created.")

    app_content = app_path.read_text(encoding="utf-8")
    new_file_content = new_file_path.read_text(encoding="utf-8")

    if "return 'Hello, world'" not in app_content:
        raise AssertionError(
            "app.py was not changed to return 'Hello, world'."
        )

    if "Phase 9 command execution works" not in new_file_content:
        raise AssertionError(
            "phase9_test.py does not contain the expected output."
        )

    command_check = run_command(
        REPOSITORY_ROOT,
        "python phase9_test.py",
    )

    if not command_check.success:
        raise AssertionError(
            command_check.error or "Final command verification failed."
        )

    if "Phase 9 command execution works" not in command_check.output:
        raise AssertionError(
            "Expected command output was not found."
        )

    print("✓ phase9_test.py was created")
    print("✓ app.py was edited")
    print("✓ Python command executed successfully")
    print("✓ Expected command output was captured")
    print("✓ Final files contain the expected changes")

    print()
    print("=" * 60)
    print("PHASE 9 INTEGRATION TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()