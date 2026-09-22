import pytest
from src.normalization.mapper import OCSFMapper
from src.registry import register_source_profile, _clear_registry, ProfileNotFoundError

@pytest.fixture(autouse=True)
def clean_registry():
    _clear_registry()
    yield

def test_map_syslog_with_complete_context():
    profile = {
        "source": "test-source-001",
        "profile_version": "1.0.0",
        "capture_year": 2024,
        "capture_timezone": "UTC",
        "vendor_name": "TestVendor",
        "product_name": "TestProduct"
    }
    register_source_profile("test-source-001", "1.0.0", profile)
    
    mapper = OCSFMapper()
    fields = {
        "syslog_month": "Feb",
        "syslog_day": "1",
        "syslog_time": "00:00:02"
    }
    
    event = mapper.map_syslog(fields, source_id="test-source-001", profile_version="1.0.0")
    
    # 2024-02-01 00:00:02 UTC is 1706745602
    assert event.get("time") == 1706745602
    assert event.get("metadata", {}).get("product", {}).get("vendor_name") == "TestVendor"
    assert event.get("metadata", {}).get("product", {}).get("name") == "TestProduct"

def test_map_syslog_missing_profile_raises_error():
    mapper = OCSFMapper()
    fields = {"syslog_month": "Feb", "syslog_day": "1", "syslog_time": "00:00:02"}
    with pytest.raises(ProfileNotFoundError):
        mapper.map_syslog(fields, source_id="unknown", profile_version="1.0.0")

def test_map_syslog_incomplete_context_omits_fields():
    profile = {
        "source": "test-source-001",
        "profile_version": "1.0.0",
        "capture_year": 2024,
        "capture_timezone": "UTC",
        "vendor_name": "TestVendor",
        "product_name": "TestProduct"
    }
    register_source_profile("test-source-001", "1.0.0", profile)

    mapper = OCSFMapper()
    event = mapper.map_syslog(
        {"syslog_month": "Feb", "syslog_day": "1"},
        source_id="test-source-001",
        profile_version="1.0.0",
    )

    assert "time" not in event
    assert event.source_profile_id == "test-source-001:1.0.0"
    assert event.source_profile_version == "1.0.0"
    assert event.injected_fields[0]["profile_id"] == "test-source-001:1.0.0"

def test_map_syslog_missing_time_components_omits_time():
    profile = {
        "source": "test-source-001",
        "profile_version": "1.0.0",
        "capture_year": 2024,
        "capture_timezone": "UTC",
        "vendor_name": "TestVendor",
        "product_name": "TestProduct"
    }
    register_source_profile("test-source-001", "1.0.0", profile)
    
    mapper = OCSFMapper()
    fields = {
        "syslog_month": "Feb",
        # missing day and time
    }
    
    event = mapper.map_syslog(fields, source_id="test-source-001", profile_version="1.0.0")
    
    assert "time" not in event
    assert event.get("metadata", {}).get("product", {}).get("vendor_name") == "TestVendor"

def test_inactive_profile_fails_closed():
    from src.registry import deactivate_source_profile, ProfileInactiveError

    profile = {
        "source": "test-source-001",
        "profile_version": "1.0.0",
        "capture_year": 2024,
        "capture_timezone": "UTC",
        "vendor_name": "TestVendor",
        "product_name": "TestProduct"
    }
    register_source_profile("test-source-001", "1.0.0", profile)
    deactivate_source_profile("test-source-001", "1.0.0")

    with pytest.raises(ProfileInactiveError):
        OCSFMapper().map_syslog(
            {"syslog_month": "Feb", "syslog_day": "1", "syslog_time": "00:00:02"},
            source_id="test-source-001",
            profile_version="1.0.0",
        )

def test_map_syslog_no_context_provided_behaves_normally():
    mapper = OCSFMapper()
    fields = {
        "syslog_month": "Feb",
        "syslog_day": "1",
        "syslog_time": "00:00:02"
    }
    event = mapper.map_syslog(fields)
    assert "time" not in event
    assert "metadata" not in event

def test_syslog_001_remains_unconfigured():
    mapper = OCSFMapper()
    fields = {
        "syslog_month": "Feb",
        "syslog_day": "1",
        "syslog_time": "00:00:02"
    }
    
    # We explicitly do not register a profile for syslog-001 in tests or prod
    with pytest.raises(ProfileNotFoundError):
        mapper.map_syslog(fields, source_id="syslog-001", profile_version="1.0.0")
