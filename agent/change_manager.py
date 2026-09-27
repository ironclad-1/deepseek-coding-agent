from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ChangeDecision(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


@dataclass
class ChangeOperation:
    """
    One concrete repository operation that belongs to a
    larger proposed change.
    """

    tool_name: str
    arguments: dict[str, Any]
    description: str
    reason: str
    files: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.tool_name, str):
            raise TypeError(
                "tool_name must be a string."
            )

        self.tool_name = self.tool_name.strip()

        if not self.tool_name:
            raise ValueError(
                "tool_name cannot be empty."
            )

        if not isinstance(self.arguments, dict):
            raise TypeError(
                "arguments must be a dictionary."
            )

        if not isinstance(self.description, str):
            raise TypeError(
                "description must be a string."
            )

        self.description = self.description.strip()

        if not self.description:
            raise ValueError(
                "description cannot be empty."
            )

        if not isinstance(self.reason, str):
            raise TypeError(
                "reason must be a string."
            )

        self.reason = self.reason.strip()

        if not self.reason:
            raise ValueError(
                "reason cannot be empty."
            )

        if not isinstance(self.files, list):
            raise TypeError(
                "files must be a list."
            )

        normalized_files: list[str] = []

        for path in self.files:
            if not isinstance(path, str):
                raise TypeError(
                    "Every file path must be a string."
                )

            path = path.strip()

            if path and path not in normalized_files:
                normalized_files.append(path)

        self.files = normalized_files


@dataclass
class ChangeProposal:
    """
    Human-facing proposal representing a set of repository
    modifications that require user approval.
    """

    summary: str
    reason: str
    operations: list[ChangeOperation] = field(
        default_factory=list
    )
    files: list[str] = field(default_factory=list)
    title: str = "Proposed Changes"

    def __post_init__(self) -> None:
        if not isinstance(self.title, str):
            raise TypeError(
                "title must be a string."
            )

        self.title = self.title.strip()

        if not self.title:
            self.title = "Proposed Changes"

        if not isinstance(self.summary, str):
            raise TypeError(
                "summary must be a string."
            )

        self.summary = self.summary.strip()

        if not self.summary:
            raise ValueError(
                "summary cannot be empty."
            )

        if not isinstance(self.reason, str):
            raise TypeError(
                "reason must be a string."
            )

        self.reason = self.reason.strip()

        if not self.reason:
            raise ValueError(
                "reason cannot be empty."
            )

        if not isinstance(self.operations, list):
            raise TypeError(
                "operations must be a list."
            )

        for operation in self.operations:
            if not isinstance(
                operation,
                ChangeOperation,
            ):
                raise TypeError(
                    "operations must contain only "
                    "ChangeOperation objects."
                )

        if not isinstance(self.files, list):
            raise TypeError(
                "files must be a list."
            )

        normalized_files: list[str] = []

        for path in self.files:
            if not isinstance(path, str):
                raise TypeError(
                    "Every file path must be a string."
                )

            path = path.strip()

            if path and path not in normalized_files:
                normalized_files.append(path)

        for operation in self.operations:
            for path in operation.files:
                if path not in normalized_files:
                    normalized_files.append(path)

        self.files = normalized_files

    @property
    def operation_count(self) -> int:
        return len(self.operations)

    @property
    def has_operations(self) -> bool:
        return bool(self.operations)

    @property
    def is_empty(self) -> bool:
        return not self.operations and not self.files

    def render(self) -> str:
        """
        Render the proposal as a human-readable approval message.
        """

        lines: list[str] = []

        lines.append("=" * 60)
        lines.append(self.title.upper())
        lines.append("=" * 60)
        lines.append("")
        lines.append("WHAT:")
        lines.append(self.summary)
        lines.append("")
        lines.append("WHY:")
        lines.append(self.reason)

        if self.files:
            lines.append("")
            lines.append("FILES:")

            for path in self.files:
                lines.append(f"- {path}")

        if self.operations:
            lines.append("")
            lines.append("OPERATIONS:")

            for index, operation in enumerate(
                self.operations,
                start=1,
            ):
                lines.append(
                    f"{index}. "
                    f"{operation.tool_name}: "
                    f"{operation.description}"
                )

        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)

    def render_detailed(self) -> str:
        """
        Render the proposal with detailed information about
        every individual operation.
        """

        lines: list[str] = []

        lines.append(self.render())

        if self.operations:
            lines.append("")
            lines.append("DETAILS:")
            lines.append("")

            for index, operation in enumerate(
                self.operations,
                start=1,
            ):
                lines.append(
                    f"Operation {index}: "
                    f"{operation.tool_name}"
                )
                lines.append(
                    f"Description: "
                    f"{operation.description}"
                )
                lines.append(
                    f"Why: "
                    f"{operation.reason}"
                )

                if operation.files:
                    lines.append(
                        "Files: "
                        + ", ".join(operation.files)
                    )

                lines.append("")

        return "\n".join(lines).rstrip()

    def to_model_context(self) -> str:
        """
        Convert the proposal into information that can be fed
        back to the model after an approval decision.
        """

        lines = [
            "A repository change proposal was evaluated.",
            "",
            "PROPOSED WHAT:",
            self.summary,
            "",
            "PROPOSED WHY:",
            self.reason,
        ]

        if self.files:
            lines.extend(
                [
                    "",
                    "PROPOSED FILES:",
                ]
            )

            lines.extend(
                f"- {path}"
                for path in self.files
            )

        if self.operations:
            lines.extend(
                [
                    "",
                    "PROPOSED OPERATIONS:",
                ]
            )

            for operation in self.operations:
                lines.append(
                    f"- {operation.tool_name}: "
                    f"{operation.description}"
                )

        return "\n".join(lines)

    def with_rejection_reason(
        self,
        rejection_reason: str,
    ) -> str:
        """
        Build model feedback after the user rejects a proposal.
        """

        if not isinstance(
            rejection_reason,
            str,
        ):
            raise TypeError(
                "rejection_reason must be a string."
            )

        rejection_reason = rejection_reason.strip()

        if not rejection_reason:
            raise ValueError(
                "rejection_reason cannot be empty."
            )

        return (
            "The user rejected the proposed repository changes.\n\n"
            f"{self.to_model_context()}\n\n"
            "USER REJECTION REASON:\n"
            f"{rejection_reason}\n\n"
            "Respect the user's rejection reason.\n"
            "Do not execute the rejected changes.\n"
            "Reconsider the task based on the user's feedback.\n"
            "You may do one of the following:\n"
            "1. Propose a revised modification.\n"
            "2. Ask the user for clarification if the intended "
            "change is ambiguous.\n"
            "3. Stop repository modification if the user does "
            "not want further changes."
        )


@dataclass
class ChangeApprovalResult:
    """
    Result returned by the change approval gate.
    """

    decision: ChangeDecision
    proposal: ChangeProposal
    rejection_reason: str | None = None

    @property
    def approved(self) -> bool:
        return self.decision == ChangeDecision.APPROVED

    @property
    def rejected(self) -> bool:
        return self.decision == ChangeDecision.REJECTED

    @property
    def cancelled(self) -> bool:
        return self.decision == ChangeDecision.CANCELLED

    def to_model_context(self) -> str:
        """
        Convert the approval result into a model-facing message.
        """

        if self.approved:
            return (
                "The user approved the proposed repository "
                "changes.\n\n"
                f"{self.proposal.to_model_context()}\n\n"
                "The approved operations may now be executed."
            )

        if self.rejected:
            if not self.rejection_reason:
                return (
                    "The user rejected the proposed repository "
                    "changes.\n\n"
                    f"{self.proposal.to_model_context()}\n\n"
                    "No rejected operation may be executed."
                )

            return self.proposal.with_rejection_reason(
                self.rejection_reason
            )

        return (
            "The user cancelled the proposed repository "
            "changes.\n\n"
            f"{self.proposal.to_model_context()}\n\n"
            "Do not execute the proposed changes."
        )


class ChangeManager:
    """
    Manage the lifecycle of a proposed repository change.

    This class does not execute repository operations and does
    not interact with the user directly.
    """

    def create_proposal(
        self,
        *,
        summary: str,
        reason: str,
        operations: list[ChangeOperation],
        files: list[str] | None = None,
        title: str = "Proposed Changes",
    ) -> ChangeProposal:
        return ChangeProposal(
            title=title,
            summary=summary,
            reason=reason,
            operations=operations,
            files=files or [],
        )

    def approved(
        self,
        proposal: ChangeProposal,
    ) -> ChangeApprovalResult:
        return ChangeApprovalResult(
            decision=ChangeDecision.APPROVED,
            proposal=proposal,
        )

    def rejected(
        self,
        proposal: ChangeProposal,
        rejection_reason: str,
    ) -> ChangeApprovalResult:
        return ChangeApprovalResult(
            decision=ChangeDecision.REJECTED,
            proposal=proposal,
            rejection_reason=rejection_reason.strip(),
        )

    def cancelled(
        self,
        proposal: ChangeProposal,
    ) -> ChangeApprovalResult:
        return ChangeApprovalResult(
            decision=ChangeDecision.CANCELLED,
            proposal=proposal,
        )