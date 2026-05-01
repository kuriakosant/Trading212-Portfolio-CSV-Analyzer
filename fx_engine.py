"""
fx_engine.py - Global multi-currency conversion utility.

Downloads and caches historical YFinance FX daily data (e.g., EURUSD=X) to
perfectly map historical account transactions across different currency views.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_historical_fx(start_str: str, end_str: str) -> pd.Series:
    """
    Fetch daily EUR/USD exchange rates to convert EUR cashflows accurately.
    Returns a date-indexed Series of the EUR/USD multiplier.
    If the fallback is used, it returns an empty Series.
    """
    if not YFINANCE_AVAILABLE:
        return pd.Series(dtype=float)
    try:
        raw = yf.download("EURUSD=X", start=start_str, end=end_str, progress=False, auto_adjust=True)
        if raw.empty:
            return pd.Series(dtype=float)
        raw.index = pd.to_datetime(raw.index).date
        
        # Forward fill weekends
        all_dates = pd.date_range(start_str, end_str, freq="D").date
        if isinstance(raw, pd.DataFrame) and "Close" in raw.columns:
            res = raw["Close"].squeeze()
        else:
            res = raw.squeeze()
            
        res = res.reindex(all_dates, method="ffill").bfill()
        return res
    except Exception:
        return pd.Series(dtype=float)


def convert_currency(val: float, from_ccy: str, to_ccy: str, dt, fx_series: pd.Series, fallback_rate: float = 1.0 / 0.86) -> float:
    """
    Convert a value from one currency to another using the exact daily historical rate.
    Uses `fallback_rate` if yfinance fails. (Currently supports EUR/USD crossing).
    """
    try:
        val = float(val or 0.0)
    except (TypeError, ValueError):
        val = 0.0

    if not val:
        return 0.0
        
    from_ccy = str(from_ccy).strip().upper()
    to_ccy   = str(to_ccy).strip().upper()
    
    if from_ccy == to_ccy:
        return val

    # Determine fallback direction
    base_rate = fallback_rate
    
    if pd.isna(dt):
        rate = base_rate
    else:
        date_key = pd.to_datetime(dt).date()
        # Base rate is EUR -> USD multiplier
        if not fx_series.empty and date_key in fx_series.index:
            rate_raw = fx_series.loc[date_key]
            if isinstance(rate_raw, pd.Series):
                rate = float(rate_raw.iloc[0])
            else:
                rate = float(rate_raw)
        else:
            rate = base_rate

    # Apply direction
    if from_ccy == "EUR" and to_ccy == "USD":
        return val * rate
    elif from_ccy == "USD" and to_ccy == "EUR":
        return val / rate
        
    # If not EUR/USD cross, return raw (fallback for unhandled currencies)
    return val
