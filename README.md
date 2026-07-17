# Commodities, Currencies & Macro: An Exploratory Research Study

An exploratory time-series investigation into **what macroeconomic factors drive commodity returns** — which factors add nothing once the obvious ones are in, and, most importantly, **which relationships are stable versus regime-dependent**.

Like the [stock–bond correlation study](https://github.com/carlinpercha-cpu/stock-bond-correlation), this repo is about **process**: a locked explore/holdout split fixed before any analysis, deliberate pruning of a wide feature set, honest factor-gating that returns clean negatives, and — the intellectual spine of the project — a holdout test that *broke* a headline finding and revealed the factor structure to be regime-conditional.

**This is a learning/research project, not investment advice and not novel academic research.** The eventual goal is a BI dashboard for a trader as market context — explicitly *not* a signal generator, since commodities and FX are adversarially efficient in ways that make short-horizon price prediction close to noise. The research confirms this directly (see finding 6).

---

## Data

All sources free; only a FRED key is required.

| Layer | Source | Frequency | Notes |
|---|---|---|---|
| Commodity prices | yfinance futures, FRED | daily | gold, silver, WTI, Brent, natgas, copper, palladium, platinum |
| Broad basket | World Bank Pink Sheet | monthly | 74 series; base metals, ags, oils, fertilizers, timber |
| Energy detail | EIA v2 API | monthly | crude/natgas spot (optional) |
| FX | FRED, ECB reference | daily | majors + trade-weighted USD + CHF/JPY safe havens |
| Macro (fast) | FRED | daily | broad USD, 10Y nominal & real, VIX, fed funds |
| Macro (slow) | FRED | monthly | CPI, PCE, M2, industrial production, unemployment |
| Geopolitical (quarantined) | Caldara–Iacoviello GPR | monthly | benchmark + threats/acts + country indices |

Data spans **1985–2026**, emitted as four gitignored parquet panels (`commodities_{daily,monthly}`, `fx_{daily,monthly}`), regenerable via `python -m src.build_panels`. Commodities and FX are kept as **separate tracks** sharing a macro layer.

---

## Method & discipline

- **Explore/holdout locked up front.** Explore ≤ 2021-12-31; holdout ≥ 2022-01-01 held out untouched — deliberately capturing the 2022 rate-hike + energy-shock regime as a genuine stress test. Defined once in `config.py`.
- **Returns, not levels.** All correlational work uses monthly log-returns / first-differences; price levels are non-stationary and their correlations spurious.
- **Prune before modeling.** The 74-series Pink Sheet basket was scored on incremental structure and cut to ~22 series showing real co-movement.
- **Gate new factors honestly, and test findings out-of-sample.** Both GPR (a candidate factor) and the headline correlations (dollar, yields) were subjected to falsification tests. Two of them failed — and those failures are the most informative results here.

---

## Findings

### 1. The dollar is the dominant commodity factor — *in normal regimes*

On the explore period, every commodity showed a strong negative monthly-return correlation with the broad trade-weighted dollar (**−0.42 to −0.60** across the core complex). Commodities are USD-priced, so a stronger dollar mechanically lowers prices. **But this is regime-conditional — see finding 5, which is the key result.**

### 2. Yields split commodities by type — same variable, opposite sign

On explore, precious metals correlated **negatively** with nominal yield changes (monetary assets — higher yields raise the opportunity cost of holding non-yielding metal), while energy and industrial metals correlated **positively** (growth assets — higher yields signal a hot economy). Gold vs the **real** 10Y yield was −0.49, the strongest single gold relationship, correctly signed. This split, too, proved partly regime-dependent out of sample (finding 5).

### 3. Base metals are a distinct factor worth carrying

Pruning surfaced the full LME industrial complex — zinc, aluminum, lead, tin, nickel — plus ags/oils, coal, iron ore, rubber. Genuine additions to the precious/energy core, giving an industrial-demand signal. Final working basket: ~30 series (8 core + ~22 new).

### 4. Geopolitical risk adds nothing over VIX + real yields (clean negative)

GPR is widely assumed to drive gold and oil, but markets price anticipation continuously through VIX and real yields. A regression gate (baseline VIX + real-yield changes; augmented + GPR) found **no incremental value**:

| Test | Baseline adj-R² | + GPR adj-R² | Δ | GPR p |
|---|---|---|---|---|
| Gold | 0.288 | 0.288 | +0.000 | 0.302 |
| Gold (threats + acts) | 0.288 | 0.284 | −0.004 | 0.32 / 0.71 |
| Oil | 0.184 | 0.190 | +0.006 | 0.134 |
| Gold, calm regime | 0.243 | 0.242 | −0.001 | 0.353 |

Across every case — including oil (strongest channel) and the calm regime (GPR's best shot) — GPR was statistically insignificant. The gate was validated on synthetic data to confirm it detects real effects and rejects noise, so this is a genuine null. **VIX, forward-looking and continuously priced, already absorbs the geopolitical signal that newspaper-based GPR captures later and noisier.** GPR stays out.

### 5. The factor structure is regime-conditional — and the dollar–oil link is undergoing a *recent, ongoing* break (the key finding)

The headline correlations were established on explore only. Re-running on the untouched 2022+ holdout revealed **structural breaks**:

| Asset | USD corr (explore) | USD corr (holdout) | Yield corr (explore) | Yield corr (holdout) |
|---|---|---|---|---|
| Gold | −0.44 | −0.51 | −0.27 | −0.38 |
| Silver | −0.52 | −0.47 | −0.02 | −0.30 |
| **WTI** | **−0.52** | **+0.12** | +0.27 | +0.22 |
| **Brent** | **−0.54** | **+0.15** | +0.37 | +0.24 |
| Copper | −0.56 | −0.53 | **+0.29** | **−0.22** |
| Platinum | −0.60 | −0.43 | +0.11 | −0.23 |

The dollar–commodity inverse relationship held for precious and most industrial metals (5 of 8) but **flipped sign for energy**. Follow-up analysis (notebook 07) then revealed something more interesting than a one-off 2022 event: a **rolling 6-month WTI–USD correlation** shows the relationship was only *modestly* disturbed by the 2022 shock (which largely reverted through 2023), then **drifted decisively positive in 2024–2026** — reaching ≈+0.4 by 2026, as positive as it had been negative for two prior decades. Yearly means: −0.17 (2021) → −0.27 (2023) → −0.07 (2024) → **+0.11 (2025) → +0.36 (2026)**.

So the dollar–oil break is **not the 2022 war shock lingering — it is a newer, still-developing regime change that mostly postdates 2022.** A 2-regime Markov-switching model (switching variance) cleanly separates calm vs high-volatility states (expected durations ~32 vs ~3 months, spiking at 2008/2015/2019/2020/2025-26) but does *not* capture the gradual sign drift — confirming that the sign change is a slow trend, not a discrete volatility event, and that a switching-*slope* model would be the right next tool.

**This is the project's most valuable result.** The dollar–commodity hedge is not a stable law; for energy it has *inverted* in the current regime. Naive full-sample analysis would report a clean −0.5 and miss that the relationship is, right now, positive.

### 6. Price direction is unpredictable; volatility regime is not

A gradient-boosting model (vs persistence + majority-class baselines, evaluated once on the holdout) was built for next-month return direction across all 8 commodities:

- **Direction: dead.** Mean holdout AUC **0.485** (below a coin flip); GBM beat both baselines in just **1 of 8** assets; the persistence baseline beat the model on most. The calibration curve was flat at 0.5 regardless of predicted confidence — probabilities were noise dressed as signal. Monthly commodity price direction is not predictable from macro factors, consistent with efficient-ish markets.
- **Volatility regime: strongly predictable.** A next-month elevated-volatility flag scored holdout **AUC 0.931, accuracy 0.944** (vs 0.704 majority). This is the one genuinely useful predictive output — largely because volatility is highly persistent (see finding 7).

### 7. Volatility regimes are energy-driven, persistent, and characterizable

Decomposing the volatility regime (notebook 05):
- **Energy defines turbulence.** Brent (high-vol/calm vol ratio **1.96**) and WTI (1.50) dominate; gold (1.24) and palladium (1.07) barely move. High-vol regimes are energy-led.
- **Duration.** Once high-vol starts, median spell is **~4 months** (can run to 16). Calm periods are far longer and stickier.
- **Persistence.** Transition matrix: P(stay calm | calm) = **0.96**, P(stay high-vol | high-vol) = **0.85**. Both states grind; they don't flip month-to-month. This is why the vol flag predicts so well.

### 8. Two clean nulls worth stating

- **Gold is not a reliable short-term VIX hedge** (gold–VIX-change corr −0.07). The dominant risk-off haven in the data is the **dollar itself** (USD–VIX +0.50).
- **Diversification does *not* collapse in commodity crises.** Average |correlation| among the 8 commodities was 0.325 (calm) vs 0.331 (high-vol) — essentially unchanged. The equity-market "correlations spike to 1 in stress" effect does **not** appear in this commodity complex at monthly frequency.

---

### 9. Cross-asset regime alignment — a modest shared stress signature

Regenerating the stock–bond correlation independently from FRED (notebook 08) and aligning it to this project's commodity volatility regime shows **directional co-movement**: the stock–bond correlation averages −0.03 in commodity-high-vol months vs −0.18 in calm months (continuous corr with commodity vol +0.16). When commodities get turbulent, the stock–bond diversification benefit weakens at the same time — consistent with a common "macro stress" driver spanning both projects. The effect is **modest, not conclusive** (30 high-vol months, wide variance) and the regenerated series only reaches back to 2017 (FRED equity-history limit), so it misses 2008. A suggestive link worth extending, not a proven unified regime.

## Next research directions

The regime-conditionality finding (5) is the spine, and it opens the most interesting questions. Roughly ordered by promise:

1. **Model the dollar–oil sign drift directly.** Notebook 07 (rolling correlation + Markov-switching) showed the break is a *recent, ongoing drift* toward positive, which a switching-*variance* model does not capture. The natural next step is a **switching-slope / time-varying-parameter regression** (or Bai-Perron structural-break dating) aimed at the *sign* change specifically, plus investigating candidate drivers (oil-trade invoicing shifts, US energy-export dynamics, the fiscal/dollar picture).

2. **Lead-lag, done rigorously.** Notebook 05 found only weak monthly lead-lag (strongest economic signal: Brent → WTI/copper, ~0.2), and the raw "top pair" (natgas→palladium) was flagged as a likely spurious correlation. The honest next step is **higher-frequency lead-lag** (daily panels, which exist) where energy→industrials transmission might be sharper and cleaner, plus a proper **Granger-causality** treatment with lag selection rather than a single-lag correlation.

3. **Regime-conditional GPR — the one place conflict data might survive.** GPR failed the aggregate monthly gate (finding 4), but two untested angles remain: **daily frequency** (the newer LLM-based AI-GPR daily index against daily returns, catching event-window reactions the monthly average washes out) and **country-specific event studies** (Russia/Saudi GPR around specific supply shocks, as case studies rather than a continuous regressor). These are narrow, honest follow-ups, not a re-litigation of the null.

4. **Extend the FX track.** FX was explored descriptively (notebook 06) but not modeled. The dollar-as-haven result (USD–VIX +0.50) is strong; a natural extension is whether **FX carry** or the **dollar smile** (USD strengthening in both risk-off *and* US-outperformance regimes) shows up, and whether FX regimes align with the commodity volatility regimes.

5. **Extend the cross-asset synthesis (finding 9) back through 2008.** The stock–bond alignment used a FRED equity series limited to 2017+. Rebuilding with a longer-history equity index (or merged SP500 levels) would let the commodity-vs-stock-bond stress alignment be tested across 2008 and 2011 — the best crisis test cases — turning the modest suggestive link into something conclusive or clearly rejected.

---

## Repo layout

```
config.py              series lists, explore/holdout split, paths
src/fetch_fred.py      prices + macro + FX majors (FRED)
src/fetch_prices.py    yfinance futures OHLCV + delayed quotes
src/fetch_slow.py      World Bank Pink Sheet + EIA (monthly)
src/fetch_gpr.py       QUARANTINED — GPR loader, used only by the gate
src/build_panels.py    joins sources -> 4 parquet panels
src/predict.py         features, targets, baselines (leak-free by construction)
notebooks/
  01_explore_commodities.ipynb   correlations, rolling stability
  02_regime_detection.ipynb      basket pruning + volatility regimes
  03_gpr_gate.ipynb              the incremental-value gate (null result)
  04_prediction.ipynb            direction (dead) + vol regime (AUC 0.93)
  05_intelligence.ipynb          regime characterization + lead-lag
  06_fx_and_robustness.ipynb     FX, regime correlations, holdout robustness
  07_dollar_oil_break.ipynb      rolling corr + Markov-switching on the USD-oil break
  08_cross_asset_regime.ipynb    commodity vol vs stock-bond correlation regimes
```

## Reproduce

```bash
pip install -r requirements.txt
cp .env.example .env          # add FRED_API_KEY (EIA_API_KEY optional)
python -m src.build_panels    # emits data/*.parquet
jupyter notebook notebooks/   # run 01 -> 06
```

Data is gitignored (regenerable; raw price data doesn't belong in a public repo). Reproducing requires a free [FRED API key](https://fred.stlouisfed.org/docs/api/api_key.html).

---

*Not investment advice. An exploratory learning project on publicly available data.*
