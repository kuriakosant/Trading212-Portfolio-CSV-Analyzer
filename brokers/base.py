"""
brokers/base.py — Abstract broker adapter contract.

Each broker adapter is responsible for three things:

    1.  Detection         Given the first line of a CSV (the header), return
                          True if the file belongs to this broker.

    2.  Parsing           Read the raw CSV file-like object into a DataFrame.
                          May do broker-specific cleanup (date formats,
                          combined currency+value strings, etc.).

    3.  Normalization     Produce a DataFrame conforming to the canonical
                          schema declared in `brokers.canonical`.

Downstream code (analyzer, charts, app) only ever sees the canonical output
and is therefore broker-agnostic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import pandas as pd

from . import canonical


class BaseBrokerAdapter(ABC):
    """Interface every broker adapter must implement."""

    # Unique short identifier (also set as _broker on every normalized row)
    name: str = ""

    # Human-readable label shown in the UI
    display_name: str = ""

    # ---------------------------------------------------------------- detect
    @classmethod
    @abstractmethod
    def detect(cls, header_line: str) -> bool:
        """Return True when the CSV's header line identifies this broker."""

    # ----------------------------------------------------------------- load
    @classmethod
    def load(cls, file_obj) -> pd.DataFrame:
        """
        Full pipeline: parse the raw CSV, normalize it to the canonical
        schema, and stamp the `_broker` column.  Subclasses usually only
        override `_parse` and `_normalize`.
        """
        raw = cls._parse(file_obj)
        norm = cls._normalize(raw)
        return canonical.ensure_canonical_columns(norm, cls.name)

    # ------------------------------------------------------ subclass hooks
    @classmethod
    @abstractmethod
    def _parse(cls, file_obj) -> pd.DataFrame:
        """Read the raw CSV into a pandas DataFrame (no schema coercion yet)."""

    @classmethod
    @abstractmethod
    def _normalize(cls, raw: pd.DataFrame) -> pd.DataFrame:
        """
        Translate broker-specific columns/values into the canonical schema.

        The returned frame should have canonical column names for whatever it
        can populate; `load()` will backfill any missing canonical columns
        with safe defaults.
        """
