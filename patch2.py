import re

with open("analyzer.py", "r") as f:
    text = f.read()

# Replace compute_summary logic
summary_old = """    sells_result  = sells["Result"].fillna(0)
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
            total_fees += val"""

summary_new = """    if fx_series is None:
        fx_series = pd.Series(dtype=float)

    def _to_base(subset, val_col, ccy_col="Currency (Total)"):
        if subset.empty or val_col not in subset.columns: 
            return pd.Series(0.0, index=subset.index)
        return subset.apply(lambda r: convert_currency(
            float(r.get(val_col, 0) or 0), 
            str(r.get(ccy_col, "EUR")), 
            base_currency, 
            r.get("Time"), 
            fx_series
        ), axis=1)

    sells_result = _to_base(sells, "Result", "Currency (Result)")
    gross_profit = float(sells_result[sells_result > 0].sum())
    gross_loss   = float(sells_result[sells_result < 0].sum())
    net_pnl      = gross_profit + gross_loss

    total_buy_volume  = float(_to_base(buys, "Total").abs().sum())
    total_sell_volume = float(_to_base(sells, "Total").abs().sum())

    div_total_eur   = float(_to_base(dividends, "Total").sum())
    div_withholding = float(_to_base(dividends, "Withholding tax").abs().sum())
    div_gross       = div_total_eur + div_withholding

    int_eur = float(_to_base(interests, "Total").sum())
    int_usd = 0.0 # Deprecated separation since everything is mapped to base_currency

    cashback_total  = float(_to_base(cashback, "Total").sum())
    total_deposited = float(_to_base(deposits, "Total").abs().sum())
    total_withdrawn = float(_to_base(withdrawals, "Total").abs().sum())
    total_card_spent= float(_to_base(card_debits, "Total").abs().sum())

    div_tax_correction_total = float(_to_base(div_tax_corrections, "Total").sum())

    fee_cols = [
        "Withholding tax", "Finra fee", "Currency conversion fee",
        "French transaction tax", "Stamp duty reserve tax", "UK PTM Levy"
    ]
    fees_breakdown = {}
    total_fees = 0.0
    for col in fee_cols:
        val = float(_to_base(df, col).abs().sum())
        if val > 0:
            fees_breakdown[col] = val
            total_fees += val"""

text = text.replace(summary_old, summary_new)

mwrr_old = """    # The rest of the dashboard standardizes on 1 USD = 0.86 EUR
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
    int_total        = sum(to_usd(row.get("Total", 0) or 0, row.get("Currency (Total)", "EUR")) for _, row in interests.iterrows())"""

mwrr_new = """    if fx_series is None:
        fx_series = pd.Series(dtype=float)

    def to_base(amount, ccy, dt):
        return convert_currency(float(amount or 0), str(ccy), base_currency, dt, fx_series)

    # Build cash-flow list in YEARS (not days) so the solver works in annual space
    cf_years = []

    for _, row in deposits.iterrows():
        yrs = (row["Time"] - t0).total_seconds() / (86400.0 * 365.0)
        val = to_base(row.get("Total", 0) or 0, row.get("Currency (Total)", "EUR"), row.get("Time"))
        cf_years.append((yrs, -abs(val)))

    for _, row in withdrawals.iterrows():
        yrs = (row["Time"] - t0).total_seconds() / (86400.0 * 365.0)
        val = to_base(row.get("Total", 0) or 0, row.get("Currency (Total)", "EUR"), row.get("Time"))
        cf_years.append((yrs, abs(val)))

    for _, row in card_debits.iterrows():
        yrs = (row["Time"] - t0).total_seconds() / (86400.0 * 365.0)
        val = to_base(row.get("Total", 0) or 0, row.get("Currency (Total)", "EUR"), row.get("Time"))
        cf_years.append((yrs, abs(val)))

    # Compute terminal value
    total_deposited  = sum(abs(to_base(row.get("Total", 0) or 0, row.get("Currency (Total)", "EUR"), row.get("Time"))) for _, row in deposits.iterrows())
    total_withdrawn  = sum(abs(to_base(row.get("Total", 0) or 0, row.get("Currency (Total)", "EUR"), row.get("Time"))) for _, row in withdrawals.iterrows())
    total_card_spent = sum(abs(to_base(row.get("Total", 0) or 0, row.get("Currency (Total)", "EUR"), row.get("Time"))) for _, row in card_debits.iterrows())
    net_deposits     = total_deposited - total_withdrawn - total_card_spent

    sells            = df[df["_category"] == "sell"]
    realized_pnl     = sum(to_base(row.get("Result", 0) or 0, row.get("Currency (Result)"), row.get("Time")) for _, row in sells.iterrows())

    dividends        = df[df["_category"] == "dividend"]
    div_total        = sum(to_base(row.get("Total", 0) or 0, row.get("Currency (Total)", "EUR"), row.get("Time")) for _, row in dividends.iterrows())

    interests        = df[df["_category"] == "interest"]
    int_total        = sum(to_base(row.get("Total", 0) or 0, row.get("Currency (Total)", "EUR"), row.get("Time")) for _, row in interests.iterrows())"""

text = text.replace(mwrr_old, mwrr_new)

cum_old = """    EUR_TO_USD = 1.0 / 0.86

    def to_usd(amount, ccy):
        return float(amount) * EUR_TO_USD if str(ccy).strip().upper() == "EUR" else float(amount)

    def extract_val(row, col="Total", ccy_col="Currency (Total)"):
        return to_usd(row.get(col, 0) or 0, row.get(ccy_col, "EUR"))

    df_clean = df.copy()
    df_clean["_val_usd"] = 0.0

    # Map the relevant USD value based on category
    for i, row in df_clean.iterrows():
        cat = row.get("_category")
        if cat in ("deposit", "withdrawal", "card_debit", "dividend", "interest"):
            df_clean.at[i, "_val_usd"] = extract_val(row)
        elif cat == "sell":
            df_clean.at[i, "_val_usd"] = extract_val(row, "Result", "Currency (Result)")"""

cum_new = """    if fx_series is None:
        fx_series = pd.Series(dtype=float)

    def extract_val(row, col="Total", ccy_col="Currency (Total)"):
        return convert_currency(float(row.get(col, 0) or 0), str(row.get(ccy_col, "EUR")), base_currency, row.get("Time"), fx_series)

    df_clean = df.copy()
    df_clean["_val_usd"] = 0.0

    # Map the relevant base currency value based on category
    for i, row in df_clean.iterrows():
        cat = row.get("_category")
        if cat in ("deposit", "withdrawal", "card_debit", "dividend", "interest"):
            df_clean.at[i, "_val_usd"] = extract_val(row)
        elif cat == "sell":
            df_clean.at[i, "_val_usd"] = extract_val(row, "Result", "Currency (Result)")"""

text = text.replace(cum_old, cum_new)

# Update return value dictionary logic so mwrr outputs are directly used
text = text.replace('mwrr = compute_mwrr(df)', 'mwrr = compute_mwrr(df, base_currency, fx_series)')

with open("analyzer.py", "w") as f:
    f.write(text)
