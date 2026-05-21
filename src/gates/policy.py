"""
Risk policy configuration.

This is the file Audit and Risk should review. Everything here is plain
data, no logic. Changes to thresholds require an ADR.
"""

from __future__ import annotations

from decimal import Decimal

# Quality threshold for auto-approval
AUTO_APPROVE_CONFIDENCE_FLOOR: float = 0.90

# Amount threshold — invoices above this always require human approval
AUTO_APPROVE_AMOUNT_LIMIT: Decimal = Decimal("5000.00")

# Hard-block flags — always routed to fraud review, no exceptions
HARD_BLOCK_FLAGS: set[str] = {
    "bank_details_changed",
    "sanctions_hit",
    "duplicate_invoice",
}

# Risk flags — block auto-approve but route to approver, not fraud
RISK_FLAGS: set[str] = {
    "new_supplier",
    "tax_invalid",
    "math_mismatch",
    "no_po",
    "po_mismatch",
}

# Tolerance for three-way match (consumed by the agent via prompt)
PRICE_TOLERANCE_PERCENT: float = 2.0
QUANTITY_TOLERANCE_PERCENT: float = 5.0
