"""Byte-for-byte losslessness tests for every ingestion path.

Proves that stored raw evidence equals the exact original input byte
sequence and that line/record offsets are preserved separately as vault
metadata (never merged into, or used to reconstruct, the payload).
"""

import hashlib
from pathlib import Path

import pytest

from src.ingestion.ingestor import (
    ingest_batch,
    ingest_bytes,
    ingest_file,
    split_raw_records,
    strip_record_terminator,
)
from src.vault import store as vault


@pytest.fixture(autouse=True)
def isolated_vault(tmp_path):
    previous = vault._BACKEND
    vault.configure_backend(vault.FileVaultBackend(tmp_path / "lossless-vault"))
    yield
    vault.configure_backend(previous)


FIXTURE_PATH = Path("fixtures/raw/syslog/syslog-001.log")


# ---------------------------------------------------------------------------
# split_raw_records: offsets and exact slices
# ---------------------------------------------------------------------------

def test_split_raw_records_slices_are_exact_original_bytes():
    data = b"alpha\r\nbeta\r\n gamma \nlast-without-newline"
    records = split_raw_records(data)

    for index, start, end, slice_bytes in records:
        assert slice_bytes == data[start:end], (
            f"Record {index}: slice is not the exact original byte range"
        )
    assert b"".join(r[3] for r in records) == data, (
        "Concatenated records must reproduce the original input byte-for-byte"
    )


def test_split_raw_records_offsets_are_contiguous_and_ordered():
    data = b"one\ntwo\r\nthree"
    records = split_raw_records(data)

    assert [r[0] for r in records] == [1, 2, 3]
    expected_start = 0
    for _, start, end, _ in records:
        assert start == expected_start
        assert end > start
        expected_start = end
    assert expected_start == len(data)


def test_split_raw_records_keeps_blank_lines_as_lossless_slices():
    data = b"a\n\nb\n"
    records = split_raw_records(data)
    assert [r[3] for r in records] == [b"a\n", b"\n", b"b\n"]
    assert b"".join(r[3] for r in records) == data


def test_strip_record_terminator_only_removes_line_ending():
    assert strip_record_terminator(b"content\r\n") == b"content"
    assert strip_record_terminator(b"content\n") == b"content"
    assert strip_record_terminator(b"content") == b"content"
    assert strip_record_terminator(b"trail\r") == b"trail"


# ---------------------------------------------------------------------------
# ingest_bytes / ingest_file: stored payload byte-for-byte
# ---------------------------------------------------------------------------

def test_ingest_bytes_stores_exact_bytes_with_offset_metadata():
    raw = b"Sep  1 00:00:02 host msg\r\n"

    result = ingest_bytes(
        raw,
        source_label="inline",
        byte_offset_start=10,
        byte_offset_end=10 + len(raw),
        record_index=2,
    )

    assert vault.get(result.locator) == raw
    metadata = vault.metadata(result.locator)
    assert metadata.byte_offset_start == 10
    assert metadata.byte_offset_end == 10 + len(raw)
    assert metadata.byte_offset_end - metadata.byte_offset_start == len(raw)
    assert metadata.record_index == 2
    assert metadata.raw_hash == hashlib.sha256(raw).hexdigest()


def test_offset_metadata_is_integrity_protected(tmp_path):
    backend = vault.FileVaultBackend(tmp_path / "tamper")
    raw = b"offset-protected\r\n"
    locator, _ = backend.put(
        raw,
        byte_offset_start=0,
        byte_offset_end=len(raw),
        record_index=1,
    )
    assert backend.verify_chain()

    metadata_path = backend.records / (locator.removeprefix("sha256:") + ".json")
    import json
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["byte_offset_start"] = 999
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    from src.vault.store import IntegrityError
    with pytest.raises(IntegrityError):
        backend.verify_chain()


def test_ingest_file_preserves_exact_bytes_including_line_endings(tmp_path):
    raw = b"line one\r\nline two\r\nline three\n"
    path = tmp_path / "crlf.log"
    path.write_bytes(raw)

    result = ingest_file(str(path))

    assert vault.get(result.locator) == raw
    assert result.sha256 == hashlib.sha256(raw).hexdigest()


def test_batch_records_round_trip_each_exact_slice():
    slices = [b"first\r\n", b"second\r\n", b"third"]
    original = b"".join(slices)

    records = split_raw_records(original)
    captured = ingest_batch([r[3] for r in records], source_label_prefix="batch")

    for captured_event, (index, start, end, slice_bytes) in zip(captured, records):
        assert vault.get(captured_event.locator) == slice_bytes
        assert vault.get(captured_event.locator) == original[start:end]


# ---------------------------------------------------------------------------
# Full fixture: demo-equivalent byte-level capture
# ---------------------------------------------------------------------------

def test_fixture_records_reproduce_original_file_byte_for_byte():
    original = FIXTURE_PATH.read_bytes()
    records = split_raw_records(original)

    for index, start, end, slice_bytes in records:
        event = ingest_bytes(
            slice_bytes,
            source_label=str(FIXTURE_PATH),
            source_id="syslog-001",
            input_format="syslog",
            byte_offset_start=start,
            byte_offset_end=end,
            record_index=index,
        )
        stored = vault.get(event.locator)
        assert stored == slice_bytes, f"Record {index} not byte-for-byte equal"
        assert stored == original[start:end]

    assert b"".join(r[3] for r in records) == original
    # CRLF terminators must survive capture (the historical bypass stripped them).
    assert all(r[3].endswith(b"\r\n") for r in records)
