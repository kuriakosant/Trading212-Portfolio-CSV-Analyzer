import re

with open("charts.py", "r") as f:
    content = f.read()

# 1. Update function signatures to include base_currency
funcs_to_update = [
    "chart_pnl_timeline(timeline_df: pd.DataFrame, freq_label: str = \"Daily\")",
    "chart_waterfall_pnl(df: pd.DataFrame, summary: dict)",
    "chart_monthly_heatmap(df_monthly: pd.DataFrame)",
    "chart_cumulative_pnl(df: pd.DataFrame)",
    "chart_portfolio_progress(df_progress: pd.DataFrame, **kwargs)",
    "chart_portfolio_drawdown(df_progress: pd.DataFrame, **kwargs)",
    "chart_mwrr_timeline(return_df: pd.DataFrame)"
]

for func in funcs_to_update:
    new_func = func.replace(")", ", base_currency: str = \"USD\")")
    content = content.replace(func, new_func)

# 2. Inject `sym` assignment after the function definitions
def inject_sym(match):
    return match.group(0) + "\n    sym = \"€\" if base_currency == \"EUR\" else \"$\"\n"

content = re.sub(r'def chart_[a-zA-Z0-9_]+\(.*base_currency: str = "USD"\) -> go\.Figure:\n    """[^"]+"""', inject_sym, content)
content = re.sub(r'def chart_[a-zA-Z0-9_]+\(.*base_currency: str = "USD"\) -> go\.Figure:\n    (?!""")', inject_sym, content)

# 3. Replace all static ($) and (EUR) with dynamic ({sym}) in string literals
content = re.sub(r'"([^"\n]+?) \(\$\)"', r'f"\1 ({sym})"', content)
content = re.sub(r'"([^"\n]+?) \(EUR\)"', r'f"\1 ({sym})"', content)

# Also fix Volume Bought string which in the patch was changed from Vol Bought to Volume Bought
content = content.replace('f"Vol Bought ({sym})"', 'f"Volume Bought ({sym})"')

with open("charts.py", "w") as f:
    f.write(content)
