"""
brokers/revolut.py — Revolut Stocks CSV adapter.

Revolut's Stocks export has a much terser schema than Trading212's:

    Date, Ticker, Type, Quantity, Price per share, Total Amount, Currency, FX Rate

Peculiarities we handle here:

  *  Timestamps are ISO-8601 UTC with variable fractional-second precision
     (3, 6, or 0 digits) and the `Z` suffix.

  *  "Price per share" and "Total Amount" are single strings that combine
     currency and value, e.g. `"USD 17.93"`, `"EUR -150"`.  We split them
     into numeric + currency components.

  *  `Type` values are Revolut-specific (BUY - MARKET, CASH TOP-UP,
     STOCK SPLIT, DIVIDEND TAX (CORRECTION), …) and must be translated into
     the canonical Action verbs declared in `brokers.canonical`.

  *  Revolut does NOT emit a per-sell realized P&L column and does NOT
     itemize fees.  `Result` is left at 0.0 here — it is filled in later
     by `brokers.fifo.fill_revolut_result()` (run after all files are
     loaded so FIFO lots are tracked chronologically across uploads).

  *  USD-ONLY POLICY.  Revolut maintains separate EUR and USD cash wallets
     and encodes internal EUR↔USD conversions as back-to-back EUR/USD cash
     rows.  Rather than trying to reconstruct those pairs heuristically
     (which is brittle), we simply drop every non-USD row at the adapter
     level.  The resulting view is the user's **USD sub-portfolio only**:

        - EUR cash top-ups / withdrawals    → excluded (staging only)
        - EUR-denominated trades & divs     → excluded (pre-conversion)
        - USD cash top-ups / withdrawals    → real deposits / withdrawals
        - USD trades, dividends, splits     → analyzed
        - USD dividend-tax corrections      → kept

     This is exactly what the user asked for: all money, P&L, FIFO basis
     and cash flow are expressed in USD end-to-end, with no currency
     reconciliation anywhere.
"""

from __future__ import annotations

import re
import pandas as pd

from .base import BaseBrokerAdapter
from . import canonical


# Exact ordered set of Revolut headers (as seen in the official export).
# We don't require strict equality in case Revolut adds trailing columns
# later — a header is a Revolut file if it starts with this marker set.
_REVOLUT_HEADER_MARKERS = (
    "Date",
    "Ticker",
    "Type",
    "Quantity",
    "Price per share",
    "Total Amount",
    "Currency",
    "FX Rate",
)


# Revolut `Type` → canonical Action verb
_ACTION_MAP: dict[str, str] = {
    "BUY - MARKET":  canonical.ACTION_MARKET_BUY,
    "BUY - LIMIT":   canonical.ACTION_LIMIT_BUY,
    "SELL - MARKET": canonical.ACTION_MARKET_SELL,
    "SELL - LIMIT":  canonical.ACTION_LIMIT_SELL,
    "DIVIDEND":      canonical.ACTION_DIVIDEND,
    "DIVIDEND TAX (CORRECTION)": canonical.ACTION_DIVIDEND_TAX_CORRECTION,
    # NOTE: CASH TOP-UP / CASH WITHDRAWAL are mapped to Deposit / Withdrawal
    # here; the FX-pairing pass may later reclassify matched pairs as
    # Currency conversion.
    "CASH TOP-UP":      canonical.ACTION_DEPOSIT,
    "CASH WITHDRAWAL":  canonical.ACTION_WITHDRAWAL,
    "STOCK SPLIT":      canonical.ACTION_STOCK_SPLIT,
}


# Parses strings like "USD 17.93", "EUR -150", "USD 1,234.56".
_PREFIXED_AMOUNT_RE = re.compile(
    r"""^\s*
        (?P<ccy>[A-Z]{3})              # 3-letter ISO currency code
        \s+
        (?P<val>-?[\d,]+(?:\.\d+)?)    # optional sign, digits, optional decimal
        \s*$""",
    re.VERBOSE,
)


def _split_prefixed_amount(cell) -> tuple[object, float]:
    """
    Split a "<CCY> <number>" Revolut cell into (currency, value).

    Returns (pd.NA, float('nan')) for empty / unparseable cells rather than
    raising, so a malformed row doesn't abort the whole import.
    """
    if cell is None or (isinstance(cell, float) and pd.isna(cell)):
        return pd.NA, float("nan")

    s = str(cell).strip()
    if not s:
        return pd.NA, float("nan")

    m = _PREFIXED_AMOUNT_RE.match(s)
    if not m:
        # Fallback: sometimes Revolut may emit just a number (e.g. future
        # variants).  Try to coerce to float and leave currency unknown.
        try:
            return pd.NA, float(s.replace(",", ""))
        except ValueError:
            return pd.NA, float("nan")

    value = float(m.group("val").replace(",", ""))
    return m.group("ccy"), value


class RevolutAdapter(BaseBrokerAdapter):
    name = "revolut"
    display_name = "Revolut"

    # --- detection ---------------------------------------------------------
    @classmethod
    def detect(cls, header_line: str) -> bool:
        cols = [c.strip() for c in header_line.split(",")]
        # Must match the first N marker columns in order
        if len(cols) < len(_REVOLUT_HEADER_MARKERS):
            return False
        return tuple(cols[: len(_REVOLUT_HEADER_MARKERS)]) == _REVOLUT_HEADER_MARKERS

    # --- parse -------------------------------------------------------------
    @classmethod
    def _parse(cls, file_obj) -> pd.DataFrame:
        # `dtype=str` keeps prefixed-amount cells intact for the normalizer.
        return pd.read_csv(file_obj, low_memory=False, dtype=str)

    # --- normalize ---------------------------------------------------------
    @classmethod
    def _normalize(cls, raw: pd.DataFrame) -> pd.DataFrame:
        raw = raw.copy()
        raw.columns = [c.strip() for c in raw.columns]

        # 1) Timestamps: ISO-8601 UTC with variable fractional seconds → naive UTC
        times = pd.to_datetime(raw["Date"], format="ISO8601", utc=True, errors="coerce")
        times = times.dt.tz_localize(None)

        # 2) Action translation (unknown types pass through verbatim so they
        #    land in the "other" bucket rather than being silently dropped).
        action = raw["Type"].map(lambda t: _ACTION_MAP.get(str(t).strip(), str(t).strip()))

        # 3) Split combined "<CCY> <value>" cells
        price_split = raw["Price per share"].apply(_split_prefixed_amount)
        price_ccy   = price_split.apply(lambda x: x[0])
        price_val   = price_split.apply(lambda x: x[1])

        total_split = raw["Total Amount"].apply(_split_prefixed_amount)
        # For Total we prefer the standalone `Currency` column as authoritative
        # (Revolut always fills it, even when Total Amount is "USD 0") and use
        # the parsed prefix only as a fallback.
        total_ccy_raw = raw["Currency"].astype(str).str.strip()
        total_ccy = total_ccy_raw.where(total_ccy_raw.ne("") & total_ccy_raw.ne("nan"),
                                         total_split.apply(lambda x: x[0]))
        total_val = total_split.apply(lambda x: x[1])

        # 4) Numeric Quantity and FX Rate
        quantity = pd.to_numeric(raw["Quantity"], errors="coerce")
        fx_rate  = pd.to_numeric(raw["FX Rate"], errors="coerce")

        # 5) Ticker: empty for cash rows (CASH TOP-UP etc.)
        ticker = raw["Ticker"].astype(str).str.strip().replace({"": pd.NA, "nan": pd.NA})

        # 6) Assemble canonical frame
        out = pd.DataFrame({
            canonical.COL_TIME:   times,
            canonical.COL_ACTION: action,
            canonical.COL_TICKER: ticker,
            canonical.COL_NAME:   ticker,     # Revolut omits a separate Name column
            canonical.COL_ISIN:   pd.NA,
            canonical.COL_SHARES:          quantity,
            canonical.COL_PRICE_PER_SHARE: price_val,
            canonical.COL_PRICE_CCY:       price_ccy,
            canonical.COL_EXCHANGE_RATE:   fx_rate,
            # Result is computed later by the FIFO pass.  Seed with 0.0 so
            # existing aggregations (.fillna(0).sum()) are safe before that
            # pass runs.
            canonical.COL_RESULT:     0.0,
            canonical.COL_RESULT_CCY: price_ccy,   # native trade currency
            canonical.COL_TOTAL:     total_val,
            canonical.COL_TOTAL_CCY: total_ccy,
            # Revolut doesn't itemize fees or withholding tax on dividend rows.
            # ensure_canonical_columns() will pad the rest with zeros / <NA>.
        })

        # 7) USD-only filter (see module docstring).
        #    Every row in the analyzed view must be USD-denominated.  This
        #    drops EUR staging cash flows and the one-off EUR-listed ETF
        #    positions, leaving a pure USD sub-portfolio.
        out = out[out[canonical.COL_TOTAL_CCY] == "USD"].reset_index(drop=True)

        return out
