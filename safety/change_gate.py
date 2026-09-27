from __future__ import annotations

from agent.change_manager import (
    ChangeApprovalResult,
    ChangeDecision,
    ChangeManager,
    ChangeProposal,
)


class ChangeGate:
    """
    Human-facing approval gate for repository changes.

    Responsibilities:
        - Display the proposed changes.
        - Ask the user for approval.
        - Capture the reason when changes are rejected.
        - Return the decision to the agent runtime.

    This class does not execute repository operations.
    """

    def __init__(
        self,
        *,
        change_manager: ChangeManager | None = None,
    ) -> None:
        self.change_manager = (
            change_manager
            if change_manager is not None
            else ChangeManager()
        )

    def request_approval(
        self,
        proposal: ChangeProposal,
    ) -> ChangeApprovalResult:
        """
        Present a change proposal and obtain the user's decision.
        """

        if not isinstance(
            proposal,
            ChangeProposal,
        ):
            raise TypeError(
                "proposal must be a ChangeProposal."
            )

        print()
        print(proposal.render())

        print()
        print(
            "Do you approve these changes?"
        )

        while True:
            response = input(
                "[y]es / [n]o / [c]ancel: "
            ).strip().lower()

            if response in {
                "y",
                "yes",
            }:
                print()
                print(
                    "[APPROVAL] User approved the proposed changes."
                )

                return self.change_manager.approved(
                    proposal
                )

            if response in {
                "n",
                "no",
            }:
                return self._handle_rejection(
                    proposal
                )

            if response in {
                "c",
                "cancel",
            }:
                print()
                print(
                    "[APPROVAL] User cancelled the proposed changes."
                )

                return self.change_manager.cancelled(
                    proposal
                )

            print(
                "Please enter 'y', 'n', or 'c'."
            )

    def _handle_rejection(
        self,
        proposal: ChangeProposal,
    ) -> ChangeApprovalResult:
        """
        Ask why the user rejected the proposal and return
        the reason to the runtime.
        """

        print()
        print(
            "[APPROVAL] User rejected the proposed changes."
        )
        print()

        while True:
            rejection_reason = input(
                "Why are you not approving these changes?\n> "
            ).strip()

            if rejection_reason:
                print()
                print(
                    "[APPROVAL] Rejection reason captured."
                )

                return self.change_manager.rejected(
                    proposal,
                    rejection_reason,
                )

            print(
                "Please provide a reason, or type "
                "'cancel' to cancel the task."
            )

            cancel_response = input(
                "> "
            ).strip().lower()

            if cancel_response in {
                "cancel",
                "c",
            }:
                print()
                print(
                    "[APPROVAL] User cancelled the proposed changes."
                )

                return self.change_manager.cancelled(
                    proposal
                )

            if cancel_response:
                rejection_reason = cancel_response

                print()
                print(
                    "[APPROVAL] Rejection reason captured."
                )

                return self.change_manager.rejected(
                    proposal,
                    rejection_reason,
                )