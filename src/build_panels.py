"""Join FRED + yfinance into the two tracks, emit four parquet files.

Outputs (gitignored, in data/):
    commodities_daily.parquet    commodities_monthly.parquet
    fx_daily.parquet             fx_monthly.parquet

Design rules enforced here:
  - Commodities and FX are SEPARATE panels sharing the macro layer.
  - GPR is NOT joined -- it stays quarantined until it earns entry.
  - Slow macro (CPI/PCE/M2/IP) is native monthly. In the DAILY panel it is
    forward-filled, and every forward-filled column is suffixed `_ff` so no
    downstream model can mistake it for a daily-updating series.

Run:  python -m src.build_panels
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config          # noqa: E402
from src import fetch_fred, fetch_prices, fetch_slow  # noqa: E402


def _resample_monthly(df: pd.DataFrame) -> pd.DataFrame:
    """Month-end last observation. For prices/fast macro this is month-end
    close; slow macro is already ~monthly so last() is a no-op alignment."""
    return df.resample("ME").last()


def build() -> dict[str, pd.DataFrame]:
    fred = fetch_fred.fetch_all()
    yf_hist = fetch_prices.fetch_history()

    prices = fred["commodity_prices"]
    fast = fred["macro_fast"]
    slow = fred["macro_slow"]
    fx = fred["fx"]

    # --- daily commodities: FRED prices + yfinance (gold/silver/etc) + fast macro
    #     slow macro forward-filled with _ff suffix -------------------------------
    slow_ff = slow.reindex(
        pd.date_range(slow.index.min(), pd.Timestamp.today(), freq="D")
    ).ffill()
    slow_ff.columns = [f"{c}_ff" for c in slow_ff.columns]

    comm_daily = pd.concat([prices, yf_hist, fast], axis=1, sort=True)
    comm_daily = comm_daily[~comm_daily.index.duplicated()].sort_index()
    comm_daily = comm_daily.join(slow_ff, how="left")

    # --- monthly commodities: month-end everything + native slow macro ----------
    comm_monthly = _resample_monthly(
        pd.concat([prices, yf_hist, fast], axis=1, sort=True)
    ).join(_resample_monthly(slow), how="left")

    # --- fx daily / monthly (separate track, same macro treatment) --------------
    fx_daily = pd.concat([fx, fast], axis=1, sort=True)
    fx_daily = fx_daily[~fx_daily.index.duplicated()].sort_index().join(slow_ff, how="left")
    fx_monthly = _resample_monthly(
        pd.concat([fx, fast], axis=1, sort=True)
    ).join(_resample_monthly(slow), how="left")

    # --- slow monthly sources (Pink Sheet full basket + EIA) -------------------
    #     MONTHLY panels only -- this data is genuinely monthly, never daily.
    slow = fetch_slow.load_all()
    if not slow.empty:
        slow.columns = [c.replace("_**", "").replace("**", "") for c in slow.columns]
        slow = slow.loc[:, ~slow.columns.duplicated()]
        comm_monthly = comm_monthly.join(slow, how="left")
        # fx monthly gets only the broad commodity context cols it may want;
        # keep fx panel lean -- join just the crude/natgas index refs
        ctx = [c for c in slow.columns if "index" in c or "crude_oil_average" in c]
        if ctx:
            fx_monthly_out = fx_monthly.join(slow[ctx], how="left")
        else:
            fx_monthly_out = fx_monthly
    else:
        fx_monthly_out = fx_monthly

    return {
        "commodities_daily": comm_daily,
        "commodities_monthly": comm_monthly,
        "fx_daily": fx_daily,
        "fx_monthly": fx_monthly_out,
    }


if __name__ == "__main__":
    panels = build()
    for name, df in panels.items():
        path = config.DATA / f"{name}.parquet"
        df = df.loc[:, ~df.columns.duplicated()]
        df.to_parquet(path)
        span = f"{df.index.min().date()} -> {df.index.max().date()}"
        print(f"{name}: {df.shape[0]}x{df.shape[1]}  {span}  -> {path.name}")
    print(f"\nExplore/holdout split: explore <= {config.EXPLORE_END}, "
          f"holdout >= {config.HOLDOUT_START}")
