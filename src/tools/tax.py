"""
validate_tax tool.

In production this calls CRA (Canada Business Number registry) or VIES (EU VAT).
In the skeleton, we do format validation only, plus a small allowlist of
"known-valid" tax IDs in src/data/tax_registry.json.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from src.agent.schemas import (
    ErrorEnvelope,
    ValidateTaxInput,
    ValidateTaxOutput,
)

TAX_ID_PATTERNS: dict[str, str] = {
    "CA": r"^\d{9}([A-Z]{2}\d{4})?$",
    "US": r"^\d{2}-\d{7}$",
    "GB": r"^GB\d{9}$",
    "DE": r"^DE\d{9}$",
}

_REGISTRY_FILE = Path(__file__).parent.parent / "data" / "tax_registry.json"


def validate_tax(inp: ValidateTaxInput) -> ValidateTaxOutput:
    if inp.country not in TAX_ID_PATTERNS:
        return ValidateTaxOutput(ok=True, valid=False)

    if not re.match(TAX_ID_PATTERNS[inp.country], inp.tax_id):
        return ValidateTaxOutput(ok=True, valid=False)

    registry: dict[str, str] = json.loads(_REGISTRY_FILE.read_text())
    registered_name = registry.get(inp.tax_id)
    if registered_name is None:
        return ValidateTaxOutput(ok=True, valid=False)

    return ValidateTaxOutput(ok=True, valid=True, registered_name=registered_name)
