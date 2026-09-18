"""
Focused unit tests for OCSF 1.3.0 Runtime Validator (Step F/G Hardened).

Verifies offline OCSF event validation against local schema artifact
(schema/ocsf/ocsf_schema.json).
"""

import copy
import hashlib
import json
import tempfile
from pathlib import Path
import pytest

from src.normalization.ocsf_validator import (
    DEFAULT_SCHEMA_PATH,
    EXPECTED_OCSF_SHA256,
    EXPECTED_OCSF_VERSION,
    OCSFValidator,
    validate_ocsf_event,
)
from src.parsers.exceptions import OCSFValidationError


@pytest.fixture
def valid_network_activity_event():
    """
    Constructs a minimal valid OCSF 1.3.0 Network Activity event (Class UID 4001, Category UID 4).
    
    This event conforms strictly to the OCSF 1.3.0 schema requirement specification:
    - class_uid: 4001 (Network Activity)
    - category_uid: 4 (Network Activity)
    - activity_id: 1 (Open)
    - type_uid: 400101 (Network Activity: Open)
    - time: 1726700000 (Epoch timestamp in seconds)
    - severity_id: 1 (Informational)
    - metadata: version 1.3.0, product vendor_name "ULPF"
    - dst_endpoint: responder endpoint object with valid IP
    """
    return {
        "class_uid": 4001,
        "category_uid": 4,
        "activity_id": 1,
        "type_uid": 400101,
        "time": 1726700000,
        "severity_id": 1,
        "metadata": {
            "version": "1.3.0",
            "product": {
                "vendor_name": "ULPF"
            }
        },
        "dst_endpoint": {
            "ip": "192.168.1.100"
        }
    }


def test_valid_ocsf_event(valid_network_activity_event):
    """1/A. Valid Event Test: Event passes schema validation cleanly."""
    validator = OCSFValidator()
    result = validator.validate(valid_network_activity_event)
    
    assert result.is_valid is True, f"Validation failed with errors: {[e.to_dict() for e in result.errors]}"
    assert len(result.errors) == 0
    assert result.class_name == "network_activity"
    assert result.class_uid == 4001
    assert result.ocsf_version == EXPECTED_OCSF_VERSION


def test_missing_required_field(valid_network_activity_event):
    """2/B. Missing Required Field Test: Removing required 'activity_id' produces INVALID status."""
    invalid_event = copy.deepcopy(valid_network_activity_event)
    del invalid_event["activity_id"]

    validator = OCSFValidator()
    result = validator.validate(invalid_event)

    assert result.is_valid is False
    assert len(result.errors) > 0
    err_paths = [e.path for e in result.errors]
    assert "activity_id" in err_paths
    assert any(e.error_type == "missing_required" for e in result.errors)


def test_wrong_type(valid_network_activity_event):
    """3/C. Wrong Type Test: Passing a string for integer 'severity_id' produces INVALID status."""
    invalid_event = copy.deepcopy(valid_network_activity_event)
    invalid_event["severity_id"] = "high"  # Should be int

    validator = OCSFValidator()
    result = validator.validate(invalid_event)

    assert result.is_valid is False
    assert len(result.errors) > 0
    err = next(e for e in result.errors if e.path == "severity_id")
    assert err.error_type == "wrong_type"
    assert "expected integer" in err.message.lower()


def test_invalid_enum(valid_network_activity_event):
    """4/D. Invalid Enum/Value Test: Passing an unmapped integer for 'severity_id' produces INVALID status."""
    invalid_event = copy.deepcopy(valid_network_activity_event)
    invalid_event["severity_id"] = 999  # Valid severities are 0, 1, 2, 3, 4, 5, 6, 99

    validator = OCSFValidator()
    result = validator.validate(invalid_event)

    assert result.is_valid is False
    assert len(result.errors) > 0
    err = next(e for e in result.errors if e.path == "severity_id")
    assert err.error_type == "invalid_enum"
    assert "not a valid enum value" in err.message


def test_nested_validation(valid_network_activity_event):
    """5/E. Nested Object Validation: Passing an invalid type in nested 'dst_endpoint.ip' fails."""
    invalid_event = copy.deepcopy(valid_network_activity_event)
    invalid_event["dst_endpoint"]["ip"] = 12345  # Should be string

    validator = OCSFValidator()
    result = validator.validate(invalid_event)

    assert result.is_valid is False
    assert len(result.errors) > 0
    err = next(e for e in result.errors if e.path == "dst_endpoint.ip")
    assert err.error_type == "wrong_type"
    assert "expected string" in err.message.lower()


def test_unknown_property_behavior(valid_network_activity_event):
    """6/F. Unknown Property Behavior: OCSF schema permits additional/unmapped properties in events."""
    event_with_custom = copy.deepcopy(valid_network_activity_event)
    event_with_custom["custom_unmapped_field"] = "custom_value"

    validator = OCSFValidator()
    result = validator.validate(event_with_custom)

    assert result.is_valid is True, f"Validation failed for unmapped property: {[e.to_dict() for e in result.errors]}"


def test_schema_driven_mutation(valid_network_activity_event):
    """7/G. Schema-Driven Mutation Test: Verifies validation behavior changes dynamically when schema is modified."""
    with open(DEFAULT_SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_data = json.load(f)

    # Create temporary modified schema copy with a new required attribute
    modified_schema = copy.deepcopy(schema_data)
    modified_schema["classes"]["network_activity"]["attributes"]["test_required_attribute"] = {
        "type": "string_t",
        "requirement": "required",
        "caption": "Test Required Attribute"
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as tmp:
        json.dump(modified_schema, tmp)
        tmp_path = tmp.name

    try:
        temp_bytes = Path(tmp_path).read_bytes()
        temp_hash = hashlib.sha256(temp_bytes).hexdigest()

        validator_mod = OCSFValidator(schema_path=tmp_path, expected_sha256=temp_hash)
        result = validator_mod.validate(valid_network_activity_event)

        assert result.is_valid is False
        assert len(result.errors) > 0
        err = next(e for e in result.errors if e.path == "test_required_attribute")
        assert err.error_type == "missing_required"
        assert "Missing required field 'test_required_attribute'" in err.message
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_schema_integrity_verification():
    """8. Schema Integrity Test: Rejects modified schema file whose SHA-256 hash does not match expected."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
        tmp.write('{"version": "1.3.0", "classes": {}}')
        tmp_path = tmp.name

    try:
        with pytest.raises(ValueError) as exc_info:
            OCSFValidator(schema_path=tmp_path, expected_sha256=EXPECTED_OCSF_SHA256)
        assert "integrity verification failed" in str(exc_info.value).lower()
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_offline_behavior(valid_network_activity_event, monkeypatch):
    """9. Offline Behavior Test: Validator runs entirely offline without socket/network access."""
    def block_network(*args, **kwargs):
        raise RuntimeError("Network socket call attempted during offline validation!")

    monkeypatch.setattr("socket.socket", block_network)
    
    validator = OCSFValidator()
    result = validator.validate(valid_network_activity_event)
    assert result.is_valid is True


def test_input_immutability(valid_network_activity_event):
    """10. Input Immutability Test: Candidate event dictionary remains unmodified by validation."""
    original_event = copy.deepcopy(valid_network_activity_event)
    event_copy = copy.deepcopy(valid_network_activity_event)

    validator = OCSFValidator()
    validator.validate(event_copy)

    assert event_copy == original_event, "Validator must not mutate input event dictionary!"


def test_convenience_function_and_raise_on_error(valid_network_activity_event):
    """11. Test convenience validate_ocsf_event and raise_on_error functionality."""
    # Valid case
    res = validate_ocsf_event(valid_network_activity_event, raise_on_error=True)
    assert res.is_valid is True

    # Invalid case with exception
    invalid_event = copy.deepcopy(valid_network_activity_event)
    invalid_event["class_uid"] = "invalid_class_uid_type"

    with pytest.raises(OCSFValidationError) as exc_info:
        validate_ocsf_event(invalid_event, raise_on_error=True)
    assert "validation failed" in str(exc_info.value).lower()
