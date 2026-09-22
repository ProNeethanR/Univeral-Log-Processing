import hashlib

import pytest

from src.ingestion.ingestor import (
    MalformedInputError,
    UnsupportedFormatError,
    ingest_and_parse,
    ingest_batch,
    ingest_bytes,
    ingest_file,
)
from src.vault import store as vault
from src.vault.store import InMemoryVaultBackend


@pytest.fixture(autouse=True)
def clear_vault():
    vault.clear()
    yield
    vault.clear()


def test_ingest_bytes_preserves_raw_and_digest():
    raw = b"Sep 22 12:00:00 firewall IN=eth0"

    result = ingest_bytes(raw, source_label="fixture:syslog-001")

    assert result.raw_ref["store"] == "vault"
    assert result.raw_ref["locator"] == f"sha256:{hashlib.sha256(raw).hexdigest()}"
    assert result.raw_ref["raw_hash"] == hashlib.sha256(raw).hexdigest()
    assert result.byte_length == len(raw)
    assert vault.get(result.locator) == raw
    assert vault.verify(result.locator)


def test_ingest_file_reads_and_preserves_exact_bytes(tmp_path):
    raw = b"binary\x00log\xff"
    path = tmp_path / "event.log"
    path.write_bytes(raw)

    result = ingest_file(str(path))

    assert result.source_path == str(path.resolve())
    assert vault.get(result.locator) == raw
    assert result.sha256 == hashlib.sha256(raw).hexdigest()


def test_empty_file_is_rejected(tmp_path):
    path = tmp_path / "empty.log"
    path.write_bytes(b"")

    with pytest.raises(MalformedInputError):
        ingest_file(str(path))


def test_ingest_and_parse_propagates_raw_reference_and_context():
    raw = "Sep 22 12:00:00 firewall IN=eth0"

    result = ingest_and_parse(
        raw,
        parser=lambda text: {"raw_event": text, "source": "syslog-001"},
        source_id="syslog-001",
        profile_version="1.0.0",
        input_format="syslog",
    )

    assert result.status == "PARSED"
    assert result.parsed["raw_event"] == raw
    assert result.source_id == "syslog-001"
    assert result.profile_version == "1.0.0"
    assert vault.get(result.raw_ref["locator"]) == raw.encode("utf-8")


def test_parser_rejection_retains_raw_evidence():
    raw = b"not-a-valid-event"

    result = ingest_and_parse(
        raw,
        parser=lambda _: (_ for _ in ()).throw(ValueError("invalid event")),
        source_id="syslog-001",
        input_format="syslog",
    )

    assert result.status == "REJECTED"
    assert "Parser rejected input" in result.error
    assert vault.get(result.raw_ref["locator"]) == raw
    assert vault.verify(result.raw_ref["locator"])
    assert result.integrity_status == "verified"


def test_integrity_state_is_unavailable_for_non_chain_backend(tmp_path):
    vault.configure_backend(InMemoryVaultBackend())
    try:
        result = ingest_and_parse(
            b"raw",
            parser=lambda _: {"parsed": True},
            source_id="syslog-001",
            input_format="syslog",
        )
        assert result.integrity_status == "unavailable"
        assert result.chain_verified is None
    finally:
        vault.configure_backend(vault.FileVaultBackend(tmp_path / "restore"))


def test_parser_rejection_reports_corrupted_raw_evidence(tmp_path):
    backend = vault.FileVaultBackend(tmp_path / "vault")
    vault.configure_backend(backend)
    try:
        def corrupt_then_reject(_):
            locator = next((backend.records / "").glob("*.raw")).stem
            (backend.records / f"{locator}.raw").write_bytes(b"tampered")
            raise ValueError("invalid event")

        result = ingest_and_parse(
            b"raw",
            parser=corrupt_then_reject,
            source_id="syslog-001",
            input_format="syslog",
        )
        assert result.status == "REJECTED"
        assert result.integrity_status == "corrupted"
        assert result.chain_verified is False
    finally:
        vault.configure_backend(vault.FileVaultBackend(tmp_path / "restore"))


def test_unsupported_format_is_explicit_and_retains_raw():
    raw = b"vendor payload"

    result = ingest_and_parse(
        raw,
        parser=lambda _: pytest.fail("unsupported input must not be parsed"),
        source_id="vendor-001",
        input_format="unknown-format",
    )

    assert result.status == "REJECTED"
    assert result.error == "Unsupported input format: unknown-format"
    assert vault.get(result.raw_ref["locator"]) == raw


def test_malformed_utf8_is_rejected_after_raw_capture():
    raw = b"\xff\xfe"

    result = ingest_and_parse(
        raw,
        parser=lambda _: pytest.fail("malformed input must not be parsed"),
        source_id="syslog-001",
        input_format="syslog",
    )

    assert result.status == "REJECTED"
    assert "Malformed UTF-8 input" in result.error
    assert vault.get(result.raw_ref["locator"]) == raw


def test_empty_input_is_rejected_without_unpreserved_event():
    with pytest.raises(MalformedInputError):
        ingest_and_parse(
            b"",
            parser=lambda _: {},
            source_id="syslog-001",
            input_format="syslog",
        )


def test_batch_input_creates_independent_raw_references():
    results = ingest_batch([b"one", "two"], source_label_prefix="batch")

    assert [result.source_path for result in results] == ["batch[0]", "batch[1]"]
    assert len({result.locator for result in results}) == 2
    assert [vault.get(result.locator) for result in results] == [b"one", b"two"]


def test_legacy_ingest_bytes_signature_remains_supported():
    result = ingest_bytes(b"legacy")

    assert result.locator.startswith("sha256:")
    assert result.sha256 == result.locator.removeprefix("sha256:")
