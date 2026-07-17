"""Fetch the Caldara-Iacoviello Geopolitical Risk (GPR) index.

QUARANTINED source. This module is NOT imported by build_panels. GPR enters the
project only through the gate notebook (03_gpr_gate), and only graduates into
the panels if it demonstrates incremental value over VIX + real yields.

Pulls the classic monthly benchmark (GPR, GPRT threats, GPRA acts). The updated
data file lives on matteoiacoviello.com. If the auto-download fails, download
the monthly file manually and drop it in data/ as gpr_monthly.(csv|xls).

Run:  python -m src.fetch_gpr
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402

# The classic monthly export. URL has moved over time; try the known ones.
GPR_URLS = [
    "https://www.matteoiacoviello.com/gpr_files/data_gpr_export.xls",
    "https://www.matteoiacoviello.com/gpr_files/data_gpr_export.csv",
]
GPR_LOCAL_XLS = config.DATA / "gpr_monthly.xls"
GPR_LOCAL_CSV = config.DATA / "gpr_monthly.csv"


def _download() -> Path | None:
    """Try to fetch the GPR export. Returns local path if available."""
    if GPR_LOCAL_CSV.exists():
        return GPR_LOCAL_CSV
    if GPR_LOCAL_XLS.exists():
        return GPR_LOCAL_XLS
    for url in GPR_URLS:
        try:
            print(f"Downloading GPR from {url} ...")
            r = requests.get(url, timeout=60)
            r.raise_for_status()
            dest = GPR_LOCAL_CSV if url.endswith(".csv") else GPR_LOCAL_XLS
            dest.write_bytes(r.content)
            return dest
        except Exception as e:
            print(f"  ! {url} failed: {e}", file=sys.stderr)
    print("  -> Manually download the monthly GPR file from "
          "matteoiacoviello.com/gpr.htm and place it in data/ as "
          "gpr_monthly.csv or gpr_monthly.xls", file=sys.stderr)
    return None


def load_gpr() -> pd.DataFrame:
    """Return month-indexed GPR benchmark + threats/acts + key country indices."""
    path = _download()
    if path is None:
        return pd.DataFrame()

    raw = pd.read_csv(path) if path.suffix == ".csv" else pd.read_excel(path)

# 'month' may already be datetime, or be YYYYMM int/float depending on file
    dcol = "month" if "month" in raw.columns else raw.columns[0]
    col = raw[dcol]
    if pd.api.types.is_datetime64_any_dtype(col):
        raw["date"] = col
    else:
        dv = col.astype("Int64").astype(str).str.strip()
        raw["date"] = pd.to_datetime(dv, format="%Y%m", errors="coerce")
    n_before = len(raw)
    raw = raw.dropna(subset=["date"]).set_index("date")
    if len(raw) == 0:
        raise ValueError(f"All {n_before} dates failed to parse. "
                         f"Sample: {raw[dcol].head().tolist()}")

    # benchmark 3 + oil/conflict-relevant country indices
    want = {
        "GPR": "gpr", "GPRT": "gpr_threats", "GPRA": "gpr_acts",
        "GPRC_ISR": "gpr_israel", "GPRC_RUS": "gpr_russia",
        "GPRC_SAU": "gpr_saudi", "GPRC_VEN": "gpr_venezuela",
        "GPRC_UKR": "gpr_ukraine",
    }
    have = {c: n for c, n in want.items() if c in raw.columns}
    out = raw[list(have.keys())].apply(pd.to_numeric, errors="coerce")
    out.columns = [have[c] for c in out.columns]
    return out.resample("ME").last().sort_index()