# How bitcoinsv.it measures BSV energy use

This document describes exactly how the figures on `/bsv-energy-consumption/`
are produced, so that anyone can reproduce them, disagree with them, or find an
error in them. The scripts are `bsv_energy_daily.py` (the complete daily series)
and `bsv_energy.py` (an independent cross-check against a second provider). Both
write JSON.

No figure on that page comes from a press release, an aggregator, or an advocacy
source. Every number is derived from consensus data or from a published,
named third-party estimate that is used as an explicit calibration anchor.

---

## 1. Hashrate

Hashrate is not taken from a dashboard. It is derived from the difficulty the
network itself is enforcing:

```
H = difficulty x 2^32 / target_block_time      (target_block_time = 600 s)
```

This is the standard identity between difficulty and expected hashrate. It is a
statistical expectation, not an instantaneous reading: over short windows actual
hashrate varies around it because block discovery is a Poisson process. Over a
day or more the error is small relative to the other uncertainties below.

Difficulty comes from the node data returned by WhatsOnChain's public API, which
reports what is in the block headers.

## 2. Power draw

```
P = H(TH/s) x efficiency(J/TH) x PUE
```

`efficiency` is the joules the mining fleet spends per terahash. It is the only
free parameter in the model and it cannot be observed directly, because nobody
publishes which machines are running on which chain. Everything else follows
from arithmetic.

`PUE` is facility overhead: cooling, power conversion, losses. We use **1.10**.

### How the efficiency parameter is chosen

We do not guess it. We **calibrate** it.

The Cambridge Centre for Alternative Finance publishes a widely used estimate of
BTC's annual electricity consumption. We take that figure, take BTC's
measured hashrate on the same day, and solve for the fleet efficiency that makes
the model reproduce Cambridge's number:

```
efficiency = (CBECI_TWh x 10^12) / (H_btc(TH/s) x PUE x 8760)
```

At the time of writing this yields **~20.1 J/TH**, which is a physically
sensible figure: it sits between an Antminer S21 (~17.5 J/TH) and an S19j XP
(~21.5 J/TH), i.e. a plausible mixed modern fleet. That the calibration lands on
a real machine's spec sheet rather than on an absurd value is the first sanity
check that the model is not broken.

We then apply **the same fleet efficiency to BSV**. This transfer is defensible
because BSV and BTC use the same hash function (SHA-256), draw on the same
hardware market, and are mined by overlapping operators. It is not certain: if
BSV is mined disproportionately on older, less efficient machines, its true
consumption is *higher* than we report. We therefore also publish two bracketing
scenarios using real spec-sheet numbers:

| Scenario | J/TH | Meaning |
|---|---|---|
| Efficient fleet | 13.0 | current top-efficiency hydro units only |
| Calibrated | ~20.1 | reproduces Cambridge's BTC estimate |
| Legacy fleet | 98.0 | S9-class hardware, as still runs where power is near free |

Annual energy is `P x 8760 hours`.

## 3. Throughput

Transaction counts are **complete, not sampled**. Every block in the window is
counted: 183,000 blocks covering 1,271 consecutive days.

This matters more on BSV than on most chains. Block sizes are extremely skewed,
so a day contains many small blocks and a few very large ones. Any partial
sample of blocks either lands on a large block or misses one, and the resulting
throughput figure can be wrong by orders of magnitude in either direction. There
is no safe way to sample BSV block data, so we do not.

Counting everything is affordable because blocks are retrieved in bulk, 1,000
per request, rather than one at a time.

**Two independent providers must agree.** The daily series comes from a bulk
block feed; a separate walk of individual blocks from a different provider over
the same seven days gave 1,149,070 transactions per day against the bulk feed's
1,155,393, a difference of 0.5%.

Nothing is extrapolated from a partial sample of blocks. Ever.

## 4. Energy per transaction

```
Wh/tx = annual_energy(Wh) / (tx_per_day x 365)
```

**This metric must be read carefully.** Energy in a
proof-of-work network is a function of hashrate, which is a function of price
and mining economics. It is *not* a function of how many transactions the
network processes. The marginal energy cost of one additional transaction is
approximately zero.

Consequently energy-per-transaction is not a property of a consensus mechanism.
It is a ratio between a chain's security spend and its current usage, and it
moves when either moves. Our own series demonstrates this directly: across 1,271
consecutive days, with no protocol change of any kind, the same chain ranged from
2.2 Wh to 14,610 Wh per transaction. That is a spread of 6,764x, close to four
orders of magnitude, driven by how busy the network was rather than by anything
about proof of work.

Two consequences follow. The low readings are no more real than the high ones: on 30 days the figure sat
below Ethereum's base-layer number, and on others it sat three orders of
magnitude above it. And a day's transaction count and its hashrate move
independently, so the busiest day is not automatically the most efficient one:
8 August 2023 carried 116.9M transactions at 482 PH/s and came out at 2.19 Wh,
while 1 May 2025 carried fewer, 88.5M, at 359 PH/s and came out lower still at
2.16 Wh.

The metric is published because it is the one most often quoted, with its full
range alongside it so that no single day can be presented as "the" figure.

For the same reason the headline figure on the page covers several days, never
a single day, and it carries its measurement window in the label.

## 5. Energy per megabyte

```
kWh/MB = annual_energy(kWh) / (MB_per_day x 365)
```

Included because BSV is used substantially as a data ledger, so the amount of
data actually written is a more faithful denominator for what the network is
doing than a transaction count is. The same caveat about fixed energy applies.

## 6. Prior work

Two published sources put a number on BSV's energy use. Neither is a neutral
research body: the major independent indices do not cover BSV at all. Cambridge's
Blockchain Network Sustainability Index covers BTC and Ethereum, the Crypto
Carbon Ratings Institute covers those plus the large proof-of-stake chains, and
Digiconomist covers BTC and Ethereum.

**Web3 CO2 Energy Index** (web3co2.com), run by SmartLedger, a BSV-ecosystem
company. It is live, refreshes daily, and states its formula:

```
hashrate / S21 hashrate (200 TH/s) = machine count
machine count x 3.5 kW           = network power
power / transactions per second  = kWh per transaction
x 0.5 kg CO2 per kWh             = carbon per transaction
```

Its current BSV figure is ~0.174 kWh/tx (0.087 kg CO2). Ours is 58 Wh/tx over 30
days. The two agree on the input that can be checked directly: its hashrate,
219.9 PH/s, sits inside our measured range of 196-221 PH/s. The divergence is the
denominator, an instantaneous 6.14 tps (~530k/day) against our full count of
1,786,119/day. Its fleet assumption, 17.5 J/TH, is *more* efficient than our
calibrated 20.1 J/TH, so hardware is not the cause. Its figure is the more
conservative of the two.

**MNP**, a Canadian accounting firm, late 2021. Reported figures:

| | MNP, 2021 | This work, 2026 |
|---|---|---|
| BTC | ~430 kWh/tx (2020) rising to ~706 kWh/tx (2021) | ~722 kWh/tx |
| BSV | ~3.3 kWh/tx (Q3 2020) falling to ~2.4 kWh/tx (Q2 2021) | ~0.058 kWh/tx |

Our BTC figure lands within ~2% of MNP's by a different method, and MNP
cross-checked their model against consumption reported by real Canadian miners
to within 1-1.5%. That is not validation of our BSV number, the years differ, but
reaching the same magnitude by an independent route is evidence the model is not
wildly wrong. BSV's figure has fallen sharply since, which is what the
inverse-throughput relationship predicts.

**Provenance caveat.** We have not obtained MNP's original report. Its site
returns HTTP 403 to automated requests and every outlet reporting it is either
BSV-aligned media or a press release, so those figures are reported, not
verified. If a reader can supply the original PDF we will reconcile against it.

Existing BSV figures disagree with each other by more than an order of
magnitude. That spread, rather than an absence of data, is why this exists: it
publishes its window, its assumptions and its code so the number can be checked
rather than trusted.

## 7. Known limitations

Stated plainly, because a methodology that hides its weaknesses is worthless:

1. **The efficiency parameter is inherited, not measured.** If BSV's fleet is
   older than BTC's, we understate BSV's consumption. The legacy-fleet
   scenario brackets this.
2. **The Cambridge anchor is itself a model**, not a meter reading, with a wide
   published range. Our BSV figure inherits that uncertainty. When Cambridge
   revises, this must be re-run, and the anchor value and its date are both
   recorded in the output JSON.
3. **Difficulty-derived hashrate is an expectation**, so short windows are noisy.
4. **Not all transactions are economically comparable.** Over the measured
   30 days, BananaBlocks' protocol tagging attributes 49,818,610 of 55,650,411
   tagged transactions (89.5%) to a single application, TxBlaster; over 24 hours
   it is 94.8%. BSV's throughput is therefore overwhelmingly machine-generated
   traffic from a few high-volume applications. The transactions are real,
   signed, mined and fee-paying, and the energy figure is unaffected either way
   since hashrate does not respond to transaction count. But if a
   per-transaction figure should count only economically distinct payments, this
   is not that, and neither is any other chain's published figure.

   That tagging is also a third check on throughput: 55,650,411 tagged against
   our block-by-block count of 53,583,570, within 4%.
5. **We do not estimate carbon.** Converting energy to emissions requires the
   regional power mix of the mining fleet, which is not published for BSV. We
   would be inventing it, so we do not report it.

## 8. Reproducing

```bash
python bsv_energy_daily.py         # complete daily series, every block
python bsv_energy.py 1008          # independent 7-day cross-check
python make_energy_chart.py        # regenerate the chart pair
```

Outputs `bsv_energy_daily.json` and `bsv_energy_result.json`, each carrying
its own generation timestamp, the calibration anchor used, and the parameters
applied. Rate limiting is respected; a full historical run takes about 30
minutes.
