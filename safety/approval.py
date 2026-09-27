from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ApprovalDecision(str, Enum):
    SAFE = "safe"
    REQUIRE_APPROVAL = "require_approval"
    DENIED = "denied"


@dataclass
class SafetyCheck:
    decision: ApprovalDecision
    reason: str

    @property
    def allowed(self) -> bool:
        return self.decision == ApprovalDecision.SAFE

    @property
    def requires_approval(self) -> bool:
        return self.decision == ApprovalDecision.REQUIRE_APPROVAL

    @property
    def denied(self) -> bool:
        return self.decision == ApprovalDecision.DENIED


SAFE_TOOLS = {
    "read_file",
    "search_repo",
    "git_status",
    "git_diff",
    "git_log",
    "git_branch",
    "git_remote",
}

APPROVAL_TOOLS = {
    "write_file",
    "edit_file",
    "git_add",
    "git_commit",
    "git_push",
}

DENIED_TOOLS = {
}

SAFE_COMMANDS = {
    ("git", "status"),
    ("git", "diff"),
    ("git", "log"),
}

APPROVAL_COMMANDS = {
    "python",
    "python.exe",
    "py",
    "py.exe",
    "pytest",
    "pytest.exe",
    "pip",
    "pip.exe",
    "git",
    "git.exe",
}

DENIED_COMMANDS = {
    "del",
    "erase",
    "rd",
    "rmdir",
    "format",
    "shutdown",
    "restart-computer",
    "stop-computer",
    "remove-item",
    "set-content",
    "add-content",
    "invoke-expression",
    "iex",
    "powershell",
    "powershell.exe",
    "cmd",
    "cmd.exe",
}


class ApprovalManager:
    """
    Phase 14 safety policy.

    This class only decides whether a tool request is:

        SAFE
        REQUIRE_APPROVAL
        DENIED

    User interaction is handled later by the agent runtime.
    """

    def check(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> SafetyCheck:
        if not isinstance(tool_name, str) or not tool_name.strip():
            return SafetyCheck(
                decision=ApprovalDecision.DENIED,
                reason="Tool name must be a non-empty string.",
            )

        if arguments is None:
            arguments = {}

        if not isinstance(arguments, dict):
            return SafetyCheck(
                decision=ApprovalDecision.DENIED,
                reason="Tool arguments must be a dictionary.",
            )

        tool_name = tool_name.strip().lower()

        if tool_name in DENIED_TOOLS:
            return SafetyCheck(
                decision=ApprovalDecision.DENIED,
                reason=(
                    f"Tool is denied by the safety policy: "
                    f"{tool_name}"
                ),
            )

        if tool_name in SAFE_TOOLS:
            return SafetyCheck(
                decision=ApprovalDecision.SAFE,
                reason=f"Tool is read-only: {tool_name}",
            )

        if tool_name in APPROVAL_TOOLS:
            if tool_name == "git_add":
                return SafetyCheck(
                    decision=ApprovalDecision.REQUIRE_APPROVAL,
                    reason=(
                        "Git staging changes the repository index "
                        "and requires user approval."
                    ),
                )

            if tool_name == "git_commit":
                return SafetyCheck(
                    decision=ApprovalDecision.REQUIRE_APPROVAL,
                    reason=(
                        "Creating a Git commit changes repository "
                        "history and requires user approval."
                    ),
                )

            if tool_name == "git_push":
                return SafetyCheck(
                    decision=ApprovalDecision.REQUIRE_APPROVAL,
                    reason=(
                        "Pushing commits to a remote repository "
                        "sends repository changes outside the local "
                        "working copy and requires explicit user "
                        "approval."
                    ),
                )

            return SafetyCheck(
                decision=ApprovalDecision.REQUIRE_APPROVAL,
                reason=(
                    f"Tool modifies repository files: "
                    f"{tool_name}"
                ),
            )

        if tool_name == "run_command":
            return self._check_command(arguments)

        return SafetyCheck(
            decision=ApprovalDecision.DENIED,
            reason=(
                f"Unknown tool is denied by default: "
                f"{tool_name}"
            ),
        )

    def _check_command(
        self,
        arguments: dict[str, Any],
    ) -> SafetyCheck:
        command = arguments.get("command")

        if not isinstance(command, str) or not command.strip():
            return SafetyCheck(
                decision=ApprovalDecision.DENIED,
                reason=(
                    "run_command requires a non-empty "
                    "command string."
                ),
            )

        parts = command.strip().split()

        if not parts:
            return SafetyCheck(
                decision=ApprovalDecision.DENIED,
                reason="Command is empty.",
            )

        executable = (
            parts[0]
            .strip('"')
            .strip("'")
            .lower()
        )

        if executable in DENIED_COMMANDS:
            return SafetyCheck(
                decision=ApprovalDecision.DENIED,
                reason=(
                    f"Command is explicitly denied: "
                    f"{executable}"
                ),
            )

        command_key = (
            executable,
            parts[1].lower() if len(parts) > 1 else "",
        )

        if command_key in SAFE_COMMANDS:
            return SafetyCheck(
                decision=ApprovalDecision.SAFE,
                reason=(
                    f"Read-only repository command: "
                    f"{command}"
                ),
            )

        if executable in APPROVAL_COMMANDS:
            return SafetyCheck(
                decision=ApprovalDecision.REQUIRE_APPROVAL,
                reason=(
                    f"Command execution requires approval: "
                    f"{command}"
                ),
            )

        return SafetyCheck(
            decision=ApprovalDecision.DENIED,
            reason=(
                f"Command is not permitted by the safety policy: "
                f"{command}"
            ),
        )