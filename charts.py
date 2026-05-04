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

C_BG       = "#030305"
C_PANEL    = "#07070a"
C_BORDER   = "rgba(255,255,255,0.05)"
C_GRID     = "rgba(255,255,255,0.03)"
C_TEXT     = "#e2e4f0"
C_MUTED    = "rgba(226,228,240,0.45)"
C_GREEN    = "#00ff88"
C_GREEN_DIM= "rgba(0,255,136,0.15)"
C_RED      = "#ff0055"
C_RED_DIM  = "rgba(255,0,85,0.15)"
C_BLUE     = "#00f0ff"
C_BLUE_DIM = "rgba(0,240,255,0.15)"
C_PURPLE   = "#b721ff"
C_PURPLE_DIM="rgba(183,33,255,0.15)"
C_AMBER    = "#ffaa00"
C_TEAL     = "#00ffcc"
C_TEAL_DIM = "rgba(0,255,204,0.15)"
FONT       = "Inter, -apple-system, BlinkMacSystemFont, sans-serif"

BASE_LAYOUT = dict(
    font        = dict(family=FONT, color=C_TEXT, size=13),
    paper_bgcolor = C_BG,
    plot_bgcolor  = C_PANEL,
    margin      = dict(l=16, r=120, t=55, b=24),  # Increased right margin to prevent Plotly text/bubble clipping
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
        transition=dict(duration=600, easing="cubic-in-out"),
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

def chart_pnl_timeline(timeline_df: pd.DataFrame, freq_label: str = "Daily", base_currency: str = "USD") -> go.Figure:
    """
    Interactive area + bar combo chart.
    Top: Cumulative P&L area. Bottom: Period P&L bars.
    Hover shows: date, period P&L, cumulative P&L, win rate.
    """
    sym = "€" if base_currency == "EUR" else "$"

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
    fig.update_yaxes(title_text=f"Cumulative P&L ({sym})", row=1, col=1,
                     title_font=dict(color=C_MUTED, size=11))
    fig.update_yaxes(title_text=f"Period P&L ({sym})", row=2, col=1,
                     title_font=dict(color=C_MUTED, size=11))

    return fig


# ---------------------------------------------------------------------------
# 2. Dividend growth — step chart with each payment + running total
# ---------------------------------------------------------------------------

def chart_dividend_growth(div_series: pd.DataFrame, base_currency: str = "USD") -> go.Figure:
    """
    Step + bar combo.
    Top: Cumulative dividend total (step line).
    Individual bars colored by ticker.
    """
    sym = "€" if base_currency == "EUR" else "$"

    if div_series.empty:
        return _empty("No dividend payments in selected period")

    sym = "€" if base_currency == "EUR" else "$"
    
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.6, 0.4],
        vertical_spacing=0.04,
    )

    # Cumulative step line
    fig.add_trace(go.Scatter(
        x=div_series["Time"],
        y=div_series[f"Cumulative ({base_currency})"],
        mode="lines+markers",
        name="Cumulative Dividends",
        line=dict(color=C_PURPLE, width=2.5, shape="hv"),
        marker=dict(size=7, color=C_PURPLE, symbol="circle",
                    line=dict(color=C_BG, width=2)),
        fill="tozeroy",
        fillcolor=C_PURPLE_DIM,
        customdata=div_series[["Ticker", f"Net ({base_currency})", f"Withholding ({base_currency})"]].values,
        hovertemplate=(
            "<b>%{x|%b %d, %Y}</b><br>"
            "─────────────────<br>"
            "Ticker         : <b>%{customdata[0]}</b><br>"
            f"This payment   : <b>{sym}%{{customdata[1]:.4f}}</b><br>"
            f"Withholding    : {sym}%{{customdata[2]:.4f}}<br>"
            f"Running total  : <b>{sym}%{{y:.4f}}</b>"
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
            y=sub[f"Net ({base_currency})"],
            name=ticker,
            marker_color=color_map[ticker],
            marker_line_width=0,
            hovertemplate=(
                f"<b>{ticker}</b><br>"
                "%{x|%b %d, %Y}<br>"
                f"Net: <b>{sym}%{{y:.4f}}</b>"
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

def chart_interest_growth(int_series: pd.DataFrame, base_currency: str = "USD") -> go.Figure:
    """
    Separate cumulative step lines for EUR and USD interest income.
    Each payment shown as a marker.
    """
    sym = "€" if base_currency == "EUR" else "$"

    if int_series.empty:
        return _empty("No interest payments in selected period")

    sym = "€" if base_currency == "EUR" else "$"
    
    fig = _fig(f"🏦 Interest Income — Cumulative Growth ({sym})", height=420)

    fig.add_trace(go.Scatter(
        x=int_series["Time"], y=int_series[f"Cumulative ({base_currency})"],
        mode="lines+markers",
        name=f"Interest ({base_currency})",
        line=dict(color=C_TEAL, width=2.5, shape="hv"),
        marker=dict(size=7, color=C_TEAL, symbol="circle",
                    line=dict(color=C_BG, width=2)),
        fill="tozeroy",
        fillcolor=C_TEAL_DIM,
        customdata=int_series[["Amount", "Action"]].values,
        hovertemplate=(
            "<b>%{x|%b %d, %Y}</b><br>"
            "Type : %{customdata[1]}<br>"
            f"Amount : <b>{sym}%{{customdata[0]:.4f}}</b><br>"
            f"Running total : <b>{sym}%{{y:.4f}}</b>"
            "<extra></extra>"
        ),
    ))

    fig.update_yaxes(title_text="Cumulative amount")
    return fig


# ---------------------------------------------------------------------------
# 4. Monthly summary — grouped bars
# ---------------------------------------------------------------------------

def chart_monthly_summary(monthly_df: pd.DataFrame, base_currency: str = "USD") -> go.Figure:
    
    sym = "€" if base_currency == "EUR" else "$"
    if monthly_df.empty:
        return _empty("No data in selected period")

    fig = _fig("📅 Monthly Breakdown", height=440)

    fig.add_trace(go.Bar(
        x=monthly_df["Month"], y=monthly_df["Profit"],
        name="Profit", marker_color=C_GREEN, marker_line_width=0,
        hovertemplate="<b>%{x}</b><br>Profit: <b>%{customdata[0]}{y:,.2f}</b><extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=monthly_df["Month"], y=monthly_df["Loss"],
        name="Loss", marker_color=C_RED, marker_line_width=0,
        hovertemplate="<b>%{x}</b><br>Loss: <b>%{customdata[0]}{y:,.2f}</b><extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=monthly_df["Month"], y=monthly_df["Net P&L"],
        name="Net P&L",
        marker_color=[C_GREEN if v >= 0 else C_RED for v in monthly_df["Net P&L"]],
        marker_line_width=0,
        hovertemplate=f"<b>%{x}</b><br>Net P&L: <b>{sym}%{y:+,.2f}</b><extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=monthly_df["Month"], y=monthly_df[f"Dividends ({base_currency})"],
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

def chart_top_tickers(ticker_df: pd.DataFrame, top_n: int = 15, base_currency: str = "USD") -> go.Figure:
    
    sym = "€" if base_currency == "EUR" else "$"
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
    fig.update_xaxes(title_text=f"Net P&L ({sym})")
    return fig


# ---------------------------------------------------------------------------
# 6. Income sources pie / donut
# ---------------------------------------------------------------------------

def chart_income_pie(summary: dict, base_currency: str = "USD") -> go.Figure:
    sym = "€" if base_currency == "EUR" else "$"
    COLORS = {
        f"Trade Profit ({sym})": C_GREEN,
        "Dividends (€)":    C_PURPLE,
        "Interest (€)":     C_TEAL,
        f"Interest ({sym})":     C_AMBER,
        "Cashback (€)":     C_BLUE,
    }

    items = []
    if summary.get("gross_profit", 0) > 0:
        items.append((f"Trade Profit ({sym})", summary["gross_profit"], 0.05))
    if summary.get("div_net_eur", 0) > 0:
        items.append(("Dividends (€)", summary["div_net_eur"], 0.0))
    if summary.get("interest_eur", 0) > 0:
        items.append(("Interest (€)", summary["interest_eur"], 0.0))
    if summary.get("interest_usd", 0) > 0:
        items.append((f"Interest ({sym})", summary["interest_usd"], 0.0))
    if summary.get("cashback_eur", 0) > 0:
        items.append(("Cashback (€)", summary["cashback_eur"], 0.0))

    if not items:
        return _empty("No income data in selected period")

    labels = [i[0] for i in items]
    values = [i[1] for i in items]
    pull   = [i[2] for i in items]
    colors = [COLORS.get(l, C_BLUE) for l in labels]
    total  = sum(values)

    fig = make_subplots(
        rows=1, cols=2,
        column_widths=[0.45, 0.55],
        specs=[[{"type": "domain"}, {"type": "xy"}]],
        horizontal_spacing=0.12,
    )

    # Left: donut — no text labels on slices, just hover
    fig.add_trace(go.Pie(
        labels=labels, values=values, pull=pull, hole=0.65,
        marker=dict(colors=colors, line=dict(color=C_BG, width=3)),
        textinfo="none",
        hovertemplate="<b>%{label}</b><br>Amount: %{value:,.4f}<br>Share: %{percent}<extra></extra>",
        showlegend=False,
    ), row=1, col=1)

    # Right: horizontal bar — one bar per source, sorted smallest → largest so the dominant one is last
    sorted_items = sorted(zip(labels, values, colors), key=lambda x: x[1])
    bar_labels = [x[0] for x in sorted_items]
    bar_values = [x[1] for x in sorted_items]
    bar_colors = [x[2] for x in sorted_items]
    bar_pcts   = [v / total * 100 for v in bar_values]

    fig.add_trace(go.Bar(
        y=bar_labels,
        x=bar_values,
        orientation="h",
        marker=dict(
            color=bar_colors,
            line=dict(color="rgba(0,0,0,0)", width=0),
        ),
        text=[f"  ${v:,.2f}  ({p:.1f}%)" for v, p in zip(bar_values, bar_pcts)],
        textposition="outside",
        textfont=dict(size=11, color=C_TEXT),
        hovertemplate="<b>%{y}</b><br>Amount: $%{x:,.4f}<extra></extra>",
        showlegend=False,
        cliponaxis=False,
    ), row=1, col=2)

    # Style the bar axes
    fig.update_xaxes(
        row=1, col=2,
        showgrid=False, zeroline=False, showticklabels=False,
        range=[0, max(bar_values) * 1.55],  # padding so labels fit
    )
    fig.update_yaxes(
        row=1, col=2,
        tickfont=dict(size=11.5, color=C_TEXT),
        showgrid=False, zeroline=False,
    )

    profit_val = summary.get("gross_profit", 0)
    fig.update_layout(
        title=dict(text="💰 Income Sources", font=dict(size=16, color=C_TEXT), x=0),
        height=420,
        paper_bgcolor=C_BG,
        plot_bgcolor=C_BG,
        font=dict(family="Inter, sans-serif", color=C_TEXT),
        margin=dict(l=10, r=30, t=50, b=10),
        transition=dict(duration=600, easing="cubic-in-out"),
        annotations=[dict(
            text=f"<b>${profit_val:,.0f}</b><br><span style='font-size:12px'>trade profit</span>",
            x=0.205, y=0.5, xref="paper", yref="paper",
            showarrow=False, font=dict(size=14, color=C_TEXT),
            align="center",
        )],
    )
    return fig


# ---------------------------------------------------------------------------
# 7. Deposits vs cumulative P&L
# ---------------------------------------------------------------------------

def chart_deposits_vs_pnl(df: pd.DataFrame, base_currency: str = "USD", fx_series=None) -> go.Figure:
    sym = "€" if base_currency == "EUR" else "$"
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
        mode="lines", name=f"Trade P&L ({sym})",
        line=dict(color=C_BLUE, width=2, shape="spline", dash="dot"),
        hovertemplate=f"<b>%{x}</b><br>Trade P&L: <b>{sym}%{y:+,.2f}</b><extra></extra>",
    ))

    return fig


# ---------------------------------------------------------------------------
# 8. Company comparison — full horizontal bar (all companies)
# ---------------------------------------------------------------------------

def chart_company_pnl_bars(company_df: pd.DataFrame, base_currency: str = "USD") -> go.Figure:
    """
    Full sorted horizontal bar chart of every company's Net P&L.
    Color: green if positive, red if negative.
    Hover: full stats.
    """
    sym = "€" if base_currency == "EUR" else "$"

    if company_df.empty:
        return _empty("No trade data in selected period")

    sym = "€" if base_currency == "EUR" else "$"
    col_pnl = f"Net P&L ({sym})"
    df = company_df.sort_values(col_pnl)
    colors = [C_GREEN if v >= 0 else C_RED for v in df[col_pnl]]

    fig = _fig(f"🏢 Net P&L by Company ({sym})", height=max(380, len(df) * 36))

    fig.add_trace(go.Bar(
        x=df[col_pnl],
        y=df["Ticker"],
        orientation="h",
        marker_color=colors,
        marker_line_width=0,
        customdata=df[[f"Gross Profit ({sym})", f"Gross Loss ({sym})", "Total Trades",
                        "Win Rate (%)", f"Best Trade ({sym})", f"Worst Trade ({sym})"]].values,
        hovertemplate=(
            "<b>%{y}</b><br>"
            "──────────────────────<br>"
            f"Net P&L       : <b>{sym}%{{x:+,.2f}}</b><br>"
            f"Gross Profit  : <b style='color:#22c55e'>{sym}%{{customdata[0]:,.2f}}</b><br>"
            f"Gross Loss    : <b style='color:#f43f5e'>{sym}%{{customdata[1]:,.2f}}</b><br>"
            "Total Trades  : %{customdata[2]}<br>"
            "Win Rate      : %{customdata[3]}%<br>"
            f"Best Trade    : {sym}%{{customdata[4]:+,.2f}}<br>"
            f"Worst Trade   : {sym}%{{customdata[5]:+,.2f}}"
            "<extra></extra>"
        ),
        text=[f"{sym}{v:+,.2f}" for v in df[col_pnl]],
        textposition="outside",
        cliponaxis=False,
        textfont=dict(size=10, color=colors),
    ))

    _add_zero_line(fig, axis="x")
    
    max_val = df[col_pnl].max()
    min_val = df[col_pnl].min()
    x_max = float(max_val) * 1.2 if max_val > 0 else 0.0
    x_min = float(min_val) * 1.2 if min_val < 0 else 0.0
    if x_max == 0 and x_min == 0:
        x_max, x_min = 1.0, -1.0
        
    fig.update_xaxes(title_text=f"Net P&L ({sym})", range=[x_min, x_max])
    return fig


# ---------------------------------------------------------------------------
# 9. Company bubble chart  (trades vs P&L, sized by volume)
# ---------------------------------------------------------------------------

def chart_company_bubble(company_df: pd.DataFrame, base_currency: str = "USD") -> go.Figure:
    """
    Scatter/bubble chart:
      X = Total Trades
      Y = Net P&L (Base)
      Size = Vol Bought (Base)
      Color = Win Rate (%)
    """
    sym = "€" if base_currency == "EUR" else "$"

    if company_df.empty:
        return _empty("No trade data in selected period")

    sym = "€" if base_currency == "EUR" else "$"
    col_pnl = f"Net P&L ({sym})"
    col_vol = f"Volume Bought ({sym})"

    df = company_df.copy()
    # Normalize bubble size
    vol_max = df[col_vol].max()
    if vol_max > 0:
        df["_size"] = (df[col_vol] / vol_max * 50 + 8).clip(upper=60)
    else:
        df["_size"] = 12

    colors = [C_GREEN if v >= 0 else C_RED for v in df[col_pnl]]

    fig = _fig(f"📊 Trades vs P&L (bubble size = volume bought in {sym})", height=480)

    fig.add_trace(go.Scatter(
        x=df["Total Trades"],
        y=df[col_pnl],
        mode="markers+text",
        text=df["Ticker"],
        textposition="top center",
        cliponaxis=False,
        textfont=dict(size=10, color=C_MUTED),
        marker=dict(
            size=df["_size"],
            color=df["Win Rate (%)"],
            colorscale=[[0, C_RED], [0.5, C_AMBER], [1, C_GREEN]],
            showscale=True,
            colorbar=dict(
                title=dict(text="Win Rate %", font=dict(color=C_MUTED, size=11)),
                tickfont=dict(color=C_MUTED, size=10),
                bgcolor="rgba(0,0,0,0)",
                bordercolor=C_BORDER,
            ),
            line=dict(color=C_BG, width=1.5),
        ),
        customdata=df[["Name", col_pnl, "Win Rate (%)",
                        col_vol, f"Best Trade ({sym})", f"Worst Trade ({sym})"]].values,
        hovertemplate=(
            "<b>%{text}</b> — %{customdata[0]}<br>"
            "──────────────────────<br>"
            "Total Trades : %{x}<br>"
            f"Net P&L      : <b>{sym}%{{customdata[1]:+,.2f}}</b><br>"
            "Win Rate     : %{customdata[2]}%<br>"
            f"Vol Bought   : {sym}%{{customdata[3]:,.0f}}<br>"
            f"Best Trade   : {sym}%{{customdata[4]:+,.2f}}<br>"
            f"Worst Trade  : {sym}%{{customdata[5]:+,.2f}}"
            "<extra></extra>"
        ),
    ))

    fig.add_hline(y=0, line_color="rgba(255,255,255,0.18)", line_width=1)
    fig.update_xaxes(title_text="Total Trades (buys + sells)")
    fig.update_yaxes(title_text=f"Net P&L ({sym})")
    return fig


# ---------------------------------------------------------------------------
# 10. Single company cumulative trade P&L timeline
# ---------------------------------------------------------------------------

def chart_company_timeline(history_df: pd.DataFrame, ticker: str, base_currency: str = "USD") -> go.Figure:
    """
    Scatter + step line showing every trade for one company.
    Sells: colored green/red by P&L.  Buys: small grey dots.
    Step line shows running cumulative P&L from sells in base_currency.
    """
    sym = "€" if base_currency == "EUR" else "$"

    if history_df.empty:
        return _empty(f"No trade history for {ticker}")

    fig = _fig(f"📉 {ticker} — Individual Trade Timeline", height=440)

    buys  = history_df[history_df["Action"].str.lower().str.startswith("market buy") |
                        history_df["Action"].str.lower().str.startswith("limit buy")]
    sells = history_df[history_df["Action"].str.lower().str.startswith("market sell") |
                        history_df["Action"].str.lower().str.startswith("limit sell")]

    sym = "€" if base_currency == "EUR" else "$"
    
    # Cumulative P&L step line
    fig.add_trace(go.Scatter(
        x=history_df["Time"],
        y=history_df[f"Cumul P&L ({sym})"],
        mode="lines",
        name="Cumul P&L",
        line=dict(color=C_BLUE, width=2, shape="hv", dash="dot"),
        hovertemplate=f"<b>%{{x|%b %d, %Y %H:%M}}</b><br>Running P&L: <b>{sym}%{{y:+,.2f}}</b><extra></extra>",
    ))

    # Buy markers
    if not buys.empty:
        fig.add_trace(go.Scatter(
            x=buys["Time"],
            y=buys[f"Cumul P&L ({sym})"],
            mode="markers",
            name="Buy",
            marker=dict(size=8, color=C_MUTED, symbol="triangle-up",
                        line=dict(color=C_BG, width=1)),
            customdata=buys[["No. of shares", "Price / share", "Total"]].values,
            hovertemplate=(
                "<b>BUY</b> — %{x|%b %d, %Y %H:%M}<br>"
                f"Shares: %{{customdata[0]:.4f}}  @  {sym}%{{customdata[1]:.2f}}<br>"
                f"Total:  {sym}%{{customdata[2]:,.2f}}<extra></extra>"
            ),
        ))

    # Sell markers — colored by P&L
    if not sells.empty:
        sell_colors = [C_GREEN if v >= 0 else C_RED for v in sells[f"Trade P&L ({sym})"]]
        fig.add_trace(go.Scatter(
            x=sells["Time"],
            y=sells[f"Cumul P&L ({sym})"],
            mode="markers",
            name="Sell",
            marker=dict(size=10, color=sell_colors, symbol="triangle-down",
                        line=dict(color=C_BG, width=1.5)),
            customdata=sells[["No. of shares", "Price / share", f"Trade P&L ({sym})", "Total"]].values,
            hovertemplate=(
                "<b>SELL</b> — %{x|%b %d, %Y %H:%M}<br>"
                f"Shares: %{{customdata[0]:.4f}}  @  {sym}%{{customdata[1]:.2f}}<br>"
                f"Trade P&L : <b>{sym}%{{customdata[2]:+,.2f}}</b><br>"
                f"Total     : {sym}%{{customdata[3]:,.2f}}<extra></extra>"
            ),
        ))

    fig.add_hline(y=0, line_color="rgba(255,255,255,0.18)", line_width=1)
    fig.update_yaxes(title_text=f"Cumulative P&L ({sym})")
    return fig


# ---------------------------------------------------------------------------
# 11. Multi-company comparison — overlaid cumulative P&L lines
# ---------------------------------------------------------------------------

def chart_company_compare(df: pd.DataFrame, tickers: list, base_currency: str = "USD", fx_series=None) -> go.Figure:
    sym = "€" if base_currency == "EUR" else "$"
    """
    Overlaid cumulative P&L lines for multiple selected tickers.
    Each ticker gets a distinct color from the palette.
    """
    if not tickers or df.empty:
        return _empty("Select at least one company to compare")

    palette = [C_BLUE, C_GREEN, C_AMBER, C_PURPLE, C_TEAL, "#f472b6", "#fb923c", C_RED]
    fig = _fig("⚖️ Multi-Company P&L Comparison", height=420)

    sells = df[df["_category"] == "sell"].copy()
    all_dates = pd.date_range(df["Time"].min().date(), df["Time"].max().date(), freq="D")

    for i, ticker in enumerate(tickers[:8]):
        t_sells = sells[sells["Ticker"] == ticker].copy()
        if t_sells.empty:
            continue
        t_sells["Date"] = t_sells["Time"].dt.date
        daily = t_sells.groupby("Date")["Result"].sum().reindex(all_dates.date, fill_value=0).cumsum()

        col = palette[i % len(palette)]
        fig.add_trace(go.Scatter(
            x=daily.index.astype(str),
            y=daily.values,
            mode="lines",
            name=ticker,
            line=dict(color=col, width=2.5, shape="spline", smoothing=0.3),
            hovertemplate=f"<b>{ticker}</b> — %{{x}}<br>Cumul P&L: <b>${{y:+,.2f}}</b><extra></extra>",
        ))

    fig.add_hline(y=0, line_color="rgba(255,255,255,0.18)", line_width=1)
    fig.update_yaxes(title_text=f"Cumulative P&L ({sym})")
    fig.update_xaxes(title_text="Date")
    return fig


# ---------------------------------------------------------------------------
# 12. Total Portfolio Progress area chart
# ---------------------------------------------------------------------------

def chart_total_portfolio(prog_df: pd.DataFrame, show_dep: bool = True, show_pnl: bool = True,
                          show_div: bool = True, show_int: bool = True,
                          chart_mode: str = "Line (Stacked Area)",
                          return_df: pd.DataFrame = None, base_currency: str = "USD") -> go.Figure:
    sym = "€" if base_currency == "EUR" else "$"
    """
    Stacked/Overlaid area chart showing the growth of net deposits and P&L.
    Optionally overlays the cumulative Return % curve on a secondary Y-axis.
    """
    if prog_df.empty:
        return _empty("No portfolio data available")

    has_return = (return_df is not None and not return_df.empty)

    if has_return:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.update_layout(
            **{k: v for k, v in BASE_LAYOUT.items() if k not in ("xaxis", "yaxis", "legend")},
            height=540,
            title=dict(text="📈 Total Portfolio Value & MWRR Return %",
                       font=dict(family=FONT, size=15, color=C_TEXT), x=0),
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            transition=dict(duration=600, easing="cubic-in-out"),
        )
        fig.update_xaxes(gridcolor=C_GRID, showline=False, tickfont=dict(color=C_MUTED, size=11))
        fig.update_yaxes(gridcolor=C_GRID, showline=False, tickfont=dict(color=C_MUTED, size=11), secondary_y=False)
    else:
        fig = _fig("📈 Total Portfolio Value Tracker", height=500)

    # Calculate dynamic total line based on what's activated
    total_line = pd.Series(0, index=prog_df.index)
    if show_dep: total_line += prog_df["Net Deposits"].fillna(0)
    if show_pnl: total_line += prog_df["Daily P&L"].fillna(0)
    if show_div: total_line += prog_df["Daily Dividends"].fillna(0)
    if show_int: total_line += prog_df["Daily Interest"].fillna(0)

    kwargs = dict(secondary_y=False) if has_return else {}

    if chart_mode == "Candlestick":
        open_arr = total_line.shift(1).fillna(total_line)
        close_arr = total_line
        df_ohlc = pd.DataFrame({"open": open_arr, "close": close_arr})
        high_arr = df_ohlc.max(axis=1) * 1.002
        low_arr  = df_ohlc.min(axis=1) * 0.998
        fig.add_trace(go.Candlestick(
            x=prog_df["Date"].astype(str),
            open=open_arr, high=high_arr, low=low_arr, close=close_arr,
            name="Daily Value",
            increasing_line_color=C_GREEN, increasing_fillcolor=C_GREEN,
            decreasing_line_color=C_RED, decreasing_fillcolor=C_RED,
        ), **kwargs)
        if not has_return:
            fig.update_layout(xaxis_rangeslider_visible=False, hovermode="x unified",
                              legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        fig.update_yaxes(title_text=f"Tracked Value ({sym})", **kwargs)
    else:
        if show_dep:
            fig.add_trace(go.Scatter(
                x=prog_df["Date"].astype(str), y=prog_df["Net Deposits"],
                mode="lines", name="Net Deposits",
                line=dict(color=C_BLUE, width=0),
                fill="tozeroy", fillcolor="rgba(56,189,248,0.3)",
                stackgroup="one",
                hovertemplate=f"<b>%{{x}}</b><br>Net Deposits: <b>{sym}%{{y:,.2f}}</b><extra></extra>",
            ), **kwargs)

        if show_pnl:
            fig.add_trace(go.Scatter(
                x=prog_df["Date"].astype(str), y=prog_df["Daily P&L"],
                mode="lines", name="Cumulative P&L",
                line=dict(color=C_GREEN, width=0),
                fill="tonexty", fillcolor="rgba(34,197,94,0.4)",
                stackgroup="one",
                hovertemplate=f"<b>%{{x}}</b><br>Cumul P&L: <b>{sym}%{{y:+,.2f}}</b><extra></extra>",
            ), **kwargs)

        if show_div:
            fig.add_trace(go.Scatter(
                x=prog_df["Date"].astype(str), y=prog_df["Daily Dividends"],
                mode="lines", name="Cumulative Dividends",
                line=dict(color=C_PURPLE, width=0),
                fill="tonexty", fillcolor="rgba(167,139,250,0.5)",
                stackgroup="one",
                hovertemplate=f"<b>%{{x}}</b><br>Dividends: <b>{sym}%{{y:,.2f}}</b><extra></extra>",
            ), **kwargs)

        if show_int:
            fig.add_trace(go.Scatter(
                x=prog_df["Date"].astype(str), y=prog_df["Daily Interest"],
                mode="lines", name="Cumulative Interest",
                line=dict(color=C_AMBER, width=0),
                fill="tonexty", fillcolor="rgba(251,191,36,0.6)",
                stackgroup="one",
                hovertemplate=f"<b>%{{x}}</b><br>Interest: <b>{sym}%{{y:,.2f}}</b><extra></extra>",
            ), **kwargs)

        fig.add_trace(go.Scatter(
            x=prog_df["Date"].astype(str), y=total_line,
            mode="lines", name="Tracked Summary",
            line=dict(color=C_TEXT, width=2, shape="spline"),
            hovertemplate=f"<b>%{{x}}</b><br>Tracked Summary: <b>{sym}%{{y:,.2f}}</b><extra></extra>",
        ), **kwargs)

        if not has_return:
            fig.update_layout(hovermode="x unified",
                              legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        fig.update_yaxes(title_text=f"Tracked Value ({sym})", **kwargs)

    # ── Overlay: MWRR Return % on secondary Y-axis ──
    if has_return and "Return %" in return_df.columns:
        r = return_df["Return %"].values
        last_r = float(r[-1])
        line_color = C_TEAL if last_r >= 0 else C_RED
        fig.add_trace(go.Scatter(
            x=return_df["Date"].astype(str),
            y=r,
            mode="lines",
            name="Return % (MWRR)",
            line=dict(color=line_color, width=2.5, dash="dot", shape="spline", smoothing=0.5),
            hovertemplate="<b>%{x}</b><br>Portfolio Return: <b>%{y:+.2f}%</b><extra></extra>",
        ), secondary_y=True)
        fig.update_yaxes(
            title_text="Return % (MWRR)",
            ticksuffix="%",
            showgrid=False,
            tickfont=dict(color=C_TEAL, size=11),
            title_font=dict(color=C_TEAL, size=11),
            secondary_y=True,
        )

    return fig


# ---------------------------------------------------------------------------
# 13. Dedicated Return % / MWRR timeline chart
# ---------------------------------------------------------------------------

def chart_return_timeline(return_df: pd.DataFrame, mwrr_annual: float = 0.0,
                          mwrr_total: float = 0.0) -> go.Figure:
    """
    Standalone premium chart for cumulative portfolio Return %.
    Shows the return curve with gradient fill, milestone annotation,
    and the final MWRR stats stamped on the title.
    """
    if return_df.empty or "Return %" not in return_df.columns:
        return _empty("Insufficient data to compute return curve")

    r = return_df["Return %"].values
    x = return_df["Date"].astype(str)
    final = float(r[-1])
    is_positive = final >= 0
    line_color = C_GREEN if is_positive else C_RED
    fill_color = "rgba(0,255,136,0.12)" if is_positive else "rgba(255,0,85,0.12)"

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.70, 0.30],
        vertical_spacing=0.04,
    )

    # ── Top: Return % curve ──
    fig.add_trace(go.Scatter(
        x=x, y=r,
        mode="lines",
        name="Cumulative Return %",
        line=dict(color=line_color, width=3, shape="spline", smoothing=0.5),
        fill="tozeroy",
        fillcolor=fill_color,
        customdata=np.column_stack([
            return_df[f"Terminal Value ({sym})"].values,
            return_df[f"Cumul Deposits ({sym})"].values,
            return_df[f"Total Gains ({sym})"].values,
        ]),
        hovertemplate=(
            "<b>%{x}</b><br>"
            "────────────────────<br>"
            "Return       : <b>%{y:+.2f}%</b><br>"
            "Terminal Val : <b>$%{customdata[0]:,.2f}</b><br>"
            "Deposited    : <b>$%{customdata[1]:,.2f}</b><br>"
            "Total Gains  : <b>$%{customdata[2]:+,.2f}</b>"
            "<extra></extra>"
        ),
    ), row=1, col=1)

    fig.add_hline(y=0, line_color="rgba(255,255,255,0.2)", line_width=1, row=1, col=1)

    # Annotate the current return
    fig.add_annotation(
        x=x.iloc[-1], y=final,
        text=f"<b>{final:+.2f}%</b>",
        showarrow=True, arrowhead=2,
        arrowcolor=line_color,
        font=dict(color=line_color, size=14, family=FONT),
        bgcolor="rgba(7,7,10,0.85)",
        bordercolor=line_color, borderwidth=1,
        borderpad=5, row=1, col=1,
    )

    # ── Bottom: Daily delta in total gains (bar) ──
    daily_delta = return_df[f"Total Gains ({sym})"].diff().fillna(0)
    bar_cols = [C_GREEN if v >= 0 else C_RED for v in daily_delta]
    fig.add_trace(go.Bar(
        x=x, y=daily_delta,
        name=f"Daily Gains Δ ({sym})",
        marker_color=bar_cols,
        marker_line_width=0,
        hovertemplate=f"<b>%{x}</b><br>Daily Δ: <b>{sym}%{y:+,.2f}</b><extra></extra>",
    ), row=2, col=1)
    fig.add_hline(y=0, line_color="rgba(255,255,255,0.2)", line_width=1, row=2, col=1)

    _ann_valid = mwrr_annual is not None and np.isfinite(float(mwrr_annual))
    ann_color  = (C_GREEN if mwrr_annual >= 0 else C_RED) if _ann_valid else C_MUTED
    tot_color  = C_GREEN if mwrr_total >= 0 else C_RED
    _ann_label = f"Annualized {mwrr_annual:+.2f}%" if _ann_valid else "Annualized N/A (< 6 mo)"
    fig.update_layout(
        **{k: v for k, v in BASE_LAYOUT.items() if k not in ("xaxis", "yaxis")},
        height=560,
        title=dict(
            text=(
                f"📊 Portfolio Return (MWRR)  ·  "
                f"<span style='color:{ann_color}'>{_ann_label}</span>  ·  "
                f"<span style='color:{tot_color}'>Total {mwrr_total:+.2f}%</span>"
            ),
            font=dict(family=FONT, size=14, color=C_TEXT),
            x=0, xanchor="left",
        ),
        showlegend=False,
        hovermode="x unified",
    )
    fig.update_xaxes(gridcolor=C_GRID, showline=False, tickfont=dict(color=C_MUTED, size=11))
    fig.update_yaxes(gridcolor=C_GRID, showline=False, tickfont=dict(color=C_MUTED, size=11))
    fig.update_yaxes(title_text="Return %", ticksuffix="%", row=1, col=1,
                     title_font=dict(color=C_MUTED, size=11))
    fig.update_yaxes(title_text=f"Daily Gains Δ ({sym})", row=2, col=1,
                     title_font=dict(color=C_MUTED, size=11))

    return fig


# ---------------------------------------------------------------------------
# 14. Return Contribution waterfall / bar chart
# ---------------------------------------------------------------------------

def chart_return_contribution(company_df: pd.DataFrame, mwrr_total: float = 0.0, base_currency: str = "USD") -> go.Figure:
    sym = "€" if base_currency == "EUR" else "$"
    """
    Horizontal bar chart showing each ticker's % contribution to total portfolio return.
    Positive = drove the return up; Negative = dragged the return down.
    """
    if company_df.empty or "Return Contribution (%)" not in company_df.columns:
        return _empty("No company return contribution data available")

    df = company_df.copy()
    df = df[df["Return Contribution (%)"] != 0].copy()
    if df.empty:
        return _empty("All positions have zero contribution")
    # Top 20 by absolute contribution, sorted ascending for horizontal bar
    df = df.reindex(df["Return Contribution (%)"].abs().nlargest(20).index)
    df = df.sort_values("Return Contribution (%)")

    colors = [C_GREEN if v >= 0 else C_RED for v in df["Return Contribution (%)"]]

    fig = _fig("🧩 Return Contribution by Position", height=max(380, len(df) * 38))

    fig.add_trace(go.Bar(
        y=df["Ticker"],
        x=df["Return Contribution (%)"],
        orientation="h",
        marker_color=colors,
        marker_line_width=0,
        customdata=df[[f"Net P&L ({sym})", "Win Rate (%)", f"Volume Bought ({sym})"]].values,
        text=[f"{v:+.1f}%" for v in df["Return Contribution (%)"]],
        textposition="outside",
        cliponaxis=False,
        textfont=dict(size=11, color=colors),
        hovertemplate=(
            "<b>%{y}</b><br>"
            "────────────────────<br>"
            "Return Contribution : <b>%{x:+.2f}%</b><br>"
            "Net P&L             : <b>$%{customdata[0]:+,.2f}</b><br>"
            "Win Rate            : %{customdata[1]:.1f}%<br>"
            "Vol Bought          : $%{customdata[2]:,.0f}"
            "<extra></extra>"
        ),
    ))

    _add_zero_line(fig, axis="x")
    max_v = df["Return Contribution (%)"].abs().max() if not df.empty else 1.0
    fig.update_xaxes(
        title_text="Return Contribution (%)",
        range=[-(max_v * 1.3), max_v * 1.3],
        ticksuffix="%",
    )

    sign_col = C_GREEN if mwrr_total >= 0 else C_RED
    fig.add_annotation(
        text=f"<b>Portfolio MWRR Total: {mwrr_total:+.2f}%</b>",
        xref="paper", yref="paper",
        x=1.0, y=1.04,
        showarrow=False,
        font=dict(size=12, color=sign_col, family=FONT),
        align="right",
    )

    return fig


# ---------------------------------------------------------------------------
# Card Spending Charts
# ---------------------------------------------------------------------------

def chart_spending_timeline(df_monthly: pd.DataFrame) -> go.Figure:
    if df_monthly.empty:
        return _empty("No Spending Data")

    fig = _fig("📅 Monthly Card Spending")
    fig.add_trace(go.Bar(
        x=df_monthly["Month"].astype(str).str[:7],
        y=df_monthly["Amount"],
        marker_color=C_BLUE,
        marker_line_width=0,
        text=df_monthly["Amount"].apply(lambda x: f"€{x:,.0f}"),
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>Spent: <b>€%{y:,.2f}</b><extra></extra>"
    ))

    fig.update_layout(
        xaxis=dict(type='category'),
        yaxis=dict(title="Amount (€)", gridcolor="rgba(255,255,255,0.05)")
    )
    return fig


def chart_spending_category_donut(df_cat: pd.DataFrame) -> go.Figure:
    if df_cat.empty:
        return _empty("No Category Data")

    fig = _fig("🛒 Spending by Category")

    # Cap to top 8, sum rest into "Other"
    top_n = 8
    if len(df_cat) > top_n:
        top_df = df_cat.iloc[:top_n].copy()
        other_sum = df_cat.iloc[top_n:]["Amount"].sum()
        other_row = pd.DataFrame({"Category": ["Other"], "Amount": [other_sum]})
        plot_df = pd.concat([top_df, other_row], ignore_index=True)
    else:
        plot_df = df_cat.copy()

    fig.add_trace(go.Pie(
        labels=plot_df["Category"],
        values=plot_df["Amount"],
        hole=0.7,
        marker=dict(colors=[C_PURPLE, C_BLUE, C_TEAL, C_GREEN, C_AMBER, C_RED, C_TEXT, C_PANEL]),
        textinfo='percent+label',
        textposition='outside',
        hovertemplate="<b>%{label}</b><br>Amount: <b>€%{value:,.2f}</b><extra></extra>"
    ))

    fig.update_layout(showlegend=False)
    return fig


def chart_top_merchants(df_merch: pd.DataFrame) -> go.Figure:
    if df_merch.empty:
        return _empty("No Merchant Data")

    fig = _fig("🏆 Top 10 Merchants")
    # Top 10 merchants
    top_df = df_merch.head(10).copy()
    top_df = top_df.sort_values(by="Amount", ascending=True)  # horizontal bar sorts bottom-to-top

    fig.add_trace(go.Bar(
        y=top_df["Merchant"],
        x=top_df["Amount"],
        orientation='h',
        marker_color=C_TEAL,
        text=top_df["Amount"].apply(lambda x: f"€{x:,.2f}"),
        textposition='outside',
        hovertemplate="<b>%{y}</b><br>Amount: <b>€%{x:,.2f}</b><extra></extra>"
    ))

    max_val = float(top_df["Amount"].max()) if not top_df.empty else 0.0
    x_max = max_val * 1.25 if max_val > 0 else 1.0

    fig.update_layout(
        xaxis=dict(title="Amount (€)", gridcolor="rgba(255,255,255,0.05)", range=[0, x_max]),
        yaxis=dict(autorange=True)
    )
    return fig

