"""
screen_sanctions tool.

Mock implementation — checks supplier name against a small static list in
src/data/sanctions_list.json. Real implementation would call OFAC SDN,
EU consolidated list, or a commercial provider.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.agent.schemas import (
    ErrorEnvelope,
    ScreenSanctionsInput,
    ScreenSanctionsOutput,
)

_SANCTIONS_FILE = Path(__file__).parent.parent / "data" / "sanctions_list.json"


def screen_sanctions(inp: ScreenSanctionsInput) -> ScreenSanctionsOutput:
    entries: list[dict] = json.loads(_SANCTIONS_FILE.read_text())
    name_lower = inp.name.lower()

    for entry in entries:
        entry_name_lower = entry["name"].lower()
        # Conservative: match if either is a substring of the other
        if entry_name_lower in name_lower or name_lower in entry_name_lower:
            if inp.country is None or entry.get("country") is None or entry["country"] == inp.country:
                return ScreenSanctionsOutput(ok=True, is_hit=True, matched_against=entry["name"])

    return ScreenSanctionsOutput(ok=True, is_hit=False)
