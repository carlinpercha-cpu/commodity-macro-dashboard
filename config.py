"""Central configuration: series definitions, the explore/holdout split, and paths.

Everything downstream imports the split and series lists from here so the
boundary between explore and holdout is defined exactly once.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Explore / holdout split  --  LOCKED. Do not tune against the holdout.
# ---------------------------------------------------------------------------
EXPLORE_END = "2021-12-31"      # explore/train: everything up to and including
HOLDOUT_START = "2022-01-01"    # holdout: 2022 rate-hike + energy shock onward
                                # (a genuine stress regime, not a quiet period)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"            # gitignored; regenerate via build_panels
DATA.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# FRED series  --  code: friendly_name
#   Grouped so build_panels knows which layer/frequency each belongs to.
# ---------------------------------------------------------------------------

# Commodity prices available on FRED (daily/most-days).
FRED_COMMODITY_PRICES = {
    # gold: yfinance GC=F in fetch_prices (FRED LBMA fix discontinued)
    # silver: yfinance SI=F in fetch_prices
    "DCOILWTICO": "wti_usd",              # WTI crude
    "DCOILBRENTEU": "brent_usd",          # Brent crude
    "DHHNGSP": "natgas_usd",              # Henry Hub natural gas spot
    "PCOPPUSDM": "copper_usd",            # global copper price (monthly)
}

# Macro layer -- fast (native daily).
FRED_MACRO_FAST = {
    "DTWEXBGS": "usd_broad",              # trade-weighted broad USD index
    "DGS10": "ust10y_nominal",            # 10Y nominal treasury
    "DFII10": "ust10y_real",              # 10Y TIPS (real yield)
    "VIXCLS": "vix",                      # CBOE VIX
    "DFF": "fed_funds",                   # effective fed funds
}

# Macro layer -- slow (native monthly). Forward-filled into the daily panel
# ONLY with an explicit flag; never treated as daily-updating by a model.
FRED_MACRO_SLOW = {
    "CPIAUCSL": "cpi",                    # CPI, all urban
    "PCEPI": "pce",                       # PCE price index
    "M2SL": "m2",                         # M2 money stock
    "INDPRO": "industrial_production",    # industrial production
    "UNRATE": "unemployment",             # unemployment rate
}

# FX majors on FRED (USD per unit / or index). Separate track from commodities.
FRED_FX = {
    "DEXUSEU": "usd_eur",                 # USD per EUR
    "DEXJPUS": "jpy_usd",                 # JPY per USD
    "DEXUSUK": "usd_gbp",                 # USD per GBP
    "DEXCHUS": "cny_usd",                 # CNY per USD
    "DEXSZUS": "chf_usd",                 # CHF per USD (safe haven)
    "DTWEXBGS": "usd_broad",              # broad USD index (shared w/ macro)
}

# ---------------------------------------------------------------------------
# yfinance futures  --  for OHLCV history + delayed real-time quotes.
#   Used for series FRED lacks or where intraday OHLCV is wanted.
# ---------------------------------------------------------------------------
YF_FUTURES = {
    "GC=F": "gold",
    "SI=F": "silver",
    "CL=F": "wti",
    "BZ=F": "brent",
    "NG=F": "natgas",
    "HG=F": "copper",
    "PA=F": "palladium",   # conflict-sensitive (Russia supply)
    "PL=F": "platinum",
}

# ---------------------------------------------------------------------------
# Resample targets emitted by build_panels.
# ---------------------------------------------------------------------------
FREQUENCIES = ("daily", "monthly")
