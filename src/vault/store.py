"""Replaceable raw-vault backends with digest verification and retention."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Protocol

STORE_TYPE = "vault"
CHAIN_VERSION = 1
GENESIS_HASH = hashlib.sha256(b"ULPF-RAW-VAULT-GENESIS-V1").hexdigest()


def canonical_record_bytes(metadata: RawRecordMetadata) -> bytes:
    """Return deterministic bytes for one record's integrity hash.

    The canonical input is UTF-8 JSON with sorted keys, compact separators,
    and explicit nulls. It contains no filesystem timestamps or serialization
    artifacts outside these named fields.
    """
    if metadata.sequence is None or metadata.previous_record_hash is None:
        raise IntegrityError("Record is missing sequence or predecessor")
    payload = {
        "capture_timestamp": metadata.capture_timestamp,
        "input_format": metadata.input_format,
        "locator": metadata.locator,
        "previous_record_hash": metadata.previous_record_hash,
        "raw_hash": metadata.raw_hash,
        "retention_expires_at": metadata.retention_expires_at,
        "sequence": metadata.sequence,
        "size": metadata.size,
        "source_id": metadata.source_id,
        "version": CHAIN_VERSION,
    }
    # Byte offsets / record index are integrity-protected when present.
    # Records captured before offset metadata existed hash identically to
    # before, keeping historical chains verifiable. ``purged_at`` is
    # deliberately excluded: it is stamped by retention purge after the
    # record is already chained.
    if metadata.byte_offset_start is not None:
        payload["byte_offset_start"] = metadata.byte_offset_start
    if metadata.byte_offset_end is not None:
        payload["byte_offset_end"] = metadata.byte_offset_end
    if metadata.record_index is not None:
        payload["record_index"] = metadata.record_index
    if metadata.profile_version is not None:
        payload["profile_version"] = metadata.profile_version
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def calculate_record_hash(metadata: RawRecordMetadata) -> str:
    return hashlib.sha256(canonical_record_bytes(metadata)).hexdigest()


def _checkpoint_bytes(checkpoint: Dict[str, Any]) -> bytes:
    payload = {key: checkpoint[key] for key in ("version", "sequence", "head_hash", "genesis_hash")}
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")

class VaultError(Exception):
    """Base class for raw-vault failures."""

class IntegrityError(VaultError):
    """Raised when the append-only integrity chain cannot be verified."""

class RecordNotFoundError(VaultError):
    """Raised when a raw locator has no stored record."""

class CorruptRecordError(IntegrityError):
    """Raised when stored bytes or metadata do not match the digest."""

class ExpiredRecordError(VaultError):
    """Raised when a record is past its retention deadline."""

class InvalidCheckpointError(IntegrityError):
    """Raised when a checkpoint is missing, malformed, or mismatched."""

@dataclass(frozen=True)
class RawRecordMetadata:
    raw_hash: str
    source_id: Optional[str]
    capture_timestamp: str
    input_format: Optional[str]
    size: int
    locator: str
    profile_version: Optional[str] = None
    retention_expires_at: Optional[str] = None
    sequence: Optional[int] = None
    previous_record_hash: Optional[str] = None
    record_hash: Optional[str] = None
    byte_offset_start: Optional[int] = None
    byte_offset_end: Optional[int] = None
    record_index: Optional[int] = None
    purged_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "raw_hash": self.raw_hash,
            "source_id": self.source_id,
            "capture_timestamp": self.capture_timestamp,
            "input_format": self.input_format,
            "size": self.size,
            "locator": self.locator,
            "retention_expires_at": self.retention_expires_at,
            "sequence": self.sequence,
            "previous_record_hash": self.previous_record_hash,
            "record_hash": self.record_hash,
            "byte_offset_start": self.byte_offset_start,
            "byte_offset_end": self.byte_offset_end,
            "record_index": self.record_index,
            "purged_at": self.purged_at,
        }
        if self.profile_version is not None:
            data["profile_version"] = self.profile_version
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RawRecordMetadata":
        return cls(**data)

class VaultBackend(Protocol):
    def put(self, raw_bytes: bytes, **metadata: Any) -> tuple[str, str]: ...
    def get(self, locator: str) -> bytes: ...
    def metadata(self, locator: str) -> RawRecordMetadata: ...
    def verify(self, locator: str) -> bool: ...
    def purge_expired(self, now: Optional[datetime] = None) -> int: ...
    def clear(self) -> None: ...
    def verification_report(self) -> Dict[str, Any]: ...

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)

def _timestamp(value: Optional[datetime]) -> str:
    current = value or _utc_now()
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc).isoformat()

def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _normalize_capture_timestamp(value: Any) -> Optional[datetime]:
    """Coerce a caller-supplied capture timestamp.

    Accepts a ``datetime`` (assumed UTC when naive) or an ISO-8601 string
    (``Z`` suffix permitted). Anything else raises ``ValueError`` so a bad
    timestamp fails loudly instead of silently falling back to "now".
    Returns ``None`` when no timestamp was supplied.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return _parse_timestamp(value)
        except ValueError as exc:
            raise ValueError(f"Invalid capture_timestamp (expected ISO-8601): {value!r}") from exc
    raise ValueError(
        f"Invalid capture_timestamp type: {type(value).__name__} "
        "(expected datetime or ISO-8601 string)"
    )

def _metadata_for(raw_bytes: bytes, locator: str, digest: str, **metadata: Any) -> RawRecordMetadata:
    capture_timestamp = _normalize_capture_timestamp(metadata.get("capture_timestamp"))
    capture = _timestamp(capture_timestamp)
    retention_expires_at = metadata.get("retention_expires_at")
    retention_seconds = metadata.get("retention_seconds")
    if retention_expires_at is None and retention_seconds is not None:
        retention_expires_at = _timestamp(
            _parse_timestamp(capture) + timedelta(seconds=float(retention_seconds))
        )
    return RawRecordMetadata(
        raw_hash=digest,
        source_id=metadata.get("source_id"),
        profile_version=metadata.get("profile_version"),
        capture_timestamp=capture,
        input_format=metadata.get("input_format"),
        size=len(raw_bytes),
        locator=locator,
        retention_expires_at=_timestamp(retention_expires_at) if isinstance(retention_expires_at, datetime) else retention_expires_at,
        byte_offset_start=metadata.get("byte_offset_start"),
        byte_offset_end=metadata.get("byte_offset_end"),
        record_index=metadata.get("record_index"),
    )

class InMemoryVaultBackend:
    """Test backend retaining the same digest, locator, and tombstone semantics."""

    def __init__(self, clock: Optional[Callable[[], datetime]] = None) -> None:
        self._records: Dict[str, tuple[Optional[bytes], RawRecordMetadata]] = {}
        self._clock = clock or _utc_now

    def put(self, raw_bytes: bytes, **metadata: Any) -> tuple[str, str]:
        digest = hashlib.sha256(raw_bytes).hexdigest()
        locator = f"sha256:{digest}"
        existing = self._records.get(digest)
        if existing is not None:
            stored_bytes, stored_metadata = existing
            if stored_metadata.raw_hash != digest:
                raise IntegrityError(f"Stored metadata digest mismatch for {locator!r}")
            if stored_bytes is None:
                # Tombstone resurrection: restore payload without a new record.
                restored = RawRecordMetadata(
                    **{**stored_metadata.to_dict(), "purged_at": None}
                )
                self._records[digest] = (bytes(raw_bytes), restored)
            return locator, digest
        self._records[digest] = (bytes(raw_bytes), _metadata_for(raw_bytes, locator, digest, **metadata))
        return locator, digest

    def _metadata(self, locator: str) -> RawRecordMetadata:
        digest = _digest_from_locator(locator)
        if digest not in self._records:
            raise RecordNotFoundError(f"Raw record not found: {locator!r}")
        return self._records[digest][1]

    def _record(self, locator: str) -> tuple[bytes, RawRecordMetadata]:
        metadata = self._metadata(locator)
        if self._records[_digest_from_locator(locator)][0] is None:
            raise RecordNotFoundError(f"Raw record not found: {locator!r}")
        _check_expiry(metadata, self._clock())
        raw_bytes = self._records[_digest_from_locator(locator)][0]
        return bytes(raw_bytes), metadata

    def get(self, locator: str) -> bytes:
        raw_bytes, metadata = self._record(locator)
        _verify_bytes(locator, raw_bytes, metadata)
        return bytes(raw_bytes)

    def metadata(self, locator: str) -> RawRecordMetadata:
        return self._metadata(locator)

    def verify(self, locator: str) -> bool:
        try:
            raw_bytes, metadata = self._record(locator)
            _verify_bytes(locator, raw_bytes, metadata)
            return True
        except (RecordNotFoundError, CorruptRecordError, ExpiredRecordError):
            return False

    def purge_expired(self, now: Optional[datetime] = None) -> int:
        current = now or self._clock()
        purged = 0
        for digest, (stored_bytes, metadata) in list(self._records.items()):
            if metadata.purged_at:
                continue
            if _is_expired(metadata, current):
                # Retention removes the payload only; the metadata tombstone
                # is retained so operational lookups stay explicit.
                self._records[digest] = (
                    None,
                    RawRecordMetadata(
                        **{**metadata.to_dict(), "purged_at": _timestamp(current)}
                    ),
                )
                purged += 1
        return purged

    def clear(self) -> None:
        self._records.clear()

    def verification_report(self) -> Dict[str, Any]:
        return {
            "status": "unavailable",
            "reason": "Configured in-memory backend has no persisted integrity chain",
            "records": 0,
            "checkpoint": {
                "status": "unavailable",
                "reason": "Configured in-memory backend does not support checkpoints",
                "sequence": None,
                "head_hash": None,
                "checkpoint_hash": None,
            },
        }

class FileVaultBackend:
    """Filesystem-backed durable vault storing raw bytes and JSON sidecars."""

    def __init__(self, root: os.PathLike[str] | str, clock: Optional[Callable[[], datetime]] = None) -> None:
        self.root = Path(root)
        self.records = self.root / "records"
        self.checkpoints = self.root / "checkpoints"
        self.records.mkdir(parents=True, exist_ok=True)
        self.checkpoints.mkdir(parents=True, exist_ok=True)
        self._clock = clock or _utc_now
        self._lock = threading.Lock()
        self._initialize_chain()

    @property
    def chain_path(self) -> Path:
        return self.root / "chain.json"

    def _initialize_chain(self) -> None:
        if not self.chain_path.exists():
            self.chain_path.write_text(json.dumps({
                "version": CHAIN_VERSION,
                "genesis_hash": GENESIS_HASH,
                "head_hash": GENESIS_HASH,
                "next_sequence": 1,
                "entries": [],
            }, sort_keys=True, separators=(",", ":")), encoding="utf-8")

    def _load_chain(self) -> Dict[str, Any]:
        try:
            chain = json.loads(self.chain_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise IntegrityError("Integrity chain state is unreadable") from exc
        if chain.get("version") != CHAIN_VERSION or chain.get("genesis_hash") != GENESIS_HASH:
            raise IntegrityError("Integrity chain genesis or version is invalid")
        return chain

    def _write_chain(self, chain: Dict[str, Any]) -> None:
        self.chain_path.write_text(json.dumps(chain, sort_keys=True, separators=(",", ":")), encoding="utf-8")

    def _paths(self, locator: str) -> tuple[Path, Path]:
        digest = _digest_from_locator(locator)
        return self.records / f"{digest}.raw", self.records / f"{digest}.json"

    def put(self, raw_bytes: bytes, **metadata: Any) -> tuple[str, str]:
        with self._lock:
            raw_bytes = bytes(raw_bytes)
            digest = hashlib.sha256(raw_bytes).hexdigest()
            locator = f"sha256:{digest}"
            raw_path, metadata_path = self._paths(locator)

            if metadata_path.exists():
                try:
                    existing = RawRecordMetadata.from_dict(
                        json.loads(metadata_path.read_text(encoding="utf-8"))
                    )
                except (OSError, json.JSONDecodeError, TypeError, KeyError) as exc:
                    raise IntegrityError(f"Existing record metadata is unreadable: {locator!r}") from exc
                if existing.raw_hash != digest:
                    raise IntegrityError(f"Existing record digest mismatch: {locator!r}")
                if not raw_path.exists():
                    # Tombstone resurrection: restore the payload for the
                    # already-chained record instead of appending a duplicate
                    # chain entry. purged_at is not part of the canonical
                    # record hash, so clearing it cannot break the chain.
                    raw_path.write_bytes(raw_bytes)
                    metadata_path.write_text(
                        json.dumps(
                            RawRecordMetadata(
                                **{**existing.to_dict(), "purged_at": None}
                            ).to_dict(),
                            sort_keys=True,
                        ),
                        encoding="utf-8",
                    )
                return locator, digest

            if raw_path.exists():
                # Stray payload without metadata is not a valid record.
                raw_path.unlink()

            chain = self._load_chain()
            sequence = chain["next_sequence"]
            previous = chain["head_hash"]
            record = _metadata_for(
                raw_bytes,
                locator,
                digest,
                **metadata,
            )
            record = RawRecordMetadata(
                **{**record.to_dict(), "sequence": sequence, "previous_record_hash": previous}
            )
            record = RawRecordMetadata(**{**record.to_dict(), "record_hash": calculate_record_hash(record)})
            raw_path.write_bytes(raw_bytes)
            metadata_path.write_text(json.dumps(record.to_dict(), sort_keys=True), encoding="utf-8")
            chain["entries"].append({"sequence": sequence, "locator": locator, "record_hash": record.record_hash})
            chain["head_hash"] = record.record_hash
            chain["next_sequence"] = sequence + 1
            self._write_chain(chain)
            return locator, digest

    def _record(self, locator: str) -> tuple[bytes, RawRecordMetadata]:
        raw_path, metadata_path = self._paths(locator)
        if not raw_path.exists() or not metadata_path.exists():
            raise RecordNotFoundError(f"Raw record not found: {locator!r}")
        try:
            metadata = RawRecordMetadata.from_dict(json.loads(metadata_path.read_text(encoding="utf-8")))
            raw_bytes = raw_path.read_bytes()
        except (OSError, json.JSONDecodeError, TypeError, KeyError) as exc:
            raise CorruptRecordError(f"Raw record metadata is unreadable: {locator!r}") from exc
        _check_expiry(metadata, self._clock())
        return raw_bytes, metadata

    def get(self, locator: str) -> bytes:
        raw_bytes, metadata = self._record(locator)
        _verify_bytes(locator, raw_bytes, metadata)
        return raw_bytes

    def metadata(self, locator: str) -> RawRecordMetadata:
        _, metadata_path = self._paths(locator)
        if not metadata_path.exists():
            raise RecordNotFoundError(f"Raw record not found: {locator!r}")
        try:
            return RawRecordMetadata.from_dict(json.loads(metadata_path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError, TypeError, KeyError) as exc:
            raise CorruptRecordError(f"Raw record metadata is unreadable: {locator!r}") from exc

    def verify(self, locator: str) -> bool:
        try:
            raw_bytes, metadata = self._record(locator)
            _verify_bytes(locator, raw_bytes, metadata)
            return True
        except (RecordNotFoundError, CorruptRecordError, ExpiredRecordError):
            return False

    def purge_expired(self, now: Optional[datetime] = None) -> int:
        current = now or self._clock()
        removed = 0
        for metadata_path in sorted(self.records.glob("*.json")):
            try:
                metadata = RawRecordMetadata.from_dict(json.loads(metadata_path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError, TypeError, KeyError):
                continue
            if metadata.purged_at:
                continue
            if _is_expired(metadata, current):
                # Retention removes the payload only. The metadata sidecar is
                # retained and tombstoned so the append-only chain keeps
                # verifying historical entries after an ordinary purge.
                raw_path = metadata_path.with_suffix(".raw")
                raw_path.unlink(missing_ok=True)
                tombstoned = RawRecordMetadata(
                    **{**metadata.to_dict(), "purged_at": _timestamp(current)}
                )
                metadata_path.write_text(
                    json.dumps(tombstoned.to_dict(), sort_keys=True), encoding="utf-8"
                )
                removed += 1
        return removed

    def clear(self) -> None:
        if self.records.exists():
            for path in self.records.iterdir():
                if path.is_file():
                    path.unlink()
        if self.checkpoints.exists():
            for path in self.checkpoints.iterdir():
                if path.is_file():
                    path.unlink()
        self._write_chain({
            "version": CHAIN_VERSION,
            "genesis_hash": GENESIS_HASH,
            "head_hash": GENESIS_HASH,
            "next_sequence": 1,
            "entries": [],
        })

    def verify_chain(self) -> bool:
        chain = self._load_chain()
        entries = chain.get("entries")
        if not isinstance(entries, list) or chain.get("next_sequence") != len(entries) + 1:
            raise IntegrityError("Integrity chain sequence state is invalid")
        previous = GENESIS_HASH
        for expected_sequence, entry in enumerate(entries, start=1):
            if entry.get("sequence") != expected_sequence:
                raise IntegrityError("Integrity chain sequence is missing or reordered")
            metadata = self.metadata(entry["locator"])
            if metadata.sequence != expected_sequence or metadata.previous_record_hash != previous:
                raise IntegrityError("Integrity chain predecessor link is broken")
            if metadata.record_hash != entry.get("record_hash") or calculate_record_hash(metadata) != metadata.record_hash:
                raise IntegrityError("Integrity chain record hash is invalid")
            if metadata.purged_at:
                # Retention tombstone: payload intentionally removed under
                # policy. Metadata linkage still verified above; raw bytes
                # are absent by design and must not fail historical checks.
                pass
            else:
                raw_bytes = self._raw_bytes(entry["locator"])
                _verify_bytes(entry["locator"], raw_bytes, metadata)
            previous = metadata.record_hash
        if chain.get("head_hash") != previous:
            raise IntegrityError("Integrity chain head is invalid")
        return True

    def _raw_bytes(self, locator: str) -> bytes:
        raw_path, _ = self._paths(locator)
        if not raw_path.exists():
            raise IntegrityError(f"Integrity chain record is missing: {locator!r}")
        return raw_path.read_bytes()

    def create_checkpoint(self) -> Dict[str, Any]:
        self.verify_chain()
        chain = self._load_chain()
        checkpoint = {
            "version": CHAIN_VERSION,
            "sequence": len(chain["entries"]),
            "head_hash": chain["head_hash"],
            "genesis_hash": GENESIS_HASH,
        }
        checkpoint["checkpoint_hash"] = hashlib.sha256(_checkpoint_bytes(checkpoint)).hexdigest()
        path = self.checkpoints / f"checkpoint-{checkpoint['sequence']}-{checkpoint['head_hash'][:12]}.json"
        path.write_text(json.dumps(checkpoint, sort_keys=True, separators=(",", ":")), encoding="utf-8")
        return checkpoint

    def verify_checkpoint(self, checkpoint: Dict[str, Any]) -> bool:
        required = {"version", "sequence", "head_hash", "genesis_hash", "checkpoint_hash"}
        if set(checkpoint) != required or checkpoint["genesis_hash"] != GENESIS_HASH:
            raise InvalidCheckpointError("Checkpoint fields or genesis hash are invalid")
        expected = hashlib.sha256(_checkpoint_bytes(checkpoint)).hexdigest()
        if expected != checkpoint["checkpoint_hash"]:
            raise InvalidCheckpointError("Checkpoint hash is invalid")
        self.verify_chain()
        chain = self._load_chain()
        if checkpoint["sequence"] > len(chain["entries"]):
            raise InvalidCheckpointError("Checkpoint sequence is beyond the chain")
        expected_head = GENESIS_HASH if checkpoint["sequence"] == 0 else chain["entries"][checkpoint["sequence"] - 1]["record_hash"]
        if checkpoint["head_hash"] != expected_head:
            raise InvalidCheckpointError("Checkpoint head does not match chain boundary")
        return True

    def _checkpoint_status(self, chain_length: int) -> Dict[str, Any]:
        """Evaluate the latest checkpoint anchor against the current chain."""
        candidates: list[Dict[str, Any]] = []
        file_count = 0
        if self.checkpoints.exists():
            for path in sorted(self.checkpoints.glob("checkpoint-*.json")):
                file_count += 1
                try:
                    checkpoint = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                if isinstance(checkpoint, dict) and "sequence" in checkpoint:
                    candidates.append(checkpoint)

        if not candidates:
            if file_count:
                return {
                    "status": "invalid",
                    "reason": "Checkpoint file(s) exist but are unreadable",
                    "sequence": None,
                    "head_hash": None,
                    "checkpoint_hash": None,
                }
            return {
                "status": "missing",
                "reason": "No checkpoint anchors the integrity chain",
                "sequence": None,
                "head_hash": None,
                "checkpoint_hash": None,
            }

        latest = max(candidates, key=lambda c: c.get("sequence", -1))
        summary = {
            "sequence": latest.get("sequence"),
            "head_hash": latest.get("head_hash"),
            "checkpoint_hash": latest.get("checkpoint_hash"),
        }
        try:
            self.verify_checkpoint(latest)
        except InvalidCheckpointError as exc:
            return {**summary, "status": "invalid", "reason": str(exc)}

        if latest["sequence"] == chain_length:
            return {**summary, "status": "valid", "reason": None}
        return {
            **summary,
            "status": "stale",
            "reason": (
                f"Checkpoint anchors sequence {latest['sequence']} "
                f"but the chain head is at {chain_length}"
            ),
        }

    def verification_report(self) -> Dict[str, Any]:
        checkpoint_unavailable = {
            "status": "unavailable",
            "reason": "Chain verification failed before checkpoint evaluation",
            "sequence": None,
            "head_hash": None,
            "checkpoint_hash": None,
        }
        try:
            self.verify_chain()
            chain = self._load_chain()
            checkpoint = self._checkpoint_status(len(chain["entries"]))
        except RecordNotFoundError as exc:
            return {
                "status": "missing",
                "reason": str(exc),
                "records": None,
                "checkpoint": dict(checkpoint_unavailable),
            }
        except (CorruptRecordError, IntegrityError, ExpiredRecordError) as exc:
            return {
                "status": "corrupted",
                "reason": str(exc),
                "records": None,
                "checkpoint": dict(checkpoint_unavailable),
            }

        # Overall status is 'verified' only when the chain verifies AND the
        # checkpoint validly anchors the current head. Anchor problems are
        # reported explicitly as missing/stale/invalid.
        if checkpoint["status"] == "valid":
            status = "verified"
            reason = None
        else:
            status = checkpoint["status"]
            reason = checkpoint["reason"]

        return {
            "status": status,
            "chain_status": "valid",
            "reason": reason,
            "records": len(chain["entries"]),
            "head_hash": chain["head_hash"],
            "genesis_hash": chain["genesis_hash"],
            "checkpoint": checkpoint,
        }

def _digest_from_locator(locator: str) -> str:
    if not isinstance(locator, str) or not locator.startswith("sha256:"):
        raise ValueError(f"Invalid locator format: {locator!r}")
    digest = locator[7:]
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise ValueError(f"Invalid locator format: {locator!r}")
    return digest

def _check_expiry(metadata: RawRecordMetadata, now: Optional[datetime] = None) -> None:
    if metadata.retention_expires_at and _parse_timestamp(metadata.retention_expires_at) <= (now or _utc_now()):
        raise ExpiredRecordError(f"Raw record expired: {metadata.locator!r}")

def _is_expired(metadata: RawRecordMetadata, now: datetime) -> bool:
    return bool(metadata.retention_expires_at and _parse_timestamp(metadata.retention_expires_at) <= now)

def _verify_bytes(locator: str, raw_bytes: bytes, metadata: RawRecordMetadata) -> None:
    digest = hashlib.sha256(raw_bytes).hexdigest()
    if digest != metadata.raw_hash or locator != metadata.locator or len(raw_bytes) != metadata.size:
        raise CorruptRecordError(f"Raw record digest or metadata mismatch: {locator!r}")

def _default_backend() -> VaultBackend:
    root = os.environ.get("ULPF_VAULT_PATH")
    if root:
        return FileVaultBackend(root)
    return FileVaultBackend(Path(tempfile.gettempdir()) / "ulpf-vault")

_BACKEND: VaultBackend = _default_backend()

def configure_backend(backend: VaultBackend) -> None:
    global _BACKEND
    _BACKEND = backend

def put(raw_bytes: bytes, **metadata: Any) -> tuple[str, str]:
    return _BACKEND.put(raw_bytes, **metadata)

def get(locator: str) -> bytes:
    return _BACKEND.get(locator)

def metadata(locator: str) -> RawRecordMetadata:
    return _BACKEND.metadata(locator)

def verify(locator: str) -> bool:
    return _BACKEND.verify(locator)

def purge_expired(now: Optional[datetime] = None) -> int:
    return _BACKEND.purge_expired(now)

def dump_to_path(locator: str, path: str) -> None:
    raw = get(locator)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)

def clear() -> None:
    _BACKEND.clear()


def verify_chain() -> bool:
    verifier = getattr(_BACKEND, "verify_chain", None)
    if verifier is None:
        raise IntegrityError("Configured vault backend does not support chain verification")
    return verifier()


def create_checkpoint() -> Dict[str, Any]:
    creator = getattr(_BACKEND, "create_checkpoint", None)
    if creator is None:
        raise IntegrityError("Configured vault backend does not support checkpoints")
    return creator()


def verify_checkpoint(checkpoint: Dict[str, Any]) -> bool:
    verifier = getattr(_BACKEND, "verify_checkpoint", None)
    if verifier is None:
        raise IntegrityError("Configured vault backend does not support checkpoints")
    return verifier(checkpoint)


def verification_report() -> Dict[str, Any]:
    reporter = getattr(_BACKEND, "verification_report", None)
    if reporter is None:
        return {
            "status": "unavailable",
            "reason": "Configured vault backend does not expose operational verification",
            "records": None,
            "checkpoint": {
                "status": "unavailable",
                "reason": "Configured vault backend does not expose operational verification",
                "sequence": None,
                "head_hash": None,
                "checkpoint_hash": None,
            },
        }
    return reporter()
