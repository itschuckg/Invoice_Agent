"""
extract_invoice tool.

In production this calls Azure Document Intelligence or AWS Textract on a PDF.
In this skeleton it reads pre-parsed JSON from src/data/invoices/{invoice_id}.json
so we can focus on the agent loop rather than OCR.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.agent.schemas import (
    ErrorEnvelope,
    ExtractedInvoice,
    ExtractInvoiceInput,
    ExtractInvoiceOutput,
)

_INVOICES_DIR = Path(__file__).parent.parent / "data" / "invoices"


def extract_invoice(inp: ExtractInvoiceInput) -> ExtractInvoiceOutput:
    path = _INVOICES_DIR / f"{inp.invoice_id}.json"
    if not path.exists():
        return ExtractInvoiceOutput(
            ok=False,
            error=ErrorEnvelope(
                code="INVOICE_NOT_FOUND",
                message=f"No invoice file for id {inp.invoice_id}",
                retryable=False,
            ),
        )
    data = json.loads(path.read_text())
    return ExtractInvoiceOutput(ok=True, data=ExtractedInvoice.model_validate(data))
