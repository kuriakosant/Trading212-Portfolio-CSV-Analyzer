"""
analyzer.py — Core data processing for Trading212 CSV exports.

Handles parsing, action classification, currency normalization,
date filtering, and aggregated P&L / income calculations.
"""

import pandas as pd
import numpy as np
from datetime import datetime, date


# ---------------------------------------------------------------------------
# Action type classification
# ---------------------------------------------------------------------------

BUY_ACTIONS = {"market buy", "limit buy"}
SELL_ACTIONS = {"market sell", "limit sell"}
DIVIDEND_ACTIONS = {"dividend (dividend)", "dividend"}
INTEREST_ACTIONS = {"interest on cash", "lending interest"}
DEPOSIT_ACTIONS = {"deposit"}
WITHDRAWAL_ACTIONS = {"withdrawal"}
FX_ACTIONS = {"currency conversion"}
CARD_DEBIT_ACTIONS = {"card debit"}
CARD_CREDIT_ACTIONS = {"card credit"}
CASHBACK_ACTIONS = {"spending cashback"}


def classify_action(action: str) -> str:
    """Return a normalized category for a given action string."""
    a = str(action).strip().lower()
    if a in BUY_ACTIONS:
        return "buy"
    if a in SELL_ACTIONS:
        return "sell"
    if a in DIVIDEND_ACTIONS:
        return "dividend"
    if a in INTEREST_ACTIONS:
        return "interest"
    if a in DEPOSIT_ACTIONS:
        return "deposit"
    if a in WITHDRAWAL_ACTIONS:
        return "withdrawal"
    if a in FX_ACTIONS:
        return "fx_conversion"
    if a in CARD_DEBIT_ACTIONS:
        return "card_debit"
    if a in CARD_CREDIT_ACTIONS:
        return "card_credit"
    if a in CASHBACK_ACTIONS:
        return "cashback"
    return "other"


# ---------------------------------------------------------------------------
# CSV loading
# ---------------------------------------------------------------------------

def load_csv(uploaded_file) -> pd.DataFrame:
    """
    Load a single Trading212 CSV export (Streamlit UploadedFile or file path).
    Returns a cleaned DataFrame.
    """
    df = pd.read_csv(uploaded_file, low_memory=False)
    return _clean_dataframe(df)


def load_csvs(uploaded_files) -> pd.DataFrame:
    """Load and merge multiple CSV files into one DataFrame."""
    frames = [load_csv(f) for f in uploaded_files]
    combined = pd.concat(frames, ignore_index=True)
    # De-duplicate by transaction ID where available
    id_col = "ID"
    if id_col in combined.columns:
        combined = combined.drop_duplicates(subset=[id_col])
    combined = combined.sort_values("Time").reset_index(drop=True)
    return combined


def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names, parse dates, coerce numerics."""
    # Strip whitespace from column names
    df.columns = [c.strip() for c in df.columns]

    # Parse Time
    df["Time"] = pd.to_datetime(df["Time"], format="%Y-%m-%d %H:%M:%S", errors="coerce")

    # Coerce numeric columns
    numeric_cols = [
        "No. of shares",
        "Price / share",
        "Exchange rate",
        "Result",
        "Total",
        "Withholding tax",
        "Finra fee",
        "Currency conversion from amount",
        "Currency conversion to amount",
        "Currency conversion fee",
        "French transaction tax",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Add a category column
    df["_category"] = df["Action"].apply(classify_action)

    return df


# ---------------------------------------------------------------------------
# Date filtering
# ---------------------------------------------------------------------------

def filter_by_date(df: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
    """Return rows whose Time falls within [start, end] inclusive."""
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    mask = (df["Time"] >= start_ts) & (df["Time"] <= end_ts)
    return df[mask].copy()


# ---------------------------------------------------------------------------
# Currency helpers
# ---------------------------------------------------------------------------

def _to_eur(row: pd.Series, amount_col: str = "Result") -> float:
    """
    Return amount converted approximately to EUR.
    Trading212 stores the exchange rate as local-currency-per-USD or similar.
    For simplicity we use the Exchange rate column:
      - If currency is EUR → amount as-is
      - If currency is USD and exchange rate != 1 → amount / exchange_rate
      - Otherwise fallback to raw amount
    """
    amount = row.get(amount_col, np.nan)
    if pd.isna(amount):
        return 0.0
    currency_col = f"Currency ({amount_col})"
    currency = str(row.get(currency_col, "")).strip().upper()
    exch = row.get("Exchange rate", np.nan)

    if currency == "EUR":
        return float(amount)
    if currency == "USD" and not pd.isna(exch) and exch not in (0, 1.0):
        return float(amount) / float(exch)
    # If exchange rate is 1.0 (USD balance account) just return USD amount
    return float(amount)


# ---------------------------------------------------------------------------
# Main aggregation
# ---------------------------------------------------------------------------

def compute_summary(df: pd.DataFrame) -> dict:
    """
    Compute all P&L, income and cash-flow aggregates for a filtered DataFrame.
    Returns a dict with pre-computed metrics (all in original currencies).
    """
    sells = df[df["_category"] == "sell"].copy()
    buys = df[df["_category"] == "buy"].copy()
    dividends = df[df["_category"] == "dividend"].copy()
    interests = df[df["_category"] == "interest"].copy()
    deposits = df[df["_category"] == "deposit"].copy()
    withdrawals = df[df["_category"] == "withdrawal"].copy()
    cashback = df[df["_category"] == "cashback"].copy()
    card_debits = df[df["_category"] == "card_debit"].copy()

    # ---- Trade P&L (Result column on sells) --------------------------------
    sells_result = sells["Result"].fillna(0)
    gross_profit = float(sells_result[sells_result > 0].sum())
    gross_loss = float(sells_result[sells_result < 0].sum())   # negative
    net_pnl = gross_profit + gross_loss                        # profit + loss

    # ---- Total buy / sell volume -------------------------------------------
    total_buy_volume = float(buys["Total"].fillna(0).abs().sum())
    total_sell_volume = float(sells["Total"].fillna(0).abs().sum())

    # ---- Dividends ---------------------------------------------------------
    # Dividend rows: Total column holds net amount after withholding
    div_total_eur = float(dividends["Total"].fillna(0).apply(
        lambda x: x if abs(x) > 0 else 0
    ).sum())
    # Also check Result column (sometimes used)
    # For dividends the Total is in EUR, Result may be 0
    div_withholding = float(dividends["Withholding tax"].fillna(0).abs().sum())
    # Gross dividend = net + withholding (withholding is already positive abs)
    div_gross = div_total_eur + div_withholding

    # ---- Interest ----------------------------------------------------------
    int_eur = float(interests["Total"].fillna(0).sum())
    int_usd = 0.0
    for _, row in interests.iterrows():
        if str(row.get("Currency (Total)", "")).strip().upper() == "USD":
            int_usd += float(row.get("Total", 0) or 0)
            int_eur -= float(row.get("Total", 0) or 0)

    # ---- Cashback ----------------------------------------------------------
    cashback_total = float(cashback["Total"].fillna(0).sum())

    # ---- Deposits / Withdrawals --------------------------------------------
    total_deposited = float(deposits["Total"].fillna(0).abs().sum())
    total_withdrawn = float(withdrawals["Total"].fillna(0).abs().sum())

    # ---- Card spending -----------------------------------------------------
    total_card_spent = float(card_debits["Total"].fillna(0).abs().sum())

    # ---- Trade counts ------------------------------------------------------
    n_sells = len(sells)
    n_buys = len(buys)
    n_winning_trades = int((sells_result > 0).sum())
    n_losing_trades = int((sells_result < 0).sum())
    win_rate = (n_winning_trades / n_sells * 100) if n_sells > 0 else 0.0

    return {
        # Trade P&L (in currency of Result — typically USD)
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "net_pnl": net_pnl,
        "n_buys": n_buys,
        "n_sells": n_sells,
        "n_winning_trades": n_winning_trades,
        "n_losing_trades": n_losing_trades,
        "win_rate": win_rate,
        "total_buy_volume": total_buy_volume,
        "total_sell_volume": total_sell_volume,
        # Income (EUR)
        "div_gross_eur": div_gross,
        "div_net_eur": div_total_eur,
        "div_withholding_eur": div_withholding,
        "interest_eur": int_eur,
        "interest_usd": int_usd,
        "cashback_eur": cashback_total,
        # Cash flow (EUR)
        "total_deposited_eur": total_deposited,
        "total_withdrawn_eur": total_withdrawn,
        "total_card_spent_eur": total_card_spent,
        # Row counts
        "n_dividends": len(dividends),
        "n_interest": len(interests),
        "n_deposits": len(deposits),
        "n_withdrawals": len(withdrawals),
    }


# ---------------------------------------------------------------------------
# Per-ticker breakdown
# ---------------------------------------------------------------------------

def ticker_pnl(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return a DataFrame with per-ticker P&L from sell transactions.
    Columns: Ticker, Name, Trades, Profit, Loss, Net P&L
    """
    sells = df[df["_category"] == "sell"].copy()
    if sells.empty:
        return pd.DataFrame(columns=["Ticker", "Name", "Sell Trades", "Profit", "Loss", "Net P&L"])

    sells["result_clean"] = sells["Result"].fillna(0)
    sells["profit"] = sells["result_clean"].clip(lower=0)
    sells["loss"] = sells["result_clean"].clip(upper=0)

    grouped = sells.groupby(["Ticker", "Name"]).agg(
        sell_trades=("result_clean", "count"),
        profit=("profit", "sum"),
        loss=("loss", "sum"),
        net=("result_clean", "sum"),
    ).reset_index()
    grouped = grouped.rename(columns={
        "sell_trades": "Sell Trades",
        "profit": "Profit",
        "loss": "Loss",
        "net": "Net P&L",
    })
    grouped = grouped.sort_values("Net P&L", ascending=False)
    return grouped


# ---------------------------------------------------------------------------
# Time-series data for charts
# ---------------------------------------------------------------------------

def daily_cumulative_pnl(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return a date-indexed DataFrame with cumulative P&L from sell Result.
    """
    sells = df[df["_category"] == "sell"][["Time", "Result"]].copy()
    if sells.empty:
        return pd.DataFrame(columns=["Date", "Daily P&L", "Cumulative P&L"])

    sells["Date"] = sells["Time"].dt.date
    sells["Result"] = sells["Result"].fillna(0)
    daily = sells.groupby("Date")["Result"].sum().reset_index()
    daily.columns = ["Date", "Daily P&L"]
    daily["Cumulative P&L"] = daily["Daily P&L"].cumsum()
    return daily


def monthly_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return a month-indexed DataFrame with:
    Profit, Loss, Net P&L, Dividends (EUR), Interest (EUR+USD) per month.
    """
    result_rows = []

    df["_month"] = df["Time"].dt.to_period("M")
    for month, group in df.groupby("_month"):
        sells = group[group["_category"] == "sell"]
        result = sells["Result"].fillna(0)
        profit = float(result.clip(lower=0).sum())
        loss = float(result.clip(upper=0).sum())

        dividends = group[group["_category"] == "dividend"]
        div_net = float(dividends["Total"].fillna(0).sum())

        interests = group[group["_category"] == "interest"]
        int_total = float(interests["Total"].fillna(0).sum())

        result_rows.append({
            "Month": str(month),
            "Profit": profit,
            "Loss": abs(loss),
            "Net P&L": profit + loss,
            "Dividends (EUR)": max(div_net, 0),
            "Interest": int_total,
        })

    return pd.DataFrame(result_rows)


def get_dividends_table(df: pd.DataFrame) -> pd.DataFrame:
    """Return dividend rows formatted for display."""
    divs = df[df["_category"] == "dividend"].copy()
    if divs.empty:
        return pd.DataFrame()
    cols = ["Time", "Ticker", "Name", "No. of shares", "Price / share",
            "Currency (Price / share)", "Total", "Currency (Total)",
            "Withholding tax", "Currency (Withholding tax)"]
    available = [c for c in cols if c in divs.columns]
    return divs[available].sort_values("Time", ascending=False).reset_index(drop=True)


def get_trades_table(df: pd.DataFrame) -> pd.DataFrame:
    """Return buy/sell rows formatted for display."""
    trades = df[df["_category"].isin(["buy", "sell"])].copy()
    if trades.empty:
        return pd.DataFrame()
    cols = ["Time", "Action", "Ticker", "Name", "No. of shares",
            "Price / share", "Currency (Price / share)",
            "Result", "Currency (Result)", "Total", "Currency (Total)"]
    available = [c for c in cols if c in trades.columns]
    return trades[available].sort_values("Time", ascending=False).reset_index(drop=True)
