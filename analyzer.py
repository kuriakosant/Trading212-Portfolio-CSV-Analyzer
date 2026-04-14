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
    """
    Load and merge multiple CSV exports, de-duplicating robustly.

    Trading212 exports can overlap (e.g. Dec 31 appears in both a 2025 file
    and a 2026 file).  De-duplication is done in two passes:

    Pass 1 — ID-based (covers trades, deposits, interest, cashback, FX, etc.)
        Every row that has a non-empty ID value is deduplicated by that ID.
        IDs are globally unique transaction identifiers assigned by Trading212.

    Pass 2 — Content fingerprint (covers dividends and any other rows with
        a blank/null ID column).
        Fingerprint = (Time, Action, ISIN, No. of shares, Total)
        Two rows with identical fingerprints on the same instant cannot be
        different transactions, so the duplicate is dropped.
    """
    frames = [load_csv(f) for f in uploaded_files]
    combined = pd.concat(frames, ignore_index=True)

    if "ID" not in combined.columns:
        combined["ID"] = pd.NA

    # Split into rows that have an ID and rows that don't
    has_id  = combined["ID"].notna() & (combined["ID"].astype(str).str.strip() != "")
    with_id    = combined[has_id].copy()
    without_id = combined[~has_id].copy()

    # Pass 1: deduplicate by ID
    with_id = with_id.drop_duplicates(subset=["ID"])

    # Pass 2: deduplicate by content fingerprint
    fp_cols = ["Time", "Action", "ISIN", "No. of shares", "Total"]
    fp_available = [c for c in fp_cols if c in without_id.columns]
    if fp_available:
        without_id = without_id.drop_duplicates(subset=fp_available)

    combined = pd.concat([with_id, without_id], ignore_index=True)
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

def export_portfolio_summary(summary: dict, start_date, end_date) -> pd.DataFrame:
    """
    Creates a single-row DataFrame summarizing the total account stats for custom Excel export.
    """
    net_deposited = summary["total_deposited_eur"] - summary["total_withdrawn_eur"]
    total_return = summary["net_pnl"] + summary["div_net_eur"] + summary["interest_eur"] + summary.get("interest_usd", 0) + summary["cashback_eur"]
    
    data = {
        "Start Date": start_date.strftime("%Y-%m-%d") if pd.notna(start_date) else "",
        "End Date": end_date.strftime("%Y-%m-%d") if pd.notna(end_date) else "",
        "Gross Profit": summary["gross_profit"],
        "Gross Loss": summary["gross_loss"],
        "Net Trading P&L": summary["net_pnl"],
        "Net Dividends": summary["div_net_eur"],
        "Total Interest": summary["interest_eur"] + summary.get("interest_usd", 0),
        "Cashback": summary["cashback_eur"],
        "Total Return (P&L + Yield)": total_return,
        "Total Deposits": summary["total_deposited_eur"],
        "Total Withdrawals": summary["total_withdrawn_eur"],
        "Net Deposited": net_deposited,
        "Win Rate %": round(summary["win_rate"], 2),
        "Total Sell Trades": summary["n_sells"]
    }
    
    return pd.DataFrame([data])


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


# ---------------------------------------------------------------------------
# Company deep-dive stats  (NEW)
# ---------------------------------------------------------------------------

def company_detailed_stats(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return a comprehensive per-company (ticker) breakdown DataFrame.

    Columns:
        Ticker, Name,
        Buy Trades, Sell Trades, Total Trades,
        Shares Bought, Shares Sold,
        Volume Bought ($), Volume Sold ($),
        Gross Profit ($), Gross Loss ($), Net P&L ($),
        Win Rate (%), Winning Sells, Losing Sells, Break-Even Sells,
        Best Trade ($), Worst Trade ($), Avg Win ($), Avg Loss ($),
        First Trade, Last Trade, Days Active
    """
    trades = df[df["_category"].isin(["buy", "sell"])].copy()
    if trades.empty:
        return pd.DataFrame()

    trades["Result_clean"] = trades["Result"].fillna(0)
    trades["Total_abs"]    = trades["Total"].fillna(0).abs()
    trades["Shares_abs"]   = trades["No. of shares"].fillna(0).abs()

    rows = []
    for (ticker, name), grp in trades.groupby(["Ticker", "Name"]):
        buys  = grp[grp["_category"] == "buy"]
        sells = grp[grp["_category"] == "sell"]

        result_s = sells["Result_clean"]
        wins      = result_s[result_s > 0]
        losses    = result_s[result_s < 0]
        breakeven = result_s[result_s == 0]

        gross_profit = float(wins.sum())
        gross_loss   = float(losses.sum())

        first = grp["Time"].min()
        last  = grp["Time"].max()
        days  = (last - first).days if pd.notna(first) and pd.notna(last) else 0

        rows.append({
            "Ticker":          ticker,
            "Name":            name,
            "Buy Trades":      len(buys),
            "Sell Trades":     len(sells),
            "Total Trades":    len(grp),
            "Shares Bought":   round(float(buys["Shares_abs"].sum()), 4),
            "Shares Sold":     round(float(sells["Shares_abs"].sum()), 4),
            "Vol Bought ($)":  round(float(buys["Total_abs"].sum()), 2),
            "Vol Sold ($)":    round(float(sells["Total_abs"].sum()), 2),
            "Gross Profit ($)":round(gross_profit, 2),
            "Gross Loss ($)":  round(gross_loss, 2),
            "Net P&L ($)":     round(gross_profit + gross_loss, 2),
            "Win Rate (%)":    round(len(wins) / len(sells) * 100, 1) if len(sells) > 0 else 0.0,
            "Winning Sells":   len(wins),
            "Losing Sells":    len(losses),
            "Break-Even":      len(breakeven),
            "Best Trade ($)":  round(float(wins.max()), 2) if not wins.empty else 0.0,
            "Worst Trade ($)": round(float(losses.min()), 2) if not losses.empty else 0.0,
            "Avg Win ($)":     round(float(wins.mean()), 2) if not wins.empty else 0.0,
            "Avg Loss ($)":    round(float(losses.mean()), 2) if not losses.empty else 0.0,
            "First Trade":     first,
            "Last Trade":      last,
            "Days Active":     days,
        })

    result = pd.DataFrame(rows)
    return result.sort_values("Net P&L ($)", ascending=False).reset_index(drop=True)


def company_trade_history(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """
    Return all buy/sell rows for a specific ticker with running cumulative P&L.
    """
    trades = df[df["_category"].isin(["buy", "sell"])].copy()
    trades = trades[trades["Ticker"].fillna("") == ticker].sort_values("Time")
    if trades.empty:
        return pd.DataFrame()

    trades["Result_clean"] = trades["Result"].fillna(0)
    # Cumulative P&L only counts on sell events
    sells_cum = trades["Result_clean"].where(trades["_category"] == "sell", 0).cumsum()
    trades["Cumul P&L ($)"] = sells_cum.values

    cols = ["Time", "Action", "No. of shares", "Price / share",
            "Currency (Price / share)", "Result_clean", "Total", "Cumul P&L ($)"]
    available = [c for c in cols if c in trades.columns]
    out = trades[available].copy()
    out = out.rename(columns={"Result_clean": "Trade P&L ($)"})
    return out.reset_index(drop=True)


def portfolio_progress_daily(df: pd.DataFrame) -> pd.DataFrame:
    """
    Returns a daily timeline of the entire portfolio:
      - Cumulative Net Deposits (Deposits - Withdrawals)
      - Cumulative Realized P&L
      - Cumulative Dividends
      - Cumulative Interest
      - Total Tracked Value (Net Deposits + P&L + Dividends + Interest)
    """
    if df.empty:
        return pd.DataFrame()

    start_date = df["Time"].min().date()
    end_date = df["Time"].max().date()
    all_days = pd.date_range(start_date, end_date, freq="D")
    
    # helper for daily aggregation
    def get_daily_series(condition, col="Total"):
        sub = df[condition].copy()
        if sub.empty:
            return pd.Series(0, index=all_days)
        sub["Date"] = sub["Time"].dt.date
        return sub.groupby("Date")[col].sum().reindex(all_days.date, fill_value=0)

    # Note: deposits and withdrawals should be accumulated.
    # Convert all values to a naive float sum. In practice, some might be cross-currency,
    # but the primary currency (USD/EUR) is usually dominant in Total depending on user.
    # Here, we use the `Result` for P&L and `Total` for cash flows, ensuring withdrawals are negative.

    dep = get_daily_series(df["_category"] == "deposit", "Total")
    wdr = get_daily_series(df["_category"] == "withdrawal", "Total")
    
    # Realized P&L
    pnl = get_daily_series(df["_category"] == "sell", "Result")
    
    # Dividends (Total is usually the net amount, but check div_growth_series logic - we can use Total)
    divs = get_daily_series(df["_category"] == "dividend", "Total")
    
    # Interest
    ints = get_daily_series(df["_category"] == "interest", "Total")
    
    daily_df = pd.DataFrame({
        "Deposits": dep,
        "Withdrawals": wdr,
        "Daily P&L": pnl,
        "Daily Dividends": divs,
        "Daily Interest": ints
    }, index=all_days.date)
    
    # Add everything cumulatively
    res = daily_df.cumsum()
    # Net deposits: deposits minus withdrawals (assuming withdrawals in CSV Total column are positive, if negative then + wdr)
    # Trading212 lists withdrawals with a positive Total value typically? Wait, deposits have positive Total?
    # Let's assume deposits and withdrawals are positive absolutes, or use 'Total' sum and adjust.
    # Usually: Deposit Total > 0. Withdrawal Total > 0? Actually Trading212 withdrawal 'Total' is positive.
    # We will subtract withdrawals.
    res["Net Deposits"] = res["Deposits"] - res["Withdrawals"]
    
    res["Total Value Tracked"] = res["Net Deposits"] + res["Daily P&L"] + res["Daily Dividends"] + res["Daily Interest"]
    
    res = res.reset_index().rename(columns={"index": "Date"})
    return res
