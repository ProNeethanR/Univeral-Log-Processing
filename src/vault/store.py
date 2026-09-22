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
    retention_expires_at: Optional[str] = None
    sequence: Optional[int] = None
    previous_record_hash: Optional[str] = None
    record_hash: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
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
        }

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

def _metadata_for(raw_bytes: bytes, locator: str, digest: str, **metadata: Any) -> RawRecordMetadata:
    capture_timestamp = metadata.get("capture_timestamp")
    capture = _timestamp(capture_timestamp if isinstance(capture_timestamp, datetime) else None)
    retention_expires_at = metadata.get("retention_expires_at")
    retention_seconds = metadata.get("retention_seconds")
    if retention_expires_at is None and retention_seconds is not None:
        retention_expires_at = _timestamp(
            _parse_timestamp(capture) + timedelta(seconds=float(retention_seconds))
        )
    return RawRecordMetadata(
        raw_hash=digest,
        source_id=metadata.get("source_id"),
        capture_timestamp=capture,
        input_format=metadata.get("input_format"),
        size=len(raw_bytes),
        locator=locator,
        retention_expires_at=_timestamp(retention_expires_at) if isinstance(retention_expires_at, datetime) else retention_expires_at,
    )

class InMemoryVaultBackend:
    """Test backend retaining the same digest and locator semantics."""

    def __init__(self, clock: Optional[Callable[[], datetime]] = None) -> None:
        self._records: Dict[str, tuple[bytes, RawRecordMetadata]] = {}
        self._clock = clock or _utc_now

    def put(self, raw_bytes: bytes, **metadata: Any) -> tuple[str, str]:
        digest = hashlib.sha256(raw_bytes).hexdigest()
        locator = f"sha256:{digest}"
        self._records[digest] = (bytes(raw_bytes), _metadata_for(raw_bytes, locator, digest, **metadata))
        return locator, digest

    def _record(self, locator: str) -> tuple[bytes, RawRecordMetadata]:
        digest = _digest_from_locator(locator)
        if digest not in self._records:
            raise RecordNotFoundError(f"Raw record not found: {locator!r}")
        raw_bytes, metadata = self._records[digest]
        _check_expiry(metadata, self._clock())
        return raw_bytes, metadata

    def get(self, locator: str) -> bytes:
        raw_bytes, metadata = self._record(locator)
        _verify_bytes(locator, raw_bytes, metadata)
        return bytes(raw_bytes)

    def metadata(self, locator: str) -> RawRecordMetadata:
        digest = _digest_from_locator(locator)
        if digest not in self._records:
            raise RecordNotFoundError(f"Raw record not found: {locator!r}")
        return self._records[digest][1]

    def verify(self, locator: str) -> bool:
        try:
            raw_bytes, metadata = self._record(locator)
            _verify_bytes(locator, raw_bytes, metadata)
            return True
        except (RecordNotFoundError, CorruptRecordError, ExpiredRecordError):
            return False

    def purge_expired(self, now: Optional[datetime] = None) -> int:
        current = now or self._clock()
        expired = [digest for digest, (_, metadata) in self._records.items() if _is_expired(metadata, current)]
        for digest in expired:
            del self._records[digest]
        return len(expired)

    def clear(self) -> None:
        self._records.clear()

    def verification_report(self) -> Dict[str, Any]:
        return {
            "status": "unavailable",
            "reason": "Configured in-memory backend has no persisted integrity chain",
            "records": 0,
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
            if raw_path.exists() and metadata_path.exists():
                return locator, digest
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
            if _is_expired(metadata, current):
                raw_path = metadata_path.with_suffix(".raw")
                metadata_path.unlink(missing_ok=True)
                raw_path.unlink(missing_ok=True)
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

    def verification_report(self) -> Dict[str, Any]:
        try:
            self.verify_chain()
            chain = self._load_chain()
            return {
                "status": "verified",
                "reason": None,
                "records": len(chain["entries"]),
                "head_hash": chain["head_hash"],
                "genesis_hash": chain["genesis_hash"],
            }
        except RecordNotFoundError as exc:
            return {"status": "missing", "reason": str(exc), "records": None}
        except (CorruptRecordError, IntegrityError, ExpiredRecordError) as exc:
            return {"status": "corrupted", "reason": str(exc), "records": None}

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
        }
    return reporter()
