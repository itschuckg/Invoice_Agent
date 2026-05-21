# Claude Code Handoff — Invoice Agent Build

Paste the contents of this file as your first message in Claude Code, OR save it as `HANDOFF.md` in the repo root and reference it.

-----

## Context

I’m building an invoice approval agent — an event-driven AI agent that processes supplier invoices, performs a three-way match (invoice ↔ PO ↔ goods receipt), screens for fraud signals, and produces a structured decision routed by policy gates.

This repo is a **skeleton**. The architecture, schemas, agent loop, policy gates, mock data, and test scaffolding are all in place. The 7 tool implementations are stubs that raise `NotImplementedError`.

**My goal:** Implement the 7 tools, get the eval suite passing on all 6 golden invoices, then iterate on the system prompt to maximize accuracy.

## Before you start — read these in order

1. `ARCHITECTURE.md` — the design context (mermaid diagram, NIST AI RMF mapping, governance decisions)
1. `CLAUDE.md` — coding conventions, tool-design rules, what “good output” looks like in this repo
1. `src/agent/schemas.py` — every data contract; the most important file
1. `src/agent/system_prompt.md` — the agent’s operating discipline
1. `src/gates/policy.py` and `src/gates/routing.py` — the deterministic policy layer (fully implemented)
1. `tests/test_tools.py` — the TDD targets

Do not modify the schemas, gates, or system prompt without asking me first. The intent of this build is to fill in tools against fixed contracts.

## Environment setup (do this first)

```bash
cp .env.example .env
# I'll add my OPENAI_API_KEY manually
pip install -e ".[dev]"
pytest tests/test_gates.py  # should be 14 green
pytest tests/test_tools.py  # should be 14 red (NotImplementedError)
```

If gate tests don’t pass, stop and tell me — something is broken in the scaffold.

## The work — 7 tools, in this order

Implement in the order below. Each tool is 20–40 lines. After each, run its tests and only proceed when green.

### 1. `src/tools/extract.py` (easiest, start here)

- Reads pre-parsed JSON from `src/data/invoices/{invoice_id}.json`
- Returns `ExtractInvoiceOutput`
- Handle missing file with structured error envelope
- Run: `pytest tests/test_tools.py -k extract -v`

### 2. `src/tools/vendor.py`

- Reads `src/data/vendor_master.json`
- Tax ID match is exact; name match is case-insensitive substring as a starting point
- Must enforce at least one lookup key provided
- Return `bank_account_on_file` — the agent uses this to detect bank-change fraud
- Run: `pytest tests/test_tools.py -k vendor -v`

### 3. `src/tools/po.py` (two functions in one file)

- Both read `src/data/pos.json`
- `lookup_po`: return PO regardless of status (don’t filter cancelled)
- `lookup_goods_receipt`: missing GR is `ok=False` with `GR_NOT_FOUND` (informational, not a system error)
- Run: `pytest tests/test_tools.py -k "po or goods" -v`

### 4. `src/tools/tax.py`

- Format validation against `TAX_ID_PATTERNS` regex map
- Registry lookup against `src/data/tax_registry.json`
- Distinguish `ok` (tool worked) from `valid` (tax ID is good) — read the TODO carefully
- Run: `pytest tests/test_tools.py -k tax -v`

### 5. `src/tools/sanctions.py`

- Case-insensitive substring match against `src/data/sanctions_list.json`
- Be conservative: false positives are fine (go to human review); false negatives are not
- Run: `pytest tests/test_tools.py -k sanctions -v`

### 6. `src/tools/erp.py` (last — agent doesn’t call this, gates output drives it)

- Generate deterministic `erp_document_id` from idempotency_key (sha256 prefix)
- Log the posting with `rich.print`
- Return `ok=True` with the fake ID
- No test required in `test_tools.py`; will be exercised by an integration test later

## After all 14 tool tests pass

Run the agent end-to-end on each invoice:

```bash
python -m src.agent.demo INV-001  # expect ERP_AUTO_POST
python -m src.agent.demo INV-002  # expect FRAUD_REVIEW (bank changed)
python -m src.agent.demo INV-003  # expect APPROVER_INBOX (math mismatch)
python -m src.agent.demo INV-004  # expect APPROVER_INBOX (over threshold)
python -m src.agent.demo INV-005  # expect APPROVER_INBOX (no PO)
python -m src.agent.demo INV-006  # expect FRAUD_REVIEW (sanctions hit)
```

If any case routes incorrectly, the fix is in one of three places (in order of likelihood):

1. The system prompt (`src/agent/system_prompt.md`) — agent reasoning issue
1. A tool returning wrong structure — debug with verbose logging
1. Schema/gate issue — ask me before changing these

## Then run the eval suite

```bash
python -m evals.run_evals
```

Target: **6/6 exact match, 0 critical false-approves, p95 latency < 30s**.

If accuracy is below 100%, iterate on the system prompt. Common improvements:

- Tighten the confidence calibration guidance
- Add explicit guidance on when to emit `bank_details_changed` flag
- Add an example of the desired AgentDecision JSON in the prompt

## Working agreement with Claude Code

- **One tool at a time.** Implement, test, commit, move on. Do not implement multiple tools in one turn.
- **Run the test before claiming done.** Show me the pytest output.
- **No scope creep.** Don’t add new tools, new schemas, new fields without asking. The scaffold is intentional.
- **Use Pydantic, not raw dicts.** Every value crossing a boundary is a typed model.
- **Honest confidence.** If you’re unsure about a business rule (tolerance interpretation, what counts as “new supplier”), ask me — don’t invent.
- **Commit messages**: `feat(tools): implement <tool>` or `fix(tools/<tool>): <thing>`. One tool per commit.

## What “done” looks like

- [ ] All 28 tests passing (`pytest`)
- [ ] All 6 demo invoices route correctly
- [ ] Eval suite at 6/6 with 0 false-approves
- [ ] Each tool implementation is ≤ 50 lines including imports
- [ ] One commit per tool
- [ ] README updated with actual run output / screenshot

## Stretch goals (only after the above is green)

1. **Add INV-007 through INV-010** covering: duplicate invoice number, currency mismatch, ambiguous vendor match, expired PO
1. **Cost telemetry**: log token counts per run; add to eval report
1. **Swap the model**: parameterize `OPENAI_MODEL` and run evals on `gpt-4o` vs `gpt-4o-mini` — produce a comparison table
1. **MCP server export**: wrap the tools as an MCP server so they’re reusable across Claude Code, Copilot, and the production runtime
1. **Bicep for Azure deployment** as Phase 2

Start with stretch goal 1 — more golden cases is the highest-leverage improvement.

## When you get stuck

Tell me:

1. What you tried
1. What error or unexpected behavior you saw
1. Which file you think is the issue
1. What you’d change if you had to guess

Then ask. I’d rather pause and re-plan than churn.

-----

**First action when you start:** Run the environment setup, paste the output of `pytest tests/test_gates.py` and `pytest tests/test_tools.py` so I can confirm we’re starting from green-gates / red-tools, then implement `extract.py`.