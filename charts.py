"""
charts.py — Plotly chart generation for Trading212 Portfolio Analyzer.
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np


# ---------------------------------------------------------------------------
# Color palette
# ---------------------------------------------------------------------------

PROFIT_COLOR = "#00e676"       # vivid green
LOSS_COLOR = "#ff1744"         # vivid red
NET_POSITIVE_COLOR = "#29b6f6" # sky blue
NET_NEGATIVE_COLOR = "#ff6d00" # orange
DIVIDEND_COLOR = "#ce93d8"     # lavender
INTEREST_COLOR = "#80cbc4"     # teal
ACCENT = "#7c4dff"             # purple
BG_COLOR = "#0e1117"
PAPER_BG = "#0e1117"
GRID_COLOR = "rgba(255,255,255,0.06)"
TEXT_COLOR = "#e0e0e0"
FONT_FAMILY = "Inter, -apple-system, sans-serif"

PLOTLY_LAYOUT = dict(
    font=dict(family=FONT_FAMILY, color=TEXT_COLOR, size=13),
    paper_bgcolor=PAPER_BG,
    plot_bgcolor=BG_COLOR,
    margin=dict(l=20, r=20, t=50, b=20),
    xaxis=dict(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR),
    yaxis=dict(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="rgba(255,255,255,0.1)"),
    hoverlabel=dict(bgcolor="#1e1e2e", bordercolor=ACCENT, font_color=TEXT_COLOR),
)


def _apply_layout(fig, title: str = "", height: int = 420) -> go.Figure:
    layout = dict(**PLOTLY_LAYOUT, title=dict(text=title, font=dict(size=16, color=TEXT_COLOR)), height=height)
    fig.update_layout(**layout)
    return fig


# ---------------------------------------------------------------------------
# 1. Cumulative P&L line chart
# ---------------------------------------------------------------------------

def chart_cumulative_pnl(daily_df: pd.DataFrame) -> go.Figure:
    """Cumulative P&L over time from sell results."""
    if daily_df.empty:
        return _empty_chart("No sell transactions in selected period")

    fig = go.Figure()

    cum = daily_df["Cumulative P&L"]
    pos_mask = cum >= 0

    fig.add_trace(go.Scatter(
        x=daily_df["Date"],
        y=daily_df["Cumulative P&L"],
        mode="lines",
        name="Cumulative P&L",
        line=dict(color=NET_POSITIVE_COLOR, width=2.5),
        fill="tozeroy",
        fillcolor="rgba(41, 182, 246, 0.12)",
        hovertemplate="<b>%{x}</b><br>Cumulative P&L: %{y:+.2f}<extra></extra>",
    ))

    # Zero line
    fig.add_hline(y=0, line_color="rgba(255,255,255,0.25)", line_dash="dot", line_width=1)

    _apply_layout(fig, "📈 Cumulative Net P&L Over Time")
    fig.update_yaxes(title_text="P&L (original currency)", tickprefix="$")
    return fig


# ---------------------------------------------------------------------------
# 2. Daily P&L bar chart
# ---------------------------------------------------------------------------

def chart_daily_pnl(daily_df: pd.DataFrame) -> go.Figure:
    """Bar chart of daily P&L colored green/red."""
    if daily_df.empty:
        return _empty_chart("No sell transactions in selected period")

    colors = [PROFIT_COLOR if v >= 0 else LOSS_COLOR for v in daily_df["Daily P&L"]]

    fig = go.Figure(go.Bar(
        x=daily_df["Date"],
        y=daily_df["Daily P&L"],
        marker_color=colors,
        name="Daily P&L",
        hovertemplate="<b>%{x}</b><br>P&L: %{y:+.2f}<extra></extra>",
    ))

    fig.add_hline(y=0, line_color="rgba(255,255,255,0.3)", line_width=1)
    _apply_layout(fig, "📊 Daily P&L")
    fig.update_yaxes(title_text="P&L (trade currency)", tickprefix="$")
    return fig


# ---------------------------------------------------------------------------
# 3. Monthly summary grouped bar chart
# ---------------------------------------------------------------------------

def chart_monthly_summary(monthly_df: pd.DataFrame) -> go.Figure:
    """Grouped bars: Profit, Loss, Dividends, Interest per month."""
    if monthly_df.empty:
        return _empty_chart("No data in selected period")

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=monthly_df["Month"], y=monthly_df["Profit"],
        name="Profit", marker_color=PROFIT_COLOR,
        hovertemplate="<b>%{x}</b><br>Profit: %{y:.2f}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=monthly_df["Month"], y=monthly_df["Loss"],
        name="Loss", marker_color=LOSS_COLOR,
        hovertemplate="<b>%{x}</b><br>Loss: %{y:.2f}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=monthly_df["Month"], y=monthly_df["Net P&L"],
        name="Net P&L",
        marker_color=[NET_POSITIVE_COLOR if v >= 0 else NET_NEGATIVE_COLOR for v in monthly_df["Net P&L"]],
        hovertemplate="<b>%{x}</b><br>Net P&L: %{y:+.2f}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=monthly_df["Month"], y=monthly_df["Dividends (EUR)"],
        name="Dividends (EUR)", marker_color=DIVIDEND_COLOR,
        hovertemplate="<b>%{x}</b><br>Dividends: €%{y:.4f}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=monthly_df["Month"], y=monthly_df["Interest"],
        name="Interest", marker_color=INTEREST_COLOR,
        hovertemplate="<b>%{x}</b><br>Interest: %{y:.4f}<extra></extra>",
    ))

    fig.update_layout(barmode="group")
    _apply_layout(fig, "📅 Monthly Breakdown", height=450)
    fig.update_yaxes(title_text="Amount")
    return fig


# ---------------------------------------------------------------------------
# 4. Top performers (ticker P&L bar)
# ---------------------------------------------------------------------------

def chart_top_tickers(ticker_df: pd.DataFrame, top_n: int = 15) -> go.Figure:
    """Horizontal bar chart of top + worst tickers by Net P&L."""
    if ticker_df.empty:
        return _empty_chart("No sell transactions in selected period")

    # Show top N by absolute net P&L
    top = ticker_df.nlargest(top_n // 2 + 1, "Net P&L") if len(ticker_df) >= top_n // 2 else ticker_df
    bottom = ticker_df.nsmallest(top_n // 2, "Net P&L")
    combined = pd.concat([top, bottom]).drop_duplicates("Ticker").sort_values("Net P&L")

    colors = [PROFIT_COLOR if v >= 0 else LOSS_COLOR for v in combined["Net P&L"]]

    fig = go.Figure(go.Bar(
        x=combined["Net P&L"],
        y=combined["Ticker"],
        orientation="h",
        marker_color=colors,
        text=[f"{v:+.2f}" for v in combined["Net P&L"]],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Net P&L: %{x:+.2f}<extra></extra>",
    ))

    fig.add_vline(x=0, line_color="rgba(255,255,255,0.3)", line_width=1)
    _apply_layout(fig, "🏆 Top & Worst Performing Tickers", height=max(350, len(combined) * 32))
    fig.update_xaxes(title_text="Net P&L (trade currency)")
    return fig


# ---------------------------------------------------------------------------
# 5. Income breakdown pie chart
# ---------------------------------------------------------------------------

def chart_income_pie(summary: dict) -> go.Figure:
    """Pie chart of income sources: trade profit, dividends, interest, cashback."""
    labels, values, pull = [], [], []

    if summary.get("gross_profit", 0) > 0:
        labels.append("Trade Profit (USD)")
        values.append(summary["gross_profit"])
        pull.append(0.05)

    if summary.get("div_net_eur", 0) > 0:
        labels.append("Dividends (EUR)")
        values.append(summary["div_net_eur"])
        pull.append(0.02)

    if summary.get("interest_eur", 0) + summary.get("interest_usd", 0) > 0:
        labels.append("Interest")
        values.append(abs(summary["interest_eur"]) + abs(summary.get("interest_usd", 0)))
        pull.append(0.02)

    if summary.get("cashback_eur", 0) > 0:
        labels.append("Cashback (EUR)")
        values.append(summary["cashback_eur"])
        pull.append(0.02)

    if not labels:
        return _empty_chart("No income data in selected period")

    COLORS = [PROFIT_COLOR, DIVIDEND_COLOR, INTEREST_COLOR, "#ffd54f", ACCENT]

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        pull=pull,
        hole=0.45,
        marker_colors=COLORS[:len(labels)],
        textinfo="label+percent",
        hovertemplate="<b>%{label}</b><br>Amount: %{value:.4f}<br>Share: %{percent}<extra></extra>",
    ))

    fig.update_layout(
        annotations=[dict(text="Income", x=0.5, y=0.5, font_size=14, showarrow=False, font_color=TEXT_COLOR)]
    )
    _apply_layout(fig, "🍕 Income Sources Breakdown", height=420)
    return fig


# ---------------------------------------------------------------------------
# 6. Cumulative deposits vs P&L
# ---------------------------------------------------------------------------

def chart_deposits_vs_pnl(df: pd.DataFrame) -> go.Figure:
    """Line chart comparing cumulative deposits against cumulative P&L."""
    if df.empty:
        return _empty_chart("No data")

    all_days = pd.date_range(df["Time"].min().date(), df["Time"].max().date(), freq="D")

    deposits = df[df["_category"] == "deposit"].copy()
    deposits["Date"] = deposits["Time"].dt.date
    dep_daily = deposits.groupby("Date")["Total"].sum().reindex(
        all_days.date, fill_value=0
    ).cumsum()

    sells = df[df["_category"] == "sell"].copy()
    sells["Date"] = sells["Time"].dt.date
    pnl_daily = sells.groupby("Date")["Result"].sum().fillna(0).reindex(
        all_days.date, fill_value=0
    ).cumsum()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dep_daily.index, y=dep_daily.values,
        mode="lines", name="Cumul. Deposits (EUR)",
        line=dict(color="#ffd54f", width=2),
        hovertemplate="<b>%{x}</b><br>Deposits: €%{y:.2f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=pnl_daily.index, y=pnl_daily.values,
        mode="lines", name="Cumul. Trade P&L (USD)",
        line=dict(color=NET_POSITIVE_COLOR, width=2, dash="dot"),
        hovertemplate="<b>%{x}</b><br>P&L: %{y:+.2f}<extra></extra>",
    ))

    _apply_layout(fig, "💰 Cumulative Deposits vs Trade P&L", height=380)
    return fig


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _empty_chart(message: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message, x=0.5, y=0.5, xref="paper", yref="paper",
        showarrow=False, font=dict(size=15, color="rgba(255,255,255,0.4)")
    )
    _apply_layout(fig)
    return fig
