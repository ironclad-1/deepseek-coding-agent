from __future__ import annotations

from typing import Any, Iterable

from agent.change_manager import (
    ChangeOperation,
    ChangeProposal,
)


class ChangePlanner:
    """
    Convert model-requested operations into human-readable
    ChangeProposal objects.

    This class does not execute tools and does not interact with
    the user.

    Proposal categories:

        LOCAL / REPOSITORY CHANGES
            - write_file
            - edit_file
            - git_add
            - git_commit
            - run_command

        REMOTE REPOSITORY CHANGE
            - git_push

    git_push is intentionally represented by a separate proposal
    builder so the runtime can require an independent approval before
    sending commits to a remote repository.
    """

    # ---------------------------------------------------------
    # Local repository changes
    # ---------------------------------------------------------

    MODIFYING_TOOLS = {
        "write_file",
        "edit_file",
        "git_add",
        "git_commit",
    }

    APPROVAL_COMMAND_TOOLS = {
        "run_command",
    }

    # ---------------------------------------------------------
    # Remote repository changes
    # ---------------------------------------------------------

    REMOTE_PUSH_TOOLS = {
        "git_push",
    }

    # All operations understood by the planner.
    ALL_APPROVAL_TOOLS = (
        MODIFYING_TOOLS
        | APPROVAL_COMMAND_TOOLS
        | REMOTE_PUSH_TOOLS
    )

    def build_proposal(
        self,
        *,
        user_message: str,
        tool_calls: Iterable[Any],
        model_summary: str | None = None,
        model_reason: str | None = None,
    ) -> ChangeProposal | None:
        """
        Build one proposal from approval-required tool calls.

        This method preserves the original behavior and may include
        git_push when it is present in tool_calls.

        The runtime should use build_local_proposal() and
        build_push_proposal() when enforcing the separate Phase 14
        remote-push approval boundary.
        """

        return self._build_proposal(
            user_message=user_message,
            tool_calls=tool_calls,
            allowed_tools=self.ALL_APPROVAL_TOOLS,
            title="Proposed Repository Changes",
            model_summary=model_summary,
            model_reason=model_reason,
        )

    def build_local_proposal(
        self,
        *,
        user_message: str,
        tool_calls: Iterable[Any],
        model_summary: str | None = None,
        model_reason: str | None = None,
    ) -> ChangeProposal | None:
        """
        Build a proposal containing local repository operations.

        Included:

            write_file
            edit_file
            git_add
            git_commit
            run_command

        git_push is intentionally excluded.
        """

        return self._build_proposal(
            user_message=user_message,
            tool_calls=tool_calls,
            allowed_tools=(
                self.MODIFYING_TOOLS
                | self.APPROVAL_COMMAND_TOOLS
            ),
            title="Proposed Repository Changes",
            model_summary=model_summary,
            model_reason=model_reason,
        )

    def build_push_proposal(
        self,
        *,
        user_message: str,
        tool_calls: Iterable[Any],
        model_summary: str | None = None,
        model_reason: str | None = None,
    ) -> ChangeProposal | None:
        """
        Build a proposal containing only remote push operations.

        A push is deliberately separated from local repository
        modifications and commits.
        """

        return self._build_proposal(
            user_message=user_message,
            tool_calls=tool_calls,
            allowed_tools=self.REMOTE_PUSH_TOOLS,
            title="Proposed Remote Push",
            model_summary=model_summary,
            model_reason=model_reason,
        )

    def _build_proposal(
        self,
        *,
        user_message: str,
        tool_calls: Iterable[Any],
        allowed_tools: set[str],
        title: str,
        model_summary: str | None,
        model_reason: str | None,
    ) -> ChangeProposal | None:
        """
        Internal proposal construction shared by all proposal types.
        """

        operations: list[ChangeOperation] = []
        files: list[str] = []

        for tool_call in tool_calls:
            operation = self._build_operation(
                tool_call=tool_call,
                user_message=user_message,
                allowed_tools=allowed_tools,
            )

            if operation is None:
                continue

            operations.append(operation)

            for path in operation.files:
                if path not in files:
                    files.append(path)

        if not operations:
            return None

        summary = self._build_summary(
            operations=operations,
            model_summary=model_summary,
        )

        reason = self._build_reason(
            user_message=user_message,
            operations=operations,
            model_reason=model_reason,
        )

        return ChangeProposal(
            title=title,
            summary=summary,
            reason=reason,
            operations=operations,
            files=files,
        )

    def _build_operation(
        self,
        *,
        tool_call: Any,
        user_message: str,
        allowed_tools: set[str],
    ) -> ChangeOperation | None:
        """
        Convert one model tool call into a ChangeOperation.
        """

        function = getattr(
            tool_call,
            "function",
            None,
        )

        if function is None:
            return None

        tool_name = getattr(
            function,
            "name",
            None,
        )

        arguments = getattr(
            function,
            "arguments",
            None,
        )

        if not isinstance(tool_name, str):
            return None

        tool_name = tool_name.strip().lower()

        if not isinstance(arguments, dict):
            return None

        if tool_name not in allowed_tools:
            return None

        files = self._extract_files(
            tool_name=tool_name,
            arguments=arguments,
        )

        description = self._describe_operation(
            tool_name=tool_name,
            arguments=arguments,
        )

        reason = self._describe_reason(
            tool_name=tool_name,
            user_message=user_message,
        )

        return ChangeOperation(
            tool_name=tool_name,
            arguments=arguments,
            description=description,
            reason=reason,
            files=files,
        )

    def _extract_files(
        self,
        *,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> list[str]:
        """
        Extract repository files involved in an operation.

        git_push does not identify individual files because it sends
        commits rather than selected working-tree paths.
        """

        files: list[str] = []

        if tool_name in {
            "write_file",
            "edit_file",
        }:
            path = arguments.get("path")

            if isinstance(path, str) and path.strip():
                files.append(path.strip())

        elif tool_name == "git_add":
            paths = arguments.get("paths")

            if isinstance(paths, list):
                for path in paths:
                    if isinstance(path, str) and path.strip():
                        files.append(path.strip())

        return files

    def _describe_operation(
        self,
        *,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> str:
        """
        Produce a concise human-readable description of an
        individual operation.
        """

        if tool_name == "write_file":
            path = str(
                arguments.get(
                    "path",
                    "unknown file",
                )
            )

            overwrite = arguments.get(
                "overwrite",
                False,
            )

            if overwrite:
                return (
                    f"Write or replace the contents of "
                    f"{path}."
                )

            return (
                f"Create {path}."
            )

        if tool_name == "edit_file":
            path = str(
                arguments.get(
                    "path",
                    "unknown file",
                )
            )

            return (
                f"Modify {path} by applying the requested "
                f"text replacement."
            )

        if tool_name == "git_add":
            paths = arguments.get("paths")

            if isinstance(paths, list):
                formatted_paths = ", ".join(
                    str(path)
                    for path in paths
                    if isinstance(path, str)
                )

                return (
                    f"Stage the selected repository paths: "
                    f"{formatted_paths}."
                )

            return (
                "Stage the selected repository paths."
            )

        if tool_name == "git_commit":
            message = arguments.get("message")

            if isinstance(message, str) and message.strip():
                return (
                    f"Create a Git commit with message: "
                    f"\"{message.strip()}\"."
                )

            return (
                "Create a Git commit from the currently "
                "staged changes."
            )

        if tool_name == "git_push":
            remote = arguments.get(
                "remote",
                "origin",
            )

            branch = arguments.get(
                "branch",
            )

            if (
                isinstance(remote, str)
                and remote.strip()
            ):
                remote_text = remote.strip()
            else:
                remote_text = "origin"

            if (
                isinstance(branch, str)
                and branch.strip()
            ):
                return (
                    f"Push the local branch "
                    f"{branch.strip()} to remote "
                    f"{remote_text}."
                )

            return (
                f"Push the current local branch to "
                f"remote {remote_text}."
            )

        if tool_name == "run_command":
            command = arguments.get("command")

            if isinstance(command, str):
                return (
                    f"Execute the approved command: "
                    f"{command.strip()}."
                )

            return (
                "Execute the requested repository command."
            )

        return (
            f"Execute the requested {tool_name} operation."
        )

    def _describe_reason(
        self,
        *,
        tool_name: str,
        user_message: str,
    ) -> str:
        """
        Produce a conservative reason for an operation.

        The planner does not invent technical claims about the
        repository. It uses the user's task as the source of
        intent when a model-provided reason is unavailable.
        """

        task = user_message.strip()

        if tool_name == "write_file":
            return (
                f"The task requires creating or updating a file "
                f"as part of the requested work. User request: "
                f"{task}"
            )

        if tool_name == "edit_file":
            return (
                f"The task requires modifying existing code or "
                f"content to address the requested work. "
                f"User request: {task}"
            )

        if tool_name == "git_add":
            return (
                "The requested changes need to be staged before "
                "they can be committed."
            )

        if tool_name == "git_commit":
            return (
                "The completed repository changes are intended to "
                "be recorded in Git history."
            )

        if tool_name == "git_push":
            return (
                "The completed commits are being sent to a remote "
                "repository. This is a separate remote operation "
                "from local repository changes and commits."
            )

        if tool_name == "run_command":
            return (
                f"The command is being requested as part of the "
                f"task workflow. User request: {task}"
            )

        return (
            f"The operation was requested as part of the task: "
            f"{task}"
        )

    def _build_summary(
        self,
        *,
        operations: list[ChangeOperation],
        model_summary: str | None,
    ) -> str:
        """
        Prefer a model-provided concise summary. Otherwise build
        a conservative summary from the concrete operations.
        """

        if isinstance(
            model_summary,
            str,
        ):
            model_summary = model_summary.strip()

            if model_summary:
                return model_summary

        descriptions = [
            operation.description
            for operation in operations
        ]

        if len(descriptions) == 1:
            return descriptions[0]

        return "\n".join(
            f"- {description}"
            for description in descriptions
        )

    def _build_reason(
        self,
        *,
        user_message: str,
        operations: list[ChangeOperation],
        model_reason: str | None,
    ) -> str:
        """
        Prefer a model-provided reason. Otherwise derive a
        conservative explanation from the task and operations.
        """

        if isinstance(
            model_reason,
            str,
        ):
            model_reason = model_reason.strip()

            if model_reason:
                return model_reason

        task = user_message.strip()

        if len(operations) == 1:
            return (
                f"This operation is required to address the "
                f"user's requested task: {task}"
            )

        return (
            f"These operations are required to address the "
            f"user's requested task: {task}"
        )


def build_change_proposal(
    *,
    user_message: str,
    tool_calls: Iterable[Any],
    model_summary: str | None = None,
    model_reason: str | None = None,
) -> ChangeProposal | None:
    """
    Convenience function for creating a general ChangeProposal.
    """

    planner = ChangePlanner()

    return planner.build_proposal(
        user_message=user_message,
        tool_calls=tool_calls,
        model_summary=model_summary,
        model_reason=model_reason,
    )


def build_local_change_proposal(
    *,
    user_message: str,
    tool_calls: Iterable[Any],
    model_summary: str | None = None,
    model_reason: str | None = None,
) -> ChangeProposal | None:
    """
    Convenience function for creating a local repository proposal.
    """

    planner = ChangePlanner()

    return planner.build_local_proposal(
        user_message=user_message,
        tool_calls=tool_calls,
        model_summary=model_summary,
        model_reason=model_reason,
    )


def build_push_change_proposal(
    *,
    user_message: str,
    tool_calls: Iterable[Any],
    model_summary: str | None = None,
    model_reason: str | None = None,
) -> ChangeProposal | None:
    """
    Convenience function for creating a remote push proposal.
    """

    planner = ChangePlanner()

    return planner.build_push_proposal(
        user_message=user_message,
        tool_calls=tool_calls,
        model_summary=model_summary,
        model_reason=model_reason,
    )