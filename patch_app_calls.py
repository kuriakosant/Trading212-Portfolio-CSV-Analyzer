import re

with open("app.py", "r") as f:
    text = f.read()

# Fix chart_company_bubble
text = text.replace('charts.chart_company_bubble(company_df)', 'charts.chart_company_bubble(company_df, base_currency)')

# Fix chart_return_contribution
text = text.replace('charts.chart_return_contribution(company_df, mwrr_total)', 'charts.chart_return_contribution(company_df, mwrr_total, base_currency)')

# Fix chart_company_compare
text = text.replace('charts.chart_company_compare(df, compare_sel)', 'charts.chart_company_compare(df, compare_sel, base_currency, fx_series)')

# Fix chart_company_timeline
text = text.replace('charts.chart_company_timeline(history, drill_ticker)', 'charts.chart_company_timeline(history, drill_ticker, base_currency)')

# Fix chart_pnl_timeline
text = text.replace('charts.chart_pnl_timeline(timeline, freq_label)', 'charts.chart_pnl_timeline(timeline, freq_label, base_currency)')

# Fix chart_return_timeline
text = text.replace('charts.chart_return_timeline(', 'charts.chart_return_timeline(base_currency=base_currency, ')

# Fix chart_income_pie
text = text.replace('charts.chart_income_pie(summary)', 'charts.chart_income_pie(summary, base_currency)')

# Fix chart_deposits_vs_pnl
text = text.replace('charts.chart_deposits_vs_pnl(df)', 'charts.chart_deposits_vs_pnl(df, base_currency, fx_series)')

# Write back
with open("app.py", "w") as f:
    f.write(text)
