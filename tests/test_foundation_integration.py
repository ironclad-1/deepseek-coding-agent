from __future__ import annotations

from pathlib import Path

from agent.model import ModelProvider
from agent.runtime import AgentRuntime
from config import REASONING_DIR
from reasoning.recorder import ReasoningRecorder
from tools.filesystem import read_file
from tools.registry import Tool, ToolRegistry
from tools.search import search_repo


REPOSITORY_ROOT = Path(
    r"C:\Users\kinga\Desktop\Try_rag\AgentTestRepos\remote-keylogger"
)


def main() -> None:
    print("=" * 60)
    print("FOUNDATION — END-TO-END INTEGRATION TEST")
    print("=" * 60)

    # ---------------------------------------------------------
    # 1. Validate repository
    # ---------------------------------------------------------

    if not REPOSITORY_ROOT.exists():
        raise FileNotFoundError(
            f"Repository not found: {REPOSITORY_ROOT}"
        )

    print(f"\nRepository: {REPOSITORY_ROOT}")

    # ---------------------------------------------------------
    # 2. Model
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
    # 3. Tool registry
    # ---------------------------------------------------------

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

    print(
        f"✓ Registered tools: {tools.names()}"
    )

    # ---------------------------------------------------------
    # 4. Reasoning recorder
    # ---------------------------------------------------------

    recorder = ReasoningRecorder(
        REASONING_DIR
    )

    print(
        f"✓ Reasoning directory: {REASONING_DIR}"
    )

    # ---------------------------------------------------------
    # 5. Agent runtime
    # ---------------------------------------------------------

    runtime = AgentRuntime(
        model=model,
        tools=tools,
        recorder=recorder,
        max_turns=10,
    )

    print("✓ Agent runtime initialized")

    # ---------------------------------------------------------
    # 6. Real repository task
    # ---------------------------------------------------------

    prompt = (
        "Find where Telegram is used in this repository, "
        "read the relevant file, and explain what it does. "
        "You MUST use search_repo first. "
        "Then use read_file on the relevant file before answering."
    )

    print("\nStarting real repository task...\n")

    answer = runtime.run(prompt)

    # ---------------------------------------------------------
    # 7. Final response
    # ---------------------------------------------------------

    print()
    print("=" * 60)
    print("FINAL ANSWER")
    print("=" * 60)
    print(answer)

    print()
    print("=" * 60)
    print("FOUNDATION INTEGRATION TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()