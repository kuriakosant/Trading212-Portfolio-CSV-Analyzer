import re

with open("analyzer.py", "r") as f:
    text = f.read()

old_func = """def company_detailed_stats(df: pd.DataFrame) -> pd.DataFrame:
    \"\"\"
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
    \"\"\"
    trades = df[df["_category"].isin(["buy", "sell"])].copy()
    if trades.empty:
        return pd.DataFrame()

    trades["Result_clean"] = trades["Result"].fillna(0)
    trades["Total_abs"]    = trades["Total"].fillna(0).abs()
    trades["Shares_abs"]   = trades["No. of shares"].fillna(0).abs()"""

new_func = """def company_detailed_stats(df: pd.DataFrame, base_currency: str = 'USD', fx_series: pd.Series = None) -> pd.DataFrame:
    \"\"\"
    Return a comprehensive per-company (ticker) breakdown DataFrame.
    \"\"\"
    trades = df[df["_category"].isin(["buy", "sell"])].copy()
    if trades.empty:
        return pd.DataFrame()

    if fx_series is None: fx_series = pd.Series(dtype=float)

    def _to_base(row, val_col, ccy_col):
        v = float(row.get(val_col, 0) or 0)
        c = str(row.get(ccy_col, "EUR"))
        return convert_currency(v, c, base_currency, row.get("Time"), fx_series)

    trades["Result_clean"] = trades.apply(lambda r: _to_base(r, "Result", "Currency (Result)"), axis=1).fillna(0)
    trades["Total_abs"]    = trades.apply(lambda r: _to_base(r, "Total", "Currency (Total)"), axis=1).fillna(0).abs()
    trades["Shares_abs"]   = trades["No. of shares"].fillna(0).abs()"""

text = text.replace(old_func, new_func)

old_return = """        rows.append({
            "Ticker": ticker,
            "Name": name,
            "Buy Trades": len(buys),
            "Sell Trades": len(sells),
            "Total Trades": len(grp),
            "Shares Bought": round(float(buys["Shares_abs"].sum()), 4),
            "Shares Sold": round(float(sells["Shares_abs"].sum()), 4),
            "Volume Bought ($)": round(float(buys["Total_abs"].sum()), 2),
            "Volume Sold ($)": round(float(sells["Total_abs"].sum()), 2),
            "Gross Profit ($)": round(gross_profit, 2),
            "Gross Loss ($)": round(abs(gross_loss), 2),
            "Net P&L ($)": round(gross_profit + gross_loss, 2),
            "Win Rate (%)": winrate,
            "Winning Sells": wins_count,
            "Losing Sells": losses_count,
            "Break-Even Sells": breakeven_count,
            "Best Trade ($)": round(float(wins_series.max() if not wins_series.empty else 0.0), 2),
            "Worst Trade ($)": round(float(losses_series.min() if not losses_series.empty else 0.0), 2),
            "Avg Win ($)": round(float(wins_series.mean() if not wins_series.empty else 0.0), 2),
            "Avg Loss ($)": round(float(losses_series.mean() if not losses_series.empty else 0.0), 2),
            "First Trade": first.strftime("%Y-%m-%d"),
            "Last Trade": last.strftime("%Y-%m-%d"),
            "Days Active": days_active
        })

    res = pd.DataFrame(rows)"""

new_return = """        sym = "€" if base_currency == "EUR" else "$"
        rows.append({
            "Ticker": ticker,
            "Name": name,
            "Buy Trades": len(buys),
            "Sell Trades": len(sells),
            "Total Trades": len(grp),
            "Shares Bought": round(float(buys["Shares_abs"].sum()), 4),
            "Shares Sold": round(float(sells["Shares_abs"].sum()), 4),
            f"Volume Bought ({sym})": round(float(buys["Total_abs"].sum()), 2),
            f"Volume Sold ({sym})": round(float(sells["Total_abs"].sum()), 2),
            f"Gross Profit ({sym})": round(gross_profit, 2),
            f"Gross Loss ({sym})": round(abs(gross_loss), 2),
            f"Net P&L ({sym})": round(gross_profit + gross_loss, 2),
            "Win Rate (%)": winrate,
            "Winning Sells": wins_count,
            "Losing Sells": losses_count,
            "Break-Even Sells": breakeven_count,
            f"Best Trade ({sym})": round(float(wins_series.max() if not wins_series.empty else 0.0), 2),
            f"Worst Trade ({sym})": round(float(losses_series.min() if not losses_series.empty else 0.0), 2),
            f"Avg Win ({sym})": round(float(wins_series.mean() if not wins_series.empty else 0.0), 2),
            f"Avg Loss ({sym})": round(float(losses_series.mean() if not losses_series.empty else 0.0), 2),
            "First Trade": first.strftime("%Y-%m-%d"),
            "Last Trade": last.strftime("%Y-%m-%d"),
            "Days Active": days_active
        })

    res = pd.DataFrame(rows)"""

text = text.replace(old_return, new_return)

with open("analyzer.py", "w") as f:
    f.write(text)
