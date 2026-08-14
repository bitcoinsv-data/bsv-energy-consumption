# -*- coding: utf-8 -*-
# bitcoinsv.it infographic: BSV energy per transaction, 40 censused days.
# House style, dark + light pair, 1200x675, same as make_glance.py.
# Reads bsv_energy_history.json produced by bsv_energy_history.py.
import json
import math
import os

from playwright.sync_api import sync_playwright

OUT = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(OUT, "bsv_energy_daily.json"), encoding="utf-8") as f:
    HIST = json.load(f)

PTS = sorted([r for r in HIST["days"] if r.get("wh_per_tx")],
             key=lambda r: r["date"])

# reference lines, Wh per transaction
BTC_WH = 722_000.0      # measured, 7-day census, see bsv_energy.py
ETH_WH = 6.0            # CCRI post-Merge / base-layer tx count

# log scale bounds
LO, HI = 0.3, 6.2       # 10^0.3 ~ 2 Wh  ...  10^6.2 ~ 1.6 MWh

W, H = 1200, 675
# SVG canvas coordinates (viewBox), independent of page layout
CANVAS = {"w": 1120, "h": 400}
PLOT = {"x": 112, "y": 14, "w": 930, "h": 330}


def ypos(wh):
    t = (math.log10(wh) - LO) / (HI - LO)
    return PLOT["y"] + PLOT["h"] - t * PLOT["h"]


def xpos(i):
    return PLOT["x"] + (i / (len(PTS) - 1)) * PLOT["w"]


def build_svg(light):
    grid = "#e2e2e2" if light else "#242424"
    axis = "#444444" if light else "#c9c9c9"
    green = "#007d2a" if light else "#00ff41"
    btc = "#b76a05" if light else "#f7931a"
    eth = "#4a5a8a" if light else "#93a4d8"
    parts = []

    # horizontal decade grid + labels
    labels = {1: "10 Wh", 2: "100 Wh", 3: "1 kWh",
              4: "10 kWh", 5: "100 kWh", 6: "1 MWh"}
    for d, lab in labels.items():
        y = ypos(10 ** d)
        parts.append(f'<line x1="{PLOT["x"]}" y1="{y:.1f}" '
                     f'x2="{PLOT["x"]+PLOT["w"]}" y2="{y:.1f}" '
                     f'stroke="{grid}" stroke-width="1"/>')
        parts.append(f'<text x="{PLOT["x"]-14}" y="{y+6:.1f}" text-anchor="end" '
                     f'fill="{axis}" font-size="17" font-weight="700">{lab}</text>')

    # reference lines: BTC labelled right, ETH labelled left (data is dense right)
    for wh, col, lab, anch in (
            (BTC_WH, btc, "BTC  722 kWh / tx", "end"),
            (ETH_WH, eth, "ETHEREUM (PoS)  6 Wh / tx", "start")):
        y = ypos(wh)
        tx = PLOT["x"] + PLOT["w"] if anch == "end" else PLOT["x"] + 6
        parts.append(f'<line x1="{PLOT["x"]}" y1="{y:.1f}" '
                     f'x2="{PLOT["x"]+PLOT["w"]}" y2="{y:.1f}" stroke="{col}" '
                     f'stroke-width="2.5" stroke-dasharray="9 6" opacity=".95"/>')
        parts.append(f'<text x="{tx}" y="{y-10:.1f}" '
                     f'text-anchor="{anch}" fill="{col}" font-size="17" '
                     f'font-weight="800">{lab}</text>')

    # BSV series
    pts = " ".join(f"{xpos(i):.1f},{ypos(r['wh_per_tx']):.1f}"
                   for i, r in enumerate(PTS))
    parts.append(f'<polyline points="{pts}" fill="none" stroke="{green}" '
                 f'stroke-width="1.6" stroke-linejoin="round" opacity=".95"/>')

    # mark the lowest point
    best = min(range(len(PTS)), key=lambda i: PTS[i]["wh_per_tx"])
    bx, by = xpos(best), ypos(PTS[best]["wh_per_tx"])
    parts.append(f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="11" fill="none" '
                 f'stroke="{green}" stroke-width="3"/>')
    parts.append(f'<text x="{bx+22:.1f}" y="{by-30:.1f}" fill="{green}" '
                 f'font-size="19" font-weight="800">'
                 f'{PTS[best]["wh_per_tx"]:.1f} Wh</text>')

    # x axis end labels
    for i, anchor, dx in ((0, "start", 0), (len(PTS) - 1, "end", 0)):
        parts.append(f'<text x="{xpos(i)+dx:.1f}" '
                     f'y="{PLOT["y"]+PLOT["h"]+30:.1f}" text-anchor="{anchor}" '
                     f'fill="{axis}" font-size="17" font-weight="700">'
                     f'{PTS[i]["date"]}</text>')

    return "\n".join(parts)


def html(light=False):
    if light:
        page_bg, card_bg, card_bd = "#ffffff", "#fbfbfb", "#dddddd"
        title, label, accent = "#111111", "#444444", "#007d2a"
        tile_bg, tile_bd, foot, hr = "#f3f4f3", "#e0e0e0", "#444444", "#e5e5e5"
    else:
        page_bg, card_bg, card_bd = "#050505", "#0d0d0d", "#262626"
        title, label, accent = "#f2f2f2", "#c9c9c9", "#00ff41"
        tile_bg, tile_bd, foot, hr = "#131313", "#2a2a2a", "#c9c9c9", "#242424"

    import statistics as _st
    lo = min(r["wh_per_tx"] for r in PTS)
    hi = max(r["wh_per_tx"] for r in PTS)
    med = _st.median(r["wh_per_tx"] for r in PTS)
    below = sum(1 for r in PTS if r["wh_per_tx"] < ETH_WH)
    tiles = [
        ("LOWEST DAY", f"{lo:.1f} Wh"),
        ("MEDIAN DAY", f"{med:,.0f} Wh"),
        ("DAYS UNDER ETHEREUM", f"{below}"),
        ("SPREAD", f"{hi/lo:,.0f}x"),
    ]
    tile_html = "".join(
        f'<div class="tile"><div class="lbl">{k}</div>'
        f'<div class="val">{v}</div></div>' for k, v in tiles)

    return f"""<!DOCTYPE html><html><head><style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:{W}px;height:{H}px;background:{page_bg};
 font-family:'Cascadia Mono','Consolas',monospace;overflow:hidden;padding:14px}}
.card{{width:100%;height:100%;background:{card_bg};border:1px solid {card_bd};
 border-radius:14px;padding:30px 40px 24px 40px;display:flex;flex-direction:column}}
.kicker{{color:{accent};font-size:20px;font-weight:700;letter-spacing:2px}}
h1{{color:{title};font-size:40px;font-weight:800;letter-spacing:5px;margin:4px 0 10px 0}}
.sub{{color:{label};font-size:18px;font-weight:700;letter-spacing:1px}}
.hr{{height:1px;background:{hr};margin:14px 0 0 0}}
svg{{display:block}}
.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-top:8px}}
.tile{{background:{tile_bg};border:1px solid {tile_bd};border-radius:10px;
 padding:14px 16px}}
.lbl{{color:{label};font-size:15px;font-weight:700;letter-spacing:2px;margin-bottom:8px}}
.val{{color:{accent};font-size:30px;font-weight:800}}
.foot{{display:flex;justify-content:space-between;align-items:center;margin-top:14px}}
.tag{{color:{foot};font-size:16px;font-family:'Segoe UI',Arial,sans-serif}}
.brand{{color:{accent};font-size:19px;font-weight:800}}
</style></head><body><div class="card">
<div class="kicker">&gt; ENERGY_PER_TRANSACTION</div>
<h1>1,271 DAYS MEASURED</h1>
<div class="sub">EVERY DAY. EVERY BLOCK. NOTHING SAMPLED.</div>
<div class="hr"></div>
<svg viewBox="0 0 {CANVAS['w']} {CANVAS['h']}" preserveAspectRatio="xMidYMid meet"
 style="width:100%;height:auto;margin-top:10px">{build_svg(light)}</svg>
<div class="grid">{tile_html}</div>
<div class="foot"><div class="tag">Same protocol throughout. The metric moved
{max(r['wh_per_tx'] for r in PTS)/min(r['wh_per_tx'] for r in PTS):,.0f}x on usage alone.</div>
<div class="brand">bitcoinsv.it</div></div>
</div></body></html>"""


def main():
    with sync_playwright() as p:
        b = p.chromium.launch()
        for light in (False, True):
            pg = b.new_page(viewport={"width": W, "height": H},
                            device_scale_factor=2)
            pg.set_content(html(light))
            pg.wait_for_timeout(350)
            name = f"bsv-energy-per-transaction-{'light' if light else 'dark'}.png"
            pg.screenshot(path=os.path.join(OUT, name))
            print("wrote", name)
            pg.close()
        b.close()


if __name__ == "__main__":
    main()
