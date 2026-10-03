# Payout Reconciliation Agent

Reconciles a sales commission payout file against source deal data and flags discrepancies, then uses an LLM (Google Gemini free tier, or Claude) to triage each exception (severity, plain-English explanation, recommended action).

**Error types detected:** wrong commission rate, missing credit (no payout for a closed deal), duplicate payout, amount mismatch, orphan payout.

## How it works
1. `generate_data.py` creates 200 synthetic deals, matching payouts, and seeds 15 known errors (4 wrong-rate, 4 missing-credit, 4 duplicate, 3 amount-mismatch) plus a ground-truth manifest.
2. `reconcile.py` recomputes each expected commission from the deal tier rate and compares it to what was paid. Deterministic rules do the detection so the numbers are auditable.
3. If `GEMINI_API_KEY` (or `ANTHROPIC_API_KEY`) is set, the LLM receives the flagged exceptions in one batched call and returns severity, explanation, and next action. Gemini is called over plain HTTPS, so no extra packages are needed. Without a key it falls back to template text.
4. Output: `output/exception_report.csv` and `output/exception_report.md`, plus a validation score against the seeded errors.

## Run it
```bash
# pip install anthropic   # only needed if you use Claude instead of Gemini
python generate_data.py
export GEMINI_API_KEY=...      # optional (free key from Google AI Studio); or ANTHROPIC_API_KEY
# Windows cmd: set GEMINI_API_KEY=...   |   PowerShell: $env:GEMINI_API_KEY="..."
# optional: GEMINI_MODEL=<model name> to override the default (gemini-3.8-flash)
python reconcile.py
```
Result on the included data: 15/15 seeded errors caught, 100% precision.

## n8n workflow
`n8n/reconciliation_workflow.json` triggers `reconcile.py` and loads the generated report, so the pipeline can be run from n8n and extended with downstream steps (email, Slack, etc.). Tested locally on Windows.

To use it: import the file into n8n, then replace the `/path/to/...` placeholders with your project folder (and `python3` with `python` on Windows). Recent n8n versions disable the Execute Command node by default; set `NODES_EXCLUDE=[]` before starting n8n to enable it. Don't put API keys in the workflow; pass them as environment variables.

## Design choices
- Rules detect, the LLM explains and prioritizes. For payments, detection should be reproducible; the LLM adds value in triage and communication.
- The LLM only sees the flagged rows and is told not to invent numbers.

## Limitations
Synthetic data, single flat rate per tier, no quota accelerators, splits, or clawbacks. Real comp plans would need those rules added.
