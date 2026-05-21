"""
lookup_po and lookup_goods_receipt.

Both read from src/data/pos.json. The data file structure:
{
  "purchase_orders": [PurchaseOrder, ...],
  "goods_receipts": [GoodsReceipt, ...]
}
"""

from __future__ import annotations

import json
from pathlib import Path

from src.agent.schemas import (
    ErrorEnvelope,
    GoodsReceipt,
    LookupGoodsReceiptInput,
    LookupGoodsReceiptOutput,
    LookupPOInput,
    LookupPOOutput,
    PurchaseOrder,
)

_PO_FILE = Path(__file__).parent.parent / "data" / "pos.json"


def _load() -> dict:
    return json.loads(_PO_FILE.read_text())


def lookup_po(inp: LookupPOInput) -> LookupPOOutput:
    data = _load()
    for record in data["purchase_orders"]:
        if record["po_number"] == inp.po_number:
            return LookupPOOutput(ok=True, data=PurchaseOrder.model_validate(record))
    return LookupPOOutput(
        ok=False,
        error=ErrorEnvelope(
            code="PO_NOT_FOUND",
            message=f"No PO found with number {inp.po_number}",
            retryable=False,
        ),
    )


def lookup_goods_receipt(inp: LookupGoodsReceiptInput) -> LookupGoodsReceiptOutput:
    data = _load()
    for record in data["goods_receipts"]:
        if record["po_number"] == inp.po_number:
            return LookupGoodsReceiptOutput(ok=True, data=GoodsReceipt.model_validate(record))
    return LookupGoodsReceiptOutput(
        ok=False,
        error=ErrorEnvelope(
            code="GR_NOT_FOUND",
            message=f"No goods receipt found for PO {inp.po_number}",
            retryable=False,
        ),
    )
