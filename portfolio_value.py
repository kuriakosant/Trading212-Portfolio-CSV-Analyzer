"""
portfolio_value.py — Historical portfolio equity reconstruction engine.

Computes the "true" total portfolio value for every historical day by:
  1. Reconstructing daily share inventory from CSV trades
  2. Fetching daily OHLC prices via yfinance
  3. Valuing each day's inventory at market prices (High/Low/Close)
  4. Adding the running realized cash balance

This powers the "Portfolio Value Chart" tab.
All values are expressed in USD (€0.86 = $1).
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from datetime import timedelta

import streamlit as st

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

EUR_TO_USD = 1.0 / 0.86   # matches the rest of the dashboard

# ---------------------------------------------------------------------------
# Ticker normalization: T212/Revolut suffix → Yahoo Finance symbol
# ---------------------------------------------------------------------------

# Each entry: fragment that appears IN the ticker → YF exchange suffix
_EXCHANGE_SUFFIX: dict[str, str] = {
    "_US_":  "",      # AAPL_US_EQ   → AAPL
    "_UK_":  ".L",    # BP_UK_EQ     → BP.L
    "_DE_":  ".DE",   # SAP_DE_EQ    → SAP.DE
    "_FR_":  ".PA",   # OR_FR_EQ     → OR.PA
    "_NL_":  ".AS",   # ASML_NL_EQ  → ASML.AS
    "_IT_":  ".MI",
    "_ES_":  ".MC",
    "_SE_":  ".ST",
    "_CH_":  ".SW",
    "_PT_":  ".LS",
    "_BE_":  ".BR",
    "_DK_":  ".CO",
    "_FI_":  ".HE",
    "_NO_":  ".OL",
    "_AU_":  ".AX",
    "_CA_":  ".TO",
    "_HK_":  ".HK",
    "_JP_":  ".T",
    "_SG_":  ".SI",
}


def normalize_ticker(raw: str | None) -> str | None:
    """Convert a T212/Revolut ticker (e.g. 'AAPL_US_EQ') to a yfinance symbol ('AAPL')."""
    if not isinstance(raw, str) or not raw.strip() or raw.lower() in ("nan", "none", ""):
        return None
    sym = raw.strip().upper()
    for fragment, suffix in _EXCHANGE_SUFFIX.items():
        if fragment in sym:
            base = sym.split(fragment)[0]
            return base + suffix
    # Fallback: strip trailing _EQ
    if sym.endswith("_EQ"):
        sym = sym[:-3]
    return sym


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_usd(amount, ccy) -> float:
    """Convert a value to USD using the fixed 0.86 rate."""
    try:
        val = float(amount or 0)
    except (TypeError, ValueError):
        val = 0.0
    return val * EUR_TO_USD if str(ccy).strip().upper() == "EUR" else val


# ---------------------------------------------------------------------------
# Step 1: Daily realized cash balance (vectorized)
# ---------------------------------------------------------------------------

def compute_daily_cash_series(df: pd.DataFrame) -> pd.Series:
    """
    Return a date-indexed Series of the running cumulative realized cash position (USD).

    Components:
      + Deposits        (in → positive)
      - Withdrawals     (out → negative)
      - Card debits     (out → negative)
      + Realized P&L    (sell result → positive/negative)
      + Dividends       (passive income → positive)
      + Interest        (passive income → positive)
    """
    if df.empty:
        return pd.Series(dtype=float)

    df = df.copy()
    df["_date"] = df["Time"].dt.date

    def usd_delta(row) -> float:
        cat = row.get("_category", "other")
        ccy_t = row.get("Currency (Total)", "EUR")
        ccy_r = row.get("Currency (Result)", "USD")
        tot   = abs(float(row.get("Total", 0) or 0))
        res   = float(row.get("Result", 0) or 0)
        if cat == "deposit":    return  _to_usd(tot, ccy_t)
        if cat == "withdrawal": return -_to_usd(tot, ccy_t)
        if cat == "card_debit": return -_to_usd(tot, ccy_t)
        if cat == "sell":       return  _to_usd(res, ccy_r)
        if cat == "dividend":   return  _to_usd(tot, ccy_t)
        if cat == "interest":   return  _to_usd(tot, ccy_t)
        return 0.0

    df["_cash_delta"] = df.apply(usd_delta, axis=1)
    daily = df.groupby("_date")["_cash_delta"].sum()

    start = daily.index.min()
    end   = daily.index.max()
    all_dates = pd.date_range(start, end, freq="D").date
    daily = daily.reindex(all_dates, fill_value=0.0)
    return daily.cumsum()


# ---------------------------------------------------------------------------
# Step 2: Daily share inventory per ticker (vectorized)
# ---------------------------------------------------------------------------

def compute_daily_inventory(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return a DataFrame where:
      - Index   = calendar date (every day from first trade to last)
      - Columns = yfinance-normalized tickers
      - Values  = cumulative shares held as of end of that day
    """
    if df.empty:
        return pd.DataFrame()

    trades = df[df["_category"].isin(["buy", "sell"])].copy()
    if trades.empty:
        return pd.DataFrame()

    trades["_date"] = trades["Time"].dt.date
    trades["_yf_ticker"] = trades["Ticker"].apply(normalize_ticker)

    # Drop rows where ticker couldn't be normalized (cash rows etc.)
    trades = trades[trades["_yf_ticker"].notna()]

    trades["_delta"] = trades.apply(
        lambda r: float(r.get("No. of shares", 0) or 0)
                  * (1.0 if r["_category"] == "buy" else -1.0),
        axis=1,
    )

    pivot = (
        trades.groupby(["_date", "_yf_ticker"])["_delta"]
        .sum()
        .unstack(fill_value=0.0)
    )

    # Expand to full calendar and cumulate
    start = pivot.index.min()
    end   = pivot.index.max()
    all_dates = pd.date_range(start, end, freq="D").date
    pivot = pivot.reindex(all_dates, fill_value=0.0)
    inventory = pivot.cumsum().clip(lower=0.0)   # clamp rounding artefacts
    return inventory


# ---------------------------------------------------------------------------
# Step 3: Price fetching via yfinance (cached for 1 hour)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_historical_prices(
    tickers: tuple,       # tuple so it's hashable for caching
    start_str: str,
    end_str:   str,
) -> dict[str, pd.DataFrame]:
    """
    Fetch daily OHLC prices for every ticker in *tickers*.
    Returns {yf_ticker → DataFrame[Open, High, Low, Close]}.
    Tickers that fail (delisted, wrong symbol) are silently dropped.
    Cached for 1 hour to avoid redundant API calls on Streamlit reruns.
    """
    if not YFINANCE_AVAILABLE or not tickers:
        return {}

    results: dict[str, pd.DataFrame] = {}

    # Batch download for speed
    try:
        raw = yf.download(
            list(tickers),
            start=start_str,
            end=end_str,
            progress=False,
            auto_adjust=True,
            group_by="ticker",
        )
    except Exception:
        raw = pd.DataFrame()

    if raw.empty:
        # Fall back to one-by-one
        for tk in tickers:
            try:
                d = yf.download(tk, start=start_str, end=end_str,
                                progress=False, auto_adjust=True)
                if not d.empty:
                    d.index = pd.to_datetime(d.index).date
                    results[tk] = d[["Open", "High", "Low", "Close"]].copy()
            except Exception:
                pass
        return results

    # --- Parse multi-ticker result ---
    raw.index = pd.to_datetime(raw.index).date

    if len(tickers) == 1:
        tk = tickers[0]
        try:
            results[tk] = raw[["Open", "High", "Low", "Close"]].copy()
        except Exception:
            pass
    else:
        for tk in tickers:
            try:
                sub = raw[tk][["Open", "High", "Low", "Close"]].copy()
                sub = sub.dropna(how="all")
                if not sub.empty:
                    results[tk] = sub
            except Exception:
                pass

    return results


# ---------------------------------------------------------------------------
# Step 4: Build daily OHLC portfolio value
# ---------------------------------------------------------------------------

def build_portfolio_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build a daily OHLC time-series for total portfolio value (unrealized + realized).

    Columns returned:
      Date, Open, High, Low, Close, Cash, Equity (unrealized USD), n_tickers_priced

    - Open  = previous day's Close (standard OHLC convention)
    - High  = cash + Σ(shares × daily_high_price per ticker)
    - Low   = cash + Σ(shares × daily_low_price per ticker)
    - Close = cash + Σ(shares × daily_close_price per ticker)
    """
    if df.empty:
        return pd.DataFrame()
    if not YFINANCE_AVAILABLE:
        return pd.DataFrame()

    cash_series = compute_daily_cash_series(df)
    inventory   = compute_daily_inventory(df)

    if inventory.empty or cash_series.empty:
        return pd.DataFrame()

    # Align both series on the same date range
    all_dates = sorted(set(cash_series.index) | set(inventory.index))
    cash_series = cash_series.reindex(all_dates, method="ffill").fillna(0.0)
    inventory   = inventory.reindex(all_dates, fill_value=0.0).ffill()

    tickers = tuple(col for col in inventory.columns if col)
    if not tickers:
        return pd.DataFrame()

    # Fetch prices (add 2 days buffer for weekends/holidays boundary)
    start_str = str(all_dates[0])
    end_str   = str(all_dates[-1] + timedelta(days=2))
    prices = fetch_historical_prices(tickers, start_str, end_str)

    not_found = [t for t in tickers if t not in prices]

    # Build day-by-day OHLC
    rows      = []
    prev_close = None
    price_dates_cache: dict[str, list] = {
        tk: sorted(prices[tk].index) for tk in prices
    }

    for d in all_dates:
        cash_val = float(cash_series.loc[d])

        eq_high = eq_low = eq_close = 0.0
        n_priced = 0

        for tk in tickers:
            shares = float(inventory.loc[d, tk])
            if shares == 0.0 or tk not in prices:
                continue

            # Nearest available price on or before this date
            avail = price_dates_cache[tk]
            candidates = [x for x in avail if x <= d]
            if not candidates:
                continue
            prow = prices[tk].loc[candidates[-1]]

            eq_high  += shares * float(prow["High"])
            eq_low   += shares * float(prow["Low"])
            eq_close += shares * float(prow["Close"])
            n_priced += 1

        port_high  = cash_val + eq_high
        port_low   = cash_val + eq_low
        port_close = cash_val + eq_close

        open_val   = prev_close if prev_close is not None else port_close
        prev_close = port_close

        rows.append({
            "Date":             d,
            "Open":             round(open_val,   2),
            "High":             round(port_high,  2),
            "Low":              round(port_low,   2),
            "Close":            round(port_close, 2),
            "Cash":             round(cash_val,   2),
            "Equity":           round(eq_close,   2),
            "n_tickers_priced": n_priced,
        })

    result = pd.DataFrame(rows)
    result._not_found_tickers = not_found   # surface for UI warning
    return result


# ---------------------------------------------------------------------------
# Step 5: Interval resampling
# ---------------------------------------------------------------------------

INTERVAL_OPTIONS = {
    "12H": "12 Hour (2 bars/day)",
    "1D":  "Daily",
    "1W":  "Weekly",
    "1M":  "Monthly",
    "3M":  "Quarterly",
    "1Y":  "Yearly",
}


def resample_ohlc(daily_ohlc: pd.DataFrame, interval: str) -> pd.DataFrame:
    """
    Resample a daily OHLC portfolio DataFrame to the requested interval.

    For 12H:   each calendar day → 2 synthetic bars
               Bar-AM: captures the descent to the day's Low
               Bar-PM: captures the ascent from Low to the day's High/Close
    For 1D:    identity (already daily)
    For 1W/1M/3M/1Y: standard OHLCV aggregation via pandas resample.
    """
    if daily_ohlc.empty:
        return daily_ohlc

    df = daily_ohlc.copy()
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date")

    if interval == "12H":
        rows = []
        for idx, row in df.iterrows():
            am_high = (float(row["Open"]) + float(row["Low"])) / 2.0
            # AM bar: open → slide down toward the day's Low
            rows.append({
                "Date":   idx,
                "Open":   row["Open"],
                "High":   am_high,
                "Low":    row["Low"],
                "Close":  row["Low"],
                "Cash":   row["Cash"],
                "Equity": row["Equity"],
                "n_tickers_priced": row["n_tickers_priced"],
            })
            # PM bar: recover from Low → Close (with High spike)
            rows.append({
                "Date":   idx + pd.Timedelta(hours=12),
                "Open":   row["Low"],
                "High":   row["High"],
                "Low":    row["Low"],
                "Close":  row["Close"],
                "Cash":   row["Cash"],
                "Equity": row["Equity"],
                "n_tickers_priced": row["n_tickers_priced"],
            })
        return pd.DataFrame(rows)

    freq_map = {
        "1D": None,
        "1W": "W",
        "1M": "ME",
        "3M": "QE",
        "1Y": "YE",
    }
    freq = freq_map.get(interval)
    if freq is None:
        return df.reset_index()

    agg = df.resample(freq).agg({
        "Open":             "first",
        "High":             "max",
        "Low":              "min",
        "Close":            "last",
        "Cash":             "last",
        "Equity":           "last",
        "n_tickers_priced": "last",
    }).dropna(subset=["Close"]).reset_index()
    agg["Date"] = agg["Date"].dt.date
    return agg
