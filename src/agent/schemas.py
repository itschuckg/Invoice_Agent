"""
Data contracts for the invoice agent.

Every tool's input/output and the final agent decision are defined here.
Keep this file authoritative — tools and gates depend on it.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared error envelope
# ---------------------------------------------------------------------------


class ErrorEnvelope(BaseModel):
    code: str  # e.g. "VENDOR_NOT_FOUND", "TAX_ID_INVALID"
    message: str
    retryable: bool = False


# ---------------------------------------------------------------------------
# Domain objects
# ---------------------------------------------------------------------------


class InvoiceLine(BaseModel):
    description: str
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal


class ExtractedInvoice(BaseModel):
    """Output of extract_invoice. Pre-OCR'd in this skeleton."""

    invoice_number: str
    invoice_date: date
    supplier_name: str
    supplier_tax_id: str | None = None
    po_reference: str | None = None
    currency: str  # ISO 4217
    subtotal: Decimal
    tax: Decimal
    total: Decimal
    bank_account: str | None = None  # supplier-provided bank on the invoice
    lines: list[InvoiceLine]


class Vendor(BaseModel):
    vendor_id: str
    name: str
    tax_id: str
    bank_account_on_file: str
    active: bool
    onboarded_on: date


class PurchaseOrder(BaseModel):
    po_number: str
    vendor_id: str
    currency: str
    lines: list[InvoiceLine]
    total: Decimal
    status: Literal["open", "closed", "cancelled"]


class GoodsReceipt(BaseModel):
    po_number: str
    received_on: date
    lines: list[InvoiceLine]


# ---------------------------------------------------------------------------
# Tool inputs / outputs
# ---------------------------------------------------------------------------


class ExtractInvoiceInput(BaseModel):
    invoice_id: str  # filename without extension in src/data/invoices/


class ExtractInvoiceOutput(BaseModel):
    ok: bool
    data: ExtractedInvoice | None = None
    error: ErrorEnvelope | None = None


class LookupVendorInput(BaseModel):
    tax_id: str | None = None
    name: str | None = None  # at least one of tax_id or name required


class LookupVendorOutput(BaseModel):
    ok: bool
    data: Vendor | None = None
    error: ErrorEnvelope | None = None


class LookupPOInput(BaseModel):
    po_number: str


class LookupPOOutput(BaseModel):
    ok: bool
    data: PurchaseOrder | None = None
    error: ErrorEnvelope | None = None


class LookupGoodsReceiptInput(BaseModel):
    po_number: str


class LookupGoodsReceiptOutput(BaseModel):
    ok: bool
    data: GoodsReceipt | None = None
    error: ErrorEnvelope | None = None


class ValidateTaxInput(BaseModel):
    tax_id: str
    country: str  # ISO 3166-1 alpha-2


class ValidateTaxOutput(BaseModel):
    ok: bool
    valid: bool = False
    registered_name: str | None = None
    error: ErrorEnvelope | None = None


class ScreenSanctionsInput(BaseModel):
    name: str
    country: str | None = None


class ScreenSanctionsOutput(BaseModel):
    ok: bool
    is_hit: bool = False
    matched_against: str | None = None
    error: ErrorEnvelope | None = None


class PostToErpInput(BaseModel):
    idempotency_key: str
    invoice: ExtractedInvoice
    vendor_id: str
    po_number: str | None = None
    gl_account: str | None = None


class PostToErpOutput(BaseModel):
    ok: bool
    erp_document_id: str | None = None
    error: ErrorEnvelope | None = None


# ---------------------------------------------------------------------------
# Agent decision
# ---------------------------------------------------------------------------


class DecisionAction(str, Enum):
    AUTO_APPROVE = "auto_approve"
    ROUTE_FOR_APPROVAL = "route_for_approval"
    HOLD_FOR_EXCEPTION = "hold_for_exception"
    REJECT = "reject"


class RouteTarget(str, Enum):
    ERP_AUTO_POST = "erp_auto_post"
    APPROVER_INBOX = "approver_inbox"
    FRAUD_REVIEW = "fraud_review"
    AP_CLERK_QUEUE = "ap_clerk_queue"


class AgentDecision(BaseModel):
    """The agent's structured output. Gates consume this and produce final routing."""

    decision: DecisionAction
    confidence: float = Field(ge=0.0, le=1.0)
    reasons: list[str]
    flags: list[str] = Field(default_factory=list)  # e.g. "bank_details_changed"
    invoice: ExtractedInvoice
    matched_vendor_id: str | None = None
    matched_po_number: str | None = None


class FinalRouting(BaseModel):
    """Output of the policy gates — what actually happens to the invoice."""

    route_to: RouteTarget
    decision: AgentDecision
    gate_notes: list[str]
