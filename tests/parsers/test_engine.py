"""
Focused unit tests for ParserEngine (Step H).

Verifies that ParserEngine authoritatively resolves parser definitions through
the Parser Registry using (source, version).
"""

import jsonschema
from pathlib import Path
import pytest

from src.parsers.engine import ParserEngine
from src.parsers.exceptions import UnsupportedOperationError, ParserDefinitionError
from src.registry import (
    _clear_registry,
    register_parser,
    ParserNotFoundError,
)


@pytest.fixture(autouse=True)
def reset_registry():
    """Clear registry before each test to ensure test isolation."""
    _clear_registry()


def test_registry_lookup_success():
    """1. Registry Lookup Test: Engine retrieves registered parser and parses log."""
    syslog_path = Path("parsers/syslog.yaml").resolve()
    register_parser("syslog-001", "1.0.0", str(syslog_path))

    engine = ParserEngine("syslog-001", "1.0.0")
    raw_log = "Sep 18 14:32:10 firewall-01 IN=eth0 OUT=eth1 SRC=192.168.1.50 DST=10.0.0.1 PROTO=TCP SPT=1234 DPT=80"
    output = engine.parse(raw_log)

    assert output.get("syslog_month") == "Sep"
    assert output.get("syslog_day") == "18"
    assert output.get("syslog_time") == "14:32:10"
    assert output.get("syslog_host") == "firewall-01"
    assert output.get("SRC") == "192.168.1.50"
    assert output.get("DST") == "10.0.0.1"
    assert output.get("PROTO") == "TCP"


def test_unregistered_parser_rejection():
    """2. Unregistered Parser Test: Requesting unregistered source/version raises ParserNotFoundError."""
    with pytest.raises(ParserNotFoundError) as exc_info:
        ParserEngine("unregistered_source", "1.0.0")
    assert "Parser not found" in str(exc_info.value)


def test_wrong_version_rejection():
    """3. Wrong Version Test: Requesting unregistered version raises ParserNotFoundError without fallback."""
    syslog_path = Path("parsers/syslog.yaml").resolve()
    register_parser("syslog-001", "1.0.0", str(syslog_path))

    with pytest.raises(ParserNotFoundError) as exc_info:
        ParserEngine("syslog-001", "9.9.9")
    assert "Parser not found" in str(exc_info.value)


def test_wrong_source_rejection():
    """4. Wrong Source Test: Requesting unregistered source raises ParserNotFoundError."""
    syslog_path = Path("parsers/syslog.yaml").resolve()
    register_parser("syslog-001", "1.0.0", str(syslog_path))

    with pytest.raises(ParserNotFoundError) as exc_info:
        ParserEngine("fortigate-001", "1.0.0")
    assert "Parser not found" in str(exc_info.value)


def test_missing_registered_file_rejection(tmp_path):
    """5. Missing Registered File Test: Retrieval fails if registered file path does not exist on disk."""
    non_existent_file = str(tmp_path / "missing_parser.yaml")
    register_parser("missing_source", "1.0.0", non_existent_file)

    with pytest.raises(FileNotFoundError) as exc_info:
        ParserEngine("missing_source", "1.0.0")
    assert "Registered parser path does not exist" in str(exc_info.value)


def test_malformed_parser_definition_rejection(tmp_path):
    """6. Malformed Parser Definition Test: Rejects definition missing required top-level fields."""
    malformed_file = tmp_path / "malformed.yaml"
    # Missing required 'source' and 'version'
    malformed_file.write_text("fields: {}\n", encoding="utf-8")

    register_parser("malformed_source", "1.0.0", str(malformed_file))

    with pytest.raises(jsonschema.ValidationError):
        ParserEngine("malformed_source", "1.0.0")


def test_unsupported_operation_rejection(tmp_path):
    """7. Unsupported Operation Test: Rejects parser definition with invalid/unsupported operation."""
    unsupported_file = tmp_path / "unsupported_op.yaml"
    content = (
        "source: test_source\n"
        "version: 1.0.0\n"
        "fields:\n"
        "  bad_field:\n"
        "    op: arbitrary_code_eval\n"
    )
    unsupported_file.write_text(content, encoding="utf-8")

    register_parser("unsupported_source", "1.0.0", str(unsupported_file))

    with pytest.raises(jsonschema.ValidationError):
        ParserEngine("unsupported_source", "1.0.0")


def test_registry_is_authoritative(tmp_path):
    """8. Registry Authoritative Test: Unregistered file on disk is NOT selected automatically."""
    unregistered_file = tmp_path / "valid_parser.yaml"
    content = (
        "source: unreg\n"
        "version: 1.0.0\n"
        "fields:\n"
        "  test:\n"
        "    op: extract\n"
        "    source: raw_event\n"
    )
    unregistered_file.write_text(content, encoding="utf-8")

    # File exists on disk, but is NOT registered in Registry
    with pytest.raises(ParserNotFoundError):
        ParserEngine("unreg", "1.0.0")


def test_deterministic_parsing_output():
    """9. Deterministic Parsing Test: Identical input + parser produces identical output across calls."""
    syslog_path = Path("parsers/syslog.yaml").resolve()
    register_parser("syslog-001", "1.0.0", str(syslog_path))

    engine = ParserEngine("syslog-001", "1.0.0")
    raw_log = "Sep 18 14:32:10 firewall-01 IN=eth0 OUT=eth1 SRC=10.0.0.5 DST=10.0.0.1 PROTO=UDP"

    output1 = engine.parse(raw_log)
    output2 = engine.parse(raw_log)

    assert output1 == output2
