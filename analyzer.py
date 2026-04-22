"""
analyzer.py — Core data processing for broker CSV exports.

Responsible for:
  * Broker-agnostic loading (dispatches to the right adapter in `brokers/`)
  * Action classification into coarse `_category` buckets
  * Date filtering
  * P&L aggregation, win-rate classification, timeline resampling
  * Per-ticker and per-company breakdowns

Downstream (charts, app) consumes the canonical schema declared in
`brokers.canonical`; this module is the single place that translates
canonical Action strings into category buckets.
"""

import pandas as pd
import numpy as np
from datetime import date

import brokers
from brokers import canonical as _canon
from brokers.fifo import fill_revolut_result

# ---------------------------------------------------------------------------
# Action type classification
# ---------------------------------------------------------------------------

BUY_ACTIONS      = {"market buy", "limit buy"}
SELL_ACTIONS     = {"market sell", "limit sell"}
DIVIDEND_ACTIONS = {"dividend (dividend)", "dividend"}
DIVIDEND_TAX_CORRECTION_ACTIONS = {"dividend tax correction", "dividend tax (correction)"}
INTEREST_ACTIONS = {"interest on cash", "lending interest"}
DEPOSIT_ACTIONS  = {"deposit"}
WITHDRAWAL_ACTIONS = {"withdrawal"}
FX_ACTIONS       = {"currency conversion"}
STOCK_SPLIT_ACTIONS = {"stock split"}
CARD_DEBIT_ACTIONS  = {"card debit"}
CARD_CREDIT_ACTIONS = {"card credit"}
CASHBACK_ACTIONS    = {"spending cashback"}

FREQ_MAP = {
    "Daily":     "D",
    "Weekly":    "W",
    "Monthly":   "ME",
    "Quarterly": "QE",
}


def classify_action(action: str) -> str:
    a = str(action).strip().lower()
    if a in BUY_ACTIONS:                     return "buy"
    if a in SELL_ACTIONS:                    return "sell"
    if a in DIVIDEND_ACTIONS:                return "dividend"
    if a in DIVIDEND_TAX_CORRECTION_ACTIONS: return "dividend_tax_correction"
    if a in INTEREST_ACTIONS:                return "interest"
    if a in DEPOSIT_ACTIONS:                 return "deposit"
    if a in WITHDRAWAL_ACTIONS:              return "withdrawal"
    if a in FX_ACTIONS:                      return "fx_conversion"
    if a in STOCK_SPLIT_ACTIONS:             return "stock_split"
    if a in CARD_DEBIT_ACTIONS:              return "card_debit"
    if a in CARD_CREDIT_ACTIONS:             return "card_credit"
    if a in CASHBACK_ACTIONS:                return "cashback"
    return "other"


# ---------------------------------------------------------------------------
# CSV loading
# ---------------------------------------------------------------------------

def load_csv(uploaded_file) -> pd.DataFrame:
    """Detect the broker, parse, normalize to canonical schema, attach _category."""
    df = brokers.load(uploaded_file)
    df[_canon.COL_CATEGORY] = df[_canon.COL_ACTION].apply(classify_action)
    return df


def load_csvs(uploaded_files) -> pd.DataFrame:
    """
    Load and merge multiple CSV exports, de-duplicating robustly.

    Broker exports can overlap in time (e.g. Dec 31 appears in both a 2025
    file and a 2026 file).  De-duplication runs in two passes and is
    **scoped per broker** so a T212 row and a Revolut row that happen to
    share identical values can never collide.

    Pass 1 — ID-based (covers trades, deposits, interest, cashback, FX, etc.
        for brokers that emit an ID column — currently only Trading212).

    Pass 2 — Content fingerprint for rows without an ID.
        Fingerprint = (Time, Action, ISIN or Ticker, No. of shares, Total, _broker)
        Two rows with identical fingerprints on the same instant cannot be
        different transactions, so the duplicate is dropped.

    After deduplication we run the FIFO pass so Revolut sells get a
    realized-P&L `Result` value (T212 rows already have it from the broker).
    """
    frames = [load_csv(f) for f in uploaded_files]
    combined = pd.concat(frames, ignore_index=True)

    # Guarantee ID and _broker exist even if all files were Revolut
    if _canon.COL_ID not in combined.columns:
        combined[_canon.COL_ID] = pd.NA
    if _canon.COL_BROKER not in combined.columns:
        combined[_canon.COL_BROKER] = "unknown"

    # Pass 1: deduplicate by (ID, _broker) for rows that have an ID.
    has_id = (combined[_canon.COL_ID].notna()
              & (combined[_canon.COL_ID].astype(str).str.strip() != ""))
    with_id    = combined[has_id].copy()
    without_id = combined[~has_id].copy()
    if not with_id.empty:
        with_id = with_id.drop_duplicates(subset=[_canon.COL_ID, _canon.COL_BROKER])

    # Pass 2: content fingerprint for rows without an ID.
    # Revolut lacks ISIN, so we fall back to Ticker to keep the fingerprint
    # discriminating enough.
    if not without_id.empty:
        isin_or_ticker = (
            without_id[_canon.COL_ISIN]
            .where(without_id[_canon.COL_ISIN].notna(), without_id[_canon.COL_TICKER])
        )
        without_id = without_id.assign(_fp_isin_or_ticker=isin_or_ticker)
        fp_cols = [
            _canon.COL_TIME,
            _canon.COL_ACTION,
            "_fp_isin_or_ticker",
            _canon.COL_SHARES,
            _canon.COL_TOTAL,
            _canon.COL_BROKER,
        ]
        fp_available = [c for c in fp_cols if c in without_id.columns]
        if fp_available:
            without_id = without_id.drop_duplicates(subset=fp_available)
        without_id = without_id.drop(columns=["_fp_isin_or_ticker"], errors="ignore")

    combined = pd.concat([with_id, without_id], ignore_index=True)
    combined = combined.sort_values(_canon.COL_TIME).reset_index(drop=True)

    # Fill realized P&L on Revolut sells via FIFO (no-op on T212 rows).
    combined = fill_revolut_result(combined)

    return combined


# ---------------------------------------------------------------------------
# Date filtering
# ---------------------------------------------------------------------------

def filter_by_date(df: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
    start_ts = pd.Timestamp(start)
    end_ts   = pd.Timestamp(end) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    return df[(df["Time"] >= start_ts) & (df["Time"] <= end_ts)].copy()


def classify_trades_for_winrate(sells_df: pd.DataFrame) -> pd.DataFrame:
    """
    Appends boolean integer columns 'is_win', 'is_loss', and 'is_valid_trade'
    to the sells dataframe. Tiny fractional losses (>-0.50 cash OR >-0.025% ROI)
    are strictly excluded from being categorized as a loss or a valid trade,
    protecting the win rate engine from auto-invest pie rebalancing spam.
    """
    df = sells_df.copy()
    if df.empty:
        df["is_win"] = 0
        df["is_loss"] = 0
        df["is_valid_trade"] = 0
        return df

    res = df.get("Result_clean", df.get("Result", pd.Series(0, index=df.index))).fillna(0)
    tot = df["Total"].fillna(0).abs()
    
    init_val = tot - res
    pct = np.where(init_val > 0, res / init_val, 0)
    
    is_win = (res > 0)
    is_raw_loss = (res < 0)
    
    # A loss is 'tiny' if it lost less than $0.50 OR lost less than 0.025%
    is_tiny_loss = is_raw_loss & ((res >= -0.50) | (pct >= -0.00025))
    is_genuine_loss = is_raw_loss & (~is_tiny_loss)
    
    df["is_win"] = is_win.astype(int)
    df["is_loss"] = is_genuine_loss.astype(int)
    df["is_valid_trade"] = (is_win | is_genuine_loss).astype(int)
    return df

# ---------------------------------------------------------------------------
# Summary aggregation
# ---------------------------------------------------------------------------

def compute_summary(df: pd.DataFrame) -> dict:
    sells      = df[df["_category"] == "sell"].copy()
    buys       = df[df["_category"] == "buy"].copy()
    dividends  = df[df["_category"] == "dividend"].copy()
    div_tax_corrections = df[df["_category"] == "dividend_tax_correction"].copy()
    stock_splits = df[df["_category"] == "stock_split"].copy()
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
    div_withholding = float(dividends.get("Withholding tax", pd.Series(dtype=float)).fillna(0).abs().sum())
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

    # Revolut-specific: dividend-tax corrections net out in most cases but
    # surface the total so the Dividends tab can show it separately.
    div_tax_correction_total = float(div_tax_corrections["Total"].fillna(0).sum())

    # Calculate aggregate fees
    fee_cols = [
        "Withholding tax", "Finra fee", "Currency conversion fee",
        "French transaction tax", "Stamp duty reserve tax", "UK PTM Levy"
    ]
    fees_breakdown = {}
    total_fees = 0.0
    for col in fee_cols:
        val = float(df.get(col, pd.Series(dtype=float)).fillna(0).abs().sum())
        if val > 0:
            fees_breakdown[col] = val
            total_fees += val

    sells_validated   = classify_trades_for_winrate(sells)
    n_sells           = len(sells)
    n_wins            = int(sells_validated["is_win"].sum()) if not sells_validated.empty else 0
    n_losses          = int(sells_validated["is_loss"].sum()) if not sells_validated.empty else 0
    n_valid_sells     = int(sells_validated["is_valid_trade"].sum()) if not sells_validated.empty else 0

    result = {
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "net_pnl": net_pnl,
        "n_buys": len(buys),
        "n_sells": n_sells,
        "n_winning_trades": n_wins,
        "n_losing_trades": n_losses,
        "win_rate": (n_wins / n_valid_sells * 100) if n_valid_sells > 0 else 0.0,
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
        "fees_breakdown": fees_breakdown,
        "total_fees": total_fees,
        "div_tax_correction_total": div_tax_correction_total,
        "n_div_tax_corrections": len(div_tax_corrections),
        "n_stock_splits": len(stock_splits),
        "brokers": sorted(df.get("_broker", pd.Series(dtype=str)).dropna().unique().tolist()),
    }

    # Attach MWRR metrics
    mwrr = compute_mwrr(df)
    result.update(mwrr)
    return result


# ---------------------------------------------------------------------------
# MWRR (Money-Weighted Rate of Return) — IRR Engine
# ---------------------------------------------------------------------------

def _solve_irr_annual(cashflows_yearly: list, tol: float = 1e-9) -> float:
    """
    Solve for the annualized IRR directly.

    cashflows_yearly: list of (years_from_start: float, amount: float)
        Negative = money IN (deposits), Positive = money OUT or terminal value.

    Works in annualized rate space so the search domain stays human-readable:
    bisection is bounded to [-99%, +1000%] annual, preventing the astronomical
    compounding that happens when working in daily rates on short periods.

    Uses multi-start Newton-Raphson (low / mid / high seeds) then falls back
    to bisection if none converge within the bounded window.
    """
    if not cashflows_yearly:
        return 0.0

    def npv(r):
        # Guard: r must be > -1 to avoid (1+r)^t on negative base
        if r <= -1.0:
            return float("inf")
        return sum(cf / (1.0 + r) ** t for t, cf in cashflows_yearly)

    def npv_deriv(r):
        if r <= -1.0:
            return float("inf")
        return sum(-t * cf / (1.0 + r) ** (t + 1.0) for t, cf in cashflows_yearly)

    # Multi-start Newton-Raphson with three seeds
    for guess in (0.10, 0.50, -0.10):
        r = guess
        converged = False
        for _ in range(300):
            f  = npv(r)
            fp = npv_deriv(r)
            if abs(fp) < 1e-14:
                break
            step = f / fp
            r_new = r - step
            # Keep within sane annual bounds
            r_new = max(-0.9999, min(r_new, 10.0))
            if abs(r_new - r) < tol:
                r = r_new
                converged = True
                break
            r = r_new
        if converged and -0.9999 < r < 10.0:
            # Sanity-check: NPV at solution should be near zero
            if abs(npv(r)) < 1.0:          # $1 tolerance is fine for typical portfolios
                return r

    # Bisection fallback — bounded to [-99%, +1000%]
    lo, hi = -0.99, 10.0
    npv_lo = npv(lo)
    npv_hi = npv(hi)

    if npv_lo * npv_hi > 0:
        # No bracketed root → fall back to 0 (caller uses simple return)
        return float("nan")

    for _ in range(600):
        mid = (lo + hi) / 2.0
        if npv(mid) * npv_lo < 0:
            hi = mid
        else:
            lo = mid
            npv_lo = npv(lo)
        if abs(hi - lo) < tol:
            break

    return (lo + hi) / 2.0


def compute_mwrr(df: pd.DataFrame) -> dict:
    """
    Compute portfolio-level Money-Weighted Rate of Return (MWRR / portfolio IRR).

    Cash-flow convention (IRR standard):
      • Deposits    → negative (money flowing INTO the portfolio)
      • Withdrawals → positive (money flowing OUT)
      • Terminal value → positive cash flow at the end of the period

    Terminal value = net_deposits + realized_pnl + dividends + interest.
    All amounts are treated as USD.

    Annualized MWRR is only meaningful for periods ≥ 180 days; for shorter
    windows it is set to None and the UI shows "N/A (< 6 mo)" instead.
    """
    empty = {
        "mwrr_annual_pct": None,          # None = not enough history to annualize
        "mwrr_total_pct": 0.0,
        "terminal_value": 0.0,
        "total_invested": 0.0,
        "days_invested": 0,
    }

    if df.empty:
        return empty

    deposits    = df[df["_category"] == "deposit"].copy()
    withdrawals = df[df["_category"] == "withdrawal"].copy()
    card_debits = df[df["_category"] == "card_debit"].copy()

    if deposits.empty:
        return empty

    t0    = df["Time"].min()
    t_end = df["Time"].max()
    days_total  = max((t_end - t0).total_seconds() / 86400.0, 1.0)
    years_total = days_total / 365.0

    # The rest of the dashboard standardizes on 1 USD = 0.86 EUR
    EUR_TO_USD = 1.0 / 0.86

    def to_usd(amount, ccy):
        return float(amount) * EUR_TO_USD if str(ccy).strip().upper() == "EUR" else float(amount)

    # Build cash-flow list in YEARS (not days) so the solver works in annual space
    cf_years = []

    for _, row in deposits.iterrows():
        yrs = (row["Time"] - t0).total_seconds() / (86400.0 * 365.0)
        val = to_usd(row.get("Total", 0) or 0, row.get("Currency (Total)", "EUR"))
        cf_years.append((yrs, -abs(val)))

    for _, row in withdrawals.iterrows():
        yrs = (row["Time"] - t0).total_seconds() / (86400.0 * 365.0)
        val = to_usd(row.get("Total", 0) or 0, row.get("Currency (Total)", "EUR"))
        cf_years.append((yrs, abs(val)))

    for _, row in card_debits.iterrows():
        yrs = (row["Time"] - t0).total_seconds() / (86400.0 * 365.0)
        val = to_usd(row.get("Total", 0) or 0, row.get("Currency (Total)", "EUR"))
        cf_years.append((yrs, abs(val)))

    # Compute terminal value (in USD)
    total_deposited  = sum(abs(to_usd(row.get("Total", 0) or 0, row.get("Currency (Total)", "EUR"))) for _, row in deposits.iterrows())
    total_withdrawn  = sum(abs(to_usd(row.get("Total", 0) or 0, row.get("Currency (Total)", "EUR"))) for _, row in withdrawals.iterrows())
    total_card_spent = sum(abs(to_usd(row.get("Total", 0) or 0, row.get("Currency (Total)", "EUR"))) for _, row in card_debits.iterrows())
    net_deposits     = total_deposited - total_withdrawn - total_card_spent

    sells            = df[df["_category"] == "sell"]
    realized_pnl     = sum(to_usd(row.get("Result", 0) or 0, row.get("Currency (Result)")) for _, row in sells.iterrows())

    dividends        = df[df["_category"] == "dividend"]
    div_total        = sum(to_usd(row.get("Total", 0) or 0, row.get("Currency (Total)", "EUR")) for _, row in dividends.iterrows())

    interests        = df[df["_category"] == "interest"]
    int_total        = sum(to_usd(row.get("Total", 0) or 0, row.get("Currency (Total)", "EUR")) for _, row in interests.iterrows())

    terminal = net_deposits + realized_pnl + div_total + int_total

    # Terminal value as the closing positive cash flow
    cf_years.append((years_total, terminal))

    # Simple total return % — always reliable, used as fallback
    simple_total_pct = (
        (terminal - net_deposits) / net_deposits * 100
        if net_deposits > 0 else 0.0
    )

    # --- Solve ---
    try:
        annual_r = _solve_irr_annual(cf_years)

        if (
            np.isnan(annual_r)
            or not np.isfinite(annual_r)
            or annual_r < -0.999
            or annual_r > 9.99     # > 999% annual is almost certainly a solver artefact
        ):
            # Fall back to simple annualization
            annual_r = (1.0 + simple_total_pct / 100.0) ** (1.0 / years_total) - 1.0

        total_r = (1.0 + annual_r) ** years_total - 1.0

        # Final guard: if total_r disagrees badly with simple_total fallback,
        # trust the simple number (protects against very short periods)
        if net_deposits > 0 and abs(total_r * 100 - simple_total_pct) > max(50.0, abs(simple_total_pct) * 2):
            annual_r = (1.0 + simple_total_pct / 100.0) ** (1.0 / years_total) - 1.0
            total_r  = simple_total_pct / 100.0

    except Exception:
        total_r  = simple_total_pct / 100.0
        annual_r = (1.0 + total_r) ** (1.0 / years_total) - 1.0 if years_total > 0 else 0.0

    # Annualized is only meaningful for periods ≥ 180 days
    annual_pct = round(annual_r * 100, 2) if days_total >= 180 else None

    return {
        "mwrr_annual_pct": annual_pct,
        "mwrr_total_pct":  round(total_r * 100, 2),
        "terminal_value":  round(terminal, 2),
        "total_invested":  round(total_deposited, 2),
        "days_invested":   int(days_total),
    }



def mwrr_cumulative_timeline(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute a daily cumulative return % curve.

    For each day, we compute the running terminal value and the running
    total invested, giving a simple cumulative return percentage.
    This provides a smooth growth curve that reflects how the portfolio
    value has evolved relative to capital deployed.
    """
    if df.empty:
        return pd.DataFrame()

    start_date = df["Time"].min().date()
    end_date = df["Time"].max().date()
    all_days = pd.date_range(start_date, end_date, freq="D")

    EUR_TO_USD = 1.0 / 0.86

    def daily_agg(condition, col="Total", force_abs=False):
        sub = df[condition].copy()
        if sub.empty:
            return pd.Series(0, index=all_days)
        sub["Date"] = sub["Time"].dt.date
        if force_abs:
            sub[col] = sub[col].abs()
        
        # Apply currency conversion
        def to_usd(row):
            ccy = row.get("Currency (Total)", "EUR") if col == "Total" else row.get("Currency (Result)", "USD")
            val = float(row.get(col, 0) or 0)
            return val * EUR_TO_USD if str(ccy).strip().upper() == "EUR" else val
        
        sub["_val_usd"] = sub.apply(to_usd, axis=1)
        return sub.groupby("Date")["_val_usd"].sum().reindex(all_days.date, fill_value=0)

    dep = daily_agg(df["_category"] == "deposit", force_abs=True).cumsum()
    wdr = daily_agg(df["_category"] == "withdrawal", force_abs=True).cumsum()
    crd = daily_agg(df["_category"] == "card_debit", force_abs=True).cumsum()
    pnl = daily_agg(df["_category"] == "sell", col="Result").cumsum()
    divs = daily_agg(df["_category"] == "dividend").cumsum()
    ints = daily_agg(df["_category"] == "interest").cumsum()

    net_dep = dep - wdr - crd
    terminal = net_dep + pnl + divs + ints
    gains = pnl + divs + ints  # total gains component

    # Return % = gains / capital deployed so far, where capital = cumulative deposits
    # Use dep (total deposited) as denominator to avoid division by small net_dep values
    return_pct = np.where(dep > 0, gains / dep * 100, 0.0)

    result = pd.DataFrame({
        "Date": all_days.date,
        "Cumul Deposits ($)": dep.values,
        "Net Deposits ($)": net_dep.values,
        "Cumul P&L ($)": pnl.values,
        "Cumul Dividends ($)": divs.values,
        "Cumul Interest ($)": ints.values,
        "Total Gains ($)": gains.values,
        "Terminal Value ($)": terminal.values,
        "Return %": return_pct,
    })

    return result


import io

def export_portfolio_excel(df: pd.DataFrame, summary: dict, start_date, end_date) -> bytes:
    """
    Creates a professionally formatted multi-sheet Excel file (.xlsx) in memory.
    Sheet 1: High-level Portfolio Total Overview
    Sheet 2: Month-by-Month Performance History
    """
    net_deposited = summary["total_deposited_eur"] - summary["total_withdrawn_eur"] - summary.get("total_card_spent_eur", 0)
    total_return = summary["net_pnl"] + summary["div_net_eur"] + summary["interest_eur"] + summary.get("interest_usd", 0) + summary["cashback_eur"]
    
    # Overview Data
    overview_data = {
        "Metric": [
            "Start Date", "End Date",
            "Total Deposits (€)", "Total Withdrawals (€)", "Net Deposited (€)",
            "Gross Profit ($)", "Gross Loss ($)", "Net Trading P&L ($)", 
            "Win Rate (%)", "Total Sell Trades",
            "Gross Dividends (€)", "Withholding Tax (€)", "Net Dividends (€)",
            "Total Interest (EUR + USD eq.)", "Cashback (€)",
            "Total Return (P&L + Yield)"
        ],
        "Value": [
            start_date.strftime("%Y-%m-%d") if pd.notna(start_date) else "",
            end_date.strftime("%Y-%m-%d") if pd.notna(end_date) else "",
            summary["total_deposited_eur"], summary["total_withdrawn_eur"], net_deposited,
            summary["gross_profit"], summary["gross_loss"], summary["net_pnl"],
            round(summary["win_rate"], 2), summary["n_sells"],
            summary["div_gross_eur"], summary["div_withholding_eur"], summary["div_net_eur"],
            summary["interest_eur"] + summary.get("interest_usd", 0), summary["cashback_eur"],
            total_return
        ]
    }
    df_overview = pd.DataFrame(overview_data)
    
    # Monthly Data (Add Deposits/Withdrawals to the standard monthly view)
    df_monthly = monthly_summary(df).copy()
    
    # Calculate monthly deposits/withdrawals
    deposits = df[df["_category"] == "deposit"].copy()
    withdrawals = df[df["_category"] == "withdrawal"].copy()
    
    dep_monthly = deposits.groupby(deposits["Time"].dt.to_period("M"))["Total"].sum() if not deposits.empty else pd.Series()
    wdr_monthly = withdrawals.groupby(withdrawals["Time"].dt.to_period("M"))["Total"].sum() if not withdrawals.empty else pd.Series()
    
    # Add to df_monthly seamlessly
    df_monthly["Deposits (€)"] = df_monthly["Month"].map(lambda m: dep_monthly.get(pd.Period(m, freq='M'), 0.0))
    df_monthly["Withdrawals (€)"] = df_monthly["Month"].map(lambda m: wdr_monthly.get(pd.Period(m, freq='M'), 0.0))
    df_monthly["Net Monthly Deposited (€)"] = df_monthly["Deposits (€)"] - df_monthly["Withdrawals (€)"]

    # Reorder columns for readability
    month_cols = ["Month", "Deposits (€)", "Withdrawals (€)", "Net Monthly Deposited (€)", 
                  "Profit", "Loss", "Net P&L", "Dividends (EUR)", "Interest"]
    df_monthly = df_monthly[[c for c in month_cols if c in df_monthly.columns]]

    # Write to Excel BytesIO
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # Sheet 1: Overview
        df_overview.to_excel(writer, sheet_name='Portfolio Summary', index=False)
        worksheet1 = writer.sheets['Portfolio Summary']
        worksheet1.set_column('A:A', 30)
        worksheet1.set_column('B:B', 20)
        
        # Add basic formatting
        workbook = writer.book
        money_fmt = workbook.add_format({'num_format': '#,##0.00'})
        worksheet1.set_column('B:B', 20, money_fmt)
        
        # Sheet 2: Monthly Performance
        df_monthly.to_excel(writer, sheet_name='Monthly Performance', index=False)
        worksheet2 = writer.sheets['Monthly Performance']
        worksheet2.set_column('A:A', 15)
        worksheet2.set_column('B:I', 18, money_fmt)
        
        # Freeze top row
        worksheet1.freeze_panes(1, 0)
        worksheet2.freeze_panes(1, 0)

    return output.getvalue()


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
    sells = classify_trades_for_winrate(sells)

    agg = sells.resample(freq).agg(
        period_pnl=("Result", "sum"),
        wins=("is_win", "sum"),
        losses=("is_loss", "sum"),
        valid_trades=("is_valid_trade", "sum"),
        trades=("Result", "count"),
    ).reset_index()
    agg = agg.rename(columns={
        "Time":       "Period",
        "period_pnl": "Period P&L", "wins": "Wins", "losses": "Losses",
        "trades":     "Trades",     "valid_trades": "Valid Trades",
    })
    
    agg["Cumulative P&L"] = agg["Period P&L"].cumsum()
    # Running win rate
    agg["Cumul Wins"]   = agg["Wins"].cumsum()
    agg["Cumul Valid"]  = agg["Valid Trades"].cumsum()
    agg["Cumul Trades"] = agg["Trades"].cumsum()
    agg["Win Rate %"]   = (agg["Cumul Wins"] / agg["Cumul Valid"].replace(0, np.nan) * 100).round(1)

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
    divs["Withholding (EUR)"] = divs.get("Withholding tax", pd.Series(0, index=divs.index)).fillna(0).abs()
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
        wins_series = result_s[result_s > 0]
        losses_series = result_s[result_s < 0]

        if len(sells) > 0:
            df_win = classify_trades_for_winrate(sells)
            wins_count = int(df_win["is_win"].sum())
            losses_count = int(df_win["is_loss"].sum())
            valid_count = int(df_win["is_valid_trade"].sum())
            winrate = round(wins_count / valid_count * 100, 1) if valid_count > 0 else 0.0
        else:
            wins_count = losses_count = breakeven_count = 0
            winrate = 0.0

        breakeven_count = len(sells) - wins_count - losses_count

        gross_profit = float(wins_series.sum()) if not wins_series.empty else 0.0
        gross_loss   = float(losses_series.sum()) if not losses_series.empty else 0.0

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
            "Win Rate (%)":    winrate,
            "Winning Sells":   wins_count,
            "Losing Sells":    losses_count,
            "Break-Even":      breakeven_count,
            "Best Trade ($)":  round(float(wins_series.max()), 2) if not wins_series.empty else 0.0,
            "Worst Trade ($)": round(float(losses_series.min()), 2) if not losses_series.empty else 0.0,
            "Avg Win ($)":     round(float(wins_series.mean()), 2) if not wins_series.empty else 0.0,
            "Avg Loss ($)":    round(float(losses_series.mean()), 2) if not losses_series.empty else 0.0,
            "First Trade":     first,
            "Last Trade":      last,
            "Days Active":     days,
        })

    result = pd.DataFrame(rows)
    result = result.sort_values("Net P&L ($)", ascending=False).reset_index(drop=True)

    # Return Contribution (%): each ticker's share of total realized P&L,
    # used to show how much each position contributed to overall portfolio return.
    total_pnl = result["Net P&L ($)"].sum()
    if total_pnl != 0:
        result["Return Contribution (%)"] = (result["Net P&L ($)"] / total_pnl * 100).round(2)
    else:
        result["Return Contribution (%)"] = 0.0

    return result


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
    def get_daily_series(condition, col="Total", force_abs=False):
        sub = df[condition].copy()
        if sub.empty:
            return pd.Series(0, index=all_days)
        sub["Date"] = sub["Time"].dt.date
        if force_abs:
            sub[col] = sub[col].abs()
        return sub.groupby("Date")[col].sum().reindex(all_days.date, fill_value=0)

    # Note: deposits and withdrawals should be accumulated.
    # Convert all values to a naive float sum. In practice, some might be cross-currency,
    # but the primary currency (USD/EUR) is usually dominant in Total depending on user.
    # Here, we use the `Result` for P&L and `Total` for cash flows, ensuring withdrawals are negative.

    dep = get_daily_series(df["_category"] == "deposit", "Total", force_abs=True)
    wdr = get_daily_series(df["_category"] == "withdrawal", "Total", force_abs=True)
    crd = get_daily_series(df["_category"] == "card_debit", "Total", force_abs=True)
    
    # Realized P&L
    pnl = get_daily_series(df["_category"] == "sell", "Result")
    
    # Dividends (Total is usually the net amount, but check div_growth_series logic - we can use Total)
    divs = get_daily_series(df["_category"] == "dividend", "Total")
    
    # Interest
    ints = get_daily_series(df["_category"] == "interest", "Total")
    
    daily_df = pd.DataFrame({
        "Deposits": dep,
        "Withdrawals": wdr,
        "Card_Spending": crd,
        "Daily P&L": pnl,
        "Daily Dividends": divs,
        "Daily Interest": ints
    }, index=all_days.date)
    
    # Add everything cumulatively
    res = daily_df.cumsum()
    # Net deposits: deposits minus withdrawals minus card spending
    res["Net Deposits"] = res["Deposits"] - res["Withdrawals"] - res["Card_Spending"]
    
    res["Total Value Tracked"] = res["Net Deposits"] + res["Daily P&L"] + res["Daily Dividends"] + res["Daily Interest"]
    
    res = res.reset_index().rename(columns={"index": "Date"})
    return res


# ---------------------------------------------------------------------------
# Card Spending Deep Dive Extracts
# ---------------------------------------------------------------------------
def card_spending_deepdive(df: pd.DataFrame) -> dict:
    """
    Returns dataframes grouped by merchant, category, and monthly timeline
    specifically for elements marked as 'card_debit'.
    Note: 'Total' on debits is negative. We take abs() for charting.
    """
    debits = df[df["_category"] == "card_debit"].copy()
    if debits.empty:
        return {
            "monthly": pd.DataFrame(), "categories": pd.DataFrame(), 
            "merchants": pd.DataFrame(), "total_spent_raw": 0.0, 
            "total_txns": 0, "avg_txn": 0.0
        }
        
    # 1. Timeline (Monthly Spending)
    debits["Month"] = debits["Time"].dt.to_period("M").dt.to_timestamp()
    monthly = debits.groupby("Month")["Total"].sum().abs().reset_index()
    monthly.rename(columns={"Total": "Amount"}, inplace=True)
    
    # 2. Categories
    cat_col = "Merchant category" if "Merchant category" in debits.columns else "Category"
    if cat_col in debits.columns:
        cat_df = debits.groupby(cat_col)["Total"].sum().abs().reset_index()
        cat_df.rename(columns={"Total": "Amount", cat_col: "Category"}, inplace=True)
        cat_df = cat_df.sort_values(by="Amount", ascending=False)
    else:
        cat_df = pd.DataFrame(columns=["Category", "Amount"])

    # 3. Merchants
    merch_col = "Merchant name" if "Merchant name" in debits.columns else "Merchant"
    if merch_col in debits.columns:
        merch_df = debits.groupby(merch_col)["Total"].sum().abs().reset_index()
        merch_df.rename(columns={"Total": "Amount", merch_col: "Merchant"}, inplace=True)
        merch_df = merch_df.sort_values(by="Amount", ascending=False)
    else:
        merch_df = pd.DataFrame(columns=["Merchant", "Amount"])

    total_spent = float(debits["Total"].sum())
    
    return {
        "monthly": monthly,
        "categories": cat_df,
        "merchants": merch_df,
        "total_spent_raw": abs(total_spent),
        "total_txns": len(debits),
        "avg_txn": abs(float(debits["Total"].mean()))
    }

