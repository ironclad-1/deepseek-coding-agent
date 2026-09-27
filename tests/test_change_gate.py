from agent.change_manager import (
    ChangeDecision,
    ChangeOperation,
    ChangeProposal,
)
from safety.change_gate import ChangeGate


def make_proposal() -> ChangeProposal:
    return ChangeProposal(
        title="Calculator Changes",
        summary="Add the addition operation.",
        reason="The current implementation only supports subtraction.",
        operations=[
            ChangeOperation(
                tool_name="edit_file",
                arguments={
                    "path": "calculator.py",
                    "old_text": "return a - b",
                    "new_text": "return a + b",
                },
                description="Update calculator logic.",
                reason="Implement addition.",
                files=["calculator.py"],
            )
        ],
    )


def test_change_gate_approval(monkeypatch):
    gate = ChangeGate()
    proposal = make_proposal()

    monkeypatch.setattr(
        "builtins.input",
        lambda _: "y",
    )

    result = gate.request_approval(proposal)

    assert result.decision == ChangeDecision.APPROVED
    assert result.approved is True
    assert result.rejected is False
    assert result.cancelled is False


def test_change_gate_rejection_collects_reason(monkeypatch):
    gate = ChangeGate()
    proposal = make_proposal()

    responses = iter(
        [
            "n",
            "Do not make any changes. I only wanted inspection.",
        ]
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _: next(responses),
    )

    result = gate.request_approval(proposal)

    assert result.decision == ChangeDecision.REJECTED
    assert result.rejected is True
    assert result.approved is False
    assert result.cancelled is False
    assert result.rejection_reason == (
        "Do not make any changes. I only wanted inspection."
    )


def test_change_gate_cancellation(monkeypatch):
    gate = ChangeGate()
    proposal = make_proposal()

    monkeypatch.setattr(
        "builtins.input",
        lambda _: "c",
    )

    result = gate.request_approval(proposal)

    assert result.decision == ChangeDecision.CANCELLED
    assert result.cancelled is True
    assert result.approved is False
    assert result.rejected is False