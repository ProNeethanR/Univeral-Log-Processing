"""
tests/integration/test_syslog_pipeline.py

Two test layers covering the Syslog-001 fixture:

  1. test_syslog_mapper_golden       — Exercises map_syslog() only (pre-enrichment).
     Compares against fixtures/expected/syslog/syslog-001.json which was
     authored as a snapshot of the pre-enrichment mapper output.  This test
     is intentionally scoped to that layer; it does NOT include enrichment.

  2. test_syslog_canonical_pipeline  — Exercises the full canonical sequence:
     parse -> map_syslog -> enrich_ocsf_headers -> validate.
     Uses semantic assertions only; no new canonical fixture is required.
     The expected OCSF validation outcome for this fixture is FAIL because
     RFC3164 syslog provides no year/timezone (time absent) and no vendor
     identity (metadata absent).  This is the correct, honest state.
"""
import json
import hashlib
from pathlib import Path

import pytest

from src.parsers.engine import ParserEngine
from src.normalization.mapper import OCSFMapper, MappingResult
from src.normalization.ocsf_validator import OCSFValidationResult
from src.registry import register_parser, _clear_registry

# Policy fields that enrich_ocsf_headers() adds — absent from legacy fixture.
_POLICY_FIELDS = {"class_uid", "category_uid", "activity_id", "type_uid", "severity_id"}
_POLICY_VALUES = {
    "class_uid": 4001,
    "category_uid": 4,
    "activity_id": 6,
    "type_uid": 400106,
    "severity_id": 1,
}


# ---------------------------------------------------------------------------
# Layer 1 — Mapper golden test (map_syslog only, pre-enrichment)
# ---------------------------------------------------------------------------

def test_syslog_mapper_golden():
    """
    Verifies raw field projection by map_syslog() against the frozen
    fixtures/expected/syslog/syslog-001.json baseline.

    Scope: map_syslog() only.  enrich_ocsf_headers() is intentionally NOT
    called here, because the legacy fixture was captured before enrichment
    was introduced.  Any diff is flagged as a mapper-layer regression.

    Policy fields (class_uid, category_uid, activity_id, type_uid,
    severity_id) are expected to be absent from the legacy fixture and from
    map_syslog() output alike; they are exclusively added by enrichment.
    """
    _clear_registry()

    raw_path = Path("fixtures/raw/syslog/syslog-001.log").resolve()
    parser_path = Path("parsers/syslog.yaml").resolve()
    expected_path = Path("fixtures/expected/syslog/syslog-001.json").resolve()

    with open(raw_path, "rb") as f:
        raw_bytes = f.read()

    # Verify raw fixture integrity
    sha256 = hashlib.sha256(raw_bytes).hexdigest()
    assert sha256 == "a3783b7c387f7248d8c90c315b9b06a73bf4f7e6d0a6631b0a2449afd5706552", (
        "SHA256 of raw fixture mismatch — fixture may have been modified."
    )

    raw_lines = raw_bytes.decode("utf-8").strip().split("\n")

    register_parser("syslog-001", "1.0.0", str(parser_path))
    engine = ParserEngine("syslog-001", "1.0.0")
    mapper = OCSFMapper()

    with open(expected_path, "r", encoding="utf-8") as f:
        expected = json.load(f)

    discrepancies = []

    for i, line in enumerate(raw_lines):
        line = line.strip()
        if not line:
            continue

        parsed_fields = engine.parse(line)
        # map_syslog only — pre-enrichment, matching the legacy fixture
        ocsf = mapper.map_syslog(parsed_fields)

        exp_event = expected[i]["ocsf_event"]

        # Sort tracing for deterministic comparison
        if "unmapped" in ocsf and "tracing" in ocsf["unmapped"]:
            ocsf["unmapped"]["tracing"] = sorted(
                ocsf["unmapped"]["tracing"], key=lambda x: x["source_field"]
            )
        if "unmapped" in exp_event and "tracing" in exp_event["unmapped"]:
            exp_event["unmapped"]["tracing"] = sorted(
                exp_event["unmapped"]["tracing"], key=lambda x: x["source_field"]
            )

        # Policy fields are not present in either the legacy fixture or map_syslog() output.
        # Strip defensively to prevent spurious failures if fixture is regenerated later.
        ocsf_clean = {k: v for k, v in ocsf.items() if k not in _POLICY_FIELDS}
        exp_clean = {k: v for k, v in exp_event.items() if k not in _POLICY_FIELDS}

        if ocsf_clean != exp_clean:
            discrepancies.append(
                f"Mapper-layer mismatch at event {i + 1}\n"
                f"Expected: {exp_clean}\n"
                f"Actual:   {ocsf_clean}\n"
            )

    if discrepancies:
        report_path = Path("tests/integration/discrepancies_report.txt").resolve()
        with open(report_path, "w", encoding="utf-8") as f:
            for d in discrepancies:
                f.write(d + "\n")
        pytest.fail(
            f"Found {len(discrepancies)} mapper-layer discrepancies. "
            f"See discrepancies_report.txt"
        )


# ---------------------------------------------------------------------------
# Layer 2 — Canonical pipeline test (full sequence, semantic assertions)
# ---------------------------------------------------------------------------

def test_syslog_canonical_pipeline():
    """
    Exercises the full canonical normalization pipeline for all 25 Syslog-001
    events:

        parse -> map_syslog -> enrich_ocsf_headers -> validate

    No new canonical fixture file is required.  All assertions are semantic:
    they verify correctness of field presence, policy values, provenance
    lineage, and the expected validation outcome.

    The expected validation result for this fixture is FAIL because:
    - 'time' is absent (RFC3164 carries no year or timezone)
    - 'metadata' is absent (no legitimate vendor identity source exists)

    This is the correct honest state, documented in test_pipeline_integration.py
    Correction 5.  It is NOT a test failure.
    """
    _clear_registry()

    raw_path = Path("fixtures/raw/syslog/syslog-001.log").resolve()
    parser_path = Path("parsers/syslog.yaml").resolve()

    with open(raw_path, "rb") as f:
        raw_bytes = f.read()

    raw_lines = [ln for ln in raw_bytes.decode("utf-8").strip().split("\n") if ln.strip()]
    assert len(raw_lines) == 25, f"Expected 25 lines, got {len(raw_lines)}"

    register_parser("syslog-001", "1.0.0", str(parser_path))
    engine = ParserEngine("syslog-001", "1.0.0")
    mapper = OCSFMapper()

    for i, line in enumerate(raw_lines, start=1):
        parsed_fields = engine.parse(line)
        assert parsed_fields, f"Event {i}: parser returned empty fields"

        # Full canonical sequence
        ocsf, val_result = mapper.map_and_validate_syslog(parsed_fields)

        # --- Policy field value assertions ---
        for field, expected_val in _POLICY_VALUES.items():
            assert field in ocsf, (
                f"Event {i}: policy field '{field}' missing from enriched output"
            )
            assert ocsf[field] == expected_val, (
                f"Event {i}: policy field '{field}' expected {expected_val}, "
                f"got {ocsf[field]}"
            )

        # --- Evidence-gap assertions: fabricated fields must be absent ---
        assert "time" not in ocsf, (
            f"Event {i}: 'time' must not be fabricated from yearless RFC3164 timestamp"
        )
        assert "metadata" not in ocsf, (
            f"Event {i}: 'metadata' must not be fabricated without a legitimate vendor source"
        )

        # --- Mapped fields must survive enrichment ---
        assert "src_endpoint" in ocsf or "unmapped" in ocsf, (
            f"Event {i}: expected src_endpoint or unmapped block after enrichment"
        )

        # --- Provenance lineage: policy_fields captured on MappingResult ---
        assert isinstance(ocsf, MappingResult), (
            f"Event {i}: map_and_validate_syslog must return a MappingResult"
        )
        policy_field_names = {pf["field"] for pf in ocsf.policy_fields}
        for field in _POLICY_VALUES:
            assert field in policy_field_names, (
                f"Event {i}: policy field '{field}' missing from MappingResult.policy_fields"
            )
        for pf in ocsf.policy_fields:
            assert pf.get("source") == "normalization_policy", (
                f"Event {i}: policy_field '{pf['field']}' source is "
                f"'{pf.get('source')}'; expected 'normalization_policy'"
            )

        # --- Validation result type and schema version ---
        assert isinstance(val_result, OCSFValidationResult), (
            f"Event {i}: validator must return OCSFValidationResult"
        )
        assert val_result.ocsf_version == "1.3.0", (
            f"Event {i}: validator must operate against frozen OCSF 1.3.0"
        )

        # --- Honest validation outcome: FAIL (missing time and metadata) ---
        assert val_result.is_valid is False, (
            f"Event {i}: validation must FAIL "
            f"(missing time/metadata is the correct honest state)"
        )
        missing = {e.path for e in val_result.errors if e.error_type == "missing_required"}
        assert "time" in missing, (
            f"Event {i}: expected missing_required error for 'time'; "
            f"got errors: {[e.to_dict() for e in val_result.errors]}"
        )
        assert "metadata" in missing, (
            f"Event {i}: expected missing_required error for 'metadata'; "
            f"got errors: {[e.to_dict() for e in val_result.errors]}"
        )
