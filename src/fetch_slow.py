"""Slow / monthly sources: World Bank Pink Sheet (full basket) + EIA energy.

These feed the MONTHLY commodities panel only. Pink Sheet is monthly by nature
(no fake daily). EIA series here are monthly spot/price series.

Both sources degrade gracefully:
  - Pink Sheet: auto-downloads the xlsx; if the download fails (host blocked,
    offline), drop CMO-Historical-Data-Monthly.xlsx into data/ manually and
    rerun -- it reads the local copy.
  - EIA: skipped with a log line if EIA_API_KEY is absent.

Run:  python -m src.fetch_slow
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402

PINK_URL = (
    "https://thedocs.worldbank.org/en/doc/"
    "18675f1d1639c7a34d463f59263ba0a2-0050012025/related/"
    "CMO-Historical-Data-Monthly.xlsx"
)
PINK_LOCAL = config.DATA / "CMO-Historical-Data-Monthly.xlsx"

EIA_BASE = "https://api.eia.gov/v2"

# EIA monthly price series (path, facet-id, friendly name).
# All under petroleum/natural-gas spot price routes.
EIA_SERIES = {
    "eia_wti_monthly": ("petroleum/pri/spt/data/", "RWTC", "wti_eia"),
    "eia_brent_monthly": ("petroleum/pri/spt/data/", "RBRTE", "brent_eia"),
    "eia_henryhub_monthly": ("natural-gas/pri/fut/data/", "RNGWHHD", "natgas_eia"),
}


# ---------------------------------------------------------------------------
# World Bank Pink Sheet
# ---------------------------------------------------------------------------
def _download_pink() -> bool:
    """Fetch the xlsx to data/ if not already present. Returns True if available."""
    if PINK_LOCAL.exists():
        return True
    try:
        print("Downloading World Bank Pink Sheet xlsx...")
        r = requests.get(PINK_URL, timeout=60)
        r.raise_for_status()
        PINK_LOCAL.write_bytes(r.content)
        return True
    except Exception as e:
        print(f"  ! Pink Sheet download failed: {e}", file=sys.stderr)
        print(f"  -> Manually download {PINK_URL}", file=sys.stderr)
        print(f"     and place it at {PINK_LOCAL}, then rerun.", file=sys.stderr)
        return False


def load_pink() -> pd.DataFrame:
    """Parse the 'Monthly Prices' sheet into a tidy month-indexed frame.

    The sheet has a two-row header block and a date column formatted like
    '1960M01'. Layout is fragile, so we locate the header row by finding the
    row whose first cell parses as a YYYY'M'MM date, then take everything below.
    """
    if not _download_pink():
        return pd.DataFrame()

    raw = pd.read_excel(PINK_LOCAL, sheet_name="Monthly Prices", header=None)

    # find first data row: first column matches <year>M<month>
    first_col = raw.iloc[:, 0].astype(str)
    mask = first_col.str.match(r"^\d{4}M\d{2}$", na=False)
    if not mask.any():
        print("  ! Could not locate date rows in Pink Sheet. Layout changed?",
              file=sys.stderr)
        return pd.DataFrame()
    first_data = mask.idxmax()

    # header names live two rows above the first data row (name row + unit row);
    # use the name row (first_data - 2) as columns, fall back to generic if odd
    header_row = max(first_data - 2, 0)
    names = raw.iloc[header_row].tolist()
    names[0] = "date"

    df = raw.iloc[first_data:].copy()
    df.columns = names
    df = df.loc[:, [c for c in df.columns if isinstance(c, str)]]  # drop NaN cols
    df["date"] = pd.to_datetime(df["date"].str.replace("M", "-"), format="%Y-%m")
    df = df.set_index("date").apply(pd.to_numeric, errors="coerce")
    df = df.dropna(axis=1, how="all")
    # normalize column names: lowercase, spaces/commas -> underscore
    df.columns = [
        "pink_" + str(c).strip().lower().replace(", ", "_").replace(" ", "_")
        .replace(",", "").replace("(", "").replace(")", "")
        for c in df.columns
    ]
    return df.sort_index()


# ---------------------------------------------------------------------------
# EIA
# ---------------------------------------------------------------------------
def _eia_key() -> str | None:
    return os.environ.get("EIA_API_KEY")


def fetch_eia_series(path: str, series_id: str, name: str, key: str) -> pd.Series:
    url = f"{EIA_BASE}/{path}"
    params = {
        "api_key": key,
        "frequency": "monthly",
        "data[0]": "value",
        "facets[series][]": series_id,
        "sort[0][column]": "period",
        "sort[0][direction]": "asc",
        "length": 5000,
    }
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    rows = r.json().get("response", {}).get("data", [])
    if not rows:
        return pd.Series(dtype="float64", name=name)
    df = pd.DataFrame(rows)
    df["period"] = pd.to_datetime(df["period"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.set_index("period")["value"].rename(name)


def load_eia() -> pd.DataFrame:
    key = _eia_key()
    if not key:
        print("  EIA_API_KEY absent -- skipping EIA (Pink Sheet only).")
        return pd.DataFrame()
    cols = {}
    for _, (path, sid, name) in EIA_SERIES.items():
        try:
            cols[name] = fetch_eia_series(path, sid, name, key)
        except Exception as e:
            print(f"  ! EIA {name} failed: {e}", file=sys.stderr)
    if not cols:
        return pd.DataFrame()
    out = pd.concat(cols.values(), axis=1, sort=True)
    out.columns = list(cols.keys())
    return out.resample("ME").last().sort_index()


def load_all() -> pd.DataFrame:
    pink = load_pink()
    eia = load_eia()
    if pink.empty and eia.empty:
        return pd.DataFrame()
    # align both to month-end
    if not pink.empty:
        pink = pink.resample("ME").last()
    frames = [f for f in (pink, eia) if not f.empty]
    return pd.concat(frames, axis=1, sort=True).sort_index()


if __name__ == "__main__":
    slow = load_all()
    if slow.empty:
        print("No slow data loaded.")
    else:
        print(f"slow monthly: {slow.shape[0]} rows, {slow.shape[1]} cols, "
              f"{slow.index.min().date()} -> {slow.index.max().date()}")
        print("sample cols:", list(slow.columns[:12]))
