"""Fixture integrity: committed raw files must match fixtures/SHA256SUMS.

FI-1 reconciliation froze the on-disk (committed) fixture corpus as
authoritative on 2026-09-23. This test guards against accidental edits to the
raw fixtures and keeps the recorded digests honest.
"""

import hashlib
import json
import os

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SUMS_PATH = os.path.join(REPO_ROOT, "fixtures", "SHA256SUMS")
MANIFEST_PATH = os.path.join(REPO_ROOT, "fixtures", "manifest.json")


def _sha256_hex(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


@pytest.fixture(scope="module")
def sums_entries():
    entries = []
    with open(SUMS_PATH, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            assert len(parts) == 3, f"malformed SHA256SUMS line: {line!r}"
            digest, size, relpath = parts
            full = os.path.join(REPO_ROOT, *relpath.split("/"))
            assert os.path.isfile(full), f"path in SHA256SUMS missing: {relpath}"
            entries.append((digest, int(size), relpath, full))
    return entries


def test_every_summed_file_exists_and_matches_disk(sums_entries):
    assert len(sums_entries) == 4, "SHA256SUMS must cover all 4 raw fixtures"
    for digest, size, relpath, full in sums_entries:
        assert os.path.getsize(full) == size, f"size mismatch: {relpath}"
        assert _sha256_hex(full) == digest, f"hash mismatch: {relpath}"


def test_manifest_matches_sums(sums_entries):
    manifest = json.load(open(MANIFEST_PATH, encoding="utf-8"))
    expected = {
        (os.path.normpath(spec["raw_file"]).replace("\\", "/"), spec["sha256"], spec["bytes"])
        for spec in manifest["fixtures"]
        if spec.get("raw_file")
    }
    recorded = {(relpath, digest, size) for digest, size, relpath, _ in sums_entries}
    assert recorded == expected, (
        "fixtures/manifest.json must match fixtures/SHA256SUMS "
        "for every entry"
    )