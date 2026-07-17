"""Fetch all FRED series (commodity prices, macro layer, FX majors).

FRED is the one hard dependency to get started. Reads FRED_API_KEY from the
environment (never hardcoded). Returns tidy long-format DataFrames per layer
so build_panels can pivot/resample as needed.

Run standalone to sanity-check:  python -m src.fetch_fred
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402

FRED_URL = "https://api.stlouisfed.org/fred/series/observations"


def _get_key() -> str:
    key = os.environ.get("FRED_API_KEY")
    if not key:
        raise RuntimeError(
            "FRED_API_KEY not set. FRED is the one required source. "
            "Add it to .env (see .env.example) or export it, then retry."
        )
    return key


def fetch_series(series_id: str, api_key: str, start: str = "1985-01-01") -> pd.Series:
    """Fetch one FRED series as a date-indexed float Series. '.' -> NaN."""
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "observation_start": start,
    }
    r = requests.get(FRED_URL, params=params, timeout=30)
    r.raise_for_status()
    obs = r.json().get("observations", [])
    if not obs:
        return pd.Series(dtype="float64", name=series_id)
    df = pd.DataFrame(obs)
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")  # '.' -> NaN
    return df.set_index("date")["value"].rename(series_id)


def fetch_group(mapping: dict[str, str], api_key: str, start: str = "1985-01-01") -> pd.DataFrame:
    """Fetch a group of series, renamed to friendly names, as wide DataFrame."""
    cols = {}
    for code, name in mapping.items():
        try:
            cols[name] = fetch_series(code, api_key, start)
            time.sleep(0.2)  # be polite to the API
        except requests.HTTPError as e:
            print(f"  ! {code} ({name}) failed: {e}. Skipping.", file=sys.stderr)
    if not cols:
        return pd.DataFrame()
    # outer-join on date; duplicate friendly names (e.g. usd_broad) collapse fine
    out = pd.concat(cols.values(), axis=1, sort=True)
    out.columns = list(cols.keys())
    return out.loc[:, ~out.columns.duplicated()].sort_index()


def fetch_all(start: str = "1985-01-01") -> dict[str, pd.DataFrame]:
    """Fetch every FRED layer. Returns dict of wide DataFrames keyed by layer."""
    key = _get_key()
    print("Fetching FRED layers...")
    layers = {
        "commodity_prices": config.FRED_COMMODITY_PRICES,
        "macro_fast": config.FRED_MACRO_FAST,
        "macro_slow": config.FRED_MACRO_SLOW,
        "fx": config.FRED_FX,
    }
    result = {}
    for name, mapping in layers.items():
        print(f"  {name} ({len(mapping)} series)...")
        result[name] = fetch_group(mapping, key, start)
    return result


if __name__ == "__main__":
    data = fetch_all()
    for name, df in data.items():
        if df.empty:
            print(f"{name}: EMPTY")
        else:
            print(f"{name}: {df.shape[0]} rows, cols={list(df.columns)}, "
                  f"latest={df.index.max().date()}")
