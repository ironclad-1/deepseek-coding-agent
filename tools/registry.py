from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class ToolResult:
    """
    Standard result returned by a tool execution.
    """

    success: bool
    output: str = ""
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_message(self) -> str:
        """
        Convert the result into a string that can be returned
        to the language model.
        """

        if self.success:
            return self.output

        return (
            f"Tool execution failed: "
            f"{self.error or 'Unknown error'}"
        )


@dataclass
class Tool:
    """
    Definition of one tool available to the agent.
    """

    name: str
    description: str
    parameters: dict[str, Any]
    function: Callable[..., Any]

    def schema(self) -> dict[str, Any]:
        """
        Convert the internal definition into the schema expected
        by Ollama.
        """

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    """
    Central registry for all tools available to the agent.
    """

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """
        Register a tool.
        """

        self._validate_tool_definition(tool)

        if tool.name in self._tools:
            raise ValueError(
                f"Tool '{tool.name}' is already registered."
            )

        self._tools[tool.name] = tool

    def unregister(self, name: str) -> None:
        """
        Remove a registered tool.
        """

        if name not in self._tools:
            raise KeyError(
                f"Tool '{name}' is not registered."
            )

        del self._tools[name]

    def get(self, name: str) -> Tool:
        """
        Retrieve a tool by name.
        """

        if name not in self._tools:
            raise KeyError(
                f"Tool '{name}' is not registered."
            )

        return self._tools[name]

    def has(self, name: str) -> bool:
        """
        Check whether a tool exists.
        """

        return name in self._tools

    def schemas(self) -> list[dict[str, Any]]:
        """
        Return all registered tools in Ollama format.
        """

        return [
            tool.schema()
            for tool in self._tools.values()
        ]

    def execute(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> ToolResult:
        """
        Execute a registered tool and normalize the result.
        """

        if not isinstance(arguments, dict):
            return ToolResult(
                success=False,
                error=(
                    f"Arguments for '{name}' must be "
                    "a dictionary."
                ),
            )

        if not self.has(name):
            return ToolResult(
                success=False,
                error=f"Unknown tool: {name}",
            )

        tool = self.get(name)

        try:
            result = tool.function(**arguments)

            if isinstance(result, ToolResult):
                return result

            return ToolResult(
                success=True,
                output=str(result),
            )

        except TypeError as exc:
            return ToolResult(
                success=False,
                error=f"Invalid arguments for '{name}': {exc}",
            )

        except Exception as exc:
            return ToolResult(
                success=False,
                error=(
                    f"{type(exc).__name__}: {exc}"
                ),
            )

    def names(self) -> list[str]:
        """
        Return all registered tool names.
        """

        return list(self._tools.keys())

    def count(self) -> int:
        """
        Return the number of registered tools.
        """

        return len(self._tools)

    @staticmethod
    def _validate_tool_definition(tool: Tool) -> None:
        """
        Validate the basic structure of a tool definition.
        """

        if not tool.name.strip():
            raise ValueError(
                "Tool name cannot be empty."
            )

        if not tool.description.strip():
            raise ValueError(
                f"Tool '{tool.name}' must have a description."
            )

        if not isinstance(tool.parameters, dict):
            raise TypeError(
                f"Parameters for '{tool.name}' must be a dictionary."
            )

        if not callable(tool.function):
            raise TypeError(
                f"Function for '{tool.name}' must be callable."
            )