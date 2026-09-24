"""Checkpoint anchoring policy for operational integrity verification.

Policy under test:
- overall verification status is 'verified' only when the chain verifies AND
  a checkpoint validly anchors the current chain head;
- anchor problems are explicit: missing / stale / invalid;
- per-record ingest verification stays chain+digest based (unchanged).
"""

import json

import pytest

from src.vault.store import FileVaultBackend, InMemoryVaultBackend


@pytest.fixture
def backend(tmp_path):
    return FileVaultBackend(tmp_path / "checkpoint-vault")


def test_report_without_checkpoint_is_missing(backend):
    backend.put(b"one")
    report = backend.verification_report()
    assert report["records"] == 1
    assert report["checkpoint"]["status"] == "missing"
    assert report["status"] == "missing"
    assert "checkpoint" in report["reason"].lower()


def test_report_is_verified_when_checkpoint_anchors_head(backend):
    backend.put(b"one")
    backend.put(b"two")
    report = backend.verification_report()
    assert report["status"] == "missing"  # no checkpoint yet

    checkpoint = backend.create_checkpoint()
    report = backend.verification_report()
    assert report["status"] == "verified"
    assert report["reason"] is None
    assert report["checkpoint"]["status"] == "valid"
    assert report["checkpoint"]["sequence"] == checkpoint["sequence"] == 2
    assert report["checkpoint"]["head_hash"] == checkpoint["head_hash"]


def test_checkpoint_goes_stale_after_new_ingestion(backend):
    backend.put(b"one")
    backend.create_checkpoint()

    backend.put(b"two")  # chain head advances past the checkpoint
    report = backend.verification_report()
    assert report["records"] == 2  # chain still verifies
    assert report["checkpoint"]["status"] == "stale"
    assert report["status"] == "stale"
    assert report["checkpoint"]["sequence"] == 1

    # Re-checkpointing restores a verified report.
    backend.create_checkpoint()
    report = backend.verification_report()
    assert report["status"] == "verified"
    assert report["checkpoint"]["status"] == "valid"
    assert report["checkpoint"]["sequence"] == 2


def test_tampered_checkpoint_reports_invalid(backend):
    backend.put(b"one")
    checkpoint = backend.create_checkpoint()

    for path in backend.checkpoints.glob("checkpoint-*.json"):
        tampered = json.loads(path.read_text(encoding="utf-8"))
        tampered["head_hash"] = "0" * 64
        path.write_text(json.dumps(tampered, sort_keys=True), encoding="utf-8")

    report = backend.verification_report()
    assert report["checkpoint"]["status"] == "invalid"
    assert report["status"] == "invalid"
    assert report["records"] == 1  # the chain itself is untouched
    assert checkpoint["sequence"] == 1


def test_recomputed_but_mismatched_checkpoint_reports_invalid(backend):
    backend.put(b"one")
    backend.put(b"two")
    backend.create_checkpoint()

    # Forge a self-consistent checkpoint hash pointing at the wrong head.
    for path in backend.checkpoints.glob("checkpoint-*.json"):
        forged = json.loads(path.read_text(encoding="utf-8"))
        forged["sequence"] = 1
        forged["head_hash"] = "f" * 64
        import hashlib
        import src.vault.store as store
        payload = {
            key: forged[key]
            for key in ("version", "sequence", "head_hash", "genesis_hash")
        }
        forged["checkpoint_hash"] = hashlib.sha256(
            store._checkpoint_bytes(payload)
        ).hexdigest()
        path.write_text(json.dumps(forged, sort_keys=True), encoding="utf-8")

    report = backend.verification_report()
    assert report["checkpoint"]["status"] == "invalid"
    assert report["status"] == "invalid"


def test_chain_corruption_is_corrupted_regardless_of_checkpoint(backend):
    backend.put(b"one")
    backend.create_checkpoint()

    # Delete the raw payload WITHOUT a retention tombstone.
    (backend.records / (list(backend.records.glob("*.raw"))[0]).name).unlink()

    report = backend.verification_report()
    assert report["status"] == "corrupted"
    assert report["records"] is None
    assert report["checkpoint"]["status"] == "unavailable"


def test_unreadable_checkpoint_file_reports_invalid(backend):
    backend.put(b"one")
    backend.create_checkpoint()
    for path in backend.checkpoints.glob("checkpoint-*.json"):
        path.write_text("not json", encoding="utf-8")

    report = backend.verification_report()
    assert report["checkpoint"]["status"] == "invalid"
    assert report["status"] == "invalid"


def test_in_memory_backend_reports_checkpoint_unavailable():
    backend = InMemoryVaultBackend()
    backend.put(b"one")
    report = backend.verification_report()
    assert report["status"] == "unavailable"
    assert report["checkpoint"]["status"] == "unavailable"
    assert "sequence" in report["checkpoint"]


def test_empty_chain_with_matching_checkpoint_is_verified(backend):
    # Checkpointing an empty chain (sequence 0) is a valid anchor.
    checkpoint = backend.create_checkpoint()
    assert checkpoint["sequence"] == 0
    report = backend.verification_report()
    assert report["status"] == "verified"
    assert report["records"] == 0
    assert report["checkpoint"]["status"] == "valid"
