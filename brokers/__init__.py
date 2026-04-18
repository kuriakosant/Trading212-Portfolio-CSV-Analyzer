"""
brokers/ — Multi-broker CSV ingestion.

Public API:

    detect(file_obj) -> BaseBrokerAdapter   # pick the right adapter for a file
    load(file_obj)   -> pd.DataFrame        # parse + normalize into canonical form
    KNOWN_ADAPTERS                          # ordered tuple of registered adapters

The canonical schema every adapter emits is declared in `brokers.canonical`.
Downstream modules (`analyzer`, `charts`, `app`) consume only the canonical
shape and must not reference broker-specific column names directly.
"""

from __future__ import annotations

from typing import IO

import pandas as pd

from .base import BaseBrokerAdapter
from .trading212 import Trading212Adapter
from .revolut import RevolutAdapter
from . import canonical, fifo

# Adapter registry — detection order matters only if two adapters could ever
# match the same header (none do today).  Add new brokers here.
KNOWN_ADAPTERS: tuple[type[BaseBrokerAdapter], ...] = (
    Trading212Adapter,
    RevolutAdapter,
)


class UnknownBrokerError(ValueError):
    """Raised when no registered adapter recognizes a CSV's header."""


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def _read_header_line(file_obj: IO) -> str:
    """
    Return the first non-empty line of `file_obj` and rewind it.

    Works for both filesystem files and Streamlit's in-memory UploadedFile
    (which supports seek/read like a normal file object).
    """
    try:
        file_obj.seek(0)
    except Exception:
        pass

    # Binary and text streams both possible; decode defensively.
    raw = file_obj.readline()
    try:
        file_obj.seek(0)
    except Exception:
        pass

    if isinstance(raw, bytes):
        raw = raw.decode("utf-8-sig", errors="replace")
    return raw.rstrip("\r\n")


def detect(file_obj: IO) -> type[BaseBrokerAdapter]:
    """Return the adapter class that recognizes this file's header."""
    header = _read_header_line(file_obj)
    for adapter in KNOWN_ADAPTERS:
        if adapter.detect(header):
            return adapter
    raise UnknownBrokerError(
        f"Unrecognized CSV header. Supported brokers: "
        f"{', '.join(a.display_name for a in KNOWN_ADAPTERS)}. "
        f"First line was: {header!r}"
    )


def load(file_obj: IO) -> pd.DataFrame:
    """
    Detect the broker and return a canonical-schema DataFrame for the file.
    """
    adapter = detect(file_obj)
    return adapter.load(file_obj)


__all__ = [
    "BaseBrokerAdapter",
    "Trading212Adapter",
    "RevolutAdapter",
    "KNOWN_ADAPTERS",
    "UnknownBrokerError",
    "canonical",
    "fifo",
    "detect",
    "load",
]
