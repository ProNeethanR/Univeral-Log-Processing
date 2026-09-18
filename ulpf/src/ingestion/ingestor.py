"""
ingestion/ingestor.py
---------------------
Reads a raw log file, stores it in the vault, and returns the event envelope
metadata (locator + SHA-256). Does not parse content.

Security contract:
  - Opens files in binary mode only.
  - Does not interpret or modify bytes.
  - Delegates all storage and hashing to vault/store.py.
"""

import os
import sys

# Allow running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.vault import store as vault


class IngestedEvent:
    """Minimal envelope produced by ingestion."""

    __slots__ = ("locator", "sha256", "byte_length", "source_path")

    def __init__(self, locator: str, sha256: str, byte_length: int, source_path: str):
        self.locator = locator
        self.sha256 = sha256
        self.byte_length = byte_length
        self.source_path = source_path

    def __repr__(self) -> str:
        return (
            f"IngestedEvent(locator={self.locator!r}, "
            f"sha256={self.sha256[:12]!r}..., "
            f"bytes={self.byte_length})"
        )


def ingest_file(path: str) -> IngestedEvent:
    """
    Read a raw log file, store in vault, return ingestion envelope.

    Parameters
    ----------
    path : str
        Absolute or relative path to the raw log file.

    Returns
    -------
    IngestedEvent

    Raises
    ------
    FileNotFoundError
        If the path does not exist.
    IsADirectoryError
        If the path is a directory.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Raw log file not found: {path!r}")
    if os.path.isdir(path):
        raise IsADirectoryError(f"Path is a directory, not a file: {path!r}")

    with open(path, "rb") as f:
        raw_bytes = f.read()

    locator, sha256 = vault.put(raw_bytes)
    return IngestedEvent(
        locator=locator,
        sha256=sha256,
        byte_length=len(raw_bytes),
        source_path=os.path.abspath(path),
    )


def ingest_bytes(raw_bytes: bytes, source_label: str = "<bytes>") -> IngestedEvent:
    """
    Store raw bytes directly (e.g. when reading from a stream).

    Parameters
    ----------
    raw_bytes : bytes
    source_label : str
        Informational label only; not used for routing.
    """
    locator, sha256 = vault.put(raw_bytes)
    return IngestedEvent(
        locator=locator,
        sha256=sha256,
        byte_length=len(raw_bytes),
        source_path=source_label,
    )
