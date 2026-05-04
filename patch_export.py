import re

with open("analyzer.py", "r") as f:
    text = f.read()

old_func = """def export_portfolio_excel(df: pd.DataFrame, summary: dict, start_date, end_date) -> bytes:
    \"\"\"
    Creates a professionally formatted multi-sheet Excel file (.xlsx) in memory.
    Sheet 1: High-level Portfolio Total Overview
    Sheet 2: Month-by-Month Performance History
    \"\"\"
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
    }"""

new_func = """def export_portfolio_excel(df: pd.DataFrame, summary: dict, start_date, end_date, base_currency="USD", fx_series=None) -> bytes:
    \"\"\"
    Creates a professionally formatted multi-sheet Excel file (.xlsx) in memory.
    Sheet 1: High-level Portfolio Total Overview
    Sheet 2: Month-by-Month Performance History
    \"\"\"
    net_deposited = summary["total_deposited_eur"] - summary["total_withdrawn_eur"] - summary.get("total_card_spent_eur", 0)
    total_return = summary["net_pnl"] + summary["div_net_eur"] + summary["interest_eur"] + summary.get("interest_usd", 0) + summary["cashback_eur"]
    
    sym = "€" if base_currency == "EUR" else "$"

    # Overview Data
    overview_data = {
        "Metric": [
            "Start Date", "End Date",
            f"Total Deposits ({sym})", f"Total Withdrawals ({sym})", f"Net Deposited ({sym})",
            f"Gross Profit ({sym})", f"Gross Loss ({sym})", f"Net Trading P&L ({sym})", 
            "Win Rate (%)", "Total Sell Trades",
            f"Gross Dividends ({sym})", f"Withholding Tax ({sym})", f"Net Dividends ({sym})",
            f"Total Interest ({sym})", f"Cashback ({sym})",
            f"Total Return ({sym})"
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
    }"""

text = text.replace(old_func, new_func)

with open("analyzer.py", "w") as f:
    f.write(text)
