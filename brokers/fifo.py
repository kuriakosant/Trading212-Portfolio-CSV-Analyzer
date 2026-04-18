"""
brokers/fifo.py — FIFO realized-P&L computation for brokers that don't
provide a pre-calculated `Result` column (currently: Revolut).

The algorithm is a classic per-ticker FIFO lot-matcher, run in strict
chronological order so buy/sell events interleave correctly across multiple
uploaded files:

    state[ticker] = deque[(remaining_qty, unit_cost_native)]

    on BUY   : append (qty, price_per_share)
    on SELL  : drain the queue FIFO to satisfy sell_qty;
               realized P&L = (sell_price - matched_cost) × matched_qty
    on SPLIT : the Revolut "STOCK SPLIT" row's Quantity is the *delta*
               applied to the user's holdings (e.g. a 3-for-2 split of
               1.2863625 shares emits a delta of +0.64318125, yielding
               1.92954375).  We rescale every remaining lot by the ratio
                   new_total / old_total
               while keeping total cost basis constant, so lot unit costs
               scale inversely.

Running the computation per-broker (not globally) is intentional: if a user
holds the same ticker on both Trading212 and Revolut, each broker's basis is
tracked independently, matching how T212 reports its own `Result`.
"""

from __future__ import annotations

from collections import defaultdict, deque
import pandas as pd

from . import canonical


# Tolerance (in shares) below which a remaining lot is treated as closed.
# Guards against float drift from fractional shares × float prices.
_EPSILON_SHARES = 1e-9


def fill_revolut_result(df: pd.DataFrame) -> pd.DataFrame:
    """
    Populate `Result` (and `Currency (Result)`) in-place for Revolut sell rows
    using FIFO cost basis.

    Only rows where `_broker == "revolut"` are touched; Trading212 rows are
    left exactly as the broker reported them.  Returns the same DataFrame
    object for call-chaining convenience.
    """
    if df.empty or canonical.COL_BROKER not in df.columns:
        return df

    is_revolut = df[canonical.COL_BROKER] == "revolut"
    if not is_revolut.any():
        return df

    # Work on the Revolut slice in chronological order.  Stable sort keeps
    # same-timestamp rows in their original file order (important when
    # Revolut batches a split immediately before a later buy).
    rev_idx = df.index[is_revolut]
    chrono = df.loc[rev_idx].sort_values(canonical.COL_TIME, kind="stable").index

    # Per-ticker deque of (remaining_qty, unit_cost).  Unit cost is in the
    # row's native trade currency (usually USD).
    lots: dict[str, deque[list[float]]] = defaultdict(deque)

    for i in chrono:
        action = df.at[i, canonical.COL_ACTION]
        ticker = df.at[i, canonical.COL_TICKER]
        if pd.isna(ticker):
            continue

        qty   = _safe_float(df.at[i, canonical.COL_SHARES])
        price = _safe_float(df.at[i, canonical.COL_PRICE_PER_SHARE])

        if action in (canonical.ACTION_MARKET_BUY, canonical.ACTION_LIMIT_BUY):
            if qty > 0 and price > 0:
                lots[ticker].append([qty, price])

        elif action in (canonical.ACTION_MARKET_SELL, canonical.ACTION_LIMIT_SELL):
            if qty <= 0 or price <= 0:
                continue
            result, matched = _drain_fifo(lots[ticker], qty, price)
            # Only record a Result when we actually had basis to match
            # against — sells with no prior buy (e.g. the user uploaded a
            # mid-history export) leave Result at 0 rather than fabricating
            # a misleading profit.
            if matched > _EPSILON_SHARES:
                df.at[i, canonical.COL_RESULT] = result
            # Currency (Result) = Currency (Price/share) for the trade
            price_ccy = df.at[i, canonical.COL_PRICE_CCY]
            if pd.notna(price_ccy):
                df.at[i, canonical.COL_RESULT_CCY] = price_ccy

        elif action == canonical.ACTION_STOCK_SPLIT:
            _apply_split(lots[ticker], qty)

    return df


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _safe_float(v) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return 0.0
    if pd.isna(f):
        return 0.0
    return f


def _drain_fifo(queue: "deque[list[float]]", sell_qty: float, sell_price: float
                ) -> tuple[float, float]:
    """
    Drain `sell_qty` shares from the head of `queue` (earliest buys first).

    Returns `(realized_pnl, matched_qty)` where `matched_qty` may be less
    than `sell_qty` if the queue ran dry (short sell or imported mid-history).
    """
    remaining = sell_qty
    realized  = 0.0
    matched   = 0.0

    while remaining > _EPSILON_SHARES and queue:
        lot_qty, lot_cost = queue[0]
        take = min(lot_qty, remaining)
        realized += take * (sell_price - lot_cost)
        matched  += take

        lot_qty -= take
        if lot_qty <= _EPSILON_SHARES:
            queue.popleft()
        else:
            queue[0][0] = lot_qty

        remaining -= take

    return realized, matched


def _apply_split(queue: "deque[list[float]]", delta_qty: float) -> None:
    """
    Apply a STOCK SPLIT row's share-delta to every remaining lot.

    Revolut encodes a split as a single row whose `Quantity` is the *change*
    in the user's total holdings (positive for forward splits, negative for
    reverse splits).  Total cost basis is preserved, so unit costs scale
    inversely to the share-count ratio.
    """
    if not queue:
        return

    old_total = sum(lot[0] for lot in queue)
    new_total = old_total + delta_qty

    if old_total <= _EPSILON_SHARES or new_total <= _EPSILON_SHARES:
        # Can't reasonably rescale; bail out quietly.
        return

    ratio = new_total / old_total
    for lot in queue:
        lot[0] *= ratio          # new share count
        lot[1] /= ratio          # new unit cost (basis preserved)
