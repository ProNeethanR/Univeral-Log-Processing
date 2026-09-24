"""Retention purge vs append-only integrity chain.

Design under test: ordinary purge removes only the raw payload and retains a
metadata tombstone (purged_at). Historical chain verification must keep
passing across expiration, purge, and subsequent ingestion.
"""

import json
from datetime import datetime, timezone

import pytest

from src.ingestion.ingestor import verify_raw_reference
from src.vault import store as vault
from src.vault.store import (
    FileVaultBackend,
    IntegrityError,
    RecordNotFoundError,
    ExpiredRecordError,
)


@pytest.fixture
def backend(tmp_path):
    return FileVaultBackend(tmp_path / "retention-vault")


@pytest.fixture
def isolated_module_backend(tmp_path):
    previous = vault._BACKEND
    vault.configure_backend(FileVaultBackend(tmp_path / "module-vault"))
    yield vault._BACKEND
    vault.configure_backend(previous)


def _expired_vault(tmp_path):
    return FileVaultBackend(
        tmp_path / "retention-vault",
        clock=lambda: datetime(2026, 1, 1, 0, 1, tzinfo=timezone.utc),
    )


def test_expiration_raises_before_purge(backend):
    capture = datetime(2026, 1, 1, tzinfo=timezone.utc)
    locator, _ = backend.put(b"expires", capture_timestamp=capture, retention_seconds=60)

    # Simulate time passing past retention using a controlled clock.
    late = FileVaultBackend(backend.root, clock=lambda: datetime(2026, 1, 1, 0, 2, tzinfo=timezone.utc))
    with pytest.raises(ExpiredRecordError):
        late.get(locator)
    # Expiration alone must not break chain verification.
    assert late.verify_chain()


def test_purge_keeps_historical_chain_verification_passing(tmp_path):
    vault_dir = tmp_path / "retention-vault"
    capture = datetime(2026, 1, 1, tzinfo=timezone.utc)
    early = FileVaultBackend(vault_dir, clock=lambda: datetime(2026, 1, 1, tzinfo=timezone.utc))

    expiring, _ = early.put(
        b"expiring evidence",
        capture_timestamp=capture,
        retention_seconds=60,
        byte_offset_start=0,
        byte_offset_end=18,
        record_index=1,
    )
    keeper, _ = early.put(b"kept evidence", capture_timestamp=capture, retention_seconds=None)
    assert early.verify_chain()

    # Ordinary purge after expiration.
    late = FileVaultBackend(vault_dir, clock=lambda: datetime(2026, 1, 2, tzinfo=timezone.utc))
    assert late.purge_expired(now=datetime(2026, 1, 2, tzinfo=timezone.utc)) == 1

    # Payload removed, tombstone metadata retained.
    with pytest.raises(RecordNotFoundError):
        late.get(expiring)
    tombstone = late.metadata(expiring)
    assert tombstone.purged_at is not None
    assert tombstone.raw_hash
    assert tombstone.sequence == 1

    # Historical chain verification still passes after ordinary purge.
    assert late.verify_chain()
    assert late.verify(keeper)

    # Purge is idempotent: already-tombstoned records are not re-counted.
    assert late.purge_expired(now=datetime(2026, 1, 3, tzinfo=timezone.utc)) == 0
    assert late.verify_chain()


def test_new_ingestion_after_purge_keeps_chain_verifiable(tmp_path):
    vault_dir = tmp_path / "retention-vault"
    capture = datetime(2026, 1, 1, tzinfo=timezone.utc)
    early = FileVaultBackend(vault_dir, clock=lambda: datetime(2026, 1, 1, tzinfo=timezone.utc))
    early.put(b"one", capture_timestamp=capture, retention_seconds=60)
    early.put(b"two", capture_timestamp=capture, retention_seconds=None)

    late = FileVaultBackend(vault_dir, clock=lambda: datetime(2026, 1, 2, tzinfo=timezone.utc))
    assert late.purge_expired(now=datetime(2026, 1, 2, tzinfo=timezone.utc)) == 1
    assert late.verify_chain()

    late.put(b"three", capture_timestamp=capture, retention_seconds=None)
    assert late.verify_chain()
    chain = json.loads(late.chain_path.read_text(encoding="utf-8"))
    assert chain["next_sequence"] == 4  # two original entries + one new; purge adds none


def test_reingest_after_purge_restores_payload_without_duplicate_chain_entry(tmp_path):
    vault_dir = tmp_path / "retention-vault"
    capture = datetime(2026, 1, 1, tzinfo=timezone.utc)
    early = FileVaultBackend(vault_dir, clock=lambda: datetime(2026, 1, 1, tzinfo=timezone.utc))
    locator, _ = early.put(
        b"resurrect me",
        capture_timestamp=capture,
        retention_seconds=60,
        record_index=1,
    )

    late = FileVaultBackend(vault_dir, clock=lambda: datetime(2026, 1, 2, tzinfo=timezone.utc))
    assert late.purge_expired(now=datetime(2026, 1, 2, tzinfo=timezone.utc)) == 1
    assert late.verify_chain()
    sequence_before = late.metadata(locator).sequence

    # Same content re-ingested: payload restored, chain entry NOT duplicated.
    same_locator, _ = late.put(b"resurrect me", record_index=1)
    assert same_locator == locator

    raw_path = late.records / (locator.removeprefix("sha256:") + ".raw")
    assert raw_path.read_bytes() == b"resurrect me", "payload must be restored on re-ingest"

    metadata = late.metadata(locator)
    assert metadata.sequence == sequence_before
    assert metadata.purged_at is None
    # Original capture/retention are canonical hash fields and stay honest:
    # the record is still past its retention deadline for access purposes.
    with pytest.raises(ExpiredRecordError):
        late.get(locator)

    assert late.verify_chain()
    chain = json.loads(late.chain_path.read_text(encoding="utf-8"))
    assert len(chain["entries"]) == 1


def test_tombstoned_metadata_tampering_still_breaks_chain(tmp_path):
    vault_dir = tmp_path / "retention-vault"
    capture = datetime(2026, 1, 1, tzinfo=timezone.utc)
    early = FileVaultBackend(vault_dir, clock=lambda: datetime(2026, 1, 1, tzinfo=timezone.utc))
    locator, _ = early.put(b"evidence", capture_timestamp=capture, retention_seconds=60)

    late = FileVaultBackend(vault_dir, clock=lambda: datetime(2026, 1, 2, tzinfo=timezone.utc))
    assert late.purge_expired(now=datetime(2026, 1, 2, tzinfo=timezone.utc)) == 1
    assert late.verify_chain()

    metadata_path = late.records / (locator.removeprefix("sha256:") + ".json")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["source_id"] = "attacker"
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    with pytest.raises(IntegrityError):
        late.verify_chain()


def test_undeleted_raw_payload_without_tombstone_still_breaks_chain(tmp_path):
    backend = FileVaultBackend(tmp_path / "retention-vault")
    locator, _ = backend.put(b"deleted outside policy")

    # Simulate raw payload vanishing WITHOUT an authorized purge tombstone.
    (backend.records / (locator.removeprefix("sha256:") + ".raw")).unlink()

    with pytest.raises(IntegrityError):
        backend.verify_chain()


def test_verify_raw_reference_reports_purged_evidence_explicitly(tmp_path, isolated_module_backend):
    backend = isolated_module_backend
    capture = datetime(2026, 1, 1, tzinfo=timezone.utc)
    early = FileVaultBackend(backend.root, clock=lambda: datetime(2026, 1, 1, tzinfo=timezone.utc))
    locator, _ = early.put(b"expiring", capture_timestamp=capture, retention_seconds=60)

    late = FileVaultBackend(backend.root, clock=lambda: datetime(2026, 1, 2, tzinfo=timezone.utc))
    vault.configure_backend(late)
    assert late.purge_expired(now=datetime(2026, 1, 2, tzinfo=timezone.utc)) == 1

    status = verify_raw_reference(locator)
    assert status["status"] == "missing"
    assert "purged" in status["reason"].lower()
    assert status["chain_verified"] is True


def test_purged_record_is_not_trusted_raw_evidence(tmp_path, isolated_module_backend):
    backend = isolated_module_backend
    capture = datetime(2026, 1, 1, tzinfo=timezone.utc)
    early = FileVaultBackend(backend.root, clock=lambda: datetime(2026, 1, 1, tzinfo=timezone.utc))
    locator, _ = early.put(b"expiring", capture_timestamp=capture, retention_seconds=60)

    late = FileVaultBackend(backend.root, clock=lambda: datetime(2026, 1, 2, tzinfo=timezone.utc))
    vault.configure_backend(late)
    late.purge_expired(now=datetime(2026, 1, 2, tzinfo=timezone.utc))

    assert verify_raw_reference(locator)["status"] != "verified"
    with pytest.raises(RecordNotFoundError):
        late.get(locator)
