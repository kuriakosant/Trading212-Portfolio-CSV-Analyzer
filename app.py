"""
app.py — Trading212 Portfolio CSV Analyzer
Premium dark Streamlit interface.
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
    page_title="T212 Portfolio Analyzer",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Premium CSS
# ---------------------------------------------------------------------------

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ── Base ── */
*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
.stApp { background: #080910 !important; }
.main .block-container { padding: 2rem 2rem 4rem !important; max-width: 1600px; }

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: #0d0e1a !important;
    border-right: 1px solid rgba(255,255,255,0.06) !important;
}
section[data-testid="stSidebar"] > div { padding-top: 1.5rem; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.12); border-radius: 99px; }

/* ── Hero header ── */
.hero {
    background: linear-gradient(135deg, #0f0c29, #1a0533, #0d0e1a);
    border: 1px solid rgba(167,139,250,0.15);
    border-radius: 20px;
    padding: 2rem 2.4rem;
    margin-bottom: 1.8rem;
    position: relative;
    overflow: hidden;
}
.hero::before {
    content: "";
    position: absolute; top: -60px; right: -60px;
    width: 280px; height: 280px;
    background: radial-gradient(circle, rgba(167,139,250,0.18) 0%, transparent 70%);
    pointer-events: none;
}
.hero::after {
    content: "";
    position: absolute; bottom: -80px; left: 30%;
    width: 300px; height: 300px;
    background: radial-gradient(circle, rgba(56,189,248,0.1) 0%, transparent 70%);
    pointer-events: none;
}
.hero-title {
    font-size: 2.1rem;
    font-weight: 800;
    background: linear-gradient(135deg, #a78bfa, #38bdf8, #22c55e);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text;
    line-height: 1.15;
    margin: 0 0 0.35rem 0;
}
.hero-sub {
    font-size: 0.92rem;
    color: rgba(226,228,240,0.45);
    margin: 0;
    font-weight: 400;
}
.hero-badge {
    display: inline-block;
    background: rgba(167,139,250,0.15);
    border: 1px solid rgba(167,139,250,0.3);
    color: #a78bfa;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 3px 10px;
    border-radius: 99px;
    margin-bottom: 0.75rem;
}

/* ── Section header ── */
.section-hdr {
    font-size: 0.72rem;
    font-weight: 700;
    color: rgba(226,228,240,0.35);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin: 2rem 0 0.9rem 0;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
.section-hdr::after {
    content: "";
    flex: 1;
    height: 1px;
    background: rgba(255,255,255,0.06);
}

/* ── Metric cards ── */
.cards-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
    gap: 12px;
    margin-bottom: 0.5rem;
}
.card {
    background: #11121e;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px;
    padding: 1.1rem 1.2rem;
    position: relative;
    overflow: hidden;
    transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
    cursor: default;
}
.card:hover {
    transform: translateY(-3px);
    border-color: rgba(255,255,255,0.14);
    box-shadow: 0 12px 40px rgba(0,0,0,0.5);
}
.card::before {
    content: "";
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    border-radius: 14px 14px 0 0;
    background: var(--accent, rgba(167,139,250,0.5));
}
.card-label {
    font-size: 0.68rem;
    font-weight: 600;
    color: rgba(226,228,240,0.38);
    text-transform: uppercase;
    letter-spacing: 0.09em;
    margin-bottom: 0.5rem;
}
.card-value {
    font-size: 1.65rem;
    font-weight: 700;
    color: var(--val-color, #e2e4f0);
    line-height: 1.1;
    font-variant-numeric: tabular-nums;
}
.card-sub {
    font-size: 0.72rem;
    color: rgba(226,228,240,0.32);
    margin-top: 0.4rem;
    font-weight: 400;
}
.card-icon {
    position: absolute;
    top: 1rem; right: 1rem;
    font-size: 1.4rem;
    opacity: 0.35;
}

/* ── Accent color helpers ── */
.accent-green  { --accent: rgba(34,197,94,0.6);  --val-color: #22c55e; }
.accent-red    { --accent: rgba(244,63,94,0.6);  --val-color: #f43f5e; }
.accent-blue   { --accent: rgba(56,189,248,0.6); --val-color: #38bdf8; }
.accent-purple { --accent: rgba(167,139,250,0.6);--val-color: #a78bfa; }
.accent-teal   { --accent: rgba(45,212,191,0.6); --val-color: #2dd4bf; }
.accent-amber  { --accent: rgba(251,191,36,0.6); --val-color: #fbbf24; }
.accent-gray   { --accent: rgba(226,228,240,0.2);--val-color: #e2e4f0; }

/* ── Upload zone ── */
.upload-zone {
    background: linear-gradient(135deg, #11121e, #0d0e1a);
    border: 1.5px dashed rgba(167,139,250,0.25);
    border-radius: 16px;
    padding: 2.4rem 2rem;
    text-align: center;
    margin: 1rem 0;
    transition: border-color 0.2s;
}
.upload-zone:hover { border-color: rgba(167,139,250,0.5); }
.upload-title { font-size: 1.1rem; font-weight: 600; color: #e2e4f0; margin: 0.5rem 0 0.25rem; }
.upload-sub { font-size: 0.82rem; color: rgba(226,228,240,0.4); }

/* ── Frequency pill row ── */
div[data-testid="stHorizontalBlock"] .stRadio > label { display: none; }
.stRadio [data-testid="stMarkdownContainer"] p { display: none; }

/* ── Date range badge ── */
.date-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(167,139,250,0.1);
    border: 1px solid rgba(167,139,250,0.2);
    border-radius: 99px;
    padding: 4px 14px;
    font-size: 0.8rem;
    color: rgba(226,228,240,0.6);
    margin-bottom: 1.5rem;
}
.date-badge b { color: #a78bfa; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: transparent !important;
    border-bottom: 1px solid rgba(255,255,255,0.07) !important;
    padding-bottom: 0;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    border-radius: 8px 8px 0 0 !important;
    color: rgba(226,228,240,0.4) !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
    padding: 8px 18px !important;
    border: none !important;
    transition: color 0.15s, background 0.15s;
}
.stTabs [data-baseweb="tab"]:hover {
    color: rgba(226,228,240,0.75) !important;
    background: rgba(255,255,255,0.04) !important;
}
.stTabs [aria-selected="true"] {
    background: rgba(167,139,250,0.1) !important;
    color: #a78bfa !important;
    border-bottom: 2px solid #a78bfa !important;
}

/* ── DataFrames ── */
.stDataFrame { border-radius: 12px; overflow: hidden; }
iframe[title="st_aggrid_wrapper"] { border-radius: 12px; }

/* ── Plotly charts ── */
.js-plotly-plot { border-radius: 14px; }

/* ── Info callout ── */
.info-callout {
    background: rgba(56,189,248,0.07);
    border: 1px solid rgba(56,189,248,0.2);
    border-radius: 12px;
    padding: 1rem 1.2rem;
    color: rgba(226,228,240,0.65);
    font-size: 0.84rem;
    line-height: 1.6;
    margin: 0.5rem 0 1rem 0;
}
.info-callout b { color: #38bdf8; }

/* ── Sidebar labels ── */
section[data-testid="stSidebar"] label {
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    color: rgba(226,228,240,0.45) !important;
    text-transform: uppercase !important;
    letter-spacing: 0.07em !important;
}
section[data-testid="stSidebar"] .stSelectbox > div,
section[data-testid="stSidebar"] .stDateInput > div {
    background: rgba(255,255,255,0.04) !important;
    border-color: rgba(255,255,255,0.1) !important;
    border-radius: 8px !important;
}

/* ── Buttons ── */
.stDownloadButton button {
    background: rgba(167,139,250,0.12) !important;
    border: 1px solid rgba(167,139,250,0.3) !important;
    border-radius: 8px !important;
    color: #a78bfa !important;
    font-size: 0.83rem !important;
    font-weight: 600 !important;
    transition: all 0.15s !important;
}
.stDownloadButton button:hover {
    background: rgba(167,139,250,0.22) !important;
    border-color: rgba(167,139,250,0.5) !important;
}

/* ── Radio buttons (timeline selector) ── */
.stRadio > div {
    display: flex;
    flex-direction: row !important;
    gap: 8px;
    flex-wrap: wrap;
}
.stRadio > div > label {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 99px !important;
    padding: 5px 16px !important;
    font-size: 0.8rem !important;
    font-weight: 500 !important;
    color: rgba(226,228,240,0.55) !important;
    cursor: pointer !important;
    transition: all 0.15s;
}
.stRadio > div > label:hover {
    border-color: rgba(167,139,250,0.4) !important;
    color: rgba(226,228,240,0.85) !important;
}
.stRadio > div > label[data-selected="true"],
.stRadio > div > label:has(input:checked) {
    background: rgba(167,139,250,0.18) !important;
    border-color: rgba(167,139,250,0.5) !important;
    color: #a78bfa !important;
}
/* hide radio dots */
.stRadio > div > label > div:first-child { display: none !important; }

/* ── Animations ── */
@keyframes fadeUp {
    from { opacity: 0; transform: translateY(16px); }
    to   { opacity: 1; transform: translateY(0); }
}
.cards-grid { animation: fadeUp 0.4s ease; }
.hero { animation: fadeUp 0.35s ease; }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def card(label: str, value: str, sub: str = "", icon: str = "", accent: str = "accent-gray") -> str:
    return f"""
    <div class="card {accent}">
        {"<span class='card-icon'>" + icon + "</span>" if icon else ""}
        <div class="card-label">{label}</div>
        <div class="card-value">{value}</div>
        {"<div class='card-sub'>" + sub + "</div>" if sub else ""}
    </div>"""


def cards_row(html_list: list) -> str:
    return "<div class='cards-grid'>" + "".join(html_list) + "</div>"


def fmt_usd(v: float, sign: bool = True) -> str:
    if sign:
        s = "+" if v >= 0 else "−"
        return f"{s}${abs(v):,.2f}"
    return f"${v:,.2f}"


def fmt_eur(v: float, decimals: int = 2) -> str:
    return f"€{v:,.{decimals}f}"


def section(label: str) -> None:
    st.markdown(f"<div class='section-hdr'><span>{label}</span></div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("""
    <div style="padding:0 0 1rem 0;">
        <div style="font-size:1.4rem;font-weight:800;
            background:linear-gradient(135deg,#a78bfa,#38bdf8);
            -webkit-background-clip:text;-webkit-text-fill-color:transparent;
            background-clip:text;margin-bottom:2px;">T212 Analyzer</div>
        <div style="font-size:0.75rem;color:rgba(226,228,240,0.35);font-weight:400;">
            Portfolio CSV Analysis Tool</div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    uploaded_files = st.file_uploader(
        "UPLOAD CSV FILES",
        type=["csv"],
        accept_multiple_files=True,
        help="Export from Trading212 → History → Download icon. Supports multiple files.",
    )

    st.divider()

    st.markdown("<div style='font-size:0.72rem;font-weight:700;color:rgba(226,228,240,0.35);text-transform:uppercase;letter-spacing:0.1em;margin-bottom:0.6rem;'>Date Range</div>", unsafe_allow_html=True)

    preset = st.selectbox(
        "Quick Preset",
        ["Custom", "This Month", "Last Month", "Last 3 Months",
         "Last 6 Months", "This Year", "All Time"],
        label_visibility="collapsed",
    )

    today = date.today()
    if preset == "This Month":
        d_start, d_end = today.replace(day=1), today
    elif preset == "Last Month":
        first_this = today.replace(day=1)
        last_end   = first_this - timedelta(days=1)
        d_start, d_end = last_end.replace(day=1), last_end
    elif preset == "Last 3 Months":
        d_start, d_end = (today - timedelta(days=90)).replace(day=1), today
    elif preset == "Last 6 Months":
        d_start, d_end = (today - timedelta(days=182)).replace(day=1), today
    elif preset == "This Year":
        d_start, d_end = today.replace(month=1, day=1), today
    else:
        d_start, d_end = date(2020, 1, 1), today

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("From", value=d_start, label_visibility="visible")
    with col2:
        end_date = st.date_input("To", value=d_end, label_visibility="visible")

    if start_date > end_date:
        st.error("Start must be before end date.")
        st.stop()

    st.divider()
    st.markdown("<div style='font-size:0.72rem;font-weight:700;color:rgba(226,228,240,0.35);text-transform:uppercase;letter-spacing:0.1em;margin-bottom:0.6rem;'>Options</div>", unsafe_allow_html=True)
    show_card_spending = st.checkbox("Card spending tab", value=False)

    st.divider()
    st.markdown(
        "<div style='font-size:0.7rem;color:rgba(226,228,240,0.2);line-height:1.6;'>"
        "CSV files are never stored or committed.<br>All analysis runs locally."
        "</div>",
        unsafe_allow_html=True
    )


# ---------------------------------------------------------------------------
# Hero header
# ---------------------------------------------------------------------------

st.markdown("""
<div class="hero">
    <div class="hero-badge">📈 Portfolio Analytics</div>
    <h1 class="hero-title">Trading212 Portfolio Analyzer</h1>
    <p class="hero-sub">Upload your CSV exports · Explore P&amp;L across any timeline · Track dividends &amp; interest growth</p>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Empty state
# ---------------------------------------------------------------------------

if not uploaded_files:
    st.markdown("""
    <div class="upload-zone">
        <div style="font-size:2.5rem;margin-bottom:0.5rem;">📂</div>
        <div class="upload-title">Upload your Trading212 CSV exports</div>
        <div class="upload-sub">Go to Trading212 → History → Download icon → Export CSV<br>
        You can upload multiple files (e.g. 2024 + 2025) and they'll be merged automatically.</div>
    </div>
    """, unsafe_allow_html=True)

    # Preview skeleton cards
    st.markdown(cards_row([
        card("Total Profit", "—", "Profitable sell trades", "💚", "accent-green"),
        card("Total Loss", "—", "Losing sell trades", "🔴", "accent-red"),
        card("Net P&L", "—", "Profit minus loss", "📊", "accent-blue"),
        card("Dividends", "—", "Net after withholding", "💵", "accent-purple"),
        card("Interest", "—", "Cash + lending", "🏦", "accent-teal"),
    ]), unsafe_allow_html=True)
    st.stop()

# ---------------------------------------------------------------------------
# Load & filter
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def load_data(files):
    return analyzer.load_csvs(files)

with st.spinner("⚡ Parsing CSV files…"):
    df_all = load_data(uploaded_files)

df = analyzer.filter_by_date(df_all, start_date, end_date)

if df.empty:
    st.warning(f"No transactions found between **{start_date}** and **{end_date}**.")
    st.stop()

# Pre-compute everything
summary     = analyzer.compute_summary(df)
monthly_df  = analyzer.monthly_summary(df)
ticker_df   = analyzer.ticker_pnl(df)
div_series  = analyzer.dividend_series(df)
int_series  = analyzer.interest_series(df)

# Date badge
days_in_range = (end_date - start_date).days + 1
st.markdown(
    f"<div class='date-badge'>📅 <b>{start_date.strftime('%b %d, %Y')}</b>"
    f" → <b>{end_date.strftime('%b %d, %Y')}</b>"
    f" &nbsp;·&nbsp; {len(df):,} transactions &nbsp;·&nbsp; {days_in_range} days</div>",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Metric cards — Row 1: P&L
# ---------------------------------------------------------------------------

section("💹 Trading P&L")

net_accent = "accent-green" if summary["net_pnl"] >= 0 else "accent-red"
st.markdown(cards_row([
    card("Total Profit",  fmt_usd(summary["gross_profit"], False),
         f"{summary['n_winning_trades']} winning trades", "💚", "accent-green"),
    card("Total Loss",    fmt_usd(summary["gross_loss"], False),
         f"{summary['n_losing_trades']} losing trades", "🔴", "accent-red"),
    card("Net P&L",       fmt_usd(summary["net_pnl"]),
         "Profit − Loss", "📈", net_accent),
    card("Win Rate",      f"{summary['win_rate']:.1f}%",
         f"{summary['n_sells']} total sell trades", "🎯", "accent-blue"),
    card("Buy Trades",    str(summary["n_buys"]),
         f"Volume: {fmt_usd(summary['total_buy_volume'], False)}", "🛒", "accent-gray"),
]), unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Metric cards — Row 2: Income & cash
# ---------------------------------------------------------------------------

section("💰 Passive Income & Cash Flow")

int_total = summary["interest_eur"] + summary.get("interest_usd", 0)
net_dep   = summary["total_deposited_eur"] - summary["total_withdrawn_eur"]
st.markdown(cards_row([
    card("Dividends (Net)",   fmt_eur(summary["div_net_eur"], 4),
         f"Gross: {fmt_eur(summary['div_gross_eur'], 4)}", "💵", "accent-purple"),
    card("Withholding Tax",   fmt_eur(summary["div_withholding_eur"], 4),
         f"{summary['n_dividends']} payments", "🏛️", "accent-red"),
    card("Interest EUR",      fmt_eur(summary["interest_eur"], 4),
         f"{summary['n_interest']} payments", "🏦", "accent-teal"),
    card("Interest USD",      f"${summary.get('interest_usd',0):,.4f}",
         "Lending + cash", "💲", "accent-amber"),
    card("Cashback",          fmt_eur(summary["cashback_eur"], 4),
         "Card rewards", "🎁", "accent-blue"),
    card("Net Deposited",     fmt_eur(net_dep),
         f"In: {fmt_eur(summary['total_deposited_eur'])} / Out: {fmt_eur(summary['total_withdrawn_eur'])}", "🏧", "accent-gray"),
]), unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

tab_names = ["📈 P&L Timeline", "📅 Monthly", "🏆 Tickers", "🏢 Companies", "💵 Dividends", "🏦 Interest", "🔄 Trades"]
if show_card_spending:
    tab_names.append("💳 Card Spending")

tabs = st.tabs(tab_names)

# ── Tab 1 : P&L Timeline ────────────────────────────────────────────────────
with tabs[0]:
    st.markdown("<div style='margin-bottom:0.6rem;'></div>", unsafe_allow_html=True)

    freq_label = st.radio(
        "Timeline resolution",
        ["Daily", "Weekly", "Monthly", "Quarterly"],
        index=1,
        horizontal=True,
        label_visibility="collapsed",
    )
    freq_code  = analyzer.FREQ_MAP[freq_label]
    timeline   = analyzer.pnl_timeline(df, freq_code)

    st.plotly_chart(charts.chart_pnl_timeline(timeline, freq_label), use_container_width=True)

    # Quick stats below chart
    if not timeline.empty:
        col1, col2, col3, col4 = st.columns(4)
        best  = timeline.loc[timeline["Period P&L"].idxmax()]
        worst = timeline.loc[timeline["Period P&L"].idxmin()]
        with col1:
            period_label = best["Period"].strftime("%b %d") if hasattr(best["Period"], "strftime") else str(best["Period"])
            st.metric("Best Period", f"+${best['Period P&L']:,.2f}", period_label)
        with col2:
            period_label2 = worst["Period"].strftime("%b %d") if hasattr(worst["Period"], "strftime") else str(worst["Period"])
            st.metric("Worst Period", f"-${abs(worst['Period P&L']):,.2f}", period_label2)
        with col3:
            active = int((timeline["Trades"] > 0).sum())
            st.metric("Active Periods", active, f"of {len(timeline)} total")
        with col4:
            avg = timeline[timeline["Trades"] > 0]["Period P&L"].mean()
            st.metric("Avg P&L / Period", f"${avg:+,.2f}", "active periods only")

    col_a, col_b = st.columns(2)
    with col_a:
        st.plotly_chart(charts.chart_income_pie(summary), use_container_width=True)
    with col_b:
        st.plotly_chart(charts.chart_deposits_vs_pnl(df), use_container_width=True)


# ── Tab 2 : Monthly summary ──────────────────────────────────────────────────
with tabs[1]:
    st.plotly_chart(charts.chart_monthly_summary(monthly_df), use_container_width=True)

    if not monthly_df.empty:
        section("Month-by-Month Details")
        display = monthly_df.copy()
        for col in ["Profit", "Loss", "Net P&L"]:
            display[col] = display[col].apply(lambda v: f"${v:+,.2f}")
        display["Dividends (EUR)"] = display["Dividends (EUR)"].apply(lambda v: f"€{v:.4f}")
        display["Interest"] = display["Interest"].apply(lambda v: f"{v:.4f}")
        st.dataframe(display, use_container_width=True, hide_index=True)


# ── Tab 3 : Tickers ──────────────────────────────────────────────────────────
with tabs[2]:
    st.plotly_chart(charts.chart_top_tickers(ticker_df), use_container_width=True)

    if not ticker_df.empty:
        section("Full Ticker P&L Breakdown")
        search = st.text_input("🔍 Filter ticker", placeholder="e.g. SOFI, WULF…",
                               label_visibility="collapsed")
        disp = ticker_df.copy()
        if search:
            disp = disp[disp["Ticker"].str.upper().str.contains(search.upper(), na=False) |
                        disp["Name"].str.upper().str.contains(search.upper(), na=False)]

        styled = disp.copy()
        styled["Profit"]  = styled["Profit"].apply(lambda v: f"+${v:,.2f}")
        styled["Loss"]    = styled["Loss"].apply(lambda v: f"-${abs(v):,.2f}")
        styled["Net P&L"] = styled["Net P&L"].apply(lambda v: f"+${v:,.2f}" if v >= 0 else f"-${abs(v):,.2f}")
        st.dataframe(styled, use_container_width=True, hide_index=True)

        csv_b = disp.to_csv(index=False).encode()
        st.download_button("⬇️ Export ticker breakdown", csv_b,
                           f"tickers_{start_date}_{end_date}.csv", "text/csv")


# ── Tab 4 : Companies ───────────────────────────────────────────────────────
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
                 f"{best_wr['Win Rate (%)']:.1f}% win rate", "🎯", "accent-teal"),
        ]), unsafe_allow_html=True)

        # ── Overview charts row ────────────────────────────────
        st.plotly_chart(charts.chart_company_pnl_bars(company_df), use_container_width=True)

        st.plotly_chart(charts.chart_company_bubble(company_df), use_container_width=True)

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
            st.plotly_chart(charts.chart_company_compare(df, compare_sel), use_container_width=True)

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
            st.markdown(cards_row([
                card("Net P&L",       f"${row['Net P&L ($)']:+,.2f}",
                     "All sell trades", "📊", net_acc),
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
                card("Avg Loss",      f"${row['Avg Loss ($)']:+,.2f}",
                     "Per losing sell", "📉", "accent-amber"),
                card("Buy Trades",    str(int(row["Buy Trades"])),
                     f"Vol: ${row['Vol Bought ($)']:,.0f}", "🛒", "accent-gray"),
                card("Days Active",   str(int(row["Days Active"])),
                     f"{row['First Trade'].strftime('%b %d') if pd.notna(row['First Trade']) else '—'} → {row['Last Trade'].strftime('%b %d, %Y') if pd.notna(row['Last Trade']) else '—'}",
                     "📅", "accent-gray"),
            ]), unsafe_allow_html=True)

            history = analyzer.company_trade_history(df, drill_ticker)
            st.plotly_chart(charts.chart_company_timeline(history, drill_ticker),
                            use_container_width=True)

            # Individual trade log
            section(f"📋 {drill_ticker} — All Trades")
            if not history.empty:
                disp = history.copy()
                disp["Time"] = disp["Time"].dt.strftime("%b %d, %Y %H:%M")
                disp["Trade P&L ($)"] = disp["Trade P&L ($)"].apply(
                    lambda v: f"${v:+,.2f}" if v != 0 else "—")
                disp["Cumul P&L ($)"] = disp["Cumul P&L ($)"].apply(
                    lambda v: f"${v:+,.2f}")
                st.dataframe(disp, use_container_width=True, hide_index=True)
                csv_co = history.to_csv(index=False).encode()
                st.download_button(f"⬇️ Export {drill_ticker} trade log", csv_co,
                                   f"{drill_ticker}_trades_{start_date}_{end_date}.csv", "text/csv")

        # ── Full company stats table ───────────────────────────
        section("📋 Full Company Stats Table")
        sort_col = st.selectbox(
            "Sort by",
            ["Net P&L ($)", "Total Trades", "Gross Profit ($)", "Win Rate (%)",
             "Vol Bought ($)", "Best Trade ($)"],
            label_visibility="collapsed",
        )
        sort_asc = st.checkbox("Ascending", value=False)
        display_co = company_df.copy().sort_values(sort_col, ascending=sort_asc)
        # Format dates for display
        for dc in ["First Trade", "Last Trade"]:
            if dc in display_co.columns:
                display_co[dc] = display_co[dc].dt.strftime("%b %d, %Y").fillna("—")
        st.dataframe(display_co.reset_index(drop=True), use_container_width=True, hide_index=True)
        csv_all_co = company_df.to_csv(index=False).encode()
        st.download_button("⬇️ Export full company stats", csv_all_co,
                           f"companies_{start_date}_{end_date}.csv", "text/csv")


# ── Tab 5 : Dividends ────────────────────────────────────────────────────────
with tabs[4]:
    if div_series.empty:
        st.markdown("<div class='info-callout'>No dividend payments found in the selected period.</div>",
                    unsafe_allow_html=True)
    else:
        # Summary banner
        total_div = summary["div_net_eur"]
        wh        = summary["div_withholding_eur"]
        st.markdown(cards_row([
            card("Total Dividends (Net)", fmt_eur(total_div, 4),
                 f"{summary['n_dividends']} payments", "💵", "accent-purple"),
            card("Gross Dividends",       fmt_eur(summary['div_gross_eur'], 4),
                 "Before withholding tax", "📊", "accent-blue"),
            card("Withholding Tax",       fmt_eur(wh, 4),
                 f"{(wh/summary['div_gross_eur']*100) if summary['div_gross_eur'] else 0:.1f}% of gross",
                 "🏛️", "accent-red"),
        ]), unsafe_allow_html=True)

        st.plotly_chart(charts.chart_dividend_growth(div_series), use_container_width=True)

        section("Individual Dividend Payments")
        disp = div_series.copy()
        disp["Net (EUR)"]         = disp["Net (EUR)"].apply(lambda v: f"€{v:.4f}")
        disp["Withholding (EUR)"] = disp["Withholding (EUR)"].apply(lambda v: f"€{v:.4f}")
        disp["Cumulative (EUR)"]  = disp["Cumulative (EUR)"].apply(lambda v: f"€{v:.4f}")
        disp["Time"]              = disp["Time"].dt.strftime("%b %d, %Y %H:%M")
        st.dataframe(disp, use_container_width=True, hide_index=True)


# ── Tab 6 : Interest ─────────────────────────────────────────────────────────
with tabs[5]:
    eur_tot = summary["interest_eur"]
    usd_tot = summary.get("interest_usd", 0)

    st.markdown(cards_row([
        card("Total EUR Interest", fmt_eur(eur_tot, 4),
             "Interest on cash + lending", "🏦", "accent-teal"),
        card("Total USD Interest", f"${usd_tot:,.4f}",
             "USD cash account interest", "💲", "accent-amber"),
        card("Total Payments", str(summary["n_interest"]),
             "Across all interest types", "📊", "accent-blue"),
    ]), unsafe_allow_html=True)

    if int_series.empty:
        st.markdown("<div class='info-callout'>No interest payments found in the selected period.</div>",
                    unsafe_allow_html=True)
    else:
        st.plotly_chart(charts.chart_interest_growth(int_series), use_container_width=True)

        section("Interest Payment Log")
        disp = int_series.copy()
        disp["Amount"]   = disp.apply(
            lambda r: f"€{r['Amount']:.4f}" if r["Currency"] == "EUR" else f"${r['Amount']:.4f}", axis=1)
        disp["Cumulative EUR"] = disp["Cumulative EUR"].apply(
            lambda v: f"€{v:.4f}" if pd.notna(v) else "—")
        disp["Cumulative USD"] = disp["Cumulative USD"].apply(
            lambda v: f"${v:.4f}" if pd.notna(v) else "—")
        disp["Time"] = disp["Time"].dt.strftime("%b %d, %Y %H:%M")
        st.dataframe(disp, use_container_width=True, hide_index=True)


# ── Tab 7 : Trades ───────────────────────────────────────────────────────────
with tabs[6]:
    trades_df = analyzer.get_trades_table(df)

    if trades_df.empty:
        st.markdown("<div class='info-callout'>No buy/sell transactions in the selected period.</div>",
                    unsafe_allow_html=True)
    else:
        col_s, col_f = st.columns([3, 1])
        with col_s:
            search2 = st.text_input("🔍 Search ticker or name", placeholder="e.g. VST, Vistra…",
                                    label_visibility="collapsed")
        with col_f:
            actions = sorted(trades_df["Action"].unique().tolist())
            act_filter = st.multiselect("Action", options=actions,
                                        placeholder="All actions", label_visibility="collapsed")

        filtered = trades_df
        if search2:
            m = (trades_df["Ticker"].fillna("").str.upper().str.contains(search2.upper()) |
                 trades_df["Name"].fillna("").str.upper().str.contains(search2.upper()))
            filtered = filtered[m]
        if act_filter:
            filtered = filtered[filtered["Action"].isin(act_filter)]

        st.markdown(
            f"<div style='font-size:0.8rem;color:rgba(226,228,240,0.35);margin-bottom:0.5rem;'>"
            f"Showing <b style='color:#a78bfa'>{len(filtered):,}</b> of {len(trades_df):,} records</div>",
            unsafe_allow_html=True,
        )
        st.dataframe(filtered.reset_index(drop=True), use_container_width=True, hide_index=True)

        csv_t = filtered.to_csv(index=False).encode()
        st.download_button("⬇️ Export trade records", csv_t,
                           f"trades_{start_date}_{end_date}.csv", "text/csv")


# ── Tab 8 : Card Spending (optional) ─────────────────────────────────────────
if show_card_spending:
    with tabs[7]:
        card_df = df[df["_category"] == "card_debit"][
            ["Time", "Total", "Currency (Total)", "Merchant name", "Merchant category"]
        ].copy()

        if card_df.empty:
            st.markdown("<div class='info-callout'>No card transactions in the selected period.</div>",
                        unsafe_allow_html=True)
        else:
            card_df["Total"] = card_df["Total"].abs()
            total_spent = summary["total_card_spent_eur"]

            st.markdown(cards_row([
                card("Total Card Spent", fmt_eur(total_spent),
                     f"{len(card_df)} transactions", "💳", "accent-red"),
            ]), unsafe_allow_html=True)

            if "Merchant category" in card_df.columns:
                by_cat = card_df.groupby("Merchant category")["Total"].sum().sort_values(ascending=False)
                import plotly.graph_objects as go_local
                cat_fig = go_local.Figure(go_local.Bar(
                    x=by_cat.index, y=by_cat.values,
                    marker_color=["#a78bfa"] * len(by_cat),
                    marker_line_width=0,
                    hovertemplate="<b>%{x}</b><br>Spent: €%{y:,.2f}<extra></extra>",
                ))
                cat_fig.update_layout(
                    paper_bgcolor="#0a0b14", plot_bgcolor="#11121e",
                    font=dict(color="#e2e4f0"), height=300,
                    margin=dict(l=10, r=10, t=30, b=10),
                    title=dict(text="Spending by Category", font=dict(size=14)),
                    xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
                    yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
                )
                st.plotly_chart(cat_fig, use_container_width=True)

            card_df["Time"] = card_df["Time"].dt.strftime("%b %d, %Y %H:%M")
            st.dataframe(card_df.sort_values("Time", ascending=False).reset_index(drop=True),
                         use_container_width=True, hide_index=True)
