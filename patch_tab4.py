import re

with open("app.py", "r") as f:
    text = f.read()

old_tab4 = """# ── Tab 4 : Companies ───────────────────────────────────────────────────────
with tabs[3]:
    company_df = analyzer.company_detailed_stats(df)

    if company_df.empty:
        st.markdown("<div class='info-callout'>No trade data in the selected period.</div>",
                    unsafe_allow_html=True)
    else:
        # ── Top summary cards ──────────────────────────────────
        top_co    = company_df.iloc[0]
        worst_co  = company_df.iloc[-1]
        most_traded = company_df.loc[company_df["Total Trades"].idxmax()]
        best_wr   = company_df.loc[company_df["Win Rate (%)"].idxmax()]

        st.markdown(cards_row([
            card("Companies Traded",   str(len(company_df)),
                 "Unique tickers with trade activity", "🏢", "accent-blue"),
            card("Best Performer",     top_co["Ticker"],
                 f"Net: +${top_co['Net P&L ($)']:,.2f}", "🥇", "accent-green"),
            card("Worst Performer",    worst_co["Ticker"],
                 f"Net: -${abs(worst_co['Net P&L ($)']):,.2f}", "🥴", "accent-red"),
            card("Most Traded",        most_traded["Ticker"],
                 f"{most_traded['Total Trades']} total trades", "🔥", "accent-amber"),
            card("Highest Win Rate",   best_wr["Ticker"],
                 f"{best_wr['Win Rate (%)']:.1f}% win rate", "🎯", "accent-teal",
                 tooltip="Micro fractional losses (<$0.50 or <0.025%) caused by Trading212 Pie rebalancing are strictly excluded from the win-rate denominator, inherently improving the geometric ratio."),
        ]), unsafe_allow_html=True)

        # ── Overview charts row ────────────────────────────────
        st.plotly_chart(charts.chart_company_pnl_bars(company_df), use_container_width=True, key="company_pnl_bars")

        st.plotly_chart(charts.chart_company_bubble(company_df), use_container_width=True, key="company_bubble")

        # ── Return Contribution chart ──────────────────────────
        section("🧩 Return Contribution (% of Portfolio MWRR)")
        st.plotly_chart(
            charts.chart_return_contribution(company_df, mwrr_total),
            use_container_width=True, key="return_contribution",
        )

        # ── Compare section ───────────────────────────────────
        section("⚖️ Compare Companies")
        all_tickers = company_df["Ticker"].tolist()
        compare_sel = st.multiselect(
            "Select 2–8 tickers to compare on the same chart",
            options=all_tickers,
            default=all_tickers[:min(4, len(all_tickers))],
            max_selections=8,
            label_visibility="collapsed",
            placeholder="Choose tickers…",
        )
        if compare_sel:
            st.plotly_chart(charts.chart_company_compare(df, compare_sel), use_container_width=True, key="company_compare")

        # ── Drill-down: single company ─────────────────────────
        section("🔍 Company Drill-Down")
        drill_ticker = st.selectbox(
            "Select a company to see every individual trade",
            options=all_tickers,
            label_visibility="collapsed",
        )
        if drill_ticker:
            # Stat cards for selected company
            row = company_df[company_df["Ticker"] == drill_ticker].iloc[0]
            net_acc = "accent-green" if row["Net P&L ($)"] >= 0 else "accent-red"
            rc = row.get("Return Contribution (%)", 0.0)
            rc_acc = "accent-green" if rc >= 0 else "accent-red"
            st.markdown(cards_row([
                card("Net P&L",       f"${row['Net P&L ($)']:+,.2f}",
                     "All sell trades", "📊", net_acc),
                card("Return Contrib",f"{rc:+.2f}%",
                     "Share of total portfolio return", "🧩", rc_acc,
                     tooltip="This ticker's contribution to the total portfolio MWRR. Computed as its Net P&L / total portfolio P&L × MWRR%."),
                card("Gross Profit",  f"${row['Gross Profit ($)']:,.2f}",
                     f"{row['Winning Sells']} winning sells", "💚", "accent-green"),
                card("Gross Loss",    f"${abs(row['Gross Loss ($)']):,.2f}",
                     f"{row['Losing Sells']} losing sells", "🔴", "accent-red"),
                card("Win Rate",       f"{row['Win Rate (%)']:.1f}%",
                     f"{row['Total Trades']} total trades", "🎯", "accent-blue"),
                card("Best Trade",    f"${row['Best Trade ($)']:+,.2f}",
                     "Single sell", "⭐", "accent-green"),
                card("Worst Trade",   f"${row['Worst Trade ($)']:+,.2f}",
                     "Single sell", "💥", "accent-red"),
                card("Avg Win",       f"${row['Avg Win ($)']:+,.2f}",
                     "Per winning sell", "📈", "accent-teal"),
                card("Avg Loss",      f"${abs(row['Avg Loss ($)']):+,.2f}",
                     "Per losing sell", "📉", "accent-amber"),
            ]), unsafe_allow_html=True)"""

new_tab4 = """# ── Tab 4 : Companies ───────────────────────────────────────────────────────
with tabs[3]:
    company_df = analyzer.company_detailed_stats(df, base_currency, fx_series)
    sym = "€" if base_currency == "EUR" else "$"

    if company_df.empty:
        st.markdown("<div class='info-callout'>No trade data in the selected period.</div>",
                    unsafe_allow_html=True)
    else:
        # ── Top summary cards ──────────────────────────────────
        top_co    = company_df.iloc[0]
        worst_co  = company_df.iloc[-1]
        most_traded = company_df.loc[company_df["Total Trades"].idxmax()]
        best_wr   = company_df.loc[company_df["Win Rate (%)"].idxmax()]

        st.markdown(cards_row([
            card("Companies Traded",   str(len(company_df)),
                 "Unique tickers with trade activity", "🏢", "accent-blue"),
            card("Best Performer",     top_co["Ticker"],
                 f"Net: {fmt_usd(top_co[f'Net P&L ({sym})'])}", "🥇", "accent-green"),
            card("Worst Performer",    worst_co["Ticker"],
                 f"Net: {fmt_usd(worst_co[f'Net P&L ({sym})'])}", "🥴", "accent-red"),
            card("Most Traded",        most_traded["Ticker"],
                 f"{most_traded['Total Trades']} total trades", "🔥", "accent-amber"),
            card("Highest Win Rate",   best_wr["Ticker"],
                 f"{best_wr['Win Rate (%)']:.1f}% win rate", "🎯", "accent-teal",
                 tooltip="Micro fractional losses (<$0.50 or <0.025%) caused by Trading212 Pie rebalancing are strictly excluded from the win-rate denominator, inherently improving the geometric ratio."),
        ]), unsafe_allow_html=True)

        # ── Overview charts row ────────────────────────────────
        st.plotly_chart(charts.chart_company_pnl_bars(company_df), use_container_width=True, key="company_pnl_bars")

        st.plotly_chart(charts.chart_company_bubble(company_df), use_container_width=True, key="company_bubble")

        # ── Return Contribution chart ──────────────────────────
        section("🧩 Return Contribution (% of Portfolio MWRR)")
        st.plotly_chart(
            charts.chart_return_contribution(company_df, mwrr_total),
            use_container_width=True, key="return_contribution",
        )

        # ── Compare section ───────────────────────────────────
        section("⚖️ Compare Companies")
        all_tickers = company_df["Ticker"].tolist()
        compare_sel = st.multiselect(
            "Select 2–8 tickers to compare on the same chart",
            options=all_tickers,
            default=all_tickers[:min(4, len(all_tickers))],
            max_selections=8,
            label_visibility="collapsed",
            placeholder="Choose tickers…",
        )
        if compare_sel:
            st.plotly_chart(charts.chart_company_compare(df, compare_sel), use_container_width=True, key="company_compare")

        # ── Drill-down: single company ─────────────────────────
        section("🔍 Company Drill-Down")
        drill_ticker = st.selectbox(
            "Select a company to see every individual trade",
            options=all_tickers,
            label_visibility="collapsed",
        )
        if drill_ticker:
            # Stat cards for selected company
            row = company_df[company_df["Ticker"] == drill_ticker].iloc[0]
            net_acc = "accent-green" if row[f"Net P&L ({sym})"] >= 0 else "accent-red"
            rc = row.get("Return Contribution (%)", 0.0)
            rc_acc = "accent-green" if rc >= 0 else "accent-red"
            st.markdown(cards_row([
                card("Net P&L",       fmt_usd(row[f'Net P&L ({sym})']),
                     "All sell trades", "📊", net_acc),
                card("Return Contrib",f"{rc:+.2f}%",
                     "Share of total portfolio return", "🧩", rc_acc,
                     tooltip="This ticker's contribution to the total portfolio MWRR. Computed as its Net P&L / total portfolio P&L × MWRR%."),
                card("Gross Profit",  fmt_usd(row[f'Gross Profit ({sym})'], False),
                     f"{row['Winning Sells']} winning sells", "💚", "accent-green"),
                card("Gross Loss",    fmt_usd(abs(row[f'Gross Loss ({sym})']), False),
                     f"{row['Losing Sells']} losing sells", "🔴", "accent-red"),
                card("Win Rate",       f"{row['Win Rate (%)']:.1f}%",
                     f"{row['Total Trades']} total trades", "🎯", "accent-blue"),
                card("Best Trade",    fmt_usd(row[f'Best Trade ({sym})']),
                     "Single sell", "⭐", "accent-green"),
                card("Worst Trade",   fmt_usd(row[f'Worst Trade ({sym})']),
                     "Single sell", "💥", "accent-red"),
                card("Avg Win",       fmt_usd(row[f'Avg Win ({sym})']),
                     "Per winning sell", "📈", "accent-teal"),
                card("Avg Loss",      fmt_usd(abs(row[f'Avg Loss ({sym})'])),
                     "Per losing sell", "📉", "accent-amber"),
            ]), unsafe_allow_html=True)"""

text = text.replace(old_tab4, new_tab4)

with open("app.py", "w") as f:
    f.write(text)
