import os
import pytest
from src.registry import (
    register_parser,
    get_parser,
    _clear_registry,
    DuplicateRegistrationError,
    ParserNotFoundError
)

@pytest.fixture(autouse=True)
def reset_registry():
    """Clear registry before each test to ensure isolation."""
    _clear_registry()

def test_successful_registration_and_retrieval(tmp_path):
    # Create a dummy parser file
    parser_file = tmp_path / "syslog_v1.yaml"
    parser_file.write_text("dummy: content")
    
    register_parser("syslog", "1.0", str(parser_file))
    
    # 1. successful registration & 2. successful retrieval
    retrieved_path = get_parser("syslog", "1.0")
    
    # 10. retrieval returns the expected parser definition
    assert retrieved_path == str(parser_file)

def test_retrieval_of_nonexistent_parser():
    # 3. retrieval of a nonexistent parser
    with pytest.raises(ParserNotFoundError, match="Parser not found for source=syslog, version=1.0"):
        get_parser("syslog", "1.0")

def test_duplicate_registration_behavior(tmp_path):
    # 4. duplicate registration behavior
    parser_file = tmp_path / "syslog_v1.yaml"
    parser_file.write_text("dummy: content")
    
    register_parser("syslog", "1.0", str(parser_file))
    
    with pytest.raises(DuplicateRegistrationError, match="Parser already registered"):
        register_parser("syslog", "1.0", str(parser_file))

def test_separate_versions_same_source(tmp_path):
    # 5. separate versions of the same source
    file_v1 = tmp_path / "syslog_v1.yaml"
    file_v1.write_text("v1")
    file_v2 = tmp_path / "syslog_v2.yaml"
    file_v2.write_text("v2")
    
    register_parser("syslog", "1.0", str(file_v1))
    register_parser("syslog", "2.0", str(file_v2))
    
    assert get_parser("syslog", "1.0") == str(file_v1)
    assert get_parser("syslog", "2.0") == str(file_v2)

def test_separate_sources_same_version(tmp_path):
    # 6. separate sources using the same version
    file_syslog = tmp_path / "syslog_v1.yaml"
    file_syslog.write_text("syslog")
    file_aws = tmp_path / "aws_v1.yaml"
    file_aws.write_text("aws")
    
    register_parser("syslog", "1.0", str(file_syslog))
    register_parser("aws", "1.0", str(file_aws))
    
    assert get_parser("syslog", "1.0") == str(file_syslog)
    assert get_parser("aws", "1.0") == str(file_aws)

def test_invalid_nonexistent_parser_path(tmp_path):
    # 7. invalid/nonexistent parser path
    non_existent_path = str(tmp_path / "does_not_exist.yaml")
    
    # Registration works without executing or eagerly validating file existence
    register_parser("syslog", "1.0", non_existent_path)
    
    # But retrieval should explicitly fail since path is nonexistent
    with pytest.raises(FileNotFoundError, match="Registered parser path does not exist"):
        get_parser("syslog", "1.0")

def test_no_silent_substitution(tmp_path):
    # 8. Registry does not silently substitute another parser/version
    file_v1 = tmp_path / "syslog_v1.yaml"
    file_v1.write_text("v1")
    register_parser("syslog", "1.0", str(file_v1))
    
    # Requesting v2 or another source should raise an explicit error, not return v1
    with pytest.raises(ParserNotFoundError):
        get_parser("syslog", "2.0")
    
    with pytest.raises(ParserNotFoundError):
        get_parser("aws", "1.0")

def test_registration_does_not_execute(tmp_path):
    # 9. registration does not execute parser operations
    # Even if the file has arbitrary content, the registry shouldn't run or parse it.
    parser_file = tmp_path / "syslog_v1.yaml"
    parser_file.write_text("{'op': 'drop'}")
    
    register_parser("syslog", "1.0", str(parser_file))
    
    # Registration is purely metadata linkage
    assert get_parser("syslog", "1.0") == str(parser_file)
