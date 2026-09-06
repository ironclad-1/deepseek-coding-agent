from pathlib import Path

from agent.model import ModelProvider
from config import REASONING_DIR
from reasoning.recorder import ReasoningRecorder


def main() -> None:
    provider = ModelProvider()

    print("Checking Ollama...")
    provider.check_connection()
    print("✓ Ollama connection successful")

    print(f"Checking model: {provider.model}...")
    if not provider.check_model():
        raise RuntimeError(
            f"Model '{provider.model}' is not installed."
        )

    print("✓ Model available")

    user_message = (
        "Explain in simple terms what a Python virtual "
        "environment is."
    )

    print("\nSending request to DeepSeek...\n")

    response = provider.chat(
        [
            {
                "role": "user",
                "content": user_message,
            }
        ],
        think=True,
        stream=False,
    )

    print("THINKING TRACE")
    print("------------------------------------------------------------")
    print(response.thinking)

    print("\nFINAL RESPONSE")
    print("------------------------------------------------------------")
    print(response.content)

    recorder = ReasoningRecorder(REASONING_DIR)

    trace_file = recorder.save(
        model=response.model,
        session_id="phase2_test",
        turn=1,
        user_message=user_message,
        thinking=response.thinking,
    )

    print("\n✓ Reasoning trace saved:")
    print(trace_file)


if __name__ == "__main__":
    main()