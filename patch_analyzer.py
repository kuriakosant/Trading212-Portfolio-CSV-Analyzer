import re

with open("analyzer.py", "r") as f:
    content = f.read()

# Add import
if "from fx_engine" not in content:
    content = content.replace("from brokers.fifo import fill_revolut_result", "from brokers.fifo import fill_revolut_result\nfrom fx_engine import convert_currency, fetch_historical_fx")

# Function signatures
def patch_sig(name):
    global content
    content = re.sub(
        rf"def {name}\(df: pd\.DataFrame\) ->",
        f"def {name}(df: pd.DataFrame, base_currency: str = 'USD', fx_series: pd.Series = None) ->",
        content
    )

patch_sig("compute_summary")
patch_sig("monthly_summary")
patch_sig("ticker_pnl")
patch_sig("dividend_series")
patch_sig("interest_series")
patch_sig("mwrr_cumulative_timeline")
patch_sig("compute_mwrr")

with open("analyzer.py", "w") as f:
    f.write(content)
