"""
post_to_erp.

The agent does NOT call this. The orchestrator does, after the policy gates
return ERP_AUTO_POST. Kept here so the contract is visible.

In production: NetSuite SuiteREST POST, with idempotency_key as External ID
to prevent duplicate postings on retry.
"""

from __future__ import annotations

import hashlib

from rich import print as rprint

from src.agent.schemas import (
    ErrorEnvelope,
    PostToErpInput,
    PostToErpOutput,
)


def post_to_erp(inp: PostToErpInput) -> PostToErpOutput:
    doc_id = "NS-" + hashlib.sha256(inp.idempotency_key.encode()).hexdigest()[:12]
    rprint(
        f"[green]ERP POST[/green] idempotency_key={inp.idempotency_key!r} "
        f"invoice={inp.invoice.invoice_number!r} vendor={inp.vendor_id!r} "
        f"doc_id={doc_id!r}"
    )
    return PostToErpOutput(ok=True, erp_document_id=doc_id)
