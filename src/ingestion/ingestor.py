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
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, Iterable, List, Optional, Union

# Allow running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.vault import store as vault


class IngestionError(Exception):
    """Base class for formal ingestion-boundary failures."""


class UnsupportedFormatError(IngestionError):
    """Raised when an input format is not explicitly supported."""


class MalformedInputError(IngestionError):
    """Raised when raw input cannot be decoded or is empty."""


class IngestedEvent:
    """Minimal envelope produced by ingestion."""

    __slots__ = ("locator", "sha256", "byte_length", "source_path", "raw_ref", "metadata", "integrity_status", "integrity_reason", "chain_verified")

    def __init__(self, locator: str, sha256: str, byte_length: int, source_path: str, metadata=None, integrity=None):
        self.locator = locator
        self.sha256 = sha256
        self.byte_length = byte_length
        self.source_path = source_path
        self.raw_ref = {
            "store": vault.STORE_TYPE,
            "locator": locator,
            "raw_hash": sha256,
        }
        self.metadata = metadata
        integrity = integrity or {"status": "unavailable", "reason": "Integrity state was not provided", "chain_verified": None}
        self.integrity_status = integrity["status"]
        self.integrity_reason = integrity.get("reason")
        self.chain_verified = integrity.get("chain_verified")

    def __repr__(self) -> str:
        return (
            f"IngestedEvent(locator={self.locator!r}, "
            f"sha256={self.sha256[:12]!r}..., "
            f"bytes={self.byte_length})"
        )


@dataclass(frozen=True)
class IngestionResult:
    """Result of raw capture and optional parser execution."""

    ingested: IngestedEvent
    source_id: Optional[str]
    profile_version: Optional[str]
    input_format: str
    status: str
    parsed: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    integrity_status: str = "unavailable"
    integrity_reason: Optional[str] = None
    chain_verified: Optional[bool] = None

    @property
    def raw_ref(self) -> dict:
        """Return the stable reference to the preserved raw record."""
        return dict(self.ingested.raw_ref)


SUPPORTED_FORMATS = frozenset({"syslog"})


def _coerce_raw_bytes(raw_input: Union[bytes, bytearray, memoryview, str]) -> bytes:
    if isinstance(raw_input, str):
        return raw_input.encode("utf-8")
    if isinstance(raw_input, (bytes, bytearray, memoryview)):
        return bytes(raw_input)
    raise MalformedInputError("Raw input must be bytes-like or UTF-8 text")


def _capture(
    raw_input: Union[bytes, bytearray, memoryview, str],
    source_label: str,
    **metadata: Any,
) -> IngestedEvent:
    raw_bytes = _coerce_raw_bytes(raw_input)
    if not raw_bytes:
        raise MalformedInputError("Raw input must not be empty")
    return ingest_bytes(raw_bytes, source_label=source_label, **metadata)


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

    return _capture(raw_bytes, os.path.abspath(path))


def ingest_bytes(
    raw_bytes: bytes,
    source_label: str = "<bytes>",
    *,
    source_id: Optional[str] = None,
    input_format: Optional[str] = None,
    capture_timestamp: Optional[datetime] = None,
    retention_seconds: Optional[float] = None,
) -> IngestedEvent:
    """
    Store raw bytes directly (e.g. when reading from a stream).

    Parameters
    ----------
    raw_bytes : bytes
    source_label : str
        Informational label only; not used for routing.
    """
    if not isinstance(raw_bytes, bytes):
        raise MalformedInputError("ingest_bytes requires bytes")
    if not raw_bytes:
        raise MalformedInputError("Raw input must not be empty")

    locator, sha256 = vault.put(
        raw_bytes,
        source_id=source_id,
        input_format=input_format,
        capture_timestamp=capture_timestamp,
        retention_seconds=retention_seconds,
    )
    record_metadata = vault.metadata(locator)
    integrity = verify_raw_reference(locator)
    return IngestedEvent(
        locator=locator,
        sha256=sha256,
        byte_length=len(raw_bytes),
        source_path=source_label,
        metadata=record_metadata,
        integrity=integrity,
    )


def verify_raw_reference(locator: str) -> Dict[str, Any]:
    """Verify one raw record and its chain without returning raw content."""
    try:
        if not vault.verify(locator):
            try:
                vault.metadata(locator)
            except vault.RecordNotFoundError:
                return {"status": "missing", "reason": "Raw record is missing", "chain_verified": False}
            return {"status": "corrupted", "reason": "Raw payload or metadata digest verification failed", "chain_verified": False}
        vault.verify_chain()
        return {"status": "verified", "reason": None, "chain_verified": True}
    except vault.RecordNotFoundError:
        return {"status": "missing", "reason": "Raw record is missing", "chain_verified": False}
    except vault.ExpiredRecordError:
        return {"status": "corrupted", "reason": "Raw record is expired", "chain_verified": False}
    except vault.IntegrityError as exc:
        if "does not support chain" in str(exc):
            return {"status": "unavailable", "reason": str(exc), "chain_verified": None}
        return {"status": "corrupted", "reason": str(exc), "chain_verified": False}
    except (AttributeError, NotImplementedError) as exc:
        return {"status": "unavailable", "reason": str(exc), "chain_verified": None}


def ingest_and_parse(
    raw_input: Union[bytes, bytearray, memoryview, str],
    *,
    parser: Callable[[str], Dict[str, Any]],
    source_id: str,
    input_format: str,
    profile_version: Optional[str] = None,
    source_label: str = "<bytes>",
) -> IngestionResult:
    """Capture raw input before parsing and return a traceable processing result.

    Parser and format failures are returned with the preserved raw reference so
    callers can inspect or replay the exact input. No format is guessed.
    """
    try:
        ingested = _capture(
            raw_input,
            source_label,
            source_id=source_id,
            input_format=input_format,
        )
    except IngestionError as exc:
        raise

    if input_format not in SUPPORTED_FORMATS:
        return IngestionResult(
            ingested=ingested,
            source_id=source_id,
            profile_version=profile_version,
            input_format=input_format,
            status="REJECTED",
            error=f"Unsupported input format: {input_format}",
            integrity_status=ingested.integrity_status,
            integrity_reason=ingested.integrity_reason,
            chain_verified=ingested.chain_verified,
        )

    try:
        text = _coerce_raw_bytes(raw_input).decode("utf-8")
    except UnicodeDecodeError as exc:
        return IngestionResult(
            ingested=ingested,
            source_id=source_id,
            profile_version=profile_version,
            input_format=input_format,
            status="REJECTED",
            error=f"Malformed UTF-8 input: {exc}",
            integrity_status=ingested.integrity_status,
            integrity_reason=ingested.integrity_reason,
            chain_verified=ingested.chain_verified,
        )

    if not text.strip():
        return IngestionResult(
            ingested=ingested,
            source_id=source_id,
            profile_version=profile_version,
            input_format=input_format,
            status="REJECTED",
            error="Malformed input: no event content",
            integrity_status=ingested.integrity_status,
            integrity_reason=ingested.integrity_reason,
            chain_verified=ingested.chain_verified,
        )

    try:
        parsed = parser(text)
    except Exception as exc:
        integrity = verify_raw_reference(ingested.locator)
        return IngestionResult(
            ingested=ingested,
            source_id=source_id,
            profile_version=profile_version,
            input_format=input_format,
            status="REJECTED",
            error=f"Parser rejected input: {exc}; integrity={integrity['status']}",
            integrity_status=integrity["status"],
            integrity_reason=integrity["reason"],
            chain_verified=integrity["chain_verified"],
        )

    integrity = verify_raw_reference(ingested.locator)
    return IngestionResult(
        ingested=ingested,
        source_id=source_id,
        profile_version=profile_version,
        input_format=input_format,
        status="PARSED",
        parsed=parsed,
        error=None if integrity["status"] == "verified" else integrity["reason"],
        integrity_status=integrity["status"],
        integrity_reason=integrity["reason"],
        chain_verified=integrity["chain_verified"],
    )


def ingest_batch(
    inputs: Iterable[Union[bytes, bytearray, memoryview, str]],
    *,
    source_label_prefix: str = "<batch>",
) -> List[IngestedEvent]:
    """Capture each batch item independently with one stable raw reference."""
    return [
        _capture(raw_input, f"{source_label_prefix}[{index}]")
        for index, raw_input in enumerate(inputs)
    ]
