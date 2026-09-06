from agent.model import ModelProvider
from config import REASONING_DIR
from reasoning.recorder import ReasoningRecorder


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

    user_message = (
        "Explain why Git is useful for software development. "
        "Keep the final answer concise."
    )

    stream = provider.chat(
        [
            {
                "role": "user",
                "content": user_message,
            }
        ],
        think=True,
        stream=True,
    )

    thinking_parts: list[str] = []
    content_parts: list[str] = []

    print("THINKING STREAM")
    print("------------------------------------------------------------")

    for chunk in stream:
        thinking = chunk.message.thinking or ""
        content = chunk.message.content or ""

        if thinking:
            thinking_parts.append(thinking)
            print(thinking, end="", flush=True)

        if content:
            content_parts.append(content)

    thinking = "".join(thinking_parts)
    content = "".join(content_parts)

    print("\n\nFINAL RESPONSE")
    print("------------------------------------------------------------")
    print(content)

    recorder = ReasoningRecorder(REASONING_DIR)

    trace_file = recorder.save(
        model=provider.model,
        session_id="phase2_streaming_test",
        turn=1,
        user_message=user_message,
        thinking=thinking,
    )

    print("\n✓ Streaming completed")
    print(f"✓ Reasoning saved to:\n  {trace_file}")


if __name__ == "__main__":
    main()