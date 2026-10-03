"""Generate synthetic deals + commission payouts with seeded errors and a ground-truth manifest."""
import csv, random
from pathlib import Path

random.seed(42)
OUT = Path("data"); OUT.mkdir(exist_ok=True)
RATES = {"Standard": 0.08, "Growth": 0.10, "Enterprise": 0.12}
REPS = ["Avery Chen", "Jordan Patel", "Sam Rivera", "Taylor Brooks", "Morgan Lee", "Riley Nguyen",
        "Casey Diaz", "Jamie Foster", "Drew Kim", "Parker Singh", "Quinn Murphy", "Blake Torres"]
N_DEALS = 200

deals = []
for i in range(N_DEALS):
    tier = random.choices(list(RATES), weights=[5, 3, 2])[0]
    deals.append({
        "deal_id": f"D-{1001 + i}",
        "rep": random.choice(REPS),
        "close_date": f"2026-{random.randint(7, 9):02d}-{random.randint(1, 28):02d}",
        "tier": tier,
        "deal_amount": random.randrange(5000, 80000, 250),
    })

payouts = []
for n, d in enumerate(deals):
    rate = RATES[d["tier"]]
    payouts.append({
        "payout_id": f"P-{5001 + n}", "deal_id": d["deal_id"], "rep": d["rep"],
        "rate_applied": rate, "amount_paid": round(d["deal_amount"] * rate, 2),
    })

# Seed errors on distinct deals
idx = random.sample(range(N_DEALS), 15)
plan = ["wrong_rate"] * 4 + ["missing_credit"] * 4 + ["duplicate"] * 4 + ["amount_mismatch"] * 3
manifest, drop, extra = [], set(), []
for i, kind in zip(idx, plan):
    d, p = deals[i], payouts[i]
    if kind == "wrong_rate":
        wrong = random.choice([r for r in RATES.values() if r != p["rate_applied"]])
        p["rate_applied"] = wrong
        p["amount_paid"] = round(d["deal_amount"] * wrong, 2)
    elif kind == "missing_credit":
        drop.add(i)
    elif kind == "duplicate":
        extra.append({**p, "payout_id": f"P-{9000 + len(extra)}"})
    elif kind == "amount_mismatch":
        p["amount_paid"] = round(p["amount_paid"] + random.choice([-1, 1]) * random.randint(150, 900), 2)
    manifest.append({"deal_id": d["deal_id"], "error_type": kind})

payouts = [p for j, p in enumerate(payouts) if j not in drop] + extra
random.shuffle(payouts)

def write(name, rows):
    with open(OUT / name, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

write("deals.csv", deals)
write("payouts.csv", payouts)
write("seeded_errors_manifest.csv", manifest)
print(f"{len(deals)} deals, {len(payouts)} payout rows, {len(manifest)} seeded errors")
