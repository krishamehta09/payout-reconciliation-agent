"""Reconcile payouts vs. deals. Rules detect discrepancies; an LLM (Gemini or Claude) triages and explains them."""
import argparse, csv, json, os
from collections import defaultdict
from pathlib import Path

RATES = {"Standard": 0.08, "Growth": 0.10, "Enterprise": 0.12}
TOL = 0.01

def read(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))

def detect(deals, payouts):
    by_deal = defaultdict(list)
    for p in payouts:
        by_deal[p["deal_id"]].append(p)
    known = {d["deal_id"] for d in deals}
    out = []
    for d in deals:
        amt, rate = float(d["deal_amount"]), RATES[d["tier"]]
        expected = round(amt * rate, 2)
        rows = by_deal.get(d["deal_id"], [])
        base = {"deal_id": d["deal_id"], "rep": d["rep"], "expected_rate": rate, "expected_amount": expected}
        if not rows:
            out.append({**base, "error_type": "missing_credit", "paid_amount": 0.0,
                        "variance": -expected, "detail": "No payout found for closed deal"})
            continue
        if len(rows) > 1:
            out.append({**base, "error_type": "duplicate", "paid_amount": sum(float(r["amount_paid"]) for r in rows),
                        "variance": round(sum(float(r["amount_paid"]) for r in rows) - expected, 2),
                        "detail": f"{len(rows)} payouts: {', '.join(r['payout_id'] for r in rows)}"})
        r = rows[0]
        paid, applied = float(r["amount_paid"]), float(r["rate_applied"])
        if abs(applied - rate) > 1e-9:
            out.append({**base, "error_type": "wrong_rate", "paid_amount": paid,
                        "variance": round(paid - expected, 2),
                        "detail": f"Rate applied {applied:.0%}, expected {rate:.0%} ({d['tier']})"})
        elif len(rows) == 1 and abs(paid - expected) > TOL:
            out.append({**base, "error_type": "amount_mismatch", "paid_amount": paid,
                        "variance": round(paid - expected, 2),
                        "detail": f"Paid {paid:,.2f}, expected {expected:,.2f} at correct rate"})
    for p in payouts:
        if p["deal_id"] not in known:
            out.append({"deal_id": p["deal_id"], "rep": p["rep"], "expected_rate": "", "expected_amount": 0.0,
                        "error_type": "orphan_payout", "paid_amount": float(p["amount_paid"]),
                        "variance": float(p["amount_paid"]), "detail": "Payout references unknown deal"})
    return out

def fallback_triage(exc):
    sev = "high" if abs(exc["variance"]) >= 2000 else "medium" if abs(exc["variance"]) >= 500 else "low"
    return {"severity": sev, "explanation": exc["detail"], "recommended_action": "Review with Finance before next payout run"}

SYSTEM_PROMPT = ("You are a sales-comp operations analyst. For each payout exception, return severity "
                 "(high/medium/low, based on dollar variance and error type), a one-sentence plain-English "
                 "explanation, and one recommended action specific to the error type. Use ONLY the facts given; "
                 "do not invent numbers. Respond with a JSON array only, same order as input, each item having "
                 "keys: index, severity, explanation, recommended_action.")

def build_payload(exceptions):
    keys = ("deal_id", "rep", "error_type", "expected_amount", "paid_amount", "variance", "detail")
    return [{"index": i, **{k: e[k] for k in keys}} for i, e in enumerate(exceptions)]

def parse_items(text, n):
    text = text.strip().strip("`").removeprefix("json").strip()
    items = {item["index"]: item for item in json.loads(text)}
    for it in items.values():
        it["severity"] = str(it.get("severity", "medium")).lower()
    if len(items) != n:
        raise ValueError(f"model returned {len(items)} items, expected {n}")
    return items

def gemini_triage(exceptions):
    """One batched call to the Gemini API via plain HTTPS (no extra packages needed).
    Retries temporary errors (429/500/503) with backoff, then tries fallback models."""
    import time, urllib.request, urllib.error
    primary = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
    models = [primary] + [m for m in ("gemini-3.5-flash", "gemini-3.1-flash-lite") if m != primary]
    body = json.dumps({"systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
                       "contents": [{"role": "user", "parts": [{"text": json.dumps(build_payload(exceptions))}]}],
                       "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2}}).encode()
    last = None
    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        for attempt in range(4):
            req = urllib.request.Request(url, data=body, method="POST",
                                         headers={"Content-Type": "application/json",
                                                  "x-goog-api-key": os.environ["GEMINI_API_KEY"]})
            try:
                with urllib.request.urlopen(req, timeout=120) as r:
                    data = json.load(r)
                print(f"Gemini model used: {model}")
                return parse_items(data["candidates"][0]["content"]["parts"][0]["text"], len(exceptions))
            except urllib.error.HTTPError as e:
                last = f"{model}: HTTP {e.code}: {e.read().decode()[:200]}"
                if e.code in (429, 500, 503):
                    wait = 3 * 2 ** attempt
                    print(f"{model} busy (HTTP {e.code}); retrying in {wait}s...")
                    time.sleep(wait)
                    continue
                break  # 404/400/403: don't retry this model, try the next one
    raise RuntimeError(last)

def claude_triage(exceptions):
    import anthropic
    client = anthropic.Anthropic()
    msg = client.messages.create(model=os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5"),
                                 max_tokens=4000, system=SYSTEM_PROMPT,
                                 messages=[{"role": "user", "content": json.dumps(build_payload(exceptions))}])
    return parse_items(msg.content[0].text, len(exceptions))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--deals", default="data/deals.csv")
    ap.add_argument("--payouts", default="data/payouts.csv")
    ap.add_argument("--manifest", default="data/seeded_errors_manifest.csv")
    ap.add_argument("--out", default="output")
    a = ap.parse_args()
    Path(a.out).mkdir(exist_ok=True)

    exc = detect(read(a.deals), read(a.payouts))
    mode = "rules only"
    triage = {}
    for name, envkey, fn, label in (("gemini", "GEMINI_API_KEY", gemini_triage, "rules + Gemini triage"),
                                    ("claude", "ANTHROPIC_API_KEY", claude_triage, "rules + Claude triage")):
        if os.environ.get(envkey) and exc:
            try:
                triage = fn(exc); mode = label
            except Exception as e:
                print(f"{name} triage failed ({e}); using fallback text.")
            break
    for i, e in enumerate(exc):
        t = triage.get(i) or fallback_triage(e)
        e.update(severity=t["severity"], explanation=t["explanation"], recommended_action=t["recommended_action"])
    order = {"high": 0, "medium": 1, "low": 2}
    exc.sort(key=lambda e: (order.get(e["severity"], 3), -abs(e["variance"])))

    cols = ["deal_id", "rep", "error_type", "severity", "expected_amount", "paid_amount", "variance",
            "explanation", "recommended_action"]
    csv_path = Path(a.out) / "exception_report.csv"
    try:
        f = open(csv_path, "w", newline="")
    except PermissionError:
        csv_path = Path(a.out) / "exception_report_new.csv"
        print(f"exception_report.csv is open in another program (Excel?). Writing to {csv_path.name} instead.")
        f = open(csv_path, "w", newline="")
    with f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore"); w.writeheader(); w.writerows(exc)

    # Validate against ground truth
    truth = {(r["deal_id"], r["error_type"]) for r in read(a.manifest)} if Path(a.manifest).exists() else set()
    found = {(e["deal_id"], e["error_type"]) for e in exc}
    tp = len(truth & found)
    recall = tp / len(truth) if truth else float("nan")
    precision = tp / len(found) if found else float("nan")

    net = sum(e["variance"] for e in exc)
    lines = [f"# Payout Reconciliation Exception Report", "", f"Mode: {mode}  ",
             f"Exceptions flagged: **{len(exc)}**  ", f"Net dollar variance: **${net:,.2f}**  ",
             f"Validation vs. seeded errors: caught {tp}/{len(truth)} (recall {recall:.0%}), precision {precision:.0%}", "",
             "| Deal | Rep | Type | Severity | Variance | Action |", "|---|---|---|---|---:|---|"]
    lines += [f"| {e['deal_id']} | {e['rep']} | {e['error_type']} | {e['severity']} | ${e['variance']:,.2f} | {e['recommended_action']} |" for e in exc]
    (Path(a.out) / "exception_report.md").write_text("\n".join(lines))
    print(f"[{mode}] flagged {len(exc)} | caught {tp}/{len(truth)} seeded errors | precision {precision:.0%} | net variance ${net:,.2f}")

if __name__ == "__main__":
    main()
