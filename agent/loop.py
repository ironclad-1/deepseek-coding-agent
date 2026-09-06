from __future__ import annotations

from agent.runtime import AgentRuntime


def run_interactive(runtime: AgentRuntime) -> None:
    """
    Run an interactive terminal session with the agent.
    """

    print("=" * 60)
    print("DEEPSEEK CODING AGENT")
    print("=" * 60)
    print("Type 'exit' or 'quit' to stop.")
    print()

    while True:
        try:
            user_input = input("You > ").strip()

        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            return

        if not user_input:
            continue

        if user_input.lower() in {"exit", "quit"}:
            print("Exiting.")
            return

        try:
            answer = runtime.run(user_input)

        except Exception as exc:
            print()
            print(f"[AGENT ERROR] {type(exc).__name__}: {exc}")
            print()
            continue

        print()
        print("Agent >")
        print(answer)
        print()