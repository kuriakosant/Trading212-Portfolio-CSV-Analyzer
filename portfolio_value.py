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

from fx_engine import fetch_historical_fx, convert_currency

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

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
# ---------------------------------------------------------------------------
# Step 1: FX Rates & Daily realized cash metrics
# ---------------------------------------------------------------------------

def compute_daily_metrics(df: pd.DataFrame, fx_series: pd.Series, base_currency: str = "USD") -> pd.DataFrame:
    """
    Return a date-indexed DataFrame with true tracking for:
      - Cash: Realized uninvested account balance (in base_currency).
      - Net_Deposits: True deployed principal (Basis) from bank deposits - withdrawals (in base_currency).
    """
    if df.empty:
        return pd.DataFrame({"Cash": pd.Series(dtype=float), "Net_Deposits": pd.Series(dtype=float)})

    df = df.copy()
    df["_date"] = df["Time"].dt.date

    def calc_row(row) -> pd.Series:
        dt  = row["_date"]
        cat = row.get("_category", "other")
        ccy = str(row.get("Currency (Total)", "EUR")).strip().upper()
        tot = abs(float(row.get("Total", 0) or 0))
        
        # Convert the transaction size perfectly into the Base Currency using that day's rate
        val_base = convert_currency(tot, ccy, base_currency, dt, fx_series)
        
        cash_delta = 0.0
        dep_delta  = 0.0
        
        if cat == "deposit":
            cash_delta = val_base
            dep_delta  = val_base
        elif cat in ("withdrawal", "card_debit"):
            cash_delta = -val_base
            dep_delta  = -val_base
        elif cat == "buy":
            cash_delta = -val_base
        elif cat == "sell":
            cash_delta = val_base
        elif cat in ("dividend", "interest", "cashback"):
            cash_delta = val_base
            
        return pd.Series({"cash_delta": cash_delta, "dep_delta": dep_delta})

    deltas = df.apply(calc_row, axis=1)
    df["cash_delta"] = deltas["cash_delta"]
    df["dep_delta"]  = deltas["dep_delta"]
    
    daily = df.groupby("_date")[["cash_delta", "dep_delta"]].sum()

    start = daily.index.min()
    end   = daily.index.max()
    all_dates = pd.date_range(start, end, freq="D").date
    daily = daily.reindex(all_dates, fill_value=0.0)
    
    return pd.DataFrame({
        "Cash": daily["cash_delta"].cumsum(),
        "Net_Deposits": daily["dep_delta"].cumsum(),
    })


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

def build_portfolio_ohlc(df: pd.DataFrame, base_currency: str = "USD") -> pd.DataFrame:
    """
    Build a daily OHLC time-series for total portfolio value (unrealized + realized).

    Columns returned:
      Date, Open, High, Low, Close, Cash, Net_Deposits, Equity (unrealized), n_tickers_priced,
      Alt_Close, Alt_Equity
    """
    if df.empty:
        return pd.DataFrame()
    if not YFINANCE_AVAILABLE:
        return pd.DataFrame()

    inventory = compute_daily_inventory(df)

    all_raw_dates = set(df["Time"].dt.date) | set(inventory.index)
    if not all_raw_dates:
        return pd.DataFrame()
        
    start_str = str(min(all_raw_dates))
    end_str   = str(max(all_raw_dates) + timedelta(days=2))
    
    fx_series = fetch_historical_fx(start_str, end_str)

    cash_metrics = compute_daily_metrics(df, fx_series, base_currency=base_currency)
    cash_series  = cash_metrics["Cash"]
    dep_series   = cash_metrics["Net_Deposits"]

    if inventory.empty or cash_series.empty:
        return pd.DataFrame()

    # Align both series on the same date range
    all_dates = sorted(set(cash_series.index) | set(inventory.index))
    cash_series = cash_series.reindex(all_dates, method="ffill").fillna(0.0)
    dep_series  = dep_series.reindex(all_dates, method="ffill").fillna(0.0)
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
        dep_val  = float(dep_series.loc[d])

        eq_high = eq_low = eq_close = 0.0
        n_priced = 0

        for tk in tickers:
            shares = float(inventory.loc[d, tk])
            if shares == 0.0 or tk not in prices:
                continue

            avail = price_dates_cache[tk]
            candidates = [x for x in avail if x <= d]
            if not candidates:
                continue
            prow = prices[tk].loc[candidates[-1]]

            # YFinance provides stock prices heavily in USD/local. Assuming USD.
            h = convert_currency(float(prow["High"]),  "USD", base_currency, d, fx_series)
            l = convert_currency(float(prow["Low"]),   "USD", base_currency, d, fx_series)
            c = convert_currency(float(prow["Close"]), "USD", base_currency, d, fx_series)

            eq_high  += shares * h
            eq_low   += shares * l
            eq_close += shares * c
            n_priced += 1

        port_high  = cash_val + eq_high
        port_low   = cash_val + eq_low
        port_close = cash_val + eq_close

        open_val   = prev_close if prev_close is not None else port_close
        prev_close = port_close
        
        # Calculate Alternate Currency (e.g., if base=USD, alt=EUR)
        alt_ccy = "EUR" if base_currency == "USD" else "USD"
        alt_port_close = convert_currency(port_close, base_currency, alt_ccy, d, fx_series)
        alt_eq_close   = convert_currency(eq_close,   base_currency, alt_ccy, d, fx_series)

        rows.append({
            "Date":             d,
            "Open":             round(open_val,   2),
            "High":             round(port_high,  2),
            "Low":              round(port_low,   2),
            "Close":            round(port_close, 2),
            "Cash":             round(cash_val,   2),
            "Net_Deposits":     round(dep_val,    2),
            "Equity":           round(eq_close,   2),
            "Alt_Close":        round(alt_port_close, 2),
            "Alt_Equity":       round(alt_eq_close, 2),
            "n_tickers_priced": n_priced,
        })

    result = pd.DataFrame(rows)
    result.attrs["not_found_tickers"] = not_found   # surface for UI warning
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
                "Net_Deposits": row["Net_Deposits"],
                "Equity": row["Equity"],
                "Alt_Close": row["Alt_Close"],
                "Alt_Equity": row["Alt_Equity"],
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
                "Net_Deposits": row["Net_Deposits"],
                "Equity": row["Equity"],
                "Alt_Close": row["Alt_Close"],
                "Alt_Equity": row["Alt_Equity"],
                "n_tickers_priced": row["n_tickers_priced"],
            })
            
        res_df = pd.DataFrame(rows)
        # Calculate row-to-row interval differences
        res_df["_open_to_close_pct"] = (res_df["Close"] - res_df["Open"]) / res_df["Open"] * 100
        res_df["_open_to_close_usd"] = (res_df["Close"] - res_df["Open"])
        return res_df

    freq_map = {
        "1D": None,
        "1W": "W",
        "1M": "ME",
        "3M": "QE",
        "1Y": "YE",
    }
    freq = freq_map.get(interval)
    if freq is None:
        df = df.reset_index()
        # Daily row-to-row
        df["_open_to_close_pct"] = (df["Close"] - df["Open"]) / df["Open"] * 100
        df["_open_to_close_usd"] = (df["Close"] - df["Open"])
        return df

    agg = df.resample(freq).agg({
        "Open":             "first",
        "High":             "max",
        "Low":              "min",
        "Close":            "last",
        "Cash":             "last",
        "Net_Deposits":     "last",
        "Equity":           "last",
        "Alt_Close":        "last",
        "Alt_Equity":       "last",
        "n_tickers_priced": "last",
    }).dropna(subset=["Close"]).reset_index()
    agg["Date"] = agg["Date"].dt.date
    
    # Calculate interval diffs on the resampled matrix
    agg["_open_to_close_pct"] = (agg["Close"] - agg["Open"]) / agg["Open"] * 100
    agg["_open_to_close_usd"] = (agg["Close"] - agg["Open"])
    
    return agg
