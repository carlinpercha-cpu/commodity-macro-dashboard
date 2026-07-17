"""Prediction layer: next-month direction (primary) + vol-regime flag (secondary).

Design commitments (honest by construction):
  - Target is next-month return DIRECTION, not the return itself. Monthly
    commodity returns are noise-dominated; regression predicts the mean.
  - Every model is compared against a naive baseline (persistence + majority
    class). "Barely beats baseline" is a valid, reportable result.
  - Features are built ONLY from information available at prediction time
    (lagged). No same-month macro leaks into the same-month target.
  - Train on explore (<= EXPLORE_END), evaluate ONCE on the untouched holdout.

Nothing here touches the holdout except the final evaluate() call.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402

CORE = ["gold", "silver", "wti", "brent", "natgas", "copper", "palladium", "platinum"]
MACRO_FAST = ["usd_broad", "ust10y_nominal", "ust10y_real", "vix", "fed_funds"]


def build_features(monthly: pd.DataFrame) -> pd.DataFrame:
    """Construct lagged, leak-free features from the monthly panel.

    All features are known AT the start of the month we're predicting into:
    they use data through month t to predict the return over month t+1.
    """
    df = pd.DataFrame(index=monthly.index)

    # price returns (this month's realized return -- a feature for next month)
    for c in CORE:
        r = np.log(monthly[c].where(monthly[c] > 0)).diff()
        df[f"{c}_ret"] = r
        df[f"{c}_ret_3m"] = r.rolling(3).mean()      # momentum
        df[f"{c}_vol_6m"] = r.rolling(6).std()       # own volatility

    # macro CHANGES this month (known at month-end, used for next month)
    for m in MACRO_FAST:
        df[f"{m}_chg"] = monthly[m].diff()
    df["usd_broad_level"] = monthly["usd_broad"]      # level matters for FX-priced

    # cross-sectional market vol state (the regime signal from notebook 02)
    core_ret = np.log(monthly[CORE].where(monthly[CORE] > 0)).diff()
    df["mkt_vol_12m"] = core_ret.rolling(12).std().mean(axis=1)

    return df


def build_targets(monthly: pd.DataFrame) -> pd.DataFrame:
    """Next-month direction per asset (+ next-month elevated-vol flag).

    CRITICAL: target is shifted -1 so row t holds the OUTCOME of month t+1.
    Features at row t are all known by end of month t. No leakage.
    """
    tgt = pd.DataFrame(index=monthly.index)
    for c in CORE:
        r = np.log(monthly[c].where(monthly[c] > 0)).diff()
        nxt = r.shift(-1)
        # nullable Int64: last row (no future month) stays <NA>, not a crash
        tgt[f"{c}_up"] = (nxt > 0).where(nxt.notna()).astype("Int64")

    core_ret = np.log(monthly[CORE].where(monthly[CORE] > 0)).diff()
    mkt_vol = core_ret.rolling(12).std().mean(axis=1)
    hi = mkt_vol > mkt_vol.loc[:config.EXPLORE_END].quantile(0.70)  # explore-derived cutoff
    nxt_hi = hi.shift(-1)
    tgt["vol_elevated"] = nxt_hi.where(mkt_vol.shift(-1).notna()).astype("Int64")
    return tgt


def split(df: pd.DataFrame):
    """Explore / holdout split on the locked date."""
    ex = df.loc[:config.EXPLORE_END]
    ho = df.loc[config.HOLDOUT_START:]
    return ex, ho


# ---- baselines -------------------------------------------------------------
def baseline_persistence(feat_col: pd.Series, y_true: pd.Series) -> float:
    """Predict next-month direction = this-month direction. Accuracy."""
    pred = (feat_col > 0).astype(int)
    ok = y_true.notna() & pred.notna()
    return (pred[ok] == y_true[ok]).mean()


def baseline_majority(y_train: pd.Series, y_test: pd.Series) -> float:
    """Predict the majority class from train, always. Accuracy on test."""
    maj = int(y_train.mean() >= 0.5)
    return (y_test == maj).mean()


if __name__ == "__main__":
    monthly = pd.read_parquet(config.DATA / "commodities_monthly.parquet")
    X = build_features(monthly)
    Y = build_targets(monthly)
    Xe, Xh = split(X)
    Ye, Yh = split(Y)
    print(f"features: {X.shape[1]} cols")
    print(f"explore: {Xe.shape[0]} months, holdout: {Xh.shape[0]} months")
    print(f"targets: {[c for c in Y.columns]}")
