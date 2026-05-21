"""
lookup_vendor tool.

Reads src/data/vendor_master.json. Returns Vendor with bank_account_on_file
so the agent can compare against the invoice's bank account and detect
bank-detail-change fraud.
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

from src.agent.schemas import (
    ErrorEnvelope,
    LookupVendorInput,
    LookupVendorOutput,
    Vendor,
)

_VENDOR_FILE = Path(__file__).parent.parent / "data" / "vendor_master.json"


def lookup_vendor(inp: LookupVendorInput) -> LookupVendorOutput:
    if not inp.tax_id and not inp.name:
        return LookupVendorOutput(
            ok=False,
            error=ErrorEnvelope(
                code="MISSING_LOOKUP_KEY",
                message="At least one of tax_id or name must be provided",
                retryable=False,
            ),
        )

    records = json.loads(_VENDOR_FILE.read_text())
    matches: list[dict] = []

    if inp.tax_id:
        matches = [r for r in records if r["tax_id"] == inp.tax_id]
    else:
        name_lower = inp.name.lower()  # type: ignore[union-attr]
        matches = [r for r in records if name_lower in r["name"].lower()]

    if not matches:
        return LookupVendorOutput(
            ok=False,
            error=ErrorEnvelope(
                code="VENDOR_NOT_FOUND",
                message=f"No vendor matched the provided lookup key",
                retryable=False,
            ),
        )

    if len(matches) > 1:
        warnings.warn(f"Ambiguous vendor match ({len(matches)} results); returning first")

    return LookupVendorOutput(ok=True, data=Vendor.model_validate(matches[0]))
