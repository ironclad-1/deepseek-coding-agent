from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterator

import ollama

from config import (
    KEEP_ALIVE,
    MODEL_NAME,
    OLLAMA_HOST,
    REQUEST_TIMEOUT,
)


@dataclass
class ModelResponse:
    """
    Normalized response from the Ollama model.

    thinking:
        Reasoning trace exposed by the model/API.

    content:
        Final natural-language response.

    tool_calls:
        Tool calls requested by the model, to be handled later
        by the Agent Runtime.

    raw:
        Original Ollama response for debugging when needed.
    """

    model: str
    thinking: str = ""
    content: str = ""
    tool_calls: list[Any] = field(default_factory=list)
    raw: Any = None


class ModelProvider:
    """Ollama interface used by the agent."""

    def __init__(
        self,
        model: str = MODEL_NAME,
        host: str = OLLAMA_HOST,
    ) -> None:
        self.model = model
        self.host = host

        self.client = ollama.Client(
            host=host,
            timeout=REQUEST_TIMEOUT,
        )

    def check_connection(self) -> bool:
        """Verify that Ollama is reachable."""

        try:
            self.client.list()
            return True
        except Exception as exc:
            raise RuntimeError(
                f"Unable to connect to Ollama at {self.host}: {exc}"
            ) from exc

    def check_model(self) -> bool:
        """Check whether the configured model is installed."""

        try:
            response = self.client.list()

            for model in response.models:
                if model.model == self.model:
                    return True

            return False

        except Exception as exc:
            raise RuntimeError(
                f"Unable to inspect Ollama models: {exc}"
            ) from exc

    def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        think: bool = True,
        stream: bool = False,
        tools: list[dict[str, Any]] | None = None,
    ) -> ModelResponse | Iterator[Any]:
        """
        Send a chat request to Ollama.

        When stream=False, returns a normalized ModelResponse.
        When stream=True, returns Ollama's response iterator.

        Tool definitions are accepted now so Phase 3/5 can use the
        same model layer without redesigning it.
        """

        try:
            response = self.client.chat(
                model=self.model,
                messages=messages,
                think=think,
                stream=stream,
                tools=tools,
                keep_alive=KEEP_ALIVE,
            )

            if stream:
                return response

            thinking = getattr(response.message, "thinking", "") or ""
            content = getattr(response.message, "content", "") or ""

            tool_calls = getattr(response.message, "tool_calls", None)

            if tool_calls is None:
                tool_calls = []

            return ModelResponse(
                model=self.model,
                thinking=thinking,
                content=content,
                tool_calls=list(tool_calls),
                raw=response,
            )

        except ollama.ResponseError as exc:
            raise RuntimeError(
                f"Ollama error ({exc.status_code}): {exc.error}"
            ) from exc

        except Exception as exc:
            raise RuntimeError(
                f"Model request failed: {exc}"
            ) from exc