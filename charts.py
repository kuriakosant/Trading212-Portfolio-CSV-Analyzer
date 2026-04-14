"""
charts.py — Plotly chart generation for Trading212 Portfolio Analyzer.
All charts use a premium dark theme with rich hover tooltips.
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------

C_BG       = "#0a0b14"
C_PANEL    = "#11121e"
C_BORDER   = "rgba(255,255,255,0.07)"
C_GRID     = "rgba(255,255,255,0.05)"
C_TEXT     = "#e2e4f0"
C_MUTED    = "rgba(226,228,240,0.45)"
C_GREEN    = "#22c55e"
C_GREEN_DIM= "rgba(34,197,94,0.12)"
C_RED      = "#f43f5e"
C_RED_DIM  = "rgba(244,63,94,0.12)"
C_BLUE     = "#38bdf8"
C_BLUE_DIM = "rgba(56,189,248,0.12)"
C_PURPLE   = "#a78bfa"
C_PURPLE_DIM="rgba(167,139,250,0.12)"
C_AMBER    = "#fbbf24"
C_TEAL     = "#2dd4bf"
C_TEAL_DIM = "rgba(45,212,191,0.12)"
FONT       = "Inter, -apple-system, BlinkMacSystemFont, sans-serif"

BASE_LAYOUT = dict(
    font        = dict(family=FONT, color=C_TEXT, size=13),
    paper_bgcolor = C_BG,
    plot_bgcolor  = C_PANEL,
    margin      = dict(l=12, r=12, t=52, b=16),
    hoverlabel  = dict(
        bgcolor="#1c1d2e",
        bordercolor=C_PURPLE,
        font=dict(family=FONT, color=C_TEXT, size=13),
    ),
    legend = dict(
        bgcolor="rgba(255,255,255,0.03)",
        bordercolor=C_BORDER,
        borderwidth=1,
        font=dict(size=12),
    ),
    xaxis = dict(
        gridcolor=C_GRID, zerolinecolor=C_GRID,
        showline=False, tickfont=dict(color=C_MUTED, size=11),
    ),
    yaxis = dict(
        gridcolor=C_GRID, zerolinecolor="rgba(255,255,255,0.15)",
        showline=False, tickfont=dict(color=C_MUTED, size=11),
    ),
)


def _fig(title: str = "", height: int = 420) -> go.Figure:
    fig = go.Figure()
    layout = dict(**BASE_LAYOUT,
        height=height,
        title=dict(
            text=title,
            font=dict(family=FONT, size=15, color=C_TEXT),
            x=0, xanchor="left", pad=dict(l=4),
        ),
    )
    fig.update_layout(**layout)
    return fig


def _add_zero_line(fig, axis="y"):
    if axis == "y":
        fig.add_hline(y=0, line_color="rgba(255,255,255,0.18)", line_width=1)
    else:
        fig.add_vline(x=0, line_color="rgba(255,255,255,0.18)", line_width=1)


def _empty(msg: str) -> go.Figure:
    fig = _fig()
    fig.add_annotation(
        text=msg, x=0.5, y=0.5, xref="paper", yref="paper",
        showarrow=False, font=dict(size=14, color=C_MUTED),
    )
    return fig


# ---------------------------------------------------------------------------
# 1. P&L Timeline  (resampled — Daily / Weekly / Monthly / Quarterly)
# ---------------------------------------------------------------------------

def chart_pnl_timeline(timeline_df: pd.DataFrame, freq_label: str = "Daily") -> go.Figure:
    """
    Interactive area + bar combo chart.
    Top: Cumulative P&L area. Bottom: Period P&L bars.
    Hover shows: date, period P&L, cumulative P&L, win rate.
    """
    if timeline_df.empty:
        return _empty("No sell transactions in selected period")

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.65, 0.35],
        vertical_spacing=0.04,
        subplot_titles=("", ""),
    )

    x = timeline_df["Period"]
    cum = timeline_df["Cumulative P&L"]
    period = timeline_df["Period P&L"]

    # ---- Cumulative area (top) ----
    pos_fill = C_GREEN_DIM if cum.iloc[-1] >= 0 else C_RED_DIM
    line_col = C_GREEN    if cum.iloc[-1] >= 0 else C_RED

    hover_top = (
        "<b>%{x|%b %d, %Y}</b><br>"
        "Cumulative P&L: <b>%{y:+,.2f}</b><br>"
        "Win rate: <b>" + timeline_df["Win Rate %"].astype(str) + "%</b><br>"
        "<extra></extra>"
    )

    fig.add_trace(go.Scatter(
        x=x, y=cum,
        mode="lines",
        name="Cumulative P&L",
        line=dict(color=line_col, width=2.5, shape="spline", smoothing=0.4),
        fill="tozeroy",
        fillcolor=pos_fill,
        customdata=np.column_stack([
            timeline_df["Period P&L"],
            timeline_df["Win Rate %"],
            timeline_df["Trades"],
        ]),
        hovertemplate=(
            "<b>%{x|%b %d, %Y}</b><br>"
            "─────────────────<br>"
            "Cumulative P&L : <b>%{y:+,.2f}</b><br>"
            "Period P&L     : <b>%{customdata[0]:+,.2f}</b><br>"
            "Win rate       : <b>%{customdata[1]}%</b><br>"
            "Trades         : %{customdata[2]}"
            "<extra></extra>"
        ),
    ), row=1, col=1)

    # ---- Period P&L bars (bottom) ----
    bar_colors = [C_GREEN if v >= 0 else C_RED for v in period]
    fig.add_trace(go.Bar(
        x=x, y=period,
        name="Period P&L",
        marker_color=bar_colors,
        marker_line_width=0,
        customdata=np.column_stack([timeline_df["Wins"], timeline_df["Losses"]]),
        hovertemplate=(
            "<b>%{x|%b %d, %Y}</b><br>"
            "Period P&L : <b>%{y:+,.2f}</b><br>"
            "Wins / Losses : %{customdata[0]} / %{customdata[1]}"
            "<extra></extra>"
        ),
    ), row=2, col=1)

    fig.add_hline(y=0, line_color="rgba(255,255,255,0.18)", line_width=1, row=2, col=1)

    fig.update_layout(
        **{k: v for k, v in BASE_LAYOUT.items() if k not in ("xaxis", "yaxis")},
        height=520,
        title=dict(
            text=f"📈 P&L Timeline — {freq_label} view",
            font=dict(family=FONT, size=15, color=C_TEXT),
            x=0, xanchor="left",
        ),
        showlegend=False,
        hovermode="x unified",
    )
    fig.update_xaxes(gridcolor=C_GRID, showline=False, tickfont=dict(color=C_MUTED, size=11))
    fig.update_yaxes(gridcolor=C_GRID, showline=False, tickfont=dict(color=C_MUTED, size=11))
    fig.update_yaxes(title_text="Cumulative P&L ($)", row=1, col=1,
                     title_font=dict(color=C_MUTED, size=11))
    fig.update_yaxes(title_text="Period P&L ($)", row=2, col=1,
                     title_font=dict(color=C_MUTED, size=11))

    return fig


# ---------------------------------------------------------------------------
# 2. Dividend growth — step chart with each payment + running total
# ---------------------------------------------------------------------------

def chart_dividend_growth(div_series: pd.DataFrame) -> go.Figure:
    """
    Step + bar combo.
    Top: Cumulative dividend total (step line).
    Individual bars colored by ticker.
    """
    if div_series.empty:
        return _empty("No dividend payments in selected period")

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.6, 0.4],
        vertical_spacing=0.04,
    )

    # Cumulative step line
    fig.add_trace(go.Scatter(
        x=div_series["Time"],
        y=div_series["Cumulative (EUR)"],
        mode="lines+markers",
        name="Cumulative Dividends",
        line=dict(color=C_PURPLE, width=2.5, shape="hv"),
        marker=dict(size=7, color=C_PURPLE, symbol="circle",
                    line=dict(color=C_BG, width=2)),
        fill="tozeroy",
        fillcolor=C_PURPLE_DIM,
        customdata=div_series[["Ticker", "Net (EUR)", "Withholding (EUR)"]].values,
        hovertemplate=(
            "<b>%{x|%b %d, %Y}</b><br>"
            "─────────────────<br>"
            "Ticker         : <b>%{customdata[0]}</b><br>"
            "This payment   : <b>€%{customdata[1]:.4f}</b><br>"
            "Withholding    : €%{customdata[2]:.4f}<br>"
            "Running total  : <b>€%{y:.4f}</b>"
            "<extra></extra>"
        ),
    ), row=1, col=1)

    # Individual dividend bars
    tickers = div_series["Ticker"].fillna("Unknown").unique()
    palette = [C_PURPLE, C_BLUE, C_TEAL, C_AMBER, C_GREEN, "#f472b6", "#fb923c"]
    color_map = {t: palette[i % len(palette)] for i, t in enumerate(tickers)}

    for ticker in tickers:
        sub = div_series[div_series["Ticker"].fillna("Unknown") == ticker]
        fig.add_trace(go.Bar(
            x=sub["Time"],
            y=sub["Net (EUR)"],
            name=ticker,
            marker_color=color_map[ticker],
            marker_line_width=0,
            hovertemplate=(
                f"<b>{ticker}</b><br>"
                "%{x|%b %d, %Y}<br>"
                "Net: <b>€%{y:.4f}</b>"
                "<extra></extra>"
            ),
        ), row=2, col=1)

    fig.update_layout(
        **{k: v for k, v in BASE_LAYOUT.items() if k not in ("xaxis", "yaxis")},
        height=480,
        title=dict(
            text="💵 Dividend Growth — Cumulative & Individual Payments",
            font=dict(family=FONT, size=15, color=C_TEXT),
            x=0, xanchor="left",
        ),
        barmode="stack",
    )
    fig.update_xaxes(gridcolor=C_GRID, showline=False, tickfont=dict(color=C_MUTED, size=11))
    fig.update_yaxes(gridcolor=C_GRID, showline=False, tickfont=dict(color=C_MUTED, size=11))
    fig.update_yaxes(title_text="Cumulative (€)", row=1, col=1,
                     title_font=dict(color=C_MUTED, size=11))
    fig.update_yaxes(title_text="Per payment (€)", row=2, col=1,
                     title_font=dict(color=C_MUTED, size=11))
    return fig


# ---------------------------------------------------------------------------
# 3. Interest growth — EUR + USD separate step lines
# ---------------------------------------------------------------------------

def chart_interest_growth(int_series: pd.DataFrame) -> go.Figure:
    """
    Separate cumulative step lines for EUR and USD interest income.
    Each payment shown as a marker.
    """
    if int_series.empty:
        return _empty("No interest payments in selected period")

    fig = _fig("🏦 Interest Income — Cumulative Growth", height=420)

    eur = int_series[int_series["Currency"] == "EUR"].copy()
    usd = int_series[int_series["Currency"] == "USD"].copy()

    if not eur.empty:
        fig.add_trace(go.Scatter(
            x=eur["Time"], y=eur["Cumulative EUR"],
            mode="lines+markers",
            name="EUR Interest",
            line=dict(color=C_TEAL, width=2.5, shape="hv"),
            marker=dict(size=7, color=C_TEAL, symbol="circle",
                        line=dict(color=C_BG, width=2)),
            fill="tozeroy",
            fillcolor=C_TEAL_DIM,
            customdata=eur[["Amount", "Action"]].values,
            hovertemplate=(
                "<b>%{x|%b %d, %Y}</b><br>"
                "Type : %{customdata[1]}<br>"
                "Amount : <b>€%{customdata[0]:.4f}</b><br>"
                "Running total : <b>€%{y:.4f}</b>"
                "<extra></extra>"
            ),
        ))

    if not usd.empty:
        fig.add_trace(go.Scatter(
            x=usd["Time"], y=usd["Cumulative USD"],
            mode="lines+markers",
            name="USD Interest",
            line=dict(color=C_AMBER, width=2.5, shape="hv"),
            marker=dict(size=7, color=C_AMBER, symbol="diamond",
                        line=dict(color=C_BG, width=2)),
            fill="tozeroy",
            fillcolor="rgba(251,191,36,0.08)",
            customdata=usd[["Amount", "Action"]].values,
            hovertemplate=(
                "<b>%{x|%b %d, %Y}</b><br>"
                "Type : %{customdata[1]}<br>"
                "Amount : <b>${%{customdata[0]:.4f}</b><br>"
                "Running total : <b>${%{y:.4f}</b>"
                "<extra></extra>"
            ),
        ))

    fig.update_yaxes(title_text="Cumulative amount")
    return fig


# ---------------------------------------------------------------------------
# 4. Monthly summary — grouped bars
# ---------------------------------------------------------------------------

def chart_monthly_summary(monthly_df: pd.DataFrame) -> go.Figure:
    if monthly_df.empty:
        return _empty("No data in selected period")

    fig = _fig("📅 Monthly Breakdown", height=440)

    fig.add_trace(go.Bar(
        x=monthly_df["Month"], y=monthly_df["Profit"],
        name="Profit", marker_color=C_GREEN, marker_line_width=0,
        hovertemplate="<b>%{x}</b><br>Profit: <b>$%{y:,.2f}</b><extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=monthly_df["Month"], y=monthly_df["Loss"],
        name="Loss", marker_color=C_RED, marker_line_width=0,
        hovertemplate="<b>%{x}</b><br>Loss: <b>$%{y:,.2f}</b><extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=monthly_df["Month"], y=monthly_df["Net P&L"],
        name="Net P&L",
        marker_color=[C_GREEN if v >= 0 else C_RED for v in monthly_df["Net P&L"]],
        marker_line_width=0,
        hovertemplate="<b>%{x}</b><br>Net P&L: <b>$%{y:+,.2f}</b><extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=monthly_df["Month"], y=monthly_df["Dividends (EUR)"],
        name="Dividends (€)", marker_color=C_PURPLE, marker_line_width=0,
        hovertemplate="<b>%{x}</b><br>Dividends: <b>€%{y:.4f}</b><extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=monthly_df["Month"], y=monthly_df["Interest"],
        name="Interest", marker_color=C_TEAL, marker_line_width=0,
        hovertemplate="<b>%{x}</b><br>Interest: <b>%{y:.4f}</b><extra></extra>",
    ))

    fig.update_layout(barmode="group")
    return fig


# ---------------------------------------------------------------------------
# 5. Top tickers bar chart
# ---------------------------------------------------------------------------

def chart_top_tickers(ticker_df: pd.DataFrame, top_n: int = 15) -> go.Figure:
    if ticker_df.empty:
        return _empty("No sell transactions in selected period")

    n_top = max(1, top_n // 2)
    top    = ticker_df.nlargest(n_top, "Net P&L")
    bottom = ticker_df.nsmallest(n_top, "Net P&L")
    combined = pd.concat([top, bottom]).drop_duplicates("Ticker").sort_values("Net P&L")

    fig = _fig("🏆 Best & Worst Performing Tickers",
               height=max(340, len(combined) * 34))

    fig.add_trace(go.Bar(
        x=combined["Net P&L"], y=combined["Ticker"],
        orientation="h",
        marker_color=[C_GREEN if v >= 0 else C_RED for v in combined["Net P&L"]],
        marker_line_width=0,
        customdata=combined[["Profit", "Loss", "Sell Trades"]].values,
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Net P&L : <b>$%{x:+,.2f}</b><br>"
            "Profit  : $%{customdata[0]:,.2f}<br>"
            "Loss    : $%{customdata[1]:,.2f}<br>"
            "Trades  : %{customdata[2]}"
            "<extra></extra>"
        ),
        text=[f"${v:+,.2f}" for v in combined["Net P&L"]],
        textposition="outside",
        textfont=dict(color=[C_GREEN if v >= 0 else C_RED for v in combined["Net P&L"]], size=11),
    ))

    _add_zero_line(fig, axis="x")
    fig.update_xaxes(title_text="Net P&L ($)")
    return fig


# ---------------------------------------------------------------------------
# 6. Income sources pie / donut
# ---------------------------------------------------------------------------

def chart_income_pie(summary: dict) -> go.Figure:
    labels, values, pull = [], [], []
    COLOR_MAP = {
        "Trade Profit ($)": C_GREEN,
        "Dividends (€)":    C_PURPLE,
        "Interest (€)":     C_TEAL,
        "Interest ($)":     C_AMBER,
        "Cashback (€)":     C_BLUE,
    }

    if summary.get("gross_profit", 0) > 0:
        labels.append("Trade Profit ($)"); values.append(summary["gross_profit"]); pull.append(0.06)
    if summary.get("div_net_eur", 0) > 0:
        labels.append("Dividends (€)"); values.append(summary["div_net_eur"]); pull.append(0.02)
    if summary.get("interest_eur", 0) > 0:
        labels.append("Interest (€)"); values.append(summary["interest_eur"]); pull.append(0.02)
    if summary.get("interest_usd", 0) > 0:
        labels.append("Interest ($)"); values.append(summary["interest_usd"]); pull.append(0.02)
    if summary.get("cashback_eur", 0) > 0:
        labels.append("Cashback (€)"); values.append(summary["cashback_eur"]); pull.append(0.02)

    if not labels:
        return _empty("No income data in selected period")

    colors = [COLOR_MAP.get(l, C_BLUE) for l in labels]

    fig = _fig("🍩 Income Sources", height=380)
    fig.add_trace(go.Pie(
        labels=labels, values=values, pull=pull, hole=0.52,
        marker=dict(colors=colors, line=dict(color=C_BG, width=3)),
        textinfo="label+percent",
        textfont=dict(size=12, color=C_TEXT),
        hovertemplate="<b>%{label}</b><br>Amount: %{value:,.4f}<br>Share: %{percent}<extra></extra>",
    ))
    fig.update_layout(
        annotations=[dict(
            text=f"<b>${summary.get('gross_profit',0):,.0f}</b><br>profit",
            x=0.5, y=0.5, xref="paper", yref="paper",
            showarrow=False, font=dict(size=14, color=C_TEXT),
        )],
        showlegend=True,
        legend=dict(orientation="v", x=1.02, y=0.5,
                    font=dict(size=11), bgcolor="transparent"),
    )
    return fig


# ---------------------------------------------------------------------------
# 7. Deposits vs cumulative P&L
# ---------------------------------------------------------------------------

def chart_deposits_vs_pnl(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return _empty("No data")

    all_days = pd.date_range(df["Time"].min().date(), df["Time"].max().date(), freq="D")

    deposits = df[df["_category"] == "deposit"].copy()
    deposits["Date"] = deposits["Time"].dt.date
    dep = deposits.groupby("Date")["Total"].sum().reindex(all_days.date, fill_value=0).cumsum()

    sells = df[df["_category"] == "sell"].copy()
    sells["Date"] = sells["Time"].dt.date
    pnl = sells.groupby("Date")["Result"].sum().fillna(0).reindex(all_days.date, fill_value=0).cumsum()

    fig = _fig("💰 Cumulative Deposits vs Trade P&L", height=360)

    fig.add_trace(go.Scatter(
        x=dep.index.astype(str), y=dep.values,
        mode="lines", name="Deposits (€)",
        line=dict(color=C_AMBER, width=2, shape="spline"),
        fill="tozeroy", fillcolor="rgba(251,191,36,0.07)",
        hovertemplate="<b>%{x}</b><br>Total Deposited: <b>€%{y:,.2f}</b><extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=pnl.index.astype(str), y=pnl.values,
        mode="lines", name="Trade P&L ($)",
        line=dict(color=C_BLUE, width=2, shape="spline", dash="dot"),
        hovertemplate="<b>%{x}</b><br>Trade P&L: <b>$%{y:+,.2f}</b><extra></extra>",
    ))

    return fig
