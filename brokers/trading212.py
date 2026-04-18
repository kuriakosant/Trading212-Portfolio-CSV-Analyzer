"""
brokers/trading212.py — Trading212 CSV adapter.

Trading212 exports already align very closely with our canonical schema — most
columns pass through unchanged.  The only real work is:

  * tolerant date parsing (T212 exports use `YYYY-MM-DD HH:MM:SS`)
  * back-filling columns that older (pre-P&L) exports omit
  * numeric coercion on money columns
"""

from __future__ import annotations

import pandas as pd

from .base import BaseBrokerAdapter
from . import canonical


# These headers appear in every T212 "History" export we've seen.  We only
# require the intersection — T212 quietly adds/removes columns between
# export versions, so strict equality would be brittle.
_T212_HEADER_MARKERS = {"Action", "Time", "Ticker", "Total"}


class Trading212Adapter(BaseBrokerAdapter):
    name = "trading212"
    display_name = "Trading212"

    # --- detection ---------------------------------------------------------
    @classmethod
    def detect(cls, header_line: str) -> bool:
        cols = {c.strip() for c in header_line.split(",")}
        return _T212_HEADER_MARKERS.issubset(cols)

    # --- parse -------------------------------------------------------------
    @classmethod
    def _parse(cls, file_obj) -> pd.DataFrame:
        return pd.read_csv(file_obj, low_memory=False)

    # --- normalize ---------------------------------------------------------
    @classmethod
    def _normalize(cls, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df.columns = [c.strip() for c in df.columns]

        # Back-compat: older T212 exports (2024 and earlier) omit the P&L
        # columns entirely.  Seed them with 0.0 so downstream aggregations
        # don't need to special-case their absence.
        back_compat_cols = [
            canonical.COL_RESULT,
            "Result (EUR)",
            "Result (USD)",
            canonical.COL_WITHHOLDING,
            "Withholding tax (EUR)",
            "Withholding tax (USD)",
        ]
        for col in back_compat_cols:
            if col not in df.columns:
                df[col] = 0.0

        df[canonical.COL_TIME] = pd.to_datetime(
            df[canonical.COL_TIME],
            format="%Y-%m-%d %H:%M:%S",
            errors="coerce",
        )

        for col in canonical.NUMERIC_COLUMNS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        return df
