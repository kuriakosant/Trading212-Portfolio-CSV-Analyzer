"""
app.py — Trading212 Portfolio CSV Analyzer
Streamlit app for analyzing Trading212 CSV exports.
"""

import streamlit as st
import pandas as pd
from datetime import date, timedelta

import analyzer
import charts

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Trading212 Portfolio Analyzer",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS — premium dark theme
# ---------------------------------------------------------------------------

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, sans-serif !important;
    }

    .stApp {
        background: #0e1117;
    }

    section[data-testid="stSidebar"] {
        background: #13141a;
        border-right: 1px solid rgba(255,255,255,0.07);
    }

    /* Metric cards */
    .metric-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 14px;
        padding: 20px 22px;
        margin-bottom: 10px;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 32px rgba(0,0,0,0.4);
    }
    .metric-label {
        font-size: 12px;
        font-weight: 500;
        color: rgba(255,255,255,0.45);
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 6px;
    }
    .metric-value {
        font-size: 28px;
        font-weight: 700;
        line-height: 1.1;
    }
    .metric-sub {
        font-size: 12px;
        color: rgba(255,255,255,0.35);
        margin-top: 4px;
    }
    .color-profit  { color: #00e676; }
    .color-loss    { color: #ff1744; }
    .color-neutral { color: #29b6f6; }
    .color-divid   { color: #ce93d8; }
    .color-inter   { color: #80cbc4; }
    .color-deposit { color: #ffd54f; }
    .color-white   { color: #e0e0e0; }

    /* Section headers */
    .section-header {
        font-size: 18px;
        font-weight: 600;
        color: #e0e0e0;
        margin: 28px 0 14px 0;
        padding-bottom: 8px;
        border-bottom: 1px solid rgba(255,255,255,0.08);
    }

    /* Info banner */
    .info-banner {
        background: linear-gradient(135deg, #1a237e22, #4a148c22);
        border: 1px solid rgba(124,77,255,0.3);
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 20px;
        color: rgba(255,255,255,0.7);
        font-size: 14px;
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: transparent;
        border-bottom: 1px solid rgba(255,255,255,0.08);
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        color: rgba(255,255,255,0.5);
        border-radius: 8px 8px 0 0;
        padding: 8px 18px;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background: rgba(124,77,255,0.15) !important;
        color: #ce93d8 !important;
        border-bottom: 2px solid #7c4dff;
    }

    /* DataFrames */
    .stDataFrame {
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 10px;
        overflow: hidden;
    }

    div[data-testid="stMetric"] {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 10px;
        padding: 14px;
    }

    /* Upload area */
    [data-testid="stFileUploader"] {
        border-radius: 12px;
    }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: #0e1117; }
    ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.15); border-radius: 3px; }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def metric_card(label: str, value: str, sub: str = "", color_class: str = "color-white") -> str:
    return f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value {color_class}">{value}</div>
        {"<div class='metric-sub'>" + sub + "</div>" if sub else ""}
    </div>
    """


def fmt(value: float, prefix: str = "", decimals: int = 2) -> str:
    if value >= 0:
        return f"{prefix}{value:,.{decimals}f}"
    return f"-{prefix}{abs(value):,.{decimals}f}"


def fmt_signed(value: float, prefix: str = "$") -> str:
    sign = "+" if value >= 0 else ""
    return f"{sign}{prefix}{value:,.2f}"


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("## 📈 Portfolio Analyzer")
    st.markdown("---")

    uploaded_files = st.file_uploader(
        "Upload Trading212 CSV(s)",
        type=["csv"],
        accept_multiple_files=True,
        help="Export from Trading212 → History → Download. You can upload multiple files (e.g. one per year).",
    )

    st.markdown("---")
    st.markdown("### 📅 Date Range")

    preset = st.selectbox(
        "Quick Preset",
        ["Custom", "This Month", "Last Month", "Last 3 Months", "This Year", "All Time"],
        index=0,
    )

    today = date.today()

    if preset == "This Month":
        default_start = today.replace(day=1)
        default_end = today
    elif preset == "Last Month":
        first_this = today.replace(day=1)
        last_month_end = first_this - timedelta(days=1)
        default_start = last_month_end.replace(day=1)
        default_end = last_month_end
    elif preset == "Last 3 Months":
        default_start = (today - timedelta(days=90)).replace(day=1)
        default_end = today
    elif preset == "This Year":
        default_start = today.replace(month=1, day=1)
        default_end = today
    else:  # Custom / All Time
        default_start = date(2020, 1, 1)
        default_end = today

    start_date = st.date_input("Start Date", value=default_start)
    end_date = st.date_input("End Date", value=default_end)

    if start_date > end_date:
        st.error("Start date must be before end date.")
        st.stop()

    st.markdown("---")
    st.markdown("### ⚙️ Options")
    show_card_spending = st.checkbox("Include card spending analysis", value=False)
    show_raw = st.checkbox("Show raw data tab", value=True)

    st.markdown("---")
    st.markdown(
        "<div style='color:rgba(255,255,255,0.3);font-size:11px;'>Trading212 Portfolio Analyzer<br>Supports multi-file uploads</div>",
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Main content
# ---------------------------------------------------------------------------

st.markdown("""
<div style="display:flex;align-items:center;gap:14px;margin-bottom:8px;">
    <span style="font-size:42px">📈</span>
    <div>
        <h1 style="margin:0;font-size:32px;font-weight:700;background:linear-gradient(135deg,#7c4dff,#29b6f6);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">
            Portfolio Analyzer
        </h1>
        <p style="margin:0;color:rgba(255,255,255,0.45);font-size:14px;">Trading212 CSV export analysis</p>
    </div>
</div>
""", unsafe_allow_html=True)

if not uploaded_files:
    st.markdown("""
    <div class="info-banner">
        👋 <strong>Welcome!</strong> Upload one or more Trading212 CSV exports using the sidebar to get started.<br><br>
        <strong>How to export:</strong> Open Trading212 → History → tap the download icon → select date range → export CSV.
        You can upload multiple files (e.g. Jan–Apr 2026 + full year 2025) and they will be merged automatically.
    </div>
    """, unsafe_allow_html=True)

    # Demo columns
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(metric_card("Trade P&L", "—", "Sell result totals", "color-neutral"), unsafe_allow_html=True)
    with col2:
        st.markdown(metric_card("Dividends", "—", "Net after withholding", "color-divid"), unsafe_allow_html=True)
    with col3:
        st.markdown(metric_card("Interest", "—", "Cash + lending interest", "color-inter"), unsafe_allow_html=True)
    st.stop()

# ---------------------------------------------------------------------------
# Load & filter data
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner="Parsing CSV files…")
def load_data(files):
    return analyzer.load_csvs(files)


with st.spinner("Loading data…"):
    df_all = load_data(uploaded_files)

# Apply date filter
df = analyzer.filter_by_date(df_all, start_date, end_date)

if df.empty:
    st.warning(f"No transactions found between **{start_date}** and **{end_date}**. Try adjusting the date range.")
    st.stop()

# Compute everything
summary = analyzer.compute_summary(df)
daily_pnl_df = analyzer.daily_cumulative_pnl(df)
monthly_df = analyzer.monthly_summary(df)
ticker_df = analyzer.ticker_pnl(df)

# ---------------------------------------------------------------------------
# Date range header
# ---------------------------------------------------------------------------

st.markdown(
    f"<div style='color:rgba(255,255,255,0.4);font-size:13px;margin-bottom:20px;'>"
    f"Showing data from <strong style='color:#ce93d8'>{start_date}</strong> to "
    f"<strong style='color:#ce93d8'>{end_date}</strong> — "
    f"<strong style='color:#e0e0e0'>{len(df):,}</strong> transactions</div>",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Summary metric cards — Row 1: P&L
# ---------------------------------------------------------------------------

st.markdown("<div class='section-header'>💹 Trading P&amp;L</div>", unsafe_allow_html=True)

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.markdown(metric_card(
        "Total Profit",
        fmt_signed(summary["gross_profit"]),
        f"{summary['n_winning_trades']} winning trades",
        "color-profit",
    ), unsafe_allow_html=True)
with c2:
    st.markdown(metric_card(
        "Total Loss",
        fmt_signed(summary["gross_loss"]),
        f"{summary['n_losing_trades']} losing trades",
        "color-loss",
    ), unsafe_allow_html=True)
with c3:
    net_color = "color-profit" if summary["net_pnl"] >= 0 else "color-loss"
    st.markdown(metric_card(
        "Net P&L",
        fmt_signed(summary["net_pnl"]),
        "Profit − Loss",
        net_color,
    ), unsafe_allow_html=True)
with c4:
    win_pct = f"{summary['win_rate']:.1f}% win rate"
    st.markdown(metric_card(
        "Total Sell Trades",
        f"{summary['n_sells']}",
        win_pct,
        "color-neutral",
    ), unsafe_allow_html=True)
with c5:
    st.markdown(metric_card(
        "Total Buy Trades",
        f"{summary['n_buys']}",
        f"Volume: ${summary['total_buy_volume']:,.0f}",
        "color-white",
    ), unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Summary metric cards — Row 2: Income
# ---------------------------------------------------------------------------

st.markdown("<div class='section-header'>💰 Passive Income &amp; Cash</div>", unsafe_allow_html=True)

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.markdown(metric_card(
        "Dividends (Net)",
        f"€{summary['div_net_eur']:,.4f}",
        f"Gross: €{summary['div_gross_eur']:,.4f}",
        "color-divid",
    ), unsafe_allow_html=True)
with c2:
    st.markdown(metric_card(
        "Withholding Tax",
        f"€{summary['div_withholding_eur']:,.4f}",
        f"{summary['n_dividends']} dividend payments",
        "color-loss",
    ), unsafe_allow_html=True)
with c3:
    inter_total = summary["interest_eur"] + summary.get("interest_usd", 0)
    st.markdown(metric_card(
        "Interest on Cash",
        f"€{summary['interest_eur']:,.4f}",
        f"+ ${summary.get('interest_usd', 0):,.4f} USD · {summary['n_interest']} payments",
        "color-inter",
    ), unsafe_allow_html=True)
with c4:
    st.markdown(metric_card(
        "Spending Cashback",
        f"€{summary['cashback_eur']:,.4f}",
        "Card rewards",
        "color-deposit",
    ), unsafe_allow_html=True)
with c5:
    net_deposited = summary["total_deposited_eur"] - summary["total_withdrawn_eur"]
    st.markdown(metric_card(
        "Net Deposited",
        f"€{net_deposited:,.2f}",
        f"In: €{summary['total_deposited_eur']:,.2f} / Out: €{summary['total_withdrawn_eur']:,.2f}",
        "color-white",
    ), unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

tab_labels = ["📈 Charts", "🔄 Trades", "💵 Dividends & Interest"]
if show_raw:
    tab_labels.append("📂 Raw Data")

tabs = st.tabs(tab_labels)

# ---- Tab 1: Charts ---------------------------------------------------------
with tabs[0]:
    # Cumulative P&L
    st.plotly_chart(charts.chart_cumulative_pnl(daily_pnl_df), use_container_width=True)

    col_a, col_b = st.columns(2)
    with col_a:
        st.plotly_chart(charts.chart_daily_pnl(daily_pnl_df), use_container_width=True)
    with col_b:
        st.plotly_chart(charts.chart_income_pie(summary), use_container_width=True)

    st.plotly_chart(charts.chart_monthly_summary(monthly_df), use_container_width=True)

    col_c, col_d = st.columns([3, 2])
    with col_c:
        st.plotly_chart(charts.chart_top_tickers(ticker_df), use_container_width=True)
    with col_d:
        st.plotly_chart(charts.chart_deposits_vs_pnl(df), use_container_width=True)


# ---- Tab 2: Trades ---------------------------------------------------------
with tabs[1]:
    trades_df = analyzer.get_trades_table(df)

    if trades_df.empty:
        st.info("No buy/sell transactions in the selected period.")
    else:
        st.markdown(f"**{len(trades_df)} trade records** in period")

        # Per-ticker breakdown first
        if not ticker_df.empty:
            st.markdown("<div class='section-header'>Per-Ticker P&L Summary</div>", unsafe_allow_html=True)

            styled = ticker_df.copy()
            styled["Profit"] = styled["Profit"].apply(lambda x: f"+${x:,.2f}")
            styled["Loss"] = styled["Loss"].apply(lambda x: f"-${abs(x):,.2f}")
            styled["Net P&L"] = styled["Net P&L"].apply(
                lambda x: f"+${x:,.2f}" if x >= 0 else f"-${abs(x):,.2f}"
            )
            st.dataframe(styled, use_container_width=True, hide_index=True)

        st.markdown("<div class='section-header'>Individual Trade Records</div>", unsafe_allow_html=True)

        # Search/filter
        search = st.text_input("🔍 Filter by ticker or name", placeholder="e.g. SOFI, Vistra…")
        filtered = trades_df
        if search:
            mask = (
                trades_df["Ticker"].fillna("").str.upper().str.contains(search.upper()) |
                trades_df["Name"].fillna("").str.upper().str.contains(search.upper())
            )
            filtered = trades_df[mask]

        action_filter = st.multiselect(
            "Filter by action",
            options=sorted(trades_df["Action"].unique().tolist()),
            default=[],
            placeholder="All actions",
        )
        if action_filter:
            filtered = filtered[filtered["Action"].isin(action_filter)]

        st.dataframe(
            filtered.reset_index(drop=True),
            use_container_width=True,
            hide_index=True,
        )

        # Download
        csv_bytes = filtered.to_csv(index=False).encode()
        st.download_button(
            "⬇️ Download filtered trades as CSV",
            data=csv_bytes,
            file_name=f"trades_{start_date}_{end_date}.csv",
            mime="text/csv",
        )


# ---- Tab 3: Dividends & Interest ------------------------------------------
with tabs[2]:
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("<div class='section-header'>💵 Dividends</div>", unsafe_allow_html=True)
        div_df = analyzer.get_dividends_table(df)
        if div_df.empty:
            st.info("No dividends in the selected period.")
        else:
            st.markdown(f"**{len(div_df)} dividend payments** | Net: **€{summary['div_net_eur']:.4f}** | Withholding: **€{summary['div_withholding_eur']:.4f}**")
            st.dataframe(div_df, use_container_width=True, hide_index=True)

    with col_right:
        st.markdown("<div class='section-header'>🏦 Interest &amp; Cashback</div>", unsafe_allow_html=True)
        interest_df = df[df["_category"].isin(["interest", "cashback"])][
            ["Time", "Action", "Total", "Currency (Total)"]
        ].sort_values("Time", ascending=False).reset_index(drop=True)

        if interest_df.empty:
            st.info("No interest/cashback in the selected period.")
        else:
            total_interest = interest_df[interest_df["Action"].str.lower().str.contains("interest", na=False)]["Total"].sum()
            total_cashback = interest_df[interest_df["Action"].str.lower().str.contains("cashback", na=False)]["Total"].sum()
            st.markdown(f"**{len(interest_df)} payments** | Interest: **{total_interest:.4f}** | Cashback: **€{total_cashback:.4f}**")
            st.dataframe(interest_df, use_container_width=True, hide_index=True)

    # Card spending analysis (optional)
    if show_card_spending:
        st.markdown("<div class='section-header'>💳 Card Spending</div>", unsafe_allow_html=True)
        card_df = df[df["_category"] == "card_debit"][
            ["Time", "Total", "Currency (Total)", "Merchant name", "Merchant category"]
        ].copy()
        if not card_df.empty:
            card_df["Total"] = card_df["Total"].abs()
            st.markdown(f"**{len(card_df)} transactions** | Total spent: **€{summary['total_card_spent_eur']:,.2f}**")

            # Spending by category
            if "Merchant category" in card_df.columns:
                by_cat = card_df.groupby("Merchant category")["Total"].sum().sort_values(ascending=False)
                cat_fig = px.bar(
                    x=by_cat.index, y=by_cat.values,
                    labels={"x": "Category", "y": "Total Spent (EUR)"},
                    color_discrete_sequence=["#7c4dff"]
                )
                cat_fig.update_layout(
                    paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                    font=dict(color="#e0e0e0"), height=300,
                    margin=dict(l=10, r=10, t=30, b=10),
                )
                st.plotly_chart(cat_fig, use_container_width=True)

            st.dataframe(card_df.sort_values("Time", ascending=False).reset_index(drop=True),
                         use_container_width=True, hide_index=True)


# ---- Tab 4: Raw Data -------------------------------------------------------
if show_raw:
    with tabs[3]:
        st.markdown(f"**{len(df):,} rows** in filter period | Full dataset: **{len(df_all):,} rows**")

        category_filter = st.multiselect(
            "Filter by category",
            options=sorted(df["_category"].unique().tolist()),
            default=[],
            placeholder="All categories",
        )

        display_df = df.drop(columns=["_month"], errors="ignore")

        if category_filter:
            display_df = display_df[display_df["_category"].isin(category_filter)]

        st.dataframe(display_df.reset_index(drop=True), use_container_width=True, hide_index=True)

        csv_raw = display_df.to_csv(index=False).encode()
        st.download_button(
            "⬇️ Download filtered raw data",
            data=csv_raw,
            file_name=f"trading212_raw_{start_date}_{end_date}.csv",
            mime="text/csv",
        )
