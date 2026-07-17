# Commodities, Currencies & Macro: An Exploratory Research Study

An exploratory time-series investigation into **what macroeconomic factors actually drive commodity returns** — and, just as importantly, **which candidate factors turn out to add nothing** once the obvious ones are already in the model.

Like the [stock–bond correlation study](https://github.com/carlinpercha-cpu/stock-bond-correlation), this repo is less about a single headline answer than about the **process**: a locked explore/holdout split fixed before any analysis, deliberate pruning of a wide feature set down to what shows real structure, and an honest "does this factor earn its place" gate that returns a clean negative result.

**This is a learning/research project, not investment advice and not novel academic research.** The eventual goal is a BI dashboard for a trader to use as market context — explicitly *not* a trading signal generator, since commodities and FX are adversarially efficient in ways that make short-horizon price prediction close to noise.

---

## Data

All sources are free. Only a FRED key is strictly required; EIA is optional.

| Layer | Source | Frequency | Notes |
|---|---|---|---|
| Commodity prices | yfinance futures, FRED | daily | gold, silver, WTI, Brent, natgas, copper, palladium, platinum |
| Broad basket | World Bank Pink Sheet | monthly | 74 series; base metals, ags, oils, fertilizers, timber |
| Energy detail | EIA v2 API | monthly | crude/natgas spot (optional) |
| FX | FRED, ECB reference | daily | majors + trade-weighted USD + CHF/JPY safe havens |
| Macro (fast) | FRED | daily | broad USD, 10Y nominal & real, VIX, fed funds |
| Macro (slow) | FRED | monthly | CPI, PCE, M2, industrial production, unemployment |
| Geopolitical (quarantined) | Caldara–Iacoviello GPR | monthly | benchmark + threats/acts + country indices |

Data spans **1985–2026**. Two tracks — commodities and FX — are kept **separate** with a shared macro layer, since their generating processes differ. Everything is emitted as four gitignored parquet panels (`commodities_{daily,monthly}`, `fx_{daily,monthly}`), regenerable via `python -m src.build_panels`.

---

## Method & discipline

- **Explore/holdout locked up front.** Explore ≤ 2021-12-31; holdout ≥ 2022-01-01 held out untouched (deliberately capturing the 2022 rate-hike + energy-shock regime as a genuine stress test). Defined once in `config.py`, imported everywhere.
- **Returns, not levels.** All correlational work uses monthly log-returns (prices) and first-differences (rate/level macro series), since price levels are non-stationary and their correlations are spurious co-trending.
- **Prune before modeling.** The 74-series Pink Sheet basket was scored on incremental structure and cut to the ~22 series showing real co-movement, discarding idiosyncratic noise.
- **Gate new factors honestly.** Geopolitical risk was quarantined and admitted to the panels only if it beat VIX + real yields on incremental explanatory power. It did not (see below).

---

## Findings

### 1. The dollar dominates everything

Every commodity shows a strong negative monthly-return correlation with the broad trade-weighted dollar — from **−0.42 to −0.60** across the core complex. This is the single most consistent relationship in the data. Commodities are USD-priced, so a stronger dollar mechanically lowers prices. For any dashboard, the dollar is the top macro feature, full stop.

### 2. Yields split commodities by type — same variable, opposite sign

| Commodity | vs 10Y nominal yield change |
|---|---|
| Gold | −0.27 |
| Silver | −0.02 |
| Copper | +0.29 |
| WTI | +0.27 |
| Brent | +0.37 |

Precious metals correlate **negatively** with yields (they are monetary assets — higher yields raise the opportunity cost of holding non-yielding metal), while energy and industrial metals correlate **positively** (they are growth assets — higher yields signal a hot economy that demands them). The same macro variable carries opposite signs depending on the commodity's economic role. This echoes the central lesson of the stock–bond study: a relationship's sign can depend entirely on how, and on what, it is measured.

Gold vs the **real** 10Y yield is **−0.49** — the strongest single gold relationship, and correctly signed, since the real yield is the true opportunity cost of holding gold.

### 3. The gold–real-yield link is state-dependent, but gradually

A 1-year rolling correlation of gold returns against real-yield changes stays negative throughout 2004–2021 but breathes between roughly **−0.05 and −0.52**, with the tightest coupling clustering around crises (2008–09, 2018, 2020). Splitting by a volatility regime (high-vol = top 30% of average 12-month core volatility) gives:

| Regime | gold vs real-yield-change corr |
|---|---|
| Calm | −0.46 |
| High-vol | −0.52 |
| Full sample | −0.49 |

The relationship strengthens in stress, in the expected direction — but the monthly gap is **modest**, smaller than the dramatic swings the daily rolling correlation suggests. The honest reading: gold's sensitivity to real yields is **robustly negative in all regimes** and somewhat stronger in stress. This argues for treating regime as a *continuous conditioning variable* rather than a hard two-state switch.

### 4. Base metals are a distinct factor worth carrying

Pruning the Pink Sheet basket surfaced the full London Metal Exchange industrial complex — **zinc, aluminum, lead, tin, nickel** — plus ags/oils (soybean, palm, rapeseed, sugar, cotton), coal, iron ore, and rubber. These are genuine additions to the precious/energy core, giving the dashboard an industrial-demand signal distinct from the monetary (precious) and energy factors. The final working basket is **~30 series**: 8 core + ~22 new.

### 5. Geopolitical risk adds nothing over VIX + real yields (the negative result)

The centerpiece. Geopolitical risk (GPR) is widely assumed to drive gold and oil. But the market prices *anticipation* continuously through VIX and real yields, so the real question is whether GPR adds anything **incremental** once those are already in the model. A regression gate (baseline: VIX + real-yield changes; augmented: + GPR change) says no:

| Test | Baseline adj-R² | + GPR adj-R² | Δ | GPR p-value |
|---|---|---|---|---|
| Gold | 0.288 | 0.288 | +0.000 | 0.302 |
| Gold (threats + acts split) | 0.288 | 0.284 | −0.004 | 0.32 / 0.71 |
| Oil | 0.184 | 0.190 | +0.006 | 0.134 |
| Gold, calm regime only | 0.243 | 0.242 | −0.001 | 0.353 |

Across every case — including oil (the channel where conflict *should* bite hardest) and the calm regime (GPR's best shot at explaining gold when the yield link is weak) — GPR is **statistically insignificant and adds essentially zero explanatory power**. The gate was validated on synthetic data to confirm it *detects* a real effect when present and *rejects* noise, so this is a genuine null, not a broken test.

**Conclusion:** at monthly frequency, the Caldara–Iacoviello GPR index provides no incremental explanatory power for commodity returns over VIX and real yields — including in low-volatility regimes and for oil specifically. VIX, being forward-looking and continuously priced, already absorbs the geopolitical signal that newspaper-based GPR captures later and more noisily. **GPR stays out of the model.**

*Caveats / future work:* this tested the monthly aggregate index. Daily frequency (against the newer LLM-based AI-GPR daily index) or country-specific indices in targeted event studies (e.g. Saudi/Russia GPR around specific supply shocks) could still carry signal and remain open questions.

---

## Repo layout

```
config.py              series lists, explore/holdout split, paths
src/fetch_fred.py      prices + macro + FX majors (FRED)
src/fetch_prices.py    yfinance futures OHLCV + delayed quotes
src/fetch_slow.py      World Bank Pink Sheet + EIA (monthly)
src/fetch_gpr.py       QUARANTINED — GPR loader, used only by the gate
src/build_panels.py    joins sources -> 4 parquet panels
notebooks/
  01_explore_commodities.ipynb   correlations, rolling stability
  02_regime_detection.ipynb      basket pruning + volatility regimes
  03_gpr_gate.ipynb              the incremental-value gate
```

## Reproduce

```bash
pip install -r requirements.txt
cp .env.example .env          # add FRED_API_KEY (EIA_API_KEY optional)
python -m src.build_panels    # emits data/*.parquet
jupyter notebook notebooks/   # run 01 -> 02 -> 03
```

Data is gitignored (regenerable, and raw price data doesn't belong in a public repo). Reproducing requires a free [FRED API key](https://fred.stlouisfed.org/docs/api/api_key.html).

---

*Not investment advice. An exploratory learning project on publicly available data.*
