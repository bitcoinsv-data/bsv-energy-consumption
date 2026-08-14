#!/usr/bin/env python3
"""
bsv_energy.py - measured energy and energy-per-transaction for BSV, calibrated
against Cambridge's published Bitcoin estimate.

Method (see METHOD.md for the long form):

  1. Network hashrate is derived from consensus difficulty, not from a
     third-party dashboard:  H = difficulty * 2^32 / target_block_time
  2. Power draw is  H * efficiency(J/TH) * PUE.  The efficiency figure is the
     one free parameter, so we CALIBRATE it: we solve for the fleet efficiency
     that reproduces Cambridge's published Bitcoin annual consumption at the
     measured Bitcoin hashrate, then apply that same basket to BSV. Both chains
     are SHA-256 and draw on the same hardware pool, so the transfer is
     defensible. We also report a low/high band from real ASIC spec sheets.
  3. Throughput is measured by walking real block headers, not from an
     aggregator: sum of num_tx and size over N blocks, scaled to a day.
  4. Energy per transaction = annual energy / annual transactions. This figure
     is throughput-normalised consumption. It is NOT "the energy to send one
     transaction" and the write-up must say so.

Outputs bsv_energy_result.json next to this script.
"""

import json
import sys
import time
import urllib.request
from datetime import datetime, timezone

WOC = "https://api.whatsonchain.com/v1/bsv/main"
UA = {"User-Agent": "bitcoinsv.it-open-data/1.0 (+https://bitcoinsv.it/about/)"}

# --- calibration anchors -------------------------------------------------
# Cambridge CBECI published best-guess for Bitcoin, and the date it refers to.
# Update these two together, never one alone.
CBECI_BTC_TWH = 175.0
CBECI_BTC_ASOF = "2025 best-guess (CCAF/CBECI)"

# Spec-sheet efficiency band, J/TH, for the low/high scenarios.
ASIC_BEST = 13.0    # current top-efficiency hydro units
ASIC_OLD = 98.0     # S9-class, still running where power is near-free
PUE = 1.10          # facility overhead (cooling, conversion losses)

BLOCK_TIME = 600    # seconds, both chains
HOURS_PER_YEAR = 8760


def get(url, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except Exception as e:
            if i == tries - 1:
                raise
            time.sleep(1.5 * (i + 1))


def hashrate_from_difficulty(diff, block_time=BLOCK_TIME):
    """Hashes per second implied by consensus difficulty."""
    return diff * (2 ** 32) / block_time


def walk_headers(n_blocks, sleep=0.34):
    """Walk back n_blocks from the tip collecting num_tx / size / time."""
    tip = get(f"{WOC}/chain/info")
    h = tip["bestblockhash"]
    rows = []
    while len(rows) < n_blocks:
        hdr = get(f"{WOC}/block/{h}/header")
        rows.append({
            "height": hdr["height"],
            "time": hdr["time"],
            "num_tx": hdr.get("num_tx") or hdr.get("txcount") or 0,
            "size": hdr["size"],
        })
        h = hdr["previousblockhash"]
        if not h:
            break
        if len(rows) % 50 == 0:
            print(f"  ... {len(rows)}/{n_blocks} headers", file=sys.stderr, flush=True)
        time.sleep(sleep)
    return tip, rows


def main(n_blocks=1008):
    print(f"Walking {n_blocks} BSV block headers (~{n_blocks/144:.1f} days)...",
          file=sys.stderr)
    tip, rows = walk_headers(n_blocks)

    span_s = rows[0]["time"] - rows[-1]["time"]
    span_days = span_s / 86400.0
    total_tx = sum(r["num_tx"] for r in rows)
    total_bytes = sum(r["size"] for r in rows)

    bsv_tx_day = total_tx / span_days
    bsv_mb_day = (total_bytes / 1e6) / span_days
    bsv_hr = hashrate_from_difficulty(tip["difficulty"])

    # Bitcoin comparison, measured the same way where possible.
    btc = get("https://mempool.space/api/v1/mining/hashrate/1w")
    btc_hr = btc["currentHashrate"]
    btc_chart = get("https://api.blockchain.info/charts/n-transactions"
                    "?timespan=30days&format=json")
    btc_tx_day = sum(p["y"] for p in btc_chart["values"]) / len(btc_chart["values"])
    btc_size = get("https://api.blockchain.info/charts/avg-block-size"
                   "?timespan=30days&format=json")
    btc_mb_day = (sum(p["y"] for p in btc_size["values"])
                  / len(btc_size["values"])) * 144.0

    # Calibrate fleet efficiency against Cambridge's Bitcoin figure.
    # TWh/yr = H(TH/s) * eff(J/TH) * PUE * 8760h / 1e12  (W->TW)
    btc_th = btc_hr / 1e12
    eff_cal = (CBECI_BTC_TWH * 1e12) / (btc_th * PUE * HOURS_PER_YEAR)

    def twh(hashrate_hs, eff):
        return (hashrate_hs / 1e12) * eff * PUE * HOURS_PER_YEAR / 1e12

    scenarios = {
        "calibrated": eff_cal,
        "efficient_fleet": ASIC_BEST,
        "legacy_fleet": ASIC_OLD,
    }

    out = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "method": "difficulty-derived hashrate x calibrated fleet efficiency x PUE",
        "calibration": {
            "anchor_twh_btc": CBECI_BTC_TWH,
            "anchor_source": CBECI_BTC_ASOF,
            "implied_fleet_efficiency_j_per_th": round(eff_cal, 2),
            "pue": PUE,
        },
        "bsv": {
            "height": tip["blocks"],
            "difficulty": tip["difficulty"],
            "hashrate_ph_s": round(bsv_hr / 1e15, 2),
            "sample_blocks": len(rows),
            "sample_days": round(span_days, 2),
            "tx_per_day": round(bsv_tx_day),
            "mb_per_day": round(bsv_mb_day, 1),
            "avg_tx_per_block": round(total_tx / len(rows), 1),
            "avg_block_mb": round((total_bytes / len(rows)) / 1e6, 3),
        },
        "btc": {
            "hashrate_eh_s": round(btc_hr / 1e18, 1),
            "tx_per_day": round(btc_tx_day),
            "mb_per_day": round(btc_mb_day, 1),
        },
        "results": {},
    }

    for name, eff in scenarios.items():
        b_twh = twh(bsv_hr, eff)
        t_twh = twh(btc_hr, eff)
        out["results"][name] = {
            "efficiency_j_per_th": round(eff, 2),
            "bsv_twh_yr": round(b_twh, 6),
            "bsv_mwh_yr": round(b_twh * 1e6, 1),
            "bsv_wh_per_tx": round(b_twh * 1e12 / (bsv_tx_day * 365), 2),
            "btc_twh_yr": round(t_twh, 2),
            "btc_kwh_per_tx": round(t_twh * 1e9 / (btc_tx_day * 365), 1),
            # energy per megabyte of data actually written to the ledger
            "bsv_kwh_per_mb": round(b_twh * 1e9 / (bsv_mb_day * 365), 1),
            "btc_kwh_per_mb": round(t_twh * 1e9 / (btc_mb_day * 365), 1),
        }

    path = "C:/Users/rodfr/scraper/bsv_energy_result.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2))
    print(f"\nwrote {path}", file=sys.stderr)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 1008)
