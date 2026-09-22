import pytest
from src.registry import (
    register_source_profile,
    get_source_profile,
    _clear_registry,
    DuplicateRegistrationError,
    ProfileNotFoundError,
    InvalidProfileError,
    ProfileInactiveError,
    AmbiguousProfileError,
    ProfileState,
    activate_source_profile,
    deactivate_source_profile,
    get_source_profile_state,
    list_source_profiles,
)

@pytest.fixture(autouse=True)
def clean_registry():
    _clear_registry()
    yield

def test_register_and_get_valid_profile():
    profile = {
        "source": "test-source-001",
        "profile_version": "1.0.0",
        "capture_year": 2026,
        "capture_timezone": "UTC",
        "vendor_name": "TestVendor",
        "product_name": "TestProduct"
    }
    register_source_profile("test-source-001", "1.0.0", profile)
    
    retrieved = get_source_profile("test-source-001", "1.0.0")
    assert retrieved == profile

def test_register_invalid_profile_raises_error():
    profile = {
        "source": "test-source-001",
        "profile_version": "1.0.0",
        # Missing required fields like capture_year, etc.
    }
    with pytest.raises(InvalidProfileError):
        register_source_profile("test-source-001", "1.0.0", profile)

def test_duplicate_profile_registration_raises_error():
    profile = {
        "source": "test-source-001",
        "profile_version": "1.0.0",
        "capture_year": 2026,
        "capture_timezone": "UTC",
        "vendor_name": "TestVendor",
        "product_name": "TestProduct"
    }
    register_source_profile("test-source-001", "1.0.0", profile)
    
    with pytest.raises(DuplicateRegistrationError):
        register_source_profile("test-source-001", "1.0.0", profile)

def test_get_nonexistent_profile_raises_error():
    with pytest.raises(ProfileNotFoundError):
        get_source_profile("test-source-001", "1.0.0")

def _profile(source="test-source-001", version="1.0.0"):
    return {
        "source": source,
        "profile_version": version,
        "capture_year": 2026,
        "capture_timezone": "UTC",
        "vendor_name": "TestVendor",
        "product_name": "TestProduct",
    }

def test_profile_can_be_registered_inactive_and_activated():
    register_source_profile("test-source-001", "1.0.0", _profile(), activate=False)
    assert get_source_profile_state("test-source-001", "1.0.0") == ProfileState.REGISTERED
    with pytest.raises(ProfileInactiveError):
        get_source_profile("test-source-001", "1.0.0")

    activate_source_profile("test-source-001", "1.0.0")
    assert get_source_profile("test-source-001", "1.0.0")["profile_version"] == "1.0.0"
    assert get_source_profile_state("test-source-001", "1.0.0") == ProfileState.ACTIVE

def test_profile_deactivation_fails_closed():
    register_source_profile("test-source-001", "1.0.0", _profile())
    deactivate_source_profile("test-source-001", "1.0.0")
    assert get_source_profile_state("test-source-001", "1.0.0") == ProfileState.INACTIVE
    with pytest.raises(ProfileInactiveError):
        get_source_profile("test-source-001", "1.0.0")

def test_versions_are_independent_and_listed_deterministically():
    register_source_profile("z-source", "2.0.0", _profile("z-source", "2.0.0"))
    register_source_profile("a-source", "1.0.0", _profile("a-source", "1.0.0"))
    register_source_profile("a-source", "2.0.0", _profile("a-source", "2.0.0"), activate=False)
    assert list_source_profiles() == [
        ("a-source", "1.0.0", ProfileState.ACTIVE),
        ("a-source", "2.0.0", ProfileState.REGISTERED),
        ("z-source", "2.0.0", ProfileState.ACTIVE),
    ]

def test_profile_identity_must_match_registry_key():
    with pytest.raises(InvalidProfileError):
        register_source_profile("test-source-001", "1.0.0", _profile("other-source", "1.0.0"))

def test_blank_lookup_is_rejected_as_ambiguous():
    with pytest.raises(AmbiguousProfileError):
        get_source_profile("", "1.0.0")
