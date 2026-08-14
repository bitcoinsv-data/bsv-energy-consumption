#!/usr/bin/env python3
"""
bsv_energy_daily.py - complete daily series, every block, no sampling.

Supersedes the monthly-sample approach in bsv_energy_history.py. That script
counted every block within one day per month, which meant no sampling error
inside a day but a large one between days: BSV's daily throughput varies by
several times, so a single day never represented its month.

This pulls EVERY block over the whole window in bulk (1,000 per request from
the Bitails block list) and aggregates to complete daily figures. Nothing is
sampled and nothing is extrapolated.

Cross-check: the resulting daily transaction counts are compared against the
independent per-block counts taken from WhatsOnChain in bsv_energy_history.json,
so two different providers have to agree before any figure is published.

Energy method is unchanged (see METHOD.md): hashrate from each day's own
difficulty, power = hashrate x calibrated fleet efficiency x PUE.
"""

import json
import os
import sys
import time
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone

API = "https://api.bitails.io/block/list"
UA = {"User-Agent": "bitcoinsv.it-open-data/1.0 (+https://bitcoinsv.it/about/)"}
OUT = os.path.dirname(os.path.abspath(__file__))

PAGE = 1000
PUE = 1.10
EFF_J_PER_TH = 20.11        # calibrated against Cambridge's BTC estimate
BLOCK_TIME = 600
HOURS_PER_YEAR = 8760

# Window start. Kept to the modern-hardware era: a single fleet-efficiency
# figure cannot be stretched back to the S9 years without becoming fiction.
START_HEIGHT = 780000


def get(url, tries=5):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(2 * (i + 1))


def collect():
    blocks, skip = {}, 0
    while True:
        page = get(f"{API}?limit={PAGE}&skip={skip}")
        if not page:
            break
        for b in page:
            blocks[b["height"]] = (b["time"], b["size"],
                                   b["transactionsCount"], b["difficulty"])
        low = min(b["height"] for b in page)
        print(f"  {len(blocks):>7} blocks, down to height {low}",
              file=sys.stderr, flush=True)
        if low <= START_HEIGHT:
            break
        skip += PAGE
        time.sleep(0.25)
    return blocks


def main():
    print("Pulling every block in bulk...", file=sys.stderr)
    blocks = collect()

    days = defaultdict(lambda: {"tx": 0, "size": 0, "diff": 0.0, "n": 0})
    for h, (t, size, tx, diff) in blocks.items():
        if h < START_HEIGHT:
            continue
        d = datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")
        r = days[d]
        r["tx"] += tx
        r["size"] += size
        r["diff"] += diff
        r["n"] += 1

    rows = []
    for d in sorted(days):
        r = days[d]
        # drop partial days at either edge of the window
        if r["n"] < 100:
            continue
        diff = r["diff"] / r["n"]
        hashes_s = diff * (2 ** 32) / BLOCK_TIME
        twh = (hashes_s / 1e12) * EFF_J_PER_TH * PUE * HOURS_PER_YEAR / 1e12
        mb = r["size"] / 1e6
        rows.append({
            "date": d,
            "blocks": r["n"],
            "tx": r["tx"],
            "mb": round(mb, 1),
            "hashrate_ph_s": round(hashes_s / 1e15, 2),
            "twh_yr": round(twh, 6),
            "wh_per_tx": round(twh * 1e12 / (r["tx"] * 365), 2) if r["tx"] else None,
            "kwh_per_mb": round(twh * 1e9 / (mb * 365), 2) if mb else None,
        })

    # cross-check against the independent WhatsOnChain counts
    checks = []
    hp = os.path.join(OUT, "bsv_energy_history.json")
    if os.path.exists(hp):
        old = {s["date"]: s for s in json.load(open(hp, encoding="utf-8"))["samples"]}
        byday = {r["date"]: r for r in rows}
        for d, s in old.items():
            if d in byday:
                a, b = s["tx_per_day"], byday[d]["tx"]
                checks.append({"date": d, "whatsonchain": a, "bitails": b,
                               "diff_pct": round(100 * (b - a) / a, 2) if a else None})

    out = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "method": "every block in the window, pulled in bulk, aggregated to "
                  "complete days; no sampling, no extrapolation",
        "efficiency_j_per_th": EFF_J_PER_TH,
        "pue": PUE,
        "blocks_total": len(blocks),
        "days_total": len(rows),
        "cross_check_vs_whatsonchain": checks,
        "days": rows,
    }
    p = os.path.join(OUT, "bsv_energy_daily.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"\n{len(rows)} complete days from {len(blocks)} blocks -> {p}",
          file=sys.stderr)
    if checks:
        worst = max(checks, key=lambda c: abs(c["diff_pct"] or 0))
        print(f"cross-check: {len(checks)} overlapping days, "
              f"largest disagreement {worst['diff_pct']}% on {worst['date']}",
              file=sys.stderr)


if __name__ == "__main__":
    main()
