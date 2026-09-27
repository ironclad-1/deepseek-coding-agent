from agent.change_manager import (
    ChangeDecision,
    ChangeManager,
    ChangeOperation,
    ChangeProposal,
)


def test_change_operation_validation_and_normalization():
    operation = ChangeOperation(
        tool_name="edit_file",
        arguments={
            "path": "calculator.py",
            "old_text": "return a - b",
            "new_text": "return a + b",
        },
        description="Replace subtraction with addition.",
        reason="The requested behavior requires addition.",
        files=["calculator.py", "calculator.py"],
    )

    assert operation.tool_name == "edit_file"
    assert operation.files == ["calculator.py"]


def test_change_proposal_contains_what_why_files_and_operations():
    operations = [
        ChangeOperation(
            tool_name="edit_file",
            arguments={
                "path": "calculator.py",
                "old_text": "return a - b",
                "new_text": "return a + b",
            },
            description="Change the calculation logic.",
            reason="Implement the requested addition behavior.",
            files=["calculator.py"],
        ),
        ChangeOperation(
            tool_name="write_file",
            arguments={
                "path": "tests/test_calculator.py",
                "content": "def test_add(): pass",
            },
            description="Add a regression test.",
            reason="Verify the new behavior.",
            files=["tests/test_calculator.py"],
        ),
    ]

    proposal = ChangeProposal(
        title="Calculator Changes",
        summary="Add the addition operation and a regression test.",
        reason="The current implementation does not support addition.",
        operations=operations,
    )

    rendered = proposal.render()

    assert "calculator changes" in rendered.lower()
    assert "WHAT:" in rendered
    assert "Add the addition operation and a regression test." in rendered
    assert "WHY:" in rendered
    assert "The current implementation does not support addition." in rendered
    assert "FILES:" in rendered
    assert "calculator.py" in rendered
    assert "tests/test_calculator.py" in rendered
    assert "OPERATIONS:" in rendered
    assert "edit_file" in rendered
    assert "write_file" in rendered


def test_change_proposal_aggregates_files():
    proposal = ChangeProposal(
        title="Test",
        summary="Modify files.",
        reason="Required for the task.",
        operations=[
            ChangeOperation(
                tool_name="edit_file",
                arguments={},
                description="Edit A.",
                reason="Reason A.",
                files=["a.py"],
            ),
            ChangeOperation(
                tool_name="write_file",
                arguments={},
                description="Edit B.",
                reason="Reason B.",
                files=["b.py"],
            ),
            ChangeOperation(
                tool_name="edit_file",
                arguments={},
                description="Edit A again.",
                reason="Reason A2.",
                files=["a.py"],
            ),
        ],
    )

    assert proposal.files == ["a.py", "b.py"]
    assert proposal.operation_count == 3
    assert proposal.has_operations is True
    assert proposal.is_empty is False


def test_rejection_feedback_contains_user_reason():
    manager = ChangeManager()

    proposal = ChangeProposal(
        title="Test Changes",
        summary="Modify calculator.py.",
        reason="Implement requested functionality.",
        operations=[
            ChangeOperation(
                tool_name="edit_file",
                arguments={"path": "calculator.py"},
                description="Edit calculator.py.",
                reason="Implement functionality.",
                files=["calculator.py"],
            )
        ],
    )

    result = manager.rejected(
        proposal,
        "Do not make any changes. I only wanted inspection.",
    )

    assert result.decision == ChangeDecision.REJECTED
    assert result.rejected is True
    assert result.approved is False
    assert result.cancelled is False

    context = result.to_model_context()

    assert "rejected" in context.lower()
    assert "Do not make any changes" in context
    assert "only wanted inspection" in context
    assert "Do not execute the rejected changes" in context