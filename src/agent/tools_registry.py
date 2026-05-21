"""
Tool registry — single source of truth for which tools the agent has,
their schemas, and their implementations.

When you add a new tool, register it here and the agent loop picks it up.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel

from src.agent.schemas import (
    ExtractInvoiceInput,
    ExtractInvoiceOutput,
    LookupGoodsReceiptInput,
    LookupGoodsReceiptOutput,
    LookupPOInput,
    LookupPOOutput,
    LookupVendorInput,
    LookupVendorOutput,
    ScreenSanctionsInput,
    ScreenSanctionsOutput,
    ValidateTaxInput,
    ValidateTaxOutput,
)
from src.tools import extract, po, sanctions, tax, vendor


class ToolSpec(BaseModel):
    name: str
    description: str
    input_schema: type[BaseModel]
    output_schema: type[BaseModel]
    handler: Callable[..., BaseModel]

    model_config = {"arbitrary_types_allowed": True}


# ---------------------------------------------------------------------------
# Registry — agent has read tools only. post_to_erp is called by the
# orchestrator AFTER the policy gates, not by the agent itself.
# ---------------------------------------------------------------------------

TOOLS: list[ToolSpec] = [
    ToolSpec(
        name="extract_invoice",
        description=(
            "Extract structured fields from an invoice PDF. "
            "Returns invoice number, dates, supplier, totals, line items, and bank account."
        ),
        input_schema=ExtractInvoiceInput,
        output_schema=ExtractInvoiceOutput,
        handler=extract.extract_invoice,
    ),
    ToolSpec(
        name="lookup_vendor",
        description=(
            "Look up a supplier in the vendor master. "
            "Prefer tax_id match. Returns bank_account_on_file for fraud comparison."
        ),
        input_schema=LookupVendorInput,
        output_schema=LookupVendorOutput,
        handler=vendor.lookup_vendor,
    ),
    ToolSpec(
        name="lookup_po",
        description="Fetch a purchase order by PO number.",
        input_schema=LookupPOInput,
        output_schema=LookupPOOutput,
        handler=po.lookup_po,
    ),
    ToolSpec(
        name="lookup_goods_receipt",
        description="Fetch the goods receipt for a PO. Confirms what was actually received.",
        input_schema=LookupGoodsReceiptInput,
        output_schema=LookupGoodsReceiptOutput,
        handler=po.lookup_goods_receipt,
    ),
    ToolSpec(
        name="validate_tax",
        description=(
            "Validate a tax ID against the appropriate registry. "
            "Returns whether the ID is valid and the registered legal name."
        ),
        input_schema=ValidateTaxInput,
        output_schema=ValidateTaxOutput,
        handler=tax.validate_tax,
    ),
    ToolSpec(
        name="screen_sanctions",
        description="Screen a supplier name against the sanctions list (OFAC SDN equivalent).",
        input_schema=ScreenSanctionsInput,
        output_schema=ScreenSanctionsOutput,
        handler=sanctions.screen_sanctions,
    ),
]


def to_openai_tools() -> list[dict[str, Any]]:
    """Convert the registry to OpenAI function-calling tool definitions."""
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.input_schema.model_json_schema(),
            },
        }
        for t in TOOLS
    ]


def get_tool(name: str) -> ToolSpec | None:
    return next((t for t in TOOLS if t.name == name), None)
