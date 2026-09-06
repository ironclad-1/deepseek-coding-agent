from __future__ import annotations

from agent.model import ModelProvider
from agent.runtime import AgentRuntime
from config import REASONING_DIR
from reasoning.recorder import ReasoningRecorder
from tools.registry import Tool, ToolRegistry


def calculator(expression: str) -> str:
    """
    Temporary calculator used only for the Phase 3 integration test.
    """

    allowed_characters = set(
        "0123456789+-*/(). "
    )

    if any(
        character not in allowed_characters
        for character in expression
    ):
        raise ValueError(
            "Calculator expression contains unsupported characters."
        )

    try:
        result = eval(
            expression,
            {"__builtins__": {}},
            {},
        )

    except Exception as exc:
        raise ValueError(
            f"Invalid arithmetic expression: {expression}"
        ) from exc

    return str(result)


def main() -> None:
    print("=" * 60)
    print("PHASE 3 — AGENT RUNTIME TEST")
    print("=" * 60)

    # ---------------------------------------------------------
    # 1. Model
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
    # 2. Tool registry
    # ---------------------------------------------------------

    tools = ToolRegistry()

    tools.register(
        Tool(
            name="calculator",
            description=(
                "Perform basic arithmetic calculations. "
                "Use this tool whenever arithmetic is required."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": (
                            "A basic arithmetic expression, "
                            "for example '237 * 19'."
                        ),
                    }
                },
                "required": ["expression"],
            },
            function=calculator,
        )
    )

    print(
        f"✓ Registered tools: {tools.names()}"
    )

    # ---------------------------------------------------------
    # 3. Reasoning recorder
    # ---------------------------------------------------------

    recorder = ReasoningRecorder(
        REASONING_DIR
    )

    print(
        f"✓ Reasoning directory: {REASONING_DIR}"
    )

    # ---------------------------------------------------------
    # 4. Agent runtime
    # ---------------------------------------------------------

    runtime = AgentRuntime(
        model=model,
        tools=tools,
        recorder=recorder,
        max_turns=10,
    )

    print("✓ Agent runtime initialized")

    # ---------------------------------------------------------
    # 5. Agent task
    # ---------------------------------------------------------

    prompt = (
        "Use the calculator tool to calculate 237 * 19. "
        "You MUST use the calculator tool. "
        "After receiving the result, give me a short final answer."
    )

    print("\nStarting agent task...")
    print()

    answer = runtime.run(prompt)

    # ---------------------------------------------------------
    # 6. Final answer
    # ---------------------------------------------------------

    print()
    print("=" * 60)
    print("FINAL ANSWER")
    print("=" * 60)
    print(answer)
    print()

    print("=" * 60)
    print("PHASE 3 TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()