import re

with open("analyzer.py", "r") as f:
    text = f.read()

old_func = """def get_trades_table(df: pd.DataFrame) -> pd.DataFrame:
    trades = df[df["_category"].isin(["buy", "sell"])].copy()
    if trades.empty:
        return pd.DataFrame()
    cols = ["Time", "Action", "Ticker", "Name", "No. of shares",
            "Price / share", "Currency (Price / share)",
            "Result", "Currency (Result)", "Total", "Currency (Total)"]
    return trades[[c for c in cols if c in trades.columns]].sort_values("Time", ascending=False).reset_index(drop=True)"""

new_func = """def get_trades_table(df: pd.DataFrame, base_currency: str = 'USD', fx_series: pd.Series = None) -> pd.DataFrame:
    trades = df[df["_category"].isin(["buy", "sell"])].copy()
    if trades.empty:
        return pd.DataFrame()
        
    if fx_series is None:
        fx_series = pd.Series(dtype=float)

    def _to_base(row, val_col, ccy_col):
        v = float(row.get(val_col, 0) or 0)
        c = str(row.get(ccy_col, "EUR"))
        return convert_currency(v, c, base_currency, row.get("Time"), fx_series)

    trades[f"Result ({base_currency})"] = trades.apply(lambda r: _to_base(r, "Result", "Currency (Result)"), axis=1).round(2)
    trades[f"Total ({base_currency})"]  = trades.apply(lambda r: _to_base(r, "Total", "Currency (Total)"), axis=1).round(2)

    cols = ["Time", "Action", "Ticker", "Name", "No. of shares",
            "Price / share", "Currency (Price / share)",
            "Result", "Currency (Result)", f"Result ({base_currency})", 
            "Total", "Currency (Total)", f"Total ({base_currency})"]
    return trades[[c for c in cols if c in trades.columns]].sort_values("Time", ascending=False).reset_index(drop=True)"""

text = text.replace(old_func, new_func)

with open("analyzer.py", "w") as f:
    f.write(text)
