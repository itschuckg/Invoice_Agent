# Invoice Approval Agent

Reference implementation of an event-driven AP invoice agent. Skeleton — you fill in the tools.

**Stack:** Python 3.11+ · Pydantic · OpenAI SDK (GPT-4o-mini) · pytest

## What's here

- Agent loop (plan → tool → observe) with tool-calling
- Pydantic schemas for every contract the agent touches
- Two-gate decision routing as pure functions
- Mock data fixtures with realistic edge cases (bank changes, sanctions, math errors)
- Eval harness skeleton with golden-set replay
- Unit test scaffolding

## What's NOT here (deliberately)

- Real Azure resources — this runs locally. Port to Foundry as Phase 2.
- Real OCR — `extract_invoice` returns pre-parsed JSON from `src/data/invoices/`
- Real ERP writes — `post_to_erp` logs and returns a fake confirmation
- Real sanctions feed — uses a static list

## Quick start

```bash
# 1. Install
pip install -e ".[dev]"

# 2. Set API key
cp .env.example .env
# edit .env, add OPENAI_API_KEY

# 3. Run the demo (single invoice)
python -m src.agent.demo

# 4. Run the full eval suite
python -m evals.run_evals

# 5. Run tests
pytest
```

## Repo layout

```
src/
  agent/        # loop, system prompt, demo entry point
  tools/        # 7 tools — YOU FILL THESE IN
  gates/        # deterministic decision routing
  data/         # mock vendor master, POs, invoices
evals/          # golden-set replay harness
tests/          # unit tests per layer
```

## Where to start

1. Read `ARCHITECTURE.md` for the design context
2. Read `CLAUDE.md` for tool-design conventions
3. Read `src/agent/schemas.py` — every tool's input/output is typed here
4. Pick a tool stub in `src/tools/` and implement it
5. Run `pytest tests/test_tools.py::test_<your_tool>` to verify
6. When all 7 tools pass, run `python -m src.agent.demo`

## Build order suggestion

| Tool | Difficulty | Why first / last |
|---|---|---|
| `extract_invoice` | Easy | Just reads pre-parsed JSON |
| `lookup_vendor` | Easy | Read + fuzzy match on JSON |
| `lookup_po` | Easy | JSON lookup by PO number |
| `lookup_goods_receipt` | Easy | JSON lookup by PO number |
| `validate_tax` | Medium | Add format validation logic |
| `screen_sanctions` | Medium | Substring + fuzzy match against list |
| `post_to_erp` | Last | Only useful once gates are working |

Implement in that order. Each tool is 20–40 lines.
