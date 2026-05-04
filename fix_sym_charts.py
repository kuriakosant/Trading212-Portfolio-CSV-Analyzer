import re

with open("charts.py", "r") as f:
    text = f.read()

# Fix chart_total_portfolio definition
text = text.replace(
    'def chart_total_portfolio(prog_df: pd.DataFrame, show_dep: bool = True, show_pnl: bool = True,\n                          show_div: bool = True, show_int: bool = True,\n                          chart_mode: str = "Line (Stacked Area)",\n                          return_df: pd.DataFrame = None) -> go.Figure:',
    'def chart_total_portfolio(prog_df: pd.DataFrame, show_dep: bool = True, show_pnl: bool = True,\n                          show_div: bool = True, show_int: bool = True,\n                          chart_mode: str = "Line (Stacked Area)",\n                          return_df: pd.DataFrame = None, base_currency: str = "USD") -> go.Figure:\n    sym = "€" if base_currency == "EUR" else "$"'
)

# Fix chart_return_timeline definition
text = text.replace(
    'def chart_return_timeline(return_df: pd.DataFrame, mwrr_annual: float = float("nan"), mwrr_total: float = 0.0) -> go.Figure:',
    'def chart_return_timeline(return_df: pd.DataFrame, mwrr_annual: float = float("nan"), mwrr_total: float = 0.0, base_currency: str = "USD") -> go.Figure:\n    sym = "€" if base_currency == "EUR" else "$"'
)

# Fix chart_return_contribution
text = text.replace(
    'def chart_return_contribution(company_df: pd.DataFrame, mwrr_total: float = 0.0) -> go.Figure:',
    'def chart_return_contribution(company_df: pd.DataFrame, mwrr_total: float = 0.0, base_currency: str = "USD") -> go.Figure:\n    sym = "€" if base_currency == "EUR" else "$"'
)

# Fix chart_company_compare
text = text.replace(
    'def chart_company_compare(df: pd.DataFrame, tickers: list) -> go.Figure:',
    'def chart_company_compare(df: pd.DataFrame, tickers: list, base_currency: str = "USD", fx_series=None) -> go.Figure:\n    sym = "€" if base_currency == "EUR" else "$"'
)

# Fix chart_income_pie
text = text.replace(
    'def chart_income_pie(summary: dict) -> go.Figure:',
    'def chart_income_pie(summary: dict, base_currency: str = "USD") -> go.Figure:\n    sym = "€" if base_currency == "EUR" else "$"'
)

# Fix chart_deposits_vs_pnl
text = text.replace(
    'def chart_deposits_vs_pnl(df: pd.DataFrame) -> go.Figure:',
    'def chart_deposits_vs_pnl(df: pd.DataFrame, base_currency: str = "USD", fx_series=None) -> go.Figure:\n    sym = "€" if base_currency == "EUR" else "$"'
)

# Fix hardcoded $ in chart_total_portfolio
text = text.replace('<b>$%{y:,.2f}</b>', '<b>%{customdata[0]}{y:,.2f}</b>') # Wait, maybe just replace with `f"<b>{sym}%{{y:,.2f}}</b>"` but wait, if it's already an f-string...
# Let's use regex for replacing hovertemplate <b>$
text = re.sub(r'hovertemplate="([^"]*)<b>\$%\{y(:[^}]*)\}</b>', r'hovertemplate=f"\1<b>{sym}%{y\2}</b>', text)

with open("charts.py", "w") as f:
    f.write(text)
