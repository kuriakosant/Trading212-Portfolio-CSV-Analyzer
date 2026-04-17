"""
brokers/canonical.py — Canonical row schema shared by all broker adapters.

Every adapter must emit a DataFrame whose columns match (or are a subset of) the
canonical list below.  Downstream modules (analyzer, charts, app) consume only
this canonical shape — they MUST NOT depend on broker-specific column names.

Keeping this contract in one place makes it trivial to add a third broker later:
write an adapter that produces a frame with these columns, and everything else
"just works".
"""

from __future__ import annotations

import pandas as pd

# ---------------------------------------------------------------------------
# Canonical column names
# ---------------------------------------------------------------------------

# Timestamp (tz-naive; all adapters must normalize to naive UTC)
COL_TIME = "Time"

# Core transaction identity
COL_ACTION   = "Action"        # canonical verb, see CANONICAL_ACTIONS below
COL_TICKER   = "Ticker"
COL_NAME     = "Name"          # falls back to Ticker when the broker omits it
COL_ISIN     = "ISIN"          # <NA> when the broker omits it

# Instrument quantities / prices
COL_SHARES          = "No. of shares"
COL_PRICE_PER_SHARE = "Price / share"
COL_PRICE_CCY       = "Currency (Price / share)"
COL_EXCHANGE_RATE   = "Exchange rate"

# Realized P&L on sells — pre-filled by the broker (T212) OR computed by us (Revolut)
COL_RESULT     = "Result"
COL_RESULT_CCY = "Currency (Result)"

# Money movements
COL_TOTAL     = "Total"          # signed or unsigned depending on action; summaries use abs()
COL_TOTAL_CCY = "Currency (Total)"

# Dividend withholding
COL_WITHHOLDING     = "Withholding tax"
COL_WITHHOLDING_CCY = "Currency (Withholding tax)"

# Per-trade fees (0.0 when the broker doesn't itemize them)
COL_FEE_FINRA    = "Finra fee"
COL_FEE_FR_TAX   = "French transaction tax"
COL_FEE_STAMP    = "Stamp duty reserve tax"
COL_FEE_PTM_LEVY = "UK PTM Levy"
COL_FEE_FX       = "Currency conversion fee"

# Currency conversion leg amounts
COL_CONV_FROM_AMOUNT = "Currency conversion from amount"
COL_CONV_TO_AMOUNT   = "Currency conversion to amount"

# Card spending (Trading212-only today; <NA> for Revolut)
COL_MERCHANT_NAME     = "Merchant name"
COL_MERCHANT_CATEGORY = "Merchant category"

# Broker-provided row id (T212 has it, Revolut does not)
COL_ID = "ID"

# Derived columns (set by analyzer / adapters, not source CSVs)
COL_CATEGORY = "_category"     # bucket: buy/sell/dividend/interest/deposit/...
COL_BROKER   = "_broker"       # "trading212" | "revolut"


# ---------------------------------------------------------------------------
# Canonical Action verbs
# ---------------------------------------------------------------------------

# These are the exact strings that adapters must emit in COL_ACTION.
# analyzer.classify_action() maps them to _category buckets.
ACTION_MARKET_BUY   = "Market buy"
ACTION_LIMIT_BUY    = "Limit buy"
ACTION_MARKET_SELL  = "Market sell"
ACTION_LIMIT_SELL   = "Limit sell"
ACTION_DIVIDEND     = "Dividend"
ACTION_DIVIDEND_TAX_CORRECTION = "Dividend tax correction"
ACTION_INTEREST_CASH    = "Interest on cash"
ACTION_LENDING_INTEREST = "Lending interest"
ACTION_DEPOSIT      = "Deposit"
ACTION_WITHDRAWAL   = "Withdrawal"
ACTION_FX_CONVERSION = "Currency conversion"
ACTION_STOCK_SPLIT  = "Stock split"
ACTION_CARD_DEBIT   = "Card debit"
ACTION_CARD_CREDIT  = "Card credit"
ACTION_CASHBACK     = "Spending cashback"


# ---------------------------------------------------------------------------
# Ordered canonical column list
# ---------------------------------------------------------------------------

CANONICAL_COLUMNS: list[str] = [
    COL_TIME,
    COL_ACTION,
    COL_TICKER,
    COL_NAME,
    COL_ISIN,
    COL_SHARES,
    COL_PRICE_PER_SHARE,
    COL_PRICE_CCY,
    COL_EXCHANGE_RATE,
    COL_RESULT,
    COL_RESULT_CCY,
    COL_TOTAL,
    COL_TOTAL_CCY,
    COL_WITHHOLDING,
    COL_WITHHOLDING_CCY,
    COL_FEE_FINRA,
    COL_FEE_FR_TAX,
    COL_FEE_STAMP,
    COL_FEE_PTM_LEVY,
    COL_FEE_FX,
    COL_CONV_FROM_AMOUNT,
    COL_CONV_TO_AMOUNT,
    COL_MERCHANT_NAME,
    COL_MERCHANT_CATEGORY,
    COL_ID,
    COL_BROKER,
]

# Numeric columns (safe to coerce via pd.to_numeric)
NUMERIC_COLUMNS: list[str] = [
    COL_SHARES,
    COL_PRICE_PER_SHARE,
    COL_EXCHANGE_RATE,
    COL_RESULT,
    COL_TOTAL,
    COL_WITHHOLDING,
    COL_FEE_FINRA,
    COL_FEE_FR_TAX,
    COL_FEE_STAMP,
    COL_FEE_PTM_LEVY,
    COL_FEE_FX,
    COL_CONV_FROM_AMOUNT,
    COL_CONV_TO_AMOUNT,
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def ensure_canonical_columns(df: pd.DataFrame, broker_name: str) -> pd.DataFrame:
    """
    Ensure every canonical column exists on `df`.

    Missing string columns get filled with <NA>; missing numeric columns get
    filled with 0.0.  This keeps downstream aggregations (which do
    `df.get(col, empty).fillna(0)`) cheap and null-safe regardless of which
    broker produced the row.
    """
    out = df.copy()
    for col in CANONICAL_COLUMNS:
        if col not in out.columns:
            if col in NUMERIC_COLUMNS:
                out[col] = 0.0
            else:
                out[col] = pd.NA
    out[COL_BROKER] = broker_name
    return out
