"""
app.py — Trading212 Portfolio CSV Analyzer
Premium dark Streamlit interface.
"""

import streamlit as st
import pandas as pd
from datetime import date, timedelta
import time

import analyzer
import charts
import io
import portfolio_value as pv
import charts_portfolio_value as cpv

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Broker Portfolio CSV Analyzer",
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
.stApp { background: #030305 !important; }
.main .block-container { padding: 2rem 2rem 4rem !important; max-width: 1600px; }

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: #060608 !important;
    border-right: 1px solid rgba(255,255,255,0.04) !important;
}
section[data-testid="stSidebar"] > div { padding-top: 1.5rem; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.12); border-radius: 99px; }

/* ── Hero header ── */
.hero {
    background: linear-gradient(135deg, #050508, #0a0a14, #050508);
    border: 1px solid rgba(167,139,250,0.15);
    border-radius: 20px;
    padding: 2rem 2.4rem;
    margin-bottom: 1.8rem;
    position: relative;
    overflow: hidden;
    box-shadow: 0 4px 50px rgba(0,0,0,0.6);
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
    display: flex;
    flex-wrap: wrap;
    align-items: stretch;
    justify-content: center;
    gap: 12px;
    margin-bottom: 0.5rem;
}
.card {
    flex: 1 1 0;
    min-width: 190px;
    background: linear-gradient(180deg, #07070a, #030305);
    border: 1px solid rgba(255,255,255,0.05);
    border-radius: 14px;
    padding: 1.1rem 1.2rem;
    position: relative;
    overflow: hidden;
    box-shadow: 0 4px 15px rgba(0,0,0,0.5);
    transition: transform 0.25s cubic-bezier(0.1, 0.9, 0.2, 1), border-color 0.25s ease, box-shadow 0.25s ease;
    cursor: default;
}
.card:hover {
    transform: translateY(-4px) scale(1.02);
    border-color: var(--accent, rgba(255,255,255,0.2));
    box-shadow: 0 15px 45px rgba(0,0,0,0.8), 0 0 25px var(--accent-glow, transparent);
    z-index: 10;
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
    animation: textCinematic 1s cubic-bezier(0.1, 0.9, 0.2, 1) forwards;
    display: inline-block;
    text-shadow: 0 0 10px var(--accent-glow, transparent);
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

/* ── Accent color helpers (Deep Neon) ── */
.accent-green  { --accent: rgba(0,255,136,0.8);  --val-color: #00ff88; --accent-glow: rgba(0,255,136,0.3); }
.accent-red    { --accent: rgba(255,0,85,0.8);   --val-color: #ff0055; --accent-glow: rgba(255,0,85,0.3); }
.accent-blue   { --accent: rgba(0,240,255,0.8);  --val-color: #00f0ff; --accent-glow: rgba(0,240,255,0.3); }
.accent-purple { --accent: rgba(183,33,255,0.8); --val-color: #b721ff; --accent-glow: rgba(183,33,255,0.3); }
.accent-teal   { --accent: rgba(0,255,204,0.8);  --val-color: #00ffcc; --accent-glow: rgba(0,255,204,0.3); }
.accent-amber  { --accent: rgba(255,170,0,0.8);  --val-color: #ffaa00; --accent-glow: rgba(255,170,0,0.3); }
.accent-gray   { --accent: rgba(255,255,255,0.3);--val-color: #ffffff; --accent-glow: rgba(255,255,255,0.1); }
.accent-glow-pulse { animation: pulseGlow 2.5s infinite alternate ease-in-out; }


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

/* ── Empty CSS cleared ── */

.card {
    animation: textCinematic 0.6s cubic-bezier(0.1, 0.9, 0.2, 1) forwards;
}

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
    0%   { opacity: 0; transform: translateY(30px) scale(0.95); filter: blur(4px); }
    100% { opacity: 1; transform: translateY(0) scale(1); filter: blur(0px); }
}
@keyframes textCinematic {
    0%   { opacity: 0; transform: translateY(15px); filter: blur(8px); letter-spacing: -2px; }
    40%  { opacity: 0.8; transform: translateY(0); filter: blur(1px); letter-spacing: 1px; }
    100% { opacity: 1; transform: translateY(0); filter: blur(0px); letter-spacing: normal; }
}
@keyframes pulseGlow {
    0%   { box-shadow: 0 0 10px var(--accent-glow, transparent); border-color: rgba(255,255,255,0.05); }
    100% { box-shadow: 0 0 35px var(--accent, transparent); border-color: var(--accent, rgba(255,255,255,0.3)); }
}
.cards-grid { animation: fadeUp 0.6s cubic-bezier(0.1, 0.9, 0.2, 1); }
.hero { animation: fadeUp 0.5s cubic-bezier(0.1, 0.9, 0.2, 1); }

</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def card(label: str, value: str, sub: str = "", icon: str = "", accent: str = "accent-gray", tooltip: str = "") -> str:
    tooltip_html = f" <span style='cursor:help; opacity:0.8;' title='{tooltip}'>ⓘ</span>" if tooltip else ""
    return f"""
    <div class="card {accent}">
        {"<span class='card-icon'>" + icon + "</span>" if icon else ""}
        <div class="card-label">{label}{tooltip_html}</div>
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
# File Uploader State Management
# ---------------------------------------------------------------------------
if "file_data" not in st.session_state:
    st.session_state.file_data = []

def sync_uploads():
    w_sidebar = st.session_state.get("sidebar_uploader")
    
    if not w_sidebar:
        st.session_state.file_data = []
        return
        
    cached = []
    for f in w_sidebar:
        clone = io.BytesIO(f.getvalue())
        clone.name = getattr(f, "name", "upload.csv")
        cached.append(clone)
    st.session_state.file_data = cached

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("""
    <div style="padding:0 0 1rem 0;">
        <div style="font-size:1.4rem;font-weight:800;
            background:linear-gradient(135deg,#a78bfa,#38bdf8);
            -webkit-background-clip:text;-webkit-text-fill-color:transparent;
            background-clip:text;margin-bottom:2px;">Broker CSV Analyzer</div>
        <div style="font-size:0.75rem;color:rgba(226,228,240,0.35);font-weight:400;">
            Trading212 · Revolut</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='font-size:0.72rem;font-weight:700;color:rgba(226,228,240,0.35);text-transform:uppercase;letter-spacing:0.1em;margin-bottom:0.6rem;'>Dashboard</div>", unsafe_allow_html=True)
    page_selection = st.radio(
        "Navigation",
        ["🏦 Portfolio Dashboard", "💳 Card Spending Analysis"],
        label_visibility="collapsed"
    )

    st.divider()

    st.file_uploader(
        "UPLOAD CSV FILES",
        type=["csv"],
        key="sidebar_uploader",
        accept_multiple_files=True,
        on_change=sync_uploads,
        help=(
            "Supports Trading212 (History → Download) and Revolut "
            "(Stocks → Statements → Account statement CSV). "
            "Mix multiple files; duplicates are merged automatically. "
            "Revolut files are analyzed as USD-only."
        ),
    )


    st.divider()
    
    st.markdown("<div style='font-size:0.72rem;font-weight:700;color:rgba(226,228,240,0.35);text-transform:uppercase;letter-spacing:0.1em;margin-bottom:0.6rem;'>Export</div>", unsafe_allow_html=True)
    # We delay generating the actual CSV binary until the user has loaded data. 
    # But Streamlit sidebar runs sequentially. If df is loaded, we can put it here, 
    # but the df loading happens in the main code block below the sidebar. 
    # So we'll use a placeholder instead and fill it later.
    export_placeholder = st.empty()

    st.divider()
    st.markdown(
        "<div style='font-size:0.7rem;color:rgba(226,228,240,0.2);line-height:1.6;'>"
        "CSV files are never stored or committed.<br>All analysis runs locally."
        "</div>",
        unsafe_allow_html=True
    )


# ---------------------------------------------------------------------------
# Dynamic Hero header
# ---------------------------------------------------------------------------

if page_selection == "🏦 Portfolio Dashboard":
    st.markdown("""
    <div class="hero">
        <div class="hero-badge">📈 Portfolio Analytics</div>
        <h1 class="hero-title">Broker Portfolio CSV Analyzer</h1>
        <p class="hero-sub">Trading212 &amp; Revolut · Explore P&amp;L across any timeline · Track dividends &amp; interest growth</p>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div class="hero">
        <div class="hero-badge">💳 Card Analytics</div>
        <h1 class="hero-title">Trading212 Card Spending</h1>
        <p class="hero-sub">Analyze your Visa/Mastercard spending habits, view merchant breakdowns, and track monthly burn rates.</p>
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Empty state
# ---------------------------------------------------------------------------

if not getattr(st.session_state, "file_data", []):
    st.markdown("""
    <br>
    <div style="font-size:2.5rem;margin-bottom:0.1rem;text-align:center;">📂</div>
    <div style="font-size:1.4rem; font-weight: 700; text-align:center; color: #fff; margin-bottom: 0.1rem;">Upload your broker CSV exports</div>
    <div style="font-size:0.85rem; text-align:center; color: rgba(226,228,240,0.4); margin-bottom: 1.5rem;">
    Trading212 → History → Download icon → Export CSV<br>
    Revolut → Stocks → Statements → Account statement (CSV)<br>
    Please use the file uploader mapped in your left Sidebar to begin!
    </div>
    """, unsafe_allow_html=True)

    # Preview skeleton cards
    st.markdown("<br><br>", unsafe_allow_html=True)
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

def load_data(files):
    # Only read if fresh, ensuring we do seek(0) safely
    for f in files:
        f.seek(0)
    return analyzer.load_csvs(files)

# Dynamic Loading Feedback
loading_text = st.empty()
pbar_container = st.empty()
for i in range(0, 101, 6):
    loading_text.markdown(f"<div style='text-align: center; color: #00ff88; font-size: 1.4rem; font-weight: 800; font-variant-numeric: tabular-nums; text-shadow: 0 0 15px rgba(0,255,136,0.5); margin-bottom: 0.5rem; animation: pulseGlow 1s infinite;'>⚡ SYNTHESIZING DATA... {i}%</div>", unsafe_allow_html=True)
    with pbar_container:
        st.progress(i)
    time.sleep(0.015)
loading_text.empty()
pbar_container.empty()

df_all = load_data(st.session_state.file_data)

# Dynamic Date Bounds based on uploaded actual CSV date range
min_date = df_all["Time"].min().date() if not df_all.empty else date(2020, 1, 1)
max_date = df_all["Time"].max().date() if not df_all.empty else date.today()

with st.sidebar:
    st.divider()
    st.markdown("<div style='font-size:0.72rem;font-weight:700;color:rgba(226,228,240,0.35);text-transform:uppercase;letter-spacing:0.1em;margin-bottom:0.6rem;'>Date Range</div>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("From", value=min_date, min_value=min_date, max_value=max_date, label_visibility="visible")
    with col2:
        end_date = st.date_input("To", value=max_date, min_value=min_date, max_value=max_date, label_visibility="visible")

    if start_date > end_date:
        st.error("Start must be before end date.")
        st.stop()

df = analyzer.filter_by_date(df_all, start_date, end_date)

if df.empty:
    st.warning(f"No transactions found between **{start_date}** and **{end_date}**.")
    st.stop()

# ---------------------------------------------------------------------------
# Sub-App Router
# ---------------------------------------------------------------------------

if page_selection == "💳 Card Spending Analysis":
    metrics = analyzer.card_spending_deepdive(df)

    if metrics["total_txns"] == 0:
        brokers_in_data = sorted(df.get("_broker", pd.Series(dtype=str)).dropna().unique().tolist())
        revolut_only = brokers_in_data == ["revolut"]

        if revolut_only:
            headline = "Card Spending data is not available from Revolut exports"
            detail   = (
                "Revolut's Stocks CSV only contains investing activity — "
                "card and merchant data lives in the separate Revolut Banking "
                "product and isn't included here.<br><br>"
                "To unlock this page, also upload a <b>Trading212</b> CSV "
                "that contains <code>Card debit</code> rows."
            )
        else:
            headline = "No card spending data found in this date range"
            detail   = (
                "Your uploaded files don't contain any <code>Card debit</code> "
                "rows within <b>{start}</b> → <b>{end}</b>.<br><br>"
                "Try widening the date range, or upload a Trading212 export "
                "that covers your card-spending history."
            ).format(start=start_date.strftime("%b %d, %Y"),
                     end=end_date.strftime("%b %d, %Y"))

        st.markdown(f"""
        <div style="margin-top:1rem;">
          <div style="font-size:3rem; text-align:center; margin-bottom:0.5rem;">💳</div>
          <div style="font-size:1.35rem; font-weight:700; text-align:center;
                      color:#fff; margin-bottom:0.4rem;">{headline}</div>
          <div style="font-size:0.9rem; text-align:center;
                      color:rgba(226,228,240,0.55); line-height:1.7;
                      max-width:640px; margin:0 auto;">{detail}</div>
        </div>
        """, unsafe_allow_html=True)
        st.stop()
        
    section("📊 Overview")
    top_merch_str = metrics["merchants"]["Merchant"].iloc[0] if not metrics["merchants"].empty else "N/A"
    st.markdown(cards_row([
        card("Total Spent", fmt_eur(metrics["total_spent_raw"]), f"{metrics['total_txns']} total transactions", "💳", "accent-blue"),
        card("Average Txn", fmt_eur(metrics["avg_txn"]), "Per swipe", "🛍️", "accent-teal"),
        card("Top Merchant", top_merch_str, "Most frequent destination", "🏆", "accent-purple"),
    ]), unsafe_allow_html=True)
    
    st.markdown("<div style='margin-bottom:1rem;'></div>", unsafe_allow_html=True)
    
    _, center_col, _ = st.columns([0.1, 0.8, 0.1])
    with center_col:
        st.plotly_chart(charts.chart_spending_timeline(metrics["monthly"]), use_container_width=True, key="spending_timeline")
    
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(charts.chart_spending_category_donut(metrics["categories"]), use_container_width=True, key="spending_donut")
    with col2:
        st.plotly_chart(charts.chart_top_merchants(metrics["merchants"]), use_container_width=True, key="top_merchants")
        
    # Halt execution here so standard portfolio UI below this isn't rendered
    st.stop()


# Pre-compute everything
summary     = analyzer.compute_summary(df)
monthly_df  = analyzer.monthly_summary(df)
ticker_df   = analyzer.ticker_pnl(df)
div_series  = analyzer.dividend_series(df)
int_series  = analyzer.interest_series(df)
return_df   = analyzer.mwrr_cumulative_timeline(df)

# Date badge
days_in_range = (end_date - start_date).days + 1
_broker_labels = {"trading212": "T212", "revolut": "Revolut"}
brokers_in_data = sorted(df.get("_broker", pd.Series(dtype=str)).dropna().unique().tolist())
broker_badge = " · ".join(_broker_labels.get(b, b.title()) for b in brokers_in_data) or "—"
st.markdown(
    f"<div class='date-badge'>📅 <b>{start_date.strftime('%b %d, %Y')}</b>"
    f" → <b>{end_date.strftime('%b %d, %Y')}</b>"
    f" &nbsp;·&nbsp; {len(df):,} transactions &nbsp;·&nbsp; {days_in_range} days"
    f" &nbsp;·&nbsp; <b>{broker_badge}</b></div>",
    unsafe_allow_html=True,
)

# Populate Summary Export in the sidebar
excel_bytes = analyzer.export_portfolio_excel(df, summary, start_date, end_date)
export_placeholder.download_button(
    "📥 Download Excel Report", 
    data=excel_bytes,
    file_name=f"Portfolio_Report_{start_date}_to_{end_date}.xlsx", 
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    help="Download a highly detailed multi-sheet Excel report for external tracking."
)

# ---------------------------------------------------------------------------
# MWRR Return Hero + Net Total Yield Header
# ---------------------------------------------------------------------------

mwrr_annual = summary.get("mwrr_annual_pct", None)   # None when period < 180 days
mwrr_total  = summary.get("mwrr_total_pct", 0.0)
terminal_v  = summary.get("terminal_value", 0.0)
total_inv   = summary.get("total_invested", 0.0)
days_inv    = summary.get("days_invested", 0)

# Display helpers
_annual_str = f"{mwrr_annual:+.2f}% / yr" if mwrr_annual is not None else "N/A (< 6 mo)"
_annual_sub = f"Total: {mwrr_total:+.2f}%  \u00b7  {days_inv} days" + (
    "" if mwrr_annual is not None else "  \u00b7  annualize needs \u2265180 days"
)
return_accent = ("accent-green" if (mwrr_annual or mwrr_total) >= 0 else "accent-red") if mwrr_annual is not None else "accent-gray"
return_sign   = "\U0001f4c8" if (mwrr_annual if mwrr_annual is not None else mwrr_total) >= 0 else "\U0001f4c9"

st.markdown(cards_row([
    card(
        "PORTFOLIO RETURN (MWRR)",
        _annual_str,
        _annual_sub,
        return_sign,
        f"{return_accent} accent-glow-pulse",
        tooltip=(
            "Money-Weighted Rate of Return (MWRR) — also known as the portfolio IRR. "
            "Adjusts for the size and exact timing of every deposit and withdrawal, "
            "reflecting your actual experience as an investor. "
            "\u26a0\ufe0f Based on REALIZED gains only (no live market price for held positions). "
            "Annualized figure requires at least 180 days of data."
        ),
    ),
]), unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Net Total Yield Header
# ---------------------------------------------------------------------------

eur_components = summary["div_net_eur"] + summary["interest_eur"] + summary["cashback_eur"]
usd_components = summary.get("interest_usd", 0) + summary["net_pnl"]
net_total_yield_usd = usd_components + (eur_components / 0.86) # Fixed $1 = €0.86 rate

yield_accent = "accent-green" if net_total_yield_usd >= 0 else "accent-red"
st.markdown(cards_row([
    card("NET TOTAL YIELD (USD)", f"${net_total_yield_usd:+,.2f}",
         "Total Account Profit (Trades + Interest + Dividends + Cashback). Rate: 0.86 EUR = 1 USD", "🌍", f"{yield_accent} accent-glow-pulse")
]), unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Metric cards — Row 1: P&L
# ---------------------------------------------------------------------------

section("💹 Trading P&L")

# -- MWRR metric row --
_ann_val    = f"{mwrr_annual:+.2f}%" if mwrr_annual is not None else "N/A (< 6 mo)"
_ann_sub    = "IRR adjusted for deposit/withdrawal timing" if mwrr_annual is not None else "Need ≥180 days to annualize"
_ann_accent = ("accent-teal" if mwrr_annual >= 0 else "accent-red") if mwrr_annual is not None else "accent-gray"
st.markdown(cards_row([
    card("Annualized Return (MWRR)", _ann_val, _ann_sub, "\U0001f4ca", _ann_accent,
         tooltip="Annualized Money-Weighted Rate of Return. Accounts for how much capital was invested at each point in time. Shown only for periods ≥ 180 days."),
    card("Total Return (MWRR)", f"{mwrr_total:+.2f}%",
         f"Over {days_inv} days total invested", "\U0001f4c8" if mwrr_total >= 0 else "\U0001f4c9",
         "accent-green" if mwrr_total >= 0 else "accent-red"),
    card("Terminal Value", f"${terminal_v:,.2f}",
         "Net deposits + realized P&L + dividends + interest", "\U0001f3e6", "accent-blue",
         tooltip="The reconstructed current portfolio value from all realized activity. Does not include unrealized gains on open positions."),
    card("Capital Deployed", f"${total_inv:,.2f}",
         f"Total gross deposits ({summary['n_deposits']} deposits)", "\U0001f4b0", "accent-amber"),
]), unsafe_allow_html=True)

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
total_out = summary["total_withdrawn_eur"] + summary.get("total_card_spent_eur", 0)
net_dep   = summary["total_deposited_eur"] - total_out
st.markdown(cards_row([
    card("Dividends (Net)",   fmt_eur(summary["div_net_eur"], 4),
         f"Gross: {fmt_eur(summary['div_gross_eur'], 4)}", "💵", "accent-purple"),
    card("Total Fees & Taxes",fmt_eur(summary.get("total_fees", 0), 2),
         "Costs, FX fees, stamp duties", "🏛️", "accent-red"),
    card("Interest EUR",      fmt_eur(summary["interest_eur"], 4),
         f"{summary['n_interest']} payments", "🏦", "accent-teal"),
    card("Interest USD",      f"${summary.get('interest_usd',0):,.4f}",
         "Lending + cash", "💲", "accent-amber"),
    card("Cashback",          fmt_eur(summary["cashback_eur"], 4),
         "Card rewards", "🎁", "accent-blue"),
    card("Net Deposited",     fmt_eur(net_dep),
         f"In: {fmt_eur(summary['total_deposited_eur'])} / Out: {fmt_eur(total_out)} (includes spends)", "🏧", "accent-gray"),
]), unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Total Portfolio Progress (Main Yield Chart)
# ---------------------------------------------------------------------------

section("📈 Total Portfolio Value Tracker")
prog_df = analyzer.portfolio_progress_daily(df)
if not prog_df.empty:
    with st.expander("⚙️ Chart Settings & Toggles", expanded=False):
        col_m, col1, col2 = st.columns([0.4, 0.3, 0.3])
        chart_mode = col_m.radio("Chart Type", ["Line (Stacked Area)", "Candlestick"], horizontal=True, label_visibility="collapsed")
        show_dep = col1.checkbox("Show Net Deposits", value=True)
        show_pnl = col1.checkbox("Show Cumulative P&L", value=True)
        show_div = col2.checkbox("Show Dividends", value=True)
        show_int = col2.checkbox("Show Interest", value=True)
    
    st.plotly_chart(charts.chart_total_portfolio(
        prog_df, show_dep, show_pnl, show_div, show_int, chart_mode,
        return_df=return_df if not return_df.empty else None,
    ), use_container_width=True, key="total_portfolio")

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

tab_names = ["📈 P&L Timeline", "📅 Monthly", "🏆 Tickers", "🏢 Companies", "💵 Dividends", "🏦 Interest", "🔄 Trades", "🧾 Fees & Taxes", "📊 Portfolio Value"]

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

    st.plotly_chart(charts.chart_pnl_timeline(timeline, freq_label), use_container_width=True, key="pnl_timeline")

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

    # -- MWRR Return % Dedicated Chart --
    section("📊 Portfolio Return % (MWRR)")
    if not return_df.empty:
        st.plotly_chart(
            charts.chart_return_timeline(
                return_df,
                mwrr_annual if mwrr_annual is not None else float("nan"),
                mwrr_total,
            ),
            use_container_width=True, key="return_timeline",
        )
    else:
        st.markdown("<div class='info-callout'>Upload files with deposit history to compute MWRR.</div>",
                    unsafe_allow_html=True)

    col_a, col_b = st.columns(2)
    with col_a:
        st.plotly_chart(charts.chart_income_pie(summary), use_container_width=True, key="income_pie")
    with col_b:
        st.plotly_chart(charts.chart_deposits_vs_pnl(df), use_container_width=True, key="deposits_vs_pnl")


# ── Tab 2 : Monthly summary ──────────────────────────────────────────────────
with tabs[1]:
    st.plotly_chart(charts.chart_monthly_summary(monthly_df), use_container_width=True, key="monthly_summary")

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
    st.plotly_chart(charts.chart_top_tickers(ticker_df), use_container_width=True, key="top_tickers")

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
                            use_container_width=True, key="company_timeline")

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

        st.plotly_chart(charts.chart_dividend_growth(div_series), use_container_width=True, key="dividend_growth")

        # Revolut-only: surface dividend-tax corrections separately when present.
        dtc_total = summary.get("div_tax_correction_total", 0.0)
        n_dtc = summary.get("n_div_tax_corrections", 0)
        if n_dtc > 0:
            st.markdown(
                "<div class='info-callout'>"
                f"<b>Dividend tax corrections:</b> {n_dtc} row(s) net to "
                f"<b>${dtc_total:+,.4f}</b> in this period. "
                "Revolut posts these as separate adjustments against prior "
                "dividends and they're tracked independently from gross / net totals above."
                "</div>",
                unsafe_allow_html=True,
            )

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
        st.plotly_chart(charts.chart_interest_growth(int_series), use_container_width=True, key="interest_growth")

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


# ── Tab 8 : Fees & Taxes ───────────────────────────────────────────────────
with tabs[7]:
    section("🧾 Analytical Breakdown of Taxes & Fees")
    fees_breakdown = summary.get("fees_breakdown", {})
    if not fees_breakdown:
        st.markdown("<div class='info-callout'>No fees or taxes paid in this period.</div>", unsafe_allow_html=True)
    else:
        # Create standard metric cards for each fee type found
        st.markdown(cards_row([
            card(k, f"{fmt_usd(v, False)}", "Total analytical cost", "💸", "accent-red") if "usd" in k.lower() else card(k, f"{fmt_eur(v)}", "Total analytical cost", "💸", "accent-red")
            for k, v in fees_breakdown.items()
        ]), unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(cards_row([
            card("Total Cumulative Fees", fmt_eur(summary.get("total_fees", 0)), "Sum of all non-trading expenses", "🧾", "accent-amber")
        ]), unsafe_allow_html=True)


# ── Tab 9 : Live Portfolio Equity (yfinance) ────────────────────────────────
with tabs[8]:
    section("📊 True Historical Portfolio Value")
    st.markdown(
        "<div style='font-size:0.9rem; color:rgba(226,228,240,0.6); margin-bottom:1.5rem;'>"
        "Calculates the true total portfolio envelope (Cash + Unrealized Equity) for every past day "
        "by combining your exact historical stock inventory with historical daily price data from Yahoo Finance.</div>",
        unsafe_allow_html=True
    )
    
    if not pv.YFINANCE_AVAILABLE:
        st.error("The `yfinance` library is not installed. Please run `pip install yfinance` to enable this feature.")
    else:
        ohlc_daily = pv.build_portfolio_ohlc(df)
        
        if ohlc_daily.empty:
            st.warning("Not enough data to build a portfolio equity curve.")
        else:
            col1, col2 = st.columns([1, 3])
            with col1:
                st.markdown("<div style='margin-bottom:0.4rem;'></div>", unsafe_allow_html=True)
                interval = st.radio(
                    "Resolution",
                    options=list(pv.INTERVAL_OPTIONS.keys()),
                    format_func=lambda x: pv.INTERVAL_OPTIONS[x],
                    index=1, # 1D
                    horizontal=False,
                )
            with col2:
                st.markdown("<div style='margin-bottom:0.4rem;'></div>", unsafe_allow_html=True)
                chart_style = st.radio(
                    "Chart Style",
                    options=["Candlestick", "Line"],
                    index=0,
                    horizontal=True,
                )

            st.markdown("<br>", unsafe_allow_html=True)
            
            # Resample
            ohlc_resampled = pv.resample_ohlc(ohlc_daily, interval)
            
            # Render main chart
            fig_port = cpv.chart_portfolio_value(
                ohlc_resampled,
                interval=pv.INTERVAL_OPTIONS[interval],
                chart_type=chart_style,
                not_found_tickers=getattr(ohlc_daily, "_not_found_tickers", []),
            )
            st.plotly_chart(fig_port, use_container_width=True, key="true_port_chart")
            
            # Coverage stats
            not_found = getattr(ohlc_daily, "_not_found_tickers", [])
            inventory_cols = pv.compute_daily_inventory(df).columns
            total_tickers = len(inventory_cols) if not inventory_cols.empty else 0
            
            st.markdown("<br>", unsafe_allow_html=True)
            cov_col, note_col = st.columns([1, 2])
            with cov_col:
                if total_tickers > 0:
                    fig_cov = cpv.chart_portfolio_coverage(ohlc_daily, not_found, total_tickers)
                    st.plotly_chart(fig_cov, use_container_width=True, key="true_port_cov")
            with note_col:
                st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
                if not_found:
                    st.warning(
                        "**Missing Tickers:**\n\n"
                        "Yahoo Finance could not find historical data for the following tickers: "
                        f"`{', '.join(not_found)}`.\n\n"
                        "Their value is excluded from the chart."
                    )
                else:
                    st.success("All historical tickers were successfully priced via Yahoo Finance! 100% Coverage.")
