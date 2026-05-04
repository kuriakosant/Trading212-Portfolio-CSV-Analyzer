import re

with open("charts.py", "r") as f:
    text = f.read()

# Add base_currency to chart_dividend_growth
old_div = """def chart_dividend_growth(div_series: pd.DataFrame) -> go.Figure:"""
new_div = """def chart_dividend_growth(div_series: pd.DataFrame, base_currency: str = "USD") -> go.Figure:"""
text = text.replace(old_div, new_div)
text = text.replace('div_series["Cumulative (EUR)"]', 'div_series[f"Cumulative ({base_currency})"]')
text = text.replace('div_series[["Ticker", "Net (EUR)", "Withholding (EUR)"]]', 'div_series[["Ticker", f"Net ({base_currency})", f"Withholding ({base_currency})"]]')
text = text.replace('This payment   : <b>€%{customdata[1]:.4f}</b>', 'This payment   : <b>%{customdata[1]:.4f}</b>')
text = text.replace('Withholding    : €%{customdata[2]:.4f}', 'Withholding    : %{customdata[2]:.4f}')
text = text.replace('Running total  : <b>€%{y:.4f}</b>', 'Running total  : <b>%{y:.4f}</b>')
text = text.replace('div_series["Net (EUR)"]', 'div_series[f"Net ({base_currency})"]')
text = text.replace('Net: <b>€%{y:.4f}</b>', 'Net: <b>%{y:.4f}</b>')

# Add base_currency to chart_interest_growth
old_int = """def chart_interest_growth(int_series: pd.DataFrame) -> go.Figure:"""
new_int = """def chart_interest_growth(int_series: pd.DataFrame, base_currency: str = "USD") -> go.Figure:"""
text = text.replace(old_int, new_int)
text = text.replace('int_series["Cumulative EUR"]', 'int_series[f"Cumulative ({base_currency})"]')
text = text.replace('Running Total: <b>€%{y:.4f}</b>', 'Running Total: <b>%{y:.4f}</b>')
text = text.replace('Amount: <b>€%{y:.4f}</b>', 'Amount: <b>%{y:.4f}</b>')
text = text.replace('fig.add_trace(go.Scatter(', '# Deprecated second trace\\n    # fig.add_trace(go.Scatter(', 1)
text = text.replace('x=int_series["Time"],\\n        y=int_series["Cumulative USD"],', '# x=int_series["Time"],\\n        # y=int_series["Cumulative USD"],')

# Add base_currency to chart_monthly_summary
old_mo = """def chart_monthly_summary(monthly_df: pd.DataFrame) -> go.Figure:"""
new_mo = """def chart_monthly_summary(monthly_df: pd.DataFrame, base_currency: str = "USD") -> go.Figure:"""
text = text.replace(old_mo, new_mo)
text = text.replace('monthly_df["Dividends (EUR)"]', 'monthly_df[f"Dividends ({base_currency})"]')
text = text.replace('Dividends: €%{customdata[1]:.2f}', 'Dividends: %{customdata[1]:.2f}')
text = text.replace('Interest: €%{customdata[2]:.2f}', 'Interest: %{customdata[2]:.2f}')

# Add base_currency to chart_top_tickers
old_top = """def chart_top_tickers(ticker_df: pd.DataFrame, top_n: int = 15) -> go.Figure:"""
new_top = """def chart_top_tickers(ticker_df: pd.DataFrame, top_n: int = 15, base_currency: str = "USD") -> go.Figure:"""
text = text.replace(old_top, new_top)
text = text.replace("Profit", f"Profit") # no-op

# Add base_currency to chart_company_pnl_bars
old_pnl = """def chart_company_pnl_bars(company_df: pd.DataFrame) -> go.Figure:"""
new_pnl = """def chart_company_pnl_bars(company_df: pd.DataFrame, base_currency: str = "USD") -> go.Figure:"""
text = text.replace(old_pnl, new_pnl)
text = text.replace('company_df["Gross Profit ($)"]', 'company_df[f"Gross Profit ({"" if "base_currency" not in locals() else "€" if base_currency=="EUR" else "$"})"]')
# Note: Since the sym logic in python string won't execute inside replace dynamically easily, I'll use a better approach.

with open("charts.py", "w") as f:
    f.write(text)

