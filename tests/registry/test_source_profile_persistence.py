"""
Tests for durable Source Profile persistence and historical replay closure (Phases 1-5).
"""

import json
from pathlib import Path
import pytest

from src.registry import (
    register_source_profile,
    get_source_profile,
    get_historical_source_profile,
    activate_source_profile,
    deactivate_source_profile,
    list_source_profiles,
    configure_profile_storage,
    _clear_registry,
    DuplicateRegistrationError,
    ProfileNotFoundError,
    ProfileInactiveError,
    InvalidProfileError,
    ProfileState,
)
from src.normalization.mapper import OCSFMapper
from src.vault import store as vault
from src.ingestion.ingestor import ingest_bytes, ingest_and_parse


@pytest.fixture(autouse=True)
def clean_registry_storage(tmp_path):
    storage = tmp_path / "registry-store"
    configure_profile_storage(storage)
    _clear_registry()
    yield
    _clear_registry()
    configure_profile_storage(None)


def _sample_profile(source="test-src", version="1.0.0", year=2024, tz="UTC", vendor="VendorX", prod="ProdY"):
    return {
        "source": source,
        "profile_version": version,
        "capture_year": year,
        "capture_timezone": tz,
        "vendor_name": vendor,
        "product_name": prod,
    }


def test_registry_persistence_survives_reload(tmp_path):
    storage = tmp_path / "custom-store"
    configure_profile_storage(storage)

    prof = _sample_profile("srv-01", "1.0.0")
    register_source_profile("srv-01", "1.0.0", prof, activate=True)

    # Verify JSON file exists in storage
    files = list(storage.glob("*.json"))
    assert len(files) == 1
    assert "srv-01__1.0.0.json" in files[0].name

    # Simulate process restart by reloading storage
    configure_profile_storage(storage)

    retrieved = get_source_profile("srv-01", "1.0.0")
    assert retrieved == prof
    assert list_source_profiles() == [("srv-01", "1.0.0", ProfileState.ACTIVE)]


def test_immutability_duplicate_registration_rejected(tmp_path):
    prof1 = _sample_profile("srv-01", "1.0.0")
    register_source_profile("srv-01", "1.0.0", prof1)

    prof2 = _sample_profile("srv-01", "1.0.0", vendor="OtherVendor")
    with pytest.raises(DuplicateRegistrationError):
        register_source_profile("srv-01", "1.0.0", prof2)


def test_activation_and_deactivation_lifecycle():
    prof = _sample_profile("srv-01", "1.0.0")
    # Register inactive
    register_source_profile("srv-01", "1.0.0", prof, activate=False)

    # Ingestion lookup rejects inactive
    with pytest.raises(ProfileInactiveError):
        get_source_profile("srv-01", "1.0.0")

    # Activate
    activate_source_profile("srv-01", "1.0.0")
    assert get_source_profile("srv-01", "1.0.0") == prof

    # Deactivate
    deactivate_source_profile("srv-01", "1.0.0")
    with pytest.raises(ProfileInactiveError):
        get_source_profile("srv-01", "1.0.0")


def test_historical_retrieval_and_replay_semantics():
    prof = _sample_profile("srv-01", "1.0.0", year=2024, tz="UTC")
    register_source_profile("srv-01", "1.0.0", prof, activate=True)

    # Deactivate version 1.0.0
    deactivate_source_profile("srv-01", "1.0.0")

    # Ingestion API rejects it
    with pytest.raises(ProfileInactiveError):
        get_source_profile("srv-01", "1.0.0")

    # Historical retrieval API retrieves it successfully
    historical = get_historical_source_profile("srv-01", "1.0.0")
    assert historical == prof

    # Replay through mapper produces deterministic event
    mapper = OCSFMapper()
    fields = {"syslog_month": "Feb", "syslog_day": "1", "syslog_time": "00:00:02"}

    # Normal mapping fails closed because profile is inactive
    with pytest.raises(ProfileInactiveError):
        mapper.map_syslog(fields, source_id="srv-01", profile_version="1.0.0")

    # Replay mapping succeeds deterministically
    event = mapper.replay_syslog(fields, source_id="srv-01", profile_version="1.0.0")
    assert event.get("time") == 1706745602
    assert event.get("metadata", {}).get("product", {}).get("vendor_name") == "VendorX"


def test_version_isolation_multiple_versions():
    prof_v1 = _sample_profile("srv-01", "1.0.0", vendor="Vendor1")
    prof_v2 = _sample_profile("srv-01", "2.0.0", vendor="Vendor2")

    register_source_profile("srv-01", "1.0.0", prof_v1, activate=True)
    register_source_profile("srv-01", "2.0.0", prof_v2, activate=True)

    # Both retrievable
    assert get_source_profile("srv-01", "1.0.0")["vendor_name"] == "Vendor1"
    assert get_source_profile("srv-01", "2.0.0")["vendor_name"] == "Vendor2"

    # Deactivate v1; v2 remains active
    deactivate_source_profile("srv-01", "1.0.0")
    with pytest.raises(ProfileInactiveError):
        get_source_profile("srv-01", "1.0.0")
    assert get_source_profile("srv-01", "2.0.0")["vendor_name"] == "Vendor2"

    # Historical lookup still accesses v1
    assert get_historical_source_profile("srv-01", "1.0.0")["vendor_name"] == "Vendor1"


def test_process_reload_preserves_historical_retrieval(tmp_path):
    storage = tmp_path / "reload-store"
    configure_profile_storage(storage)

    prof = _sample_profile("srv-01", "1.0.0")
    register_source_profile("srv-01", "1.0.0", prof, activate=True)
    deactivate_source_profile("srv-01", "1.0.0")

    # Simulate process reload
    configure_profile_storage(storage)

    with pytest.raises(ProfileInactiveError):
        get_source_profile("srv-01", "1.0.0")

    assert get_historical_source_profile("srv-01", "1.0.0") == prof


def test_vault_metadata_profile_version_persistence():
    raw = b"2026-09-24 event payload"
    event = ingest_bytes(
        raw,
        source_id="srv-01",
        input_format="syslog",
        profile_version="1.0.0",
        byte_offset_start=0,
        byte_offset_end=len(raw),
        record_index=1,
    )

    meta = vault.metadata(event.locator)
    assert meta.profile_version == "1.0.0"
    assert meta.source_id == "srv-01"
    assert meta.byte_offset_start == 0
    assert meta.byte_offset_end == len(raw)
    assert meta.record_index == 1
    assert vault.get(event.locator) == raw
    assert vault.verify(event.locator) is True


def test_vault_metadata_legacy_record_without_profile_version():
    raw = b"legacy raw payload"
    event = ingest_bytes(raw, source_id="legacy-01")
    meta = vault.metadata(event.locator)
    assert meta.profile_version is None
    assert vault.get(event.locator) == raw
    assert vault.verify(event.locator) is True


def test_syslog_001_remains_strictly_unregistered():
    with pytest.raises(ProfileNotFoundError):
        get_source_profile("syslog-001", "1.0.0")
    with pytest.raises(ProfileNotFoundError):
        get_historical_source_profile("syslog-001", "1.0.0")

    registered_sources = [src for src, _, _ in list_source_profiles()]
    assert "syslog-001" not in registered_sources


def test_corrupt_profile_storage_fails_explicitly(tmp_path):
    storage = tmp_path / "corrupt-store"
    storage.mkdir(parents=True, exist_ok=True)

    bad_file = storage / "bad__1.0.0.json"
    bad_file.write_text("{invalid json", encoding="utf-8")

    with pytest.raises(InvalidProfileError, match="Corrupt profile storage"):
        configure_profile_storage(storage)


def test_schema_invalid_persisted_profile_fails_explicitly(tmp_path):
    storage = tmp_path / "invalid-schema-store"
    storage.mkdir(parents=True, exist_ok=True)

    invalid_envelope = {
        "source": "bad-src",
        "profile_version": "1.0.0",
        "state": "active",
        "profile": {
            "source": "bad-src",
            "profile_version": "1.0.0",
            # Missing capture_year, capture_timezone, vendor_name, product_name
        },
    }
    (storage / "bad-src__1.0.0.json").write_text(json.dumps(invalid_envelope), encoding="utf-8")

    with pytest.raises(InvalidProfileError, match="failed schema validation"):
        configure_profile_storage(storage)
