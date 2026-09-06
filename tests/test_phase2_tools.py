from agent.model import ModelProvider


CALCULATOR_TOOL = {
    "type": "function",
    "function": {
        "name": "calculator",
        "description": "Perform basic arithmetic calculations.",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "A basic arithmetic expression.",
                }
            },
            "required": ["expression"],
        },
    },
}


def main() -> None:
    provider = ModelProvider()

    print("Checking Ollama...")
    provider.check_connection()
    print("✓ Ollama connection successful")

    if not provider.check_model():
        raise RuntimeError(
            f"Model '{provider.model}' is not installed."
        )

    print(f"✓ {provider.model} available\n")

    messages = [
        {
            "role": "user",
            "content": (
                "Use the calculator tool to calculate 237 * 19. "
                "You MUST use the calculator tool. "
                "Do not calculate the answer yourself."
            ),
        }
    ]

    print("Sending tool-call test...\n")

    response = provider.chat(
        messages,
        think=True,
        stream=False,
        tools=[CALCULATOR_TOOL],
    )

    print("THINKING")
    print("------------------------------------------------------------")
    print(response.thinking)

    print("\nTOOL CALLS")
    print("------------------------------------------------------------")

    if not response.tool_calls:
        print("NO TOOL CALLS RETURNED")
        return

    for tool_call in response.tool_calls:
        print(f"Tool: {tool_call.function.name}")
        print(f"Arguments: {tool_call.function.arguments}")

    print("\n✓ Tool-call compatibility confirmed")


if __name__ == "__main__":
    main()