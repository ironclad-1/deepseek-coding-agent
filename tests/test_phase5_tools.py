from __future__ import annotations

from tools.registry import Tool, ToolRegistry, ToolResult


def calculator(expression: str) -> str:
    """
    Temporary tool used to test the Phase 5 framework.
    """

    allowed_characters = set(
        "0123456789+-*/(). "
    )

    if any(
        character not in allowed_characters
        for character in expression
    ):
        raise ValueError(
            "Unsupported characters in expression."
        )

    return str(
        eval(
            expression,
            {"__builtins__": {}},
            {},
        )
    )


def main() -> None:
    print("=" * 60)
    print("PHASE 5 — TOOL SYSTEM TEST")
    print("=" * 60)

    registry = ToolRegistry()

    print("\nRegistering calculator...")

    registry.register(
        Tool(
            name="calculator",
            description=(
                "Perform basic arithmetic calculations."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": (
                            "Arithmetic expression."
                        ),
                    }
                },
                "required": ["expression"],
            },
            function=calculator,
        )
    )

    print("✓ Tool registered")
    print(f"✓ Tool names: {registry.names()}")
    print(f"✓ Tool count: {registry.count()}")

    print("\nChecking tool lookup...")

    if not registry.has("calculator"):
        raise RuntimeError(
            "Calculator was not registered."
        )

    tool = registry.get("calculator")

    print(f"✓ Found: {tool.name}")

    print("\nChecking Ollama schema...")

    schema = tool.schema()

    print(schema)

    if schema["type"] != "function":
        raise RuntimeError(
            "Invalid tool schema."
        )

    print("✓ Schema valid")

    print("\nExecuting tool...")

    result = registry.execute(
        "calculator",
        {
            "expression": "237 * 19"
        },
    )

    if not isinstance(result, ToolResult):
        raise RuntimeError(
            "Registry did not return ToolResult."
        )

    print(f"✓ Success: {result.success}")
    print(f"✓ Output: {result.output}")

    if not result.success:
        raise RuntimeError(
            f"Calculator failed: {result.error}"
        )

    if result.output != "4503":
        raise RuntimeError(
            f"Unexpected result: {result.output}"
        )

    print("\nTesting unknown tool...")

    unknown = registry.execute(
        "does_not_exist",
        {},
    )

    if unknown.success:
        raise RuntimeError(
            "Unknown tool unexpectedly succeeded."
        )

    print(f"✓ Unknown tool handled: {unknown.error}")

    print("\nTesting invalid arguments...")

    invalid = registry.execute(
        "calculator",
        [],
    )

    if invalid.success:
        raise RuntimeError(
            "Invalid arguments unexpectedly succeeded."
        )

    print(f"✓ Invalid arguments handled: {invalid.error}")

    print()
    print("=" * 60)
    print("PHASE 5 TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()