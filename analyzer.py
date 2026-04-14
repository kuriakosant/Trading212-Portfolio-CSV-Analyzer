"""
analyzer.py — Core data processing for Trading212 CSV exports.
Handles parsing, action classification, date filtering, P&L aggregation,
and timeline resampling for charting.
"""

import pandas as pd
import numpy as np
from datetime import date

# ---------------------------------------------------------------------------
# Action type classification
# ---------------------------------------------------------------------------

BUY_ACTIONS      = {"market buy", "limit buy"}
SELL_ACTIONS     = {"market sell", "limit sell"}
DIVIDEND_ACTIONS = {"dividend (dividend)", "dividend"}
INTEREST_ACTIONS = {"interest on cash", "lending interest"}
DEPOSIT_ACTIONS  = {"deposit"}
WITHDRAWAL_ACTIONS = {"withdrawal"}
FX_ACTIONS       = {"currency conversion"}
CARD_DEBIT_ACTIONS  = {"card debit"}
CARD_CREDIT_ACTIONS = {"card credit"}
CASHBACK_ACTIONS = {"spending cashback"}

FREQ_MAP = {
    "Daily":     "D",
    "Weekly":    "W",
    "Monthly":   "ME",
    "Quarterly": "QE",
}


def classify_action(action: str) -> str:
    a = str(action).strip().lower()
    if a in BUY_ACTIONS:       return "buy"
    if a in SELL_ACTIONS:      return "sell"
    if a in DIVIDEND_ACTIONS:  return "dividend"
    if a in INTEREST_ACTIONS:  return "interest"
    if a in DEPOSIT_ACTIONS:   return "deposit"
    if a in WITHDRAWAL_ACTIONS: return "withdrawal"
    if a in FX_ACTIONS:        return "fx_conversion"
    if a in CARD_DEBIT_ACTIONS:  return "card_debit"
    if a in CARD_CREDIT_ACTIONS: return "card_credit"
    if a in CASHBACK_ACTIONS:  return "cashback"
    return "other"


# ---------------------------------------------------------------------------
# CSV loading
# ---------------------------------------------------------------------------

def load_csv(uploaded_file) -> pd.DataFrame:
    df = pd.read_csv(uploaded_file, low_memory=False)
    return _clean_dataframe(df)


def load_csvs(uploaded_files) -> pd.DataFrame:
    frames = [load_csv(f) for f in uploaded_files]
    combined = pd.concat(frames, ignore_index=True)
    if "ID" in combined.columns:
        combined = combined.drop_duplicates(subset=["ID"])
    return combined.sort_values("Time").reset_index(drop=True)


def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [c.strip() for c in df.columns]
    df["Time"] = pd.to_datetime(df["Time"], format="%Y-%m-%d %H:%M:%S", errors="coerce")
    numeric_cols = [
        "No. of shares", "Price / share", "Exchange rate", "Result", "Total",
        "Withholding tax", "Finra fee", "Currency conversion from amount",
        "Currency conversion to amount", "Currency conversion fee",
        "French transaction tax",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df["_category"] = df["Action"].apply(classify_action)
    return df


# ---------------------------------------------------------------------------
# Date filtering
# ---------------------------------------------------------------------------

def filter_by_date(df: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
    start_ts = pd.Timestamp(start)
    end_ts   = pd.Timestamp(end) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    return df[(df["Time"] >= start_ts) & (df["Time"] <= end_ts)].copy()


# ---------------------------------------------------------------------------
# Summary aggregation
# ---------------------------------------------------------------------------

def compute_summary(df: pd.DataFrame) -> dict:
    sells      = df[df["_category"] == "sell"].copy()
    buys       = df[df["_category"] == "buy"].copy()
    dividends  = df[df["_category"] == "dividend"].copy()
    interests  = df[df["_category"] == "interest"].copy()
    deposits   = df[df["_category"] == "deposit"].copy()
    withdrawals= df[df["_category"] == "withdrawal"].copy()
    cashback   = df[df["_category"] == "cashback"].copy()
    card_debits= df[df["_category"] == "card_debit"].copy()

    sells_result  = sells["Result"].fillna(0)
    gross_profit  = float(sells_result[sells_result > 0].sum())
    gross_loss    = float(sells_result[sells_result < 0].sum())
    net_pnl       = gross_profit + gross_loss

    total_buy_volume  = float(buys["Total"].fillna(0).abs().sum())
    total_sell_volume = float(sells["Total"].fillna(0).abs().sum())

    div_total_eur   = float(dividends["Total"].fillna(0).sum())
    div_withholding = float(dividends["Withholding tax"].fillna(0).abs().sum())
    div_gross       = div_total_eur + div_withholding

    int_eur, int_usd = 0.0, 0.0
    for _, row in interests.iterrows():
        val = float(row.get("Total", 0) or 0)
        if str(row.get("Currency (Total)", "")).strip().upper() == "USD":
            int_usd += val
        else:
            int_eur += val

    cashback_total  = float(cashback["Total"].fillna(0).sum())
    total_deposited = float(deposits["Total"].fillna(0).abs().sum())
    total_withdrawn = float(withdrawals["Total"].fillna(0).abs().sum())
    total_card_spent= float(card_debits["Total"].fillna(0).abs().sum())

    n_sells           = len(sells)
    n_wins            = int((sells_result > 0).sum())
    n_losses          = int((sells_result < 0).sum())

    return {
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "net_pnl": net_pnl,
        "n_buys": len(buys),
        "n_sells": n_sells,
        "n_winning_trades": n_wins,
        "n_losing_trades": n_losses,
        "win_rate": (n_wins / n_sells * 100) if n_sells > 0 else 0.0,
        "total_buy_volume": total_buy_volume,
        "total_sell_volume": total_sell_volume,
        "div_gross_eur": div_gross,
        "div_net_eur": div_total_eur,
        "div_withholding_eur": div_withholding,
        "interest_eur": int_eur,
        "interest_usd": int_usd,
        "cashback_eur": cashback_total,
        "total_deposited_eur": total_deposited,
        "total_withdrawn_eur": total_withdrawn,
        "total_card_spent_eur": total_card_spent,
        "n_dividends": len(dividends),
        "n_interest": len(interests),
        "n_deposits": len(deposits),
        "n_withdrawals": len(withdrawals),
    }


# ---------------------------------------------------------------------------
# Per-ticker breakdown
# ---------------------------------------------------------------------------

def ticker_pnl(df: pd.DataFrame) -> pd.DataFrame:
    sells = df[df["_category"] == "sell"].copy()
    if sells.empty:
        return pd.DataFrame(columns=["Ticker", "Name", "Sell Trades", "Profit", "Loss", "Net P&L"])
    sells["result_clean"] = sells["Result"].fillna(0)
    grouped = sells.groupby(["Ticker", "Name"]).agg(
        sell_trades=("result_clean", "count"),
        profit=("result_clean", lambda x: x.clip(lower=0).sum()),
        loss=("result_clean", lambda x: x.clip(upper=0).sum()),
        net=("result_clean", "sum"),
    ).reset_index().rename(columns={
        "sell_trades": "Sell Trades", "profit": "Profit", "loss": "Loss", "net": "Net P&L"
    })
    return grouped.sort_values("Net P&L", ascending=False)


# ---------------------------------------------------------------------------
# Timeline / resampling  (NEW)
# ---------------------------------------------------------------------------

def pnl_timeline(df: pd.DataFrame, freq: str = "D") -> pd.DataFrame:
    """
    Resample sell P&L to the given pandas frequency string.
    Returns DataFrame with: Period, Period P&L, Cumulative P&L,
    Winning Trades, Losing Trades, Total Trades.
    """
    sells = df[df["_category"] == "sell"].copy()
    if sells.empty:
        return pd.DataFrame(columns=["Period", "Period P&L", "Cumulative P&L",
                                     "Wins", "Losses", "Trades"])

    sells = sells.set_index("Time")
    sells["Result"] = sells["Result"].fillna(0)
    sells["win"]    = (sells["Result"] > 0).astype(int)
    sells["loss"]   = (sells["Result"] < 0).astype(int)

    agg = sells.resample(freq).agg(
        period_pnl=("Result", "sum"),
        wins=("win", "sum"),
        losses=("loss", "sum"),
        trades=("Result", "count"),
    ).reset_index()
    agg.columns = ["Period", "Period P&L", "Wins", "Losses", "Trades"]
    agg["Cumulative P&L"] = agg["Period P&L"].cumsum()
    # Running win rate
    agg["Cumul Wins"]   = agg["Wins"].cumsum()
    agg["Cumul Trades"] = agg["Trades"].cumsum()
    agg["Win Rate %"]   = (agg["Cumul Wins"] / agg["Cumul Trades"].replace(0, np.nan) * 100).round(1)

    return agg


def dividend_series(df: pd.DataFrame) -> pd.DataFrame:
    """
    Each individual dividend payment with running cumulative total.
    """
    divs = df[df["_category"] == "dividend"].copy()
    if divs.empty:
        return pd.DataFrame(columns=["Time", "Ticker", "Net (EUR)", "Withholding (EUR)", "Cumulative (EUR)"])

    divs = divs.sort_values("Time")
    divs["Net (EUR)"]         = divs["Total"].fillna(0)
    divs["Withholding (EUR)"] = divs["Withholding tax"].fillna(0).abs()
    divs["Cumulative (EUR)"]  = divs["Net (EUR)"].cumsum()
    return divs[["Time", "Ticker", "Name", "Net (EUR)", "Withholding (EUR)", "Cumulative (EUR)"]].reset_index(drop=True)


def interest_series(df: pd.DataFrame) -> pd.DataFrame:
    """
    Each individual interest/lending payment with running cumulative total.
    Separates EUR and USD rows.
    """
    ints = df[df["_category"] == "interest"].copy()
    if ints.empty:
        return pd.DataFrame(columns=["Time", "Action", "Amount", "Currency", "Cumulative EUR", "Cumulative USD"])

    ints = ints.sort_values("Time")
    ints["Amount"]   = ints["Total"].fillna(0)
    ints["Currency"] = ints["Currency (Total)"].fillna("EUR").str.strip()

    eur_rows = ints[ints["Currency"] == "EUR"].copy()
    usd_rows = ints[ints["Currency"] == "USD"].copy()

    eur_rows["Cumulative EUR"] = eur_rows["Amount"].cumsum()
    usd_rows["Cumulative USD"] = usd_rows["Amount"].cumsum()

    result = pd.concat([eur_rows.assign(**{"Cumulative USD": np.nan}),
                        usd_rows.assign(**{"Cumulative EUR": np.nan})], ignore_index=True)
    result = result.sort_values("Time")
    return result[["Time", "Action", "Amount", "Currency", "Cumulative EUR", "Cumulative USD"]].reset_index(drop=True)


def monthly_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Month-level summary: Profit, Loss, Net P&L, Dividends, Interest."""
    rows = []
    temp = df.copy()
    temp["_month"] = temp["Time"].dt.to_period("M")
    for month, group in temp.groupby("_month"):
        sells    = group[group["_category"] == "sell"]
        result   = sells["Result"].fillna(0)
        profit   = float(result.clip(lower=0).sum())
        loss     = float(result.clip(upper=0).sum())
        div_net  = float(group[group["_category"] == "dividend"]["Total"].fillna(0).sum())
        int_tot  = float(group[group["_category"] == "interest"]["Total"].fillna(0).sum())
        rows.append({
            "Month": str(month),
            "Profit": profit,
            "Loss": abs(loss),
            "Net P&L": profit + loss,
            "Dividends (EUR)": max(div_net, 0),
            "Interest": int_tot,
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Display tables
# ---------------------------------------------------------------------------

def get_dividends_table(df: pd.DataFrame) -> pd.DataFrame:
    divs = df[df["_category"] == "dividend"].copy()
    if divs.empty:
        return pd.DataFrame()
    cols = ["Time", "Ticker", "Name", "No. of shares", "Price / share",
            "Currency (Price / share)", "Total", "Currency (Total)",
            "Withholding tax", "Currency (Withholding tax)"]
    return divs[[c for c in cols if c in divs.columns]].sort_values("Time", ascending=False).reset_index(drop=True)


def get_trades_table(df: pd.DataFrame) -> pd.DataFrame:
    trades = df[df["_category"].isin(["buy", "sell"])].copy()
    if trades.empty:
        return pd.DataFrame()
    cols = ["Time", "Action", "Ticker", "Name", "No. of shares",
            "Price / share", "Currency (Price / share)",
            "Result", "Currency (Result)", "Total", "Currency (Total)"]
    return trades[[c for c in cols if c in trades.columns]].sort_values("Time", ascending=False).reset_index(drop=True)
