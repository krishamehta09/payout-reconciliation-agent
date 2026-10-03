# Payout Reconciliation Agent

Reconciles a sales commission payout file against source deal data and flags discrepancies, then uses Claude to triage each exception (severity, plain-English explanation, recommended action).

**Error types detected:** wrong commission rate, missing credit (no payout for a closed deal), duplicate payout, amount mismatch, orphan payout.

## How it works
1. `generate_data.py` creates 200 synthetic deals, matching payouts, and seeds 15 known errors (4 wrong-rate, 4 missing-credit, 4 duplicate, 3 amount-mismatch) plus a ground-truth manifest.
2. `reconcile.py` recomputes each expected commission from the deal tier rate and compares it to what was paid. Deterministic rules do the detection so the numbers are auditable.
3. If `ANTHROPIC_API_KEY` is set, Claude receives the flagged exceptions in one batched call and returns severity, explanation, and next action. Without a key it falls back to template text.
4. Output: `output/exception_report.csv` and `output/exception_report.md`, plus a validation score against the seeded errors.

## Run it
```bash
pip install -r requirements.txt
python generate_data.py
export ANTHROPIC_API_KEY=...   # optional
python reconcile.py
```
Result on the included data: 15/15 seeded errors caught, 100% precision.

## n8n
Import `n8n/reconciliation_workflow.json`, update the file paths, and run. It triggers the reconciliation and loads the report for downstream steps (email, Slack, etc.).

## Design choices
- Rules detect, the LLM explains and prioritizes. For payments, detection should be reproducible; the LLM adds value in triage and communication.
- Claude only sees the flagged rows and is told not to invent numbers.

## Limitations
Synthetic data, single flat rate per tier, no quota accelerators, splits, or clawbacks. Real comp plans would need those rules added.
