"""
Gate tests. These are the deterministic policy decisions — full coverage matters here
because Audit will scrutinize this layer.

These tests pass out of the box because gates are fully implemented.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from src.agent.schemas import (
    AgentDecision,
    DecisionAction,
    ExtractedInvoice,
    InvoiceLine,
    RouteTarget,
)
from src.gates.routing import quality_gate, risk_gate, route


def _make_invoice(total: str = "500.00") -> ExtractedInvoice:
    return ExtractedInvoice(
        invoice_number="X-1",
        invoice_date=date(2026, 5, 14),
        supplier_name="Test Supplier",
        supplier_tax_id="123456789RT0001",
        po_reference="PO-5001",
        currency="CAD",
        subtotal=Decimal(total),
        tax=Decimal("0.00"),
        total=Decimal(total),
        bank_account="CA-RBC-1234567",
        lines=[
            InvoiceLine(
                description="x",
                quantity=Decimal("1"),
                unit_price=Decimal(total),
                line_total=Decimal(total),
            )
        ],
    )


def _make_decision(
    *,
    action: DecisionAction = DecisionAction.AUTO_APPROVE,
    confidence: float = 0.95,
    flags: list[str] | None = None,
    total: str = "500.00",
) -> AgentDecision:
    return AgentDecision(
        decision=action,
        confidence=confidence,
        reasons=["test"],
        flags=flags or [],
        invoice=_make_invoice(total),
        matched_vendor_id="V-1001",
        matched_po_number="PO-5001",
    )


# -------- quality gate --------


def test_quality_gate_passes_on_clean_auto_approve():
    ok, _ = quality_gate(_make_decision())
    assert ok is True


def test_quality_gate_fails_below_confidence_floor():
    ok, _ = quality_gate(_make_decision(confidence=0.85))
    assert ok is False


def test_quality_gate_fails_when_agent_did_not_recommend_approve():
    ok, _ = quality_gate(_make_decision(action=DecisionAction.HOLD_FOR_EXCEPTION))
    assert ok is False


# -------- risk gate --------


def test_risk_gate_blocks_on_bank_change():
    ok, _ = risk_gate(_make_decision(flags=["bank_details_changed"]))
    assert ok is False


def test_risk_gate_blocks_on_sanctions_hit():
    ok, _ = risk_gate(_make_decision(flags=["sanctions_hit"]))
    assert ok is False


def test_risk_gate_blocks_on_amount_above_limit():
    ok, _ = risk_gate(_make_decision(total="9000.00"))
    assert ok is False


def test_risk_gate_blocks_on_new_supplier():
    ok, _ = risk_gate(_make_decision(flags=["new_supplier"]))
    assert ok is False


def test_risk_gate_passes_clean():
    ok, _ = risk_gate(_make_decision())
    assert ok is True


# -------- routing (full integration of both gates) --------


def test_route_auto_post_when_both_gates_pass():
    final = route(_make_decision())
    assert final.route_to == RouteTarget.ERP_AUTO_POST


def test_route_fraud_review_on_bank_change_regardless_of_anything_else():
    final = route(_make_decision(confidence=1.0, flags=["bank_details_changed"]))
    assert final.route_to == RouteTarget.FRAUD_REVIEW


def test_route_fraud_review_on_sanctions_hit():
    final = route(_make_decision(flags=["sanctions_hit"]))
    assert final.route_to == RouteTarget.FRAUD_REVIEW


def test_route_approver_inbox_on_high_amount():
    final = route(_make_decision(total="9000.00"))
    assert final.route_to == RouteTarget.APPROVER_INBOX


def test_route_ap_clerk_on_reject():
    final = route(_make_decision(action=DecisionAction.REJECT))
    assert final.route_to == RouteTarget.AP_CLERK_QUEUE


def test_route_approver_inbox_when_quality_low_but_no_hard_flags():
    final = route(_make_decision(confidence=0.7))
    assert final.route_to == RouteTarget.APPROVER_INBOX
