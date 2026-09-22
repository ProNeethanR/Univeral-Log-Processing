import hashlib
import json
from datetime import datetime, timezone

import pytest

from src.ingestion.ingestor import ingest_and_parse
from src.vault.store import (
    FileVaultBackend,
    GENESIS_HASH,
    IntegrityError,
    InvalidCheckpointError,
    RawRecordMetadata,
    calculate_record_hash,
    canonical_record_bytes,
)


def test_canonical_hash_is_deterministic():
    metadata = RawRecordMetadata(
        raw_hash="a" * 64,
        source_id="source-1",
        capture_timestamp="2026-01-01T00:00:00+00:00",
        input_format="syslog",
        size=3,
        locator="sha256:" + "a" * 64,
        sequence=1,
        previous_record_hash=GENESIS_HASH,
    )

    first = canonical_record_bytes(metadata)
    second = canonical_record_bytes(metadata)

    assert first == second
    assert calculate_record_hash(metadata) == hashlib.sha256(first).hexdigest()


def test_genesis_and_append_order(tmp_path):
    vault = FileVaultBackend(tmp_path / "vault")
    assert vault.verify_chain()

    first, _ = vault.put(b"one")
    second, _ = vault.put(b"two")
    first_metadata = vault.metadata(first)
    second_metadata = vault.metadata(second)

    assert first_metadata.sequence == 1
    assert first_metadata.previous_record_hash == GENESIS_HASH
    assert second_metadata.sequence == 2
    assert second_metadata.previous_record_hash == first_metadata.record_hash
    assert vault.verify_chain()


def test_checkpoint_creation_verification_and_recreation(tmp_path):
    root = tmp_path / "vault"
    vault = FileVaultBackend(root)
    vault.put(b"checkpointed")
    checkpoint = vault.create_checkpoint()

    recreated = FileVaultBackend(root)

    assert recreated.verify_checkpoint(checkpoint)
    assert recreated.verify_chain()


def test_invalid_checkpoint_is_rejected(tmp_path):
    vault = FileVaultBackend(tmp_path / "vault")
    vault.put(b"checkpointed")
    checkpoint = vault.create_checkpoint()
    checkpoint["head_hash"] = "0" * 64

    with pytest.raises(InvalidCheckpointError):
        vault.verify_checkpoint(checkpoint)


def test_payload_modification_breaks_full_chain(tmp_path):
    vault = FileVaultBackend(tmp_path / "vault")
    locator, _ = vault.put(b"original")
    raw_path = vault.records / (locator.removeprefix("sha256:") + ".raw")
    raw_path.write_bytes(b"modified")

    with pytest.raises(IntegrityError):
        vault.verify_chain()


def test_metadata_modification_breaks_full_chain(tmp_path):
    vault = FileVaultBackend(tmp_path / "vault")
    locator, _ = vault.put(b"original", source_id="source-1")
    metadata_path = vault.records / (locator.removeprefix("sha256:") + ".json")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["source_id"] = "attacker"
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    with pytest.raises(IntegrityError):
        vault.verify_chain()


def test_deleted_record_breaks_full_chain(tmp_path):
    vault = FileVaultBackend(tmp_path / "vault")
    locator, _ = vault.put(b"deleted")
    (vault.records / (locator.removeprefix("sha256:") + ".raw")).unlink()

    with pytest.raises(IntegrityError):
        vault.verify_chain()


def test_reordered_chain_entries_break_full_chain(tmp_path):
    vault = FileVaultBackend(tmp_path / "vault")
    vault.put(b"one")
    vault.put(b"two")
    chain = json.loads(vault.chain_path.read_text(encoding="utf-8"))
    chain["entries"].reverse()
    vault.chain_path.write_text(json.dumps(chain), encoding="utf-8")

    with pytest.raises(IntegrityError):
        vault.verify_chain()


def test_broken_previous_link_breaks_full_chain(tmp_path):
    vault = FileVaultBackend(tmp_path / "vault")
    first, _ = vault.put(b"one")
    second, _ = vault.put(b"two")
    metadata_path = vault.records / (second.removeprefix("sha256:") + ".json")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["previous_record_hash"] = "0" * 64
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    with pytest.raises(IntegrityError):
        vault.verify_chain()


def test_ingestion_rejection_keeps_chain_verifiable(tmp_path, monkeypatch):
    backend = FileVaultBackend(tmp_path / "vault")
    from src.vault import store
    store.configure_backend(backend)
    try:
        result = ingest_and_parse(
            b"rejected",
            parser=lambda _: (_ for _ in ()).throw(ValueError("bad")),
            source_id="source-1",
            input_format="syslog",
        )
        assert result.status == "REJECTED"
        assert backend.get(result.raw_ref["locator"]) == b"rejected"
        assert backend.verify_chain()
    finally:
        store.configure_backend(FileVaultBackend(tmp_path / "restore"))
