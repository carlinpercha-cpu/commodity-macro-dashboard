"""Fetch commodity futures from yfinance: OHLCV history + delayed spot quotes.

This is the source for gold and silver (FRED's LBMA fixes were discontinued)
plus palladium/platinum and duplicate coverage of oil/gas/copper for intraday
OHLCV. Free tier: history is daily EOD; "real-time" quotes are ~15 min delayed
and must be labeled as such in any UI.

Run standalone:  python -m src.fetch_prices
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402

try:
    import yfinance as yf
except ImportError:
    raise SystemExit("yfinance not installed. Run: pip install -r requirements.txt")


def fetch_history(start: str = "1985-01-01") -> pd.DataFrame:
    """Daily close for every YF_FUTURES ticker, wide, friendly-named.

    Returns a date-indexed frame with one close column per commodity
    (e.g. gold, silver, wti, ...). Close is what the panels consume; full
    OHLCV is available per-ticker if a later phase needs intraday range.
    """
    tickers = list(config.YF_FUTURES.keys())
    print(f"Fetching yfinance history for {len(tickers)} futures...")
    raw = yf.download(
        tickers,
        start=start,
        auto_adjust=False,
        progress=False,
        group_by="ticker",
    )
    cols = {}
    for tk, name in config.YF_FUTURES.items():
        try:
            s = raw[tk]["Close"].dropna()
            if len(s):
                cols[name] = s
            else:
                print(f"  ! {tk} ({name}) returned no data. Skipping.", file=sys.stderr)
        except KeyError:
            print(f"  ! {tk} ({name}) not in response. Skipping.", file=sys.stderr)
    out = pd.concat(cols.values(), axis=1, sort=True)
    out.columns = list(cols.keys())
    return out.sort_index()


def fetch_quotes() -> pd.DataFrame:
    """Latest available (delayed ~15 min) price per ticker. For the monitor."""
    rows = []
    for tk, name in config.YF_FUTURES.items():
        try:
            fi = yf.Ticker(tk).fast_info
            rows.append({"commodity": name, "ticker": tk,
                         "price": fi.get("lastPrice"), "delayed": True})
        except Exception as e:  # fast_info can be flaky; degrade per-ticker
            print(f"  ! quote {tk} failed: {e}", file=sys.stderr)
    return pd.DataFrame(rows)


if __name__ == "__main__":
    hist = fetch_history()
    print(f"history: {hist.shape[0]} rows, cols={list(hist.columns)}, "
          f"latest={hist.index.max().date()}")
    print(hist.tail(2).to_string())
