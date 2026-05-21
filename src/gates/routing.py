"""
Policy gates. Pure functions. No LLM. No I/O.

These are the decisions Audit will scrutinize. Keep them simple, deterministic,
and easy to read out loud in a control review.

Configuration lives in policy.py — never in the agent prompt.
"""

from __future__ import annotations

from decimal import Decimal

from src.agent.schemas import (
    AgentDecision,
    DecisionAction,
    FinalRouting,
    RouteTarget,
)
from src.gates.policy import (
    AUTO_APPROVE_AMOUNT_LIMIT,
    AUTO_APPROVE_CONFIDENCE_FLOOR,
    HARD_BLOCK_FLAGS,
    RISK_FLAGS,
)


def quality_gate(decision: AgentDecision) -> tuple[bool, list[str]]:
    """Gate 1: is the agent's decision confident enough to even consider auto-approve?"""
    notes: list[str] = []
    if decision.decision != DecisionAction.AUTO_APPROVE:
        notes.append(f"agent did not recommend auto-approve ({decision.decision.value})")
        return False, notes
    if decision.confidence < AUTO_APPROVE_CONFIDENCE_FLOOR:
        notes.append(
            f"confidence {decision.confidence:.2f} below floor {AUTO_APPROVE_CONFIDENCE_FLOOR}"
        )
        return False, notes
    notes.append("quality gate: passed")
    return True, notes


def risk_gate(decision: AgentDecision) -> tuple[bool, list[str]]:
    """Gate 2: even if quality passed, do risk policies require human review?"""
    notes: list[str] = []

    hard_hits = [f for f in decision.flags if f in HARD_BLOCK_FLAGS]
    if hard_hits:
        notes.append(f"hard-block flags present: {hard_hits}")
        return False, notes

    risk_hits = [f for f in decision.flags if f in RISK_FLAGS]
    if risk_hits:
        notes.append(f"risk flags present: {risk_hits}")
        return False, notes

    total = decision.invoice.total
    if total > AUTO_APPROVE_AMOUNT_LIMIT:
        notes.append(
            f"invoice total {total} exceeds auto-approve limit {AUTO_APPROVE_AMOUNT_LIMIT}"
        )
        return False, notes

    notes.append("risk gate: passed")
    return True, notes


def route(decision: AgentDecision) -> FinalRouting:
    """
    Run both gates and produce the final routing.

    Decision tree:
        agent says REJECT → AP_CLERK_QUEUE for visibility
        hard-block flag present → FRAUD_REVIEW (regardless of anything else)
        both gates pass → ERP_AUTO_POST
        quality passes, risk fails → APPROVER_INBOX
        quality fails → APPROVER_INBOX or FRAUD_REVIEW depending on flags
    """
    all_notes: list[str] = []

    # Always-fraud-review path: hard-block flags trump everything
    hard_hits = [f for f in decision.flags if f in HARD_BLOCK_FLAGS]
    if hard_hits:
        all_notes.append(f"hard-block flags route to fraud review: {hard_hits}")
        return FinalRouting(
            route_to=RouteTarget.FRAUD_REVIEW,
            decision=decision,
            gate_notes=all_notes,
        )

    if decision.decision == DecisionAction.REJECT:
        all_notes.append("agent recommended reject")
        return FinalRouting(
            route_to=RouteTarget.AP_CLERK_QUEUE,
            decision=decision,
            gate_notes=all_notes,
        )

    q_ok, q_notes = quality_gate(decision)
    all_notes.extend(q_notes)
    r_ok, r_notes = risk_gate(decision)
    all_notes.extend(r_notes)

    if q_ok and r_ok:
        target = RouteTarget.ERP_AUTO_POST
    else:
        target = RouteTarget.APPROVER_INBOX

    return FinalRouting(route_to=target, decision=decision, gate_notes=all_notes)
