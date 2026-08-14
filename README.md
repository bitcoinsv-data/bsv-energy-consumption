# BSV energy consumption, measured

Open data and code behind
[bitcoinsv.it/bsv-energy-consumption](https://bitcoinsv.it/bsv-energy-consumption/).

The major independent energy indices do not cover BSV. Cambridge's Blockchain
Network Sustainability Index covers BTC and Ethereum, the Crypto Carbon Ratings
Institute covers those plus the large proof-of-stake chains, and Digiconomist
covers BTC and Ethereum.

Figures do exist, published from inside the BSV ecosystem, and they disagree with
each other by more than an order of magnitude: the live [Web3 CO2 Energy
Index](https://web3co2.com/) run by SmartLedger, and an MNP study from 2021 whose
original is no longer retrievable. See [`METHOD.md`](METHOD.md) for how this work
compares with both, including where their figure is more conservative than ours.

This repository is another estimate, derived from consensus data rather than
from a hardware assumption, and published with its method and its code so the
number can be checked rather than trusted.

## Headline result

Measured over the most recent 30 days, every block counted:

| | BSV | BTC |
|---|---|---|
| Network hashrate | 196 PH/s | 903 EH/s |
| Annual electricity | 37,917 MWh | 175 TWh |
| Transactions per day | 1,786,119 | 664,026 |
| Data written per day | 894 MB | 233 MB |
| Energy per transaction | 58 Wh | 722 kWh |
| Energy per MB written | 116 kWh | 2,057,109 kWh |

Across **1,271 consecutive days** (183,000 blocks, February 2023 to August 2026)
the energy-per-transaction figure has ranged from **2.2 Wh to 14,610 Wh**, a
spread of 6,764x, with a median of 334 Wh. On **30 of those days it was below
Ethereum's base-layer figure** of roughly 6 Wh.

That spread is the headline finding. A proof-of-work
chain's electricity draw is set by its hashrate, not by how many transactions it
processes, so energy per transaction is not a property of a consensus mechanism.
It is a ratio between a chain's security spend and how busy it happened to be on
the day you measured. Any single figure quoted for it, high or low, is an
accident of timing, including the figures in this repository.

## Files

| File | What it is |
|---|---|
| `METHOD.md` | The full method, its calibration, and its limitations. Read this first. |
| `bsv_energy_daily.py` | **The measurement.** Every block, every day, pulled in bulk. |
| `bsv_energy.py` | Independent cross-check. Walks 1,008 blocks one at a time from a different provider. |
| `make_energy_chart.py` | Generates the published chart from the daily JSON. |
| `bsv_energy_daily.json` | Complete daily series, 1,271 days. |
| `bsv_energy_result.json` | Output of the cross-check run. |

## Reproducing

```bash
python bsv_energy_daily.py         # complete daily series, every block
python bsv_energy.py 1008          # independent 7-day cross-check
python make_energy_chart.py        # regenerate the chart pair
```

Requires `playwright` for the chart only. The measurement scripts use the
standard library and two public APIs. The complete run pulls 1,000 blocks per
request and takes a few minutes.

## Method in one paragraph

Hashrate is derived from the difficulty the network is enforcing
(`H = difficulty x 2^32 / 600`), not taken from a dashboard. Power is hashrate
multiplied by fleet efficiency in joules per terahash, multiplied by a facility
overhead factor of 1.10. Fleet efficiency is the only unobservable parameter, so
it is calibrated: we solve for the efficiency that reproduces Cambridge's
published BTC estimate at BTC's measured hashrate, then apply the same figure to
BSV, which is defensible because both chains are SHA-256 and draw on the same
hardware market. That calibration currently lands at 20.1 J/TH, between an
Antminer S21 and an S19j XP. Throughput is counted from every block in the
window, never sampled and scaled. Full detail, including what this cannot tell
you, is in [`METHOD.md`](METHOD.md).

## Nothing is sampled

Every block on every day is counted. That matters more on BSV than on most
chains: block sizes are extremely skewed, so a day contains many small blocks
and a few very large ones. Any partial sample of blocks either lands on a large
block or misses one, and the resulting figure can be wrong by orders of
magnitude in either direction. Bulk retrieval (1,000 blocks per request) is what
makes counting everything affordable, so there is no reason to sample at all.

## Cross-validation

Two independent providers must agree before anything is published. The daily
series comes from a bulk block feed; a separate walk of individual blocks from a
different provider over the same seven days gave 1,149,070 transactions per day
against the bulk feed's 1,155,393, a difference of 0.5%.

## Licence

Data under [ODC-BY 1.0](https://opendatacommons.org/licenses/by/1-0/).
Code under MIT.

Corrections welcome. Open an issue.
