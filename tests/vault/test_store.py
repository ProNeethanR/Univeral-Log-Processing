from datetime import datetime, timezone

import pytest

from src.vault.store import (
    CorruptRecordError,
    ExpiredRecordError,
    FileVaultBackend,
    RecordNotFoundError,
)


@pytest.fixture
def vault(tmp_path):
    return FileVaultBackend(tmp_path / "vault")


def test_filesystem_backend_persists_across_recreation(vault, tmp_path):
    raw = b"exact raw bytes\x00\xff"
    locator, digest = vault.put(
        raw,
        source_id="syslog-001",
        input_format="syslog",
        capture_timestamp=datetime(2026, 9, 22, tzinfo=timezone.utc),
    )

    recreated = FileVaultBackend(tmp_path / "vault")

    assert recreated.get(locator) == raw
    assert recreated.verify(locator)
    assert recreated.metadata(locator).raw_hash == digest


def test_metadata_persists_with_stable_locator(vault):
    locator, digest = vault.put(
        b"event",
        source_id="source-1",
        input_format="cef",
        capture_timestamp=datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
        retention_seconds=3600,
    )

    metadata = vault.metadata(locator)
    assert metadata.raw_hash == digest
    assert metadata.source_id == "source-1"
    assert metadata.capture_timestamp == "2026-01-02T03:04:05+00:00"
    assert metadata.input_format == "cef"
    assert metadata.size == 5
    assert metadata.locator == locator
    assert metadata.retention_expires_at == "2026-01-02T04:04:05+00:00"


def test_missing_record_fails_explicitly(vault):
    with pytest.raises(RecordNotFoundError):
        vault.get("sha256:" + "0" * 64)


def test_corrupted_record_fails_digest_verification(vault):
    locator, _ = vault.put(b"original")
    raw_path = vault.records / (locator.removeprefix("sha256:") + ".raw")
    raw_path.write_bytes(b"corrupted")

    assert not vault.verify(locator)
    with pytest.raises(CorruptRecordError):
        vault.get(locator)


def test_expired_record_is_rejected_and_purged_deterministically(vault):
    capture = datetime(2026, 1, 1, tzinfo=timezone.utc)
    controlled = FileVaultBackend(
        vault.root,
        clock=lambda: datetime(2026, 1, 1, 0, 1, tzinfo=timezone.utc),
    )
    locator, _ = controlled.put(b"expires", capture_timestamp=capture, retention_seconds=60)
    now = datetime(2026, 1, 1, 0, 1, 0, tzinfo=timezone.utc)

    with pytest.raises(ExpiredRecordError):
        controlled.get(locator)
    assert controlled.purge_expired(now=now) == 1
    with pytest.raises(RecordNotFoundError):
        controlled.get(locator)


def test_unexpired_record_survives_purge(vault):
    capture = datetime(2026, 1, 1, tzinfo=timezone.utc)
    controlled = FileVaultBackend(
        vault.root,
        clock=lambda: datetime(2026, 1, 1, 0, 0, 59, tzinfo=timezone.utc),
    )
    locator, _ = controlled.put(b"retained", capture_timestamp=capture, retention_seconds=60)

    assert controlled.purge_expired(now=datetime(2026, 1, 1, 0, 0, 59, tzinfo=timezone.utc)) == 0
    assert controlled.get(locator) == b"retained"
