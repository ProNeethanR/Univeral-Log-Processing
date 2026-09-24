"""Demo publication path must vault the exact original fixture bytes.

Regression coverage for the historical bypass in event_service.load_demo_data:
the file was decoded, stripped, split, stripped per-line, and re-encoded
before vault capture, destroying CRLF terminators and byte offsets.

The shared ``demo_data`` fixture reloads demo data deterministically into an
isolated vault backend and restores in-memory state afterwards, so results do
not depend on import or collection order.
"""

import hashlib
from pathlib import Path

from src.ingestion.ingestor import split_raw_records
from src.vault import store as vault


FIXTURE_PATH = Path("fixtures/raw/syslog/syslog-001.log")


def test_demo_events_vault_exact_original_fixture_bytes(demo_data):
    original = FIXTURE_PATH.read_bytes()
    fixture_records = split_raw_records(original)
    # Non-blank fixture lines (fixture has no blank lines).
    expected_slices = [r[3] for r in fixture_records if r[3].strip(b"\r\n")]

    assert len(demo_data) == len(expected_slices)

    reassembled = bytearray()
    for envelope, expected in zip(demo_data, expected_slices):
        locator = envelope.raw_ref.locator
        stored = vault.get(locator)

        # Byte-for-byte equality against the original input slice.
        assert stored == expected, (
            f"{envelope.event_id}: stored bytes differ from original input slice"
        )

        metadata = vault.metadata(locator)
        assert metadata.byte_offset_start is not None
        assert metadata.byte_offset_end is not None
        assert original[metadata.byte_offset_start:metadata.byte_offset_end] == stored

        # CRLF terminators must survive (the old path stripped them).
        assert stored.endswith(b"\r\n")

        # Digest matches the exact stored bytes.
        assert envelope.raw_ref.raw_hash == hashlib.sha256(stored).hexdigest()

        reassembled.extend(stored)

    # Every captured slice, concatenated, reproduces the original file exactly.
    assert bytes(reassembled) == original


def test_demo_offsets_are_ordered_and_unique(demo_data):
    spans = []
    for envelope in demo_data:
        metadata = vault.metadata(envelope.raw_ref.locator)
        spans.append(
            (metadata.record_index, metadata.byte_offset_start, metadata.byte_offset_end)
        )

    assert [s[0] for s in spans] == sorted(s[0] for s in spans)
    assert len({s[0] for s in spans}) == len(spans), "record_index must be unique per event"
    for (_, _, prev_end), (_, start, _) in zip(spans, spans[1:]):
        assert start >= prev_end, "byte offsets must be non-decreasing and non-overlapping"


def test_demo_raw_hash_matches_vault_digest(demo_data):
    for envelope in demo_data:
        stored = vault.get(envelope.raw_ref.locator)
        assert envelope.raw_ref.raw_hash == hashlib.sha256(stored).hexdigest()
        assert envelope.raw_ref.locator == f"sha256:{envelope.raw_ref.raw_hash}"
        assert envelope.raw_ref.store == vault.STORE_TYPE
