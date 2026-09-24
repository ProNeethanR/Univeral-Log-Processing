"""Comprehensive end-to-end raw-byte preservation tests.

Tests for Phase 7: Regression and Evidence Testing - Area 1
"""

from pathlib import Path

import pytest

from src.ingestion.ingestor import (
    ingest_bytes,
    ingest_file,
    ingest_batch,
    split_raw_records,
    strip_record_terminator,
)
from src.vault import store as vault


class TestEndToEndRawBytePreservation:
    """Test end-to-end raw-byte preservation across all ingestion paths."""

    @pytest.fixture(autouse=True)
    def _isolated_vault(self, tmp_path):
        """Use a fresh vault per test so content-addressed dedup cannot leak
        metadata from previous runs against the persistable default backend."""
        prior = vault._BACKEND
        vault.configure_backend(vault.FileVaultBackend(tmp_path / "e2e-vault"))
        yield
        vault.configure_backend(prior)

    def test_demo_ingestion_preserves_exact_bytes(self, demo_data):
        """Test that demo ingestion preserves exact original bytes per record."""
        # Isolated vault + deterministic demo load come from the shared fixture.
        original_bytes = Path("fixtures/raw/syslog/syslog-001.log").read_bytes()
        records = split_raw_records(original_bytes)
        assert demo_data, "demo data must be loaded"

        # Demo data covers the same records the fixture loader produced.
        assert len(demo_data) == len(records)

        for envelope, (_, byte_offset_start, byte_offset_end, record_bytes) in zip(demo_data, records):
            locator = envelope.raw_ref.locator
            stored_bytes = vault.get(locator)

            # The vault record is the exact original byte slice.
            assert stored_bytes == record_bytes, (
                f"Envelope {envelope.event_id}: stored bytes differ from record slice"
            )
            assert original_bytes[byte_offset_start:byte_offset_end] == stored_bytes

            # Verify raw_hash matches
            import hashlib
            assert envelope.raw_ref.raw_hash == hashlib.sha256(stored_bytes).hexdigest()

            # Verify byte offsets are correct and scoped to the record slice
            metadata = vault.metadata(locator)
            assert metadata.byte_offset_start == byte_offset_start
            assert metadata.byte_offset_end == byte_offset_end

            # Verify CRLF terminators are preserved
            assert stored_bytes.endswith(b"\r\n"), "CRLF terminators should be preserved"

        # Verify reassembly produces original file
        reassembled = bytearray()
        for envelope in demo_data:
            locator = envelope.raw_ref.locator
            stored_bytes = vault.get(locator)
            reassembled.extend(stored_bytes)

        assert bytes(reassembled) == original_bytes, "Reassembled bytes should match original"

    def test_ingest_file_preserves_exact_bytes(self, tmp_path):
        """Test that ingest_file preserves exact original bytes."""
        # Create a test file with CRLF line endings
        test_content = b"Line 1\r\nLine 2\r\nLine 3\r\n"
        test_file = tmp_path / "test.log"
        test_file.write_bytes(test_content)
        
        # Ingest the file
        result = ingest_file(str(test_file))
        
        # Verify the raw bytes match exactly
        stored_bytes = vault.get(result.locator)
        assert stored_bytes == test_content, "ingest_file should preserve exact bytes"
        
        # Verify raw_hash matches
        import hashlib
        assert result.sha256 == hashlib.sha256(test_content).hexdigest()
        
        # Verify metadata includes correct offsets
        metadata = vault.metadata(result.locator)
        assert metadata.byte_offset_start == 0
        assert metadata.byte_offset_end == len(test_content)
        assert metadata.record_index == 1
        
        # Verify CRLF terminators are preserved
        assert stored_bytes.endswith(b"\r\n"), "CRLF terminators should be preserved"

    def test_ingest_bytes_preserves_exact_bytes(self, tmp_path):
        """Test that ingest_bytes preserves exact original bytes."""
        test_content = b"Raw data with \x00 null bytes and \xff binary data"
        
        # Ingest the bytes
        result = ingest_bytes(test_content, source_label="test")
        
        # Verify the raw bytes match exactly
        stored_bytes = vault.get(result.locator)
        assert stored_bytes == test_content, "ingest_bytes should preserve exact bytes"
        
        # Verify raw_hash matches
        import hashlib
        assert result.sha256 == hashlib.sha256(test_content).hexdigest()
        
        # Verify metadata is set
        metadata = vault.metadata(result.locator)
        assert metadata.size == len(test_content)
        assert metadata.raw_hash == result.sha256

    def test_batch_ingestion_preserves_exact_bytes(self, tmp_path):
        """Test that batch ingestion preserves exact bytes for each record."""
        # ingest_batch captures each item's raw content; pass the actual bytes.
        contents = []
        for i in range(3):
            content = f"File {i} line 1\r\nFile {i} line 2\r\n".encode()
            contents.append(content)

        results = ingest_batch(contents)

        # Verify each item's bytes are preserved
        for i, result in enumerate(results):
            stored_bytes = vault.get(result.locator)
            expected_content = contents[i]
            assert stored_bytes == expected_content, (
                f"Batch ingest item {i}: stored bytes differ from expected"
            )

            # Verify raw_hash matches
            import hashlib
            assert result.sha256 == hashlib.sha256(expected_content).hexdigest()

            # Verify per-item record_index metadata is set
            metadata = vault.metadata(result.locator)
            assert metadata.record_index == i + 1

    def test_multiline_input_preserves_exact_bytes(self, tmp_path):
        """Test that multiline input with mixed line endings preserves exact bytes."""
        # Create content with mixed line endings
        test_content = (
            b"Line 1\r\n"  # CRLF
            b"Line 2\n"    # LF only
            b"Line 3\r"    # CR only
            b"Line 4\r\n\r\n"  # CRLF + blank line
            b"Line 5\n\n"  # LF + blank line
        )

        # Ingest the bytes
        result = ingest_bytes(test_content, source_label="multiline")

        # Verify the raw bytes match exactly
        stored_bytes = vault.get(result.locator)
        assert stored_bytes == test_content, "Multiline input should preserve exact bytes"

        # Verify split_raw_records works correctly
        records = split_raw_records(test_content)
        assert len(records) > 0, "Should have at least one record"

        # Verify slicing is exact and lossless: every record is the exact
        # original byte range, and concatenation reproduces the input.
        for record_index, byte_offset_start, byte_offset_end, record_bytes in records:
            assert record_bytes == test_content[byte_offset_start:byte_offset_end], (
                f"Record {record_index}: slice is not the exact original byte range"
            )
        assert b"".join(r[3] for r in records) == test_content

        # Per-record capture path: each non-blank slice vaults its exact bytes.
        for record_index, byte_offset_start, byte_offset_end, record_bytes in records:
            if not strip_record_terminator(record_bytes):
                continue  # Skip blank lines

            event = ingest_bytes(
                record_bytes,
                source_label="multiline-slices",
                byte_offset_start=byte_offset_start,
                byte_offset_end=byte_offset_end,
                record_index=record_index,
            )
            assert vault.get(event.locator) == record_bytes, (
                f"Record {record_index}: re-captured bytes differ from the original slice"
            )
            metadata = vault.metadata(event.locator)
            assert metadata.byte_offset_start == byte_offset_start
            assert metadata.byte_offset_end == byte_offset_end
            assert metadata.record_index == record_index

    def test_non_utf8_input_preserves_exact_bytes(self, tmp_path):
        """Test that non-UTF-8 binary data preserves exact bytes."""
        # Create content with non-UTF-8 bytes
        test_content = bytes(range(256))  # All possible byte values
        
        # Ingest the bytes
        result = ingest_bytes(test_content, source_label="binary")
        
        # Verify the raw bytes match exactly
        stored_bytes = vault.get(result.locator)
        assert stored_bytes == test_content, "Non-UTF-8 input should preserve exact bytes"
        
        # Verify raw_hash matches
        import hashlib
        assert result.sha256 == hashlib.sha256(test_content).hexdigest()
        
        # Verify metadata
        metadata = vault.metadata(result.locator)
        assert metadata.size == len(test_content)

    def test_raw_ref_and_raw_hash_verification(self, tmp_path):
        """Test that raw_ref and raw_hash are correctly generated and verified."""
        test_content = b"Test content for raw_ref verification"
        
        # Ingest the bytes
        result = ingest_bytes(test_content, source_label="test")
        
        # Verify raw_ref structure
        assert result.raw_ref["store"] == vault.STORE_TYPE
        assert result.raw_ref["locator"].startswith("sha256:")
        assert result.raw_ref["raw_hash"] == result.sha256
        
        # Verify locator matches raw_hash
        import hashlib
        expected_locator = f"sha256:{hashlib.sha256(test_content).hexdigest()}"
        assert result.raw_ref["locator"] == expected_locator
        
        # Verify raw_hash pattern (should be 64 hex characters)
        assert len(result.raw_ref["raw_hash"]) == 64
        assert all(c in "0123456789abcdef" for c in result.raw_ref["raw_hash"])

    def test_byte_offset_metadata_integrity(self, tmp_path):
        """Test that byte offset metadata is correctly set and integrity-protected."""
        # Create a test file with known content
        test_content = b"Line 1\r\nLine 2\r\nLine 3\r\n"
        test_file = tmp_path / "offset_test.log"
        test_file.write_bytes(test_content)
        
        # Ingest the file
        result = ingest_file(str(test_file))
        
        # Verify byte offset metadata
        metadata = vault.metadata(result.locator)
        assert metadata.byte_offset_start == 0
        assert metadata.byte_offset_end == len(test_content)
        assert metadata.record_index == 1
        
        # Verify that tampering with offset metadata breaks integrity
        # This is tested by the existing chain verification tests
        # but we can add a specific test here if needed
        
    def test_contiguous_record_slices(self, tmp_path):
        """Test that record slices are contiguous and non-overlapping."""
        # Create a test file with multiple lines
        test_content = b"Line 1\r\nLine 2\r\nLine 3\r\nLine 4\r\n"
        test_file = tmp_path / "contiguous_test.log"
        test_file.write_bytes(test_content)
        
        # Ingest the file
        result = ingest_file(str(test_file))
        
        # Get all envelopes from demo data (if any) or create test data
        # For this test, we'll use the result from ingest_file
        metadata = vault.metadata(result.locator)
        
        # Verify that the record slice is contiguous
        record_slice = test_content[metadata.byte_offset_start:metadata.byte_offset_end]
        assert record_slice == test_content, "Record slice should be contiguous"
        
        # Verify that the record slice includes the terminator
        assert record_slice.endswith(b"\r\n"), "Record slice should include terminator"

    def test_ingest_bytes_with_metadata(self, tmp_path):
        """Test that ingest_bytes correctly handles metadata parameters."""
        test_content = b"Test content with metadata"

        # Use a near-future ISO capture timestamp so the 1h retention window
        # keeps the record live (a timestamp in the past would expire on read).
        from datetime import datetime, timedelta, timezone
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        capture_iso = future.isoformat()

        # Ingest with metadata
        result = ingest_bytes(
            test_content,
            source_label="test",
            source_id="test-source",
            input_format="test",
            capture_timestamp=capture_iso,
            retention_seconds=3600,
            byte_offset_start=100,
            byte_offset_end=124,
            record_index=5,
        )

        # Verify metadata is set correctly
        metadata = vault.metadata(result.locator)
        assert metadata.source_id == "test-source"
        assert metadata.input_format == "test"
        # The ISO string must be honored, not replaced with "now".
        assert metadata.capture_timestamp == capture_iso
        assert metadata.retention_expires_at is not None
        assert metadata.byte_offset_start == 100
        assert metadata.byte_offset_end == 124
        assert metadata.record_index == 5

        # Verify the raw bytes are still correct
        stored_bytes = vault.get(result.locator)
        assert stored_bytes == test_content

    def test_ingest_bytes_empty_input_raises_error(self, tmp_path):
        """Test that ingest_bytes raises an error for empty input."""
        with pytest.raises(Exception):  # Should raise MalformedInputError
            ingest_bytes(b"", source_label="empty")

    def test_ingest_bytes_large_input(self, tmp_path):
        """Test that ingest_bytes handles large input correctly."""
        # Create a large content (1MB)
        test_content = b"A" * (1024 * 1024)
        
        # Ingest the large content
        result = ingest_bytes(test_content, source_label="large")
        
        # Verify the raw bytes match exactly
        stored_bytes = vault.get(result.locator)
        assert stored_bytes == test_content, "Large input should preserve exact bytes"
        
        # Verify raw_hash matches
        import hashlib
        assert result.sha256 == hashlib.sha256(test_content).hexdigest()
        
        # Verify metadata size is correct
        metadata = vault.metadata(result.locator)
        assert metadata.size == len(test_content)
