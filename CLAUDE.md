# CLAUDE.md — Conventions for AI-Assisted Development

This file is read by Claude Code (and useful for GitHub Copilot too) when working in this repo. It encodes the conventions a human reviewer expects.

## Project context

Invoice Approval Agent — event-driven AP automation. Skeleton repo where tool implementations are filled in by a developer learning agent architecture. See `ARCHITECTURE.md` for the full design.

## Code conventions

- **Python 3.11+**, type hints everywhere, no `Any` without justification
- **Pydantic v2** for all data contracts — never raw dicts crossing tool boundaries
- **Pure functions** for gates and validators; no I/O, no globals
- **Structured error envelopes** from tools — never raise to the agent loop unless truly unrecoverable
- **Black + Ruff** formatting; line length 100
- **pytest** with descriptive test names — `test_<unit>_<scenario>_<expected_outcome>`

## Tool design rules (the highest-leverage convention)

Every tool follows the same contract shape:

```python
from pydantic import BaseModel

class ToolInput(BaseModel):
    # typed fields, no Optional unless truly optional
    ...

class ToolOutput(BaseModel):
    ok: bool
    data: SomeTypedPayload | None = None
    error: ErrorEnvelope | None = None
```

Rules:

1. **Single responsibility.** One tool, one job. `lookup_vendor` does not also screen sanctions.
2. **Idempotent.** Calling twice with the same input returns the same output. Especially `post_to_erp` — use an idempotency key.
3. **Structured errors.** Never raise to the agent. Return `ok=False` with a typed `ErrorEnvelope` containing `code`, `message`, `retryable`.
4. **No side effects in read tools.** Lookups never write.
5. **Authorization scoping.** Each tool declares the minimum scope it needs (in the docstring for this skeleton; in IAM/managed identity for Azure).

## Agent loop rules

- The loop owns: tool dispatch, context window management, max iterations, observation logging.
- The loop does NOT own: business decisions (gates do), persistence (orchestrator does), retries (orchestrator does).
- Max iterations: 10. If the agent hasn't decided in 10 tool calls, escalate to human.

## Gate rules

Gates are **pure functions**, no LLM, no I/O.

- Gate 1 (quality): confidence ≥ 0.9 AND within tolerance
- Gate 2 (risk): bank change OR amount > threshold OR new supplier OR sanctions hit
- Configuration lives in `src/gates/policy.py` — never in the prompt

## Schema discipline

When adding a new tool or modifying an existing one:

1. Add/modify the Pydantic schema in `src/agent/schemas.py` FIRST
2. Update the tool implementation
3. Update the tool registration in `src/agent/tools_registry.py`
4. Add a unit test
5. Add an entry to the golden set if it exercises new behavior

## When generating code

- Prefer small, focused functions over clever one-liners
- Write the test alongside the implementation
- If you find yourself writing `# TODO`, write a failing test instead
- If you're unsure about a business rule, ask — don't invent it

## What good output looks like for THIS repo

For a tool implementation request, I want:
1. The Pydantic input/output schemas (if not already present)
2. The function with full type hints
3. Structured error handling with the envelope shape
4. A pytest test covering happy path, edge case, error case
5. A one-line entry in the tool registry

Not boilerplate explanations, not philosophical preambles. Code that runs.
