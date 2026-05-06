"""
charts_portfolio_value.py — OHLC / Line chart for the Portfolio Value Chart tab.

Renders a premium trading-terminal style chart that treats the user's portfolio
as an index fund, showing its full historical market value using candlestick
OHLC bars constructed from daily unrealized equity valuations.
"""

from __future__ import annotations

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# Reuse design tokens from the existing charts module
from charts import (
    BASE_LAYOUT, FONT,
    C_BG, C_PANEL, C_GRID, C_TEXT, C_MUTED, C_BORDER,
    C_GREEN, C_GREEN_DIM, C_RED, C_RED_DIM,
    C_BLUE, C_BLUE_DIM, C_AMBER, C_TEAL, C_TEAL_DIM,
    C_PURPLE, C_PURPLE_DIM,
)

_C_UP_FILL   = "rgba(0,255,136,0.18)"
_C_DOWN_FILL = "rgba(255,0,85,0.18)"


def _hex_to_rgb(hex_color: str) -> str:
    h = hex_color.lstrip("#")
    if len(h) == 6:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"{r},{g},{b}"
    return "200,200,200"


def chart_portfolio_value(
    ohlc_df: pd.DataFrame,
    interval: str,
    chart_type: str = "Candlestick",
    base_currency: str = "USD",
    not_found_tickers: list | None = None,
) -> go.Figure:
    """
    Render the full Portfolio Value chart in trading-terminal style.

    Top panel  : Candlestick OHLC or line chart of total portfolio value.
                 A 20-period moving average is overlaid in amber.
    Bottom panel: Bar chart of the unrealized equity component (holdings value).
                  Complements the top chart like a volume sub-plot.
    """
    if ohlc_df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="⚠️ No price data available. Check your date range or yfinance connectivity.",
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
            font=dict(size=14, color=C_MUTED, family=FONT),
        )
        fig.update_layout(
            paper_bgcolor=C_BG, plot_bgcolor=C_PANEL,
            height=520,
        )
        return fig

    x = ohlc_df["Date"]

    first_close = float(ohlc_df["Close"].iloc[0])
    last_close  = float(ohlc_df["Close"].iloc[-1])
    pct_change  = (last_close - first_close) / first_close * 100 if first_close else 0.0
    trend_up    = pct_change >= 0
    trend_color = C_GREEN if trend_up else C_RED
    trend_arrow = "▲" if trend_up else "▼"
    currency_symbol = "€" if base_currency == "EUR" else "$"

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.70, 0.30],
        subplot_titles=("", ""),
    )

    # ── Top: Candlestick or Line ──────────────────────────────────────────────
    if chart_type == "Candlestick":
        fig.add_trace(go.Candlestick(
            x=x,
            open=ohlc_df["Open"],
            high=ohlc_df["High"],
            low=ohlc_df["Low"],
            close=ohlc_df["Close"],
            increasing=dict(line=dict(color=C_GREEN, width=1), fillcolor=_C_UP_FILL),
            decreasing=dict(line=dict(color=C_RED,   width=1), fillcolor=_C_DOWN_FILL),
            whiskerwidth=0.3,
            name="Portfolio",
            customdata=ohlc_df[["_open_to_close_usd", "_open_to_close_pct"]].fillna(0),
            hovertemplate=(
                f"<b>%{{x}}</b><br><br>"
                f"Open:  {currency_symbol}%{{open:,.2f}}<br>"
                f"High:  {currency_symbol}%{{high:,.2f}}<br>"
                f"Low:   {currency_symbol}%{{low:,.2f}}<br>"
                f"Close: {currency_symbol}%{{close:,.2f}}<br><br>"
                "<b>Interval &Delta;:</b> %{customdata[0]:+,.2f} (%{customdata[1]:+.2f}%)<extra></extra>"
            ),
        ), row=1, col=1)
    else:
        # Filled line — gradient fill from zero
        fig.add_trace(go.Scatter(
            x=x,
            y=ohlc_df["Close"],
            mode="lines",
            line=dict(color=trend_color, width=2.5, shape="spline", smoothing=0.5),
            fill="tozeroy",
            fillcolor=f"rgba({_hex_to_rgb(trend_color)},0.07)",
            name="Portfolio Value",
            customdata=ohlc_df[["_open_to_close_usd", "_open_to_close_pct"]].fillna(0),
            hovertemplate=(
                f"<b>%{{x}}</b><br>"
                f"Value: {currency_symbol}%{{y:,.2f}}<br><br>"
                "<b>Interval &Delta;:</b> %{customdata[0]:+,.2f} (%{customdata[1]:+.2f}%)<extra></extra>"
            ),
        ), row=1, col=1)

    # ── Moving average ────────────────────────────────────────────────────────
    ma_window = max(5, min(20, len(ohlc_df) // 5))
    if len(ohlc_df) >= ma_window:
        ma = ohlc_df["Close"].rolling(ma_window, min_periods=1).mean()
        fig.add_trace(go.Scatter(
            x=x, y=ma,
            mode="lines",
            line=dict(color=C_AMBER, width=1.8, dash="dot"),
            name=f"MA({ma_window})",
            opacity=0.85,
            hovertemplate=f"MA({ma_window}): {currency_symbol}%{{y:,.2f}}<extra></extra>",
        ), row=1, col=1)

    # ── Net Cost Basis ────────────────────────────────────────────────────────
    net_dep = ohlc_df.get("Net_Deposits")
    if net_dep is not None:
        fig.add_trace(go.Scatter(
            x=x, y=net_dep,
            mode="lines",
            line=dict(color=C_BLUE, width=1.4, dash="longdash"),
            name="Net Cost Basis",
            opacity=0.6,
            hovertemplate=f"Basis: {currency_symbol}%{{y:,.2f}}<extra></extra>",
        ), row=1, col=1)

    # ── Alternate Currency Portfolio Value ────────────────────────────────────
    alt_close = ohlc_df.get("Alt_Close")
    if alt_close is not None:
        alt_ccy = "EUR" if base_currency == "USD" else "USD"
        alt_symbol = "€" if alt_ccy == "EUR" else "$"
        fig.add_trace(go.Scatter(
            x=x, y=alt_close,
            mode="lines",
            line=dict(color=C_MUTED, width=1.2, dash="dot"),
            name=f"Value ({alt_ccy})",
            opacity=0.5,
            hovertemplate=f"{alt_ccy}: {alt_symbol}%{{y:,.2f}}<extra></extra>",
        ), row=1, col=1)

    # ── Zero / baseline reference ─────────────────────────────────────────────
    fig.add_hline(
        y=first_close,
        line_color="rgba(255,255,255,0.12)",
        line_width=1,
        line_dash="dot",
        row=1, col=1,
    )

    # ── Bottom: Holdings (unrealized equity) bar chart ────────────────────────
    equity = ohlc_df.get("Equity", pd.Series(np.zeros(len(ohlc_df))))
    cash   = ohlc_df.get("Cash",   pd.Series(np.zeros(len(ohlc_df))))

    eq_colors = [
        C_TEAL if float(e) >= 0 else C_RED
        for e in equity
    ]
    fig.add_trace(go.Bar(
        x=x,
        y=equity,
        marker_color=eq_colors,
        marker_opacity=0.55,
        marker_line_width=0,
        name="Unrealized Holdings",
        hovertemplate=f"<b>%{{x}}</b><br>Holdings: {currency_symbol}%{{y:,.2f}}<extra></extra>",
    ), row=2, col=1)

    # Cash as a thin line overlay on sub-chart
    fig.add_trace(go.Scatter(
        x=x, y=cash,
        mode="lines",
        line=dict(color=C_PURPLE, width=1.5, dash="dot"),
        name="Cash Balance",
        opacity=0.7,
        hovertemplate=f"Cash: {currency_symbol}%{{y:,.2f}}<extra></extra>",
    ), row=2, col=1)

    # currency_symbol already defined above
    fig.update_layout(
        **{k: v for k, v in BASE_LAYOUT.items()
           if k not in ("xaxis", "yaxis", "legend", "margin")},
        height=640,
        title=dict(
            text=(
                f"📈 Portfolio Value (Unrealized + Realized)  ·  "
                f"<span style='color:{trend_color};font-weight:700'>"
                f"{trend_arrow} {pct_change:+.2f}%</span>"
                f"  ·  {currency_symbol}{last_close:,.0f} current  ·  {interval}"
            ),
            font=dict(family=FONT, size=14, color=C_TEXT),
            x=0, xanchor="left",
        ),
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom", y=1.02,
            xanchor="right",  x=1,
            font=dict(family=FONT, size=11, color=C_MUTED),
            bgcolor="rgba(0,0,0,0)",
        ),
    )
    # Separate call to avoid 'multiple values for keyword argument margin'
    # that occurs when make_subplots pre-registers margin in the figure layout.
    fig.update_layout(margin=dict(l=16, r=30, t=60, b=20))

    fig.update_xaxes(
        gridcolor=C_GRID,
        showline=False,
        tickfont=dict(color=C_MUTED, size=11, family=FONT),
        zeroline=False,
    )
    fig.update_yaxes(
        gridcolor=C_GRID,
        showline=False,
        tickfont=dict(color=C_MUTED, size=11, family=FONT),
        tickprefix=currency_symbol,
        tickformat=",.0f",
        zeroline=False,
    )
    fig.update_yaxes(title_text=f"Portfolio Value ({base_currency})", row=1, col=1,
                     title_font=dict(color=C_MUTED, size=11))
    fig.update_yaxes(title_text=f"Holdings ({base_currency})", row=2, col=1,
                     title_font=dict(color=C_MUTED, size=11))

    return fig


def chart_portfolio_coverage(
    ohlc_df: pd.DataFrame,
    not_found: list,
    total_tickers: int,
) -> go.Figure:
    """
    Small coverage donut showing what % of tickers were successfully priced
    vs. those that failed to resolve on Yahoo Finance.
    """
    priced = total_tickers - len(not_found)
    fig = go.Figure(go.Pie(
        values=[priced, len(not_found)],
        labels=["Priced", "Not Found"],
        marker=dict(colors=[C_TEAL, C_RED_DIM]),
        hole=0.65,
        textinfo="none",
        hovertemplate="%{label}: %{value}<extra></extra>",
    ))
    fig.update_layout(
        **{k: v for k, v in BASE_LAYOUT.items()
           if k not in ("xaxis", "yaxis", "legend", "margin")},
        height=200,
        margin=dict(l=10, r=10, t=30, b=10),
        title=dict(
            text=f"Data Coverage: {priced}/{total_tickers} tickers priced",
            font=dict(family=FONT, size=12, color=C_MUTED),
            x=0.5, xanchor="center",
        ),
        showlegend=True,
        legend=dict(
            orientation="h", x=0.5, xanchor="center", y=-0.05,
            font=dict(size=11, color=C_MUTED),
        ),
    )
    return fig
