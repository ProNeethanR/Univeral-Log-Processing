"""
tests/normalization/test_enrichment_provenance.py

Unit tests for enrichment (enrich_ocsf_headers) and provenance lineage.

These tests are deliberately independent of any fixture file.  They verify:

  1. Enrichment adds the five policy fields to any MappingResult.
  2. Enrichment records policy_fields provenance entries correctly.
  3. Enrichment is idempotent (calling twice produces no duplicate entries).
  4. Caller-supplied fields take precedence and are NOT overwritten.
  5. policy_fields source and rationale strings are correct.
  6. injected_fields list is preserved through enrichment.
"""
import pytest
from src.normalization.mapper import OCSFMapper, MappingResult

_POLICY_VALUES = {
    "class_uid": 4001,
    "category_uid": 4,
    "activity_id": 6,
    "type_uid": 400106,
    "severity_id": 1,
}
_POLICY_RATIONALES = {
    "class_uid": "Schema-verified classification constant",
    "category_uid": "Schema-verified classification constant",
    "activity_id": "Schema-verified classification constant",
    "type_uid": "Schema-verified classification constant",
    "severity_id": "ULPF policy default",
}


def _bare_mapping_result(**extra):
    """Return a minimal MappingResult with optional extra keys."""
    mr = MappingResult(**extra)
    return mr


# ---------------------------------------------------------------------------
# 1. Enrichment adds all five policy fields
# ---------------------------------------------------------------------------

def test_enrich_adds_all_policy_fields():
    """enrich_ocsf_headers must add class_uid, category_uid, activity_id,
    type_uid, and severity_id to a bare MappingResult."""
    mapper = OCSFMapper()
    raw = _bare_mapping_result()
    enriched = mapper.enrich_ocsf_headers({}, raw)

    for field, expected_val in _POLICY_VALUES.items():
        assert field in enriched, f"Policy field '{field}' missing after enrichment"
        assert enriched[field] == expected_val, (
            f"Policy field '{field}': expected {expected_val}, got {enriched[field]}"
        )


# ---------------------------------------------------------------------------
# 2. Enrichment records policy_fields provenance entries
# ---------------------------------------------------------------------------

def test_enrich_records_policy_fields_provenance():
    """Every policy field added by enrichment must be recorded in
    MappingResult.policy_fields with correct source and rationale."""
    mapper = OCSFMapper()
    raw = _bare_mapping_result()
    enriched = mapper.enrich_ocsf_headers({}, raw)

    assert isinstance(enriched, MappingResult), (
        "enrich_ocsf_headers must return a MappingResult"
    )
    pf_by_field = {pf["field"]: pf for pf in enriched.policy_fields}

    for field in _POLICY_VALUES:
        assert field in pf_by_field, (
            f"Policy field '{field}' not recorded in MappingResult.policy_fields"
        )
        pf = pf_by_field[field]
        assert pf["source"] == "normalization_policy", (
            f"policy_fields['{field}'].source = '{pf['source']}'; "
            f"expected 'normalization_policy'"
        )
        assert pf["value"] == _POLICY_VALUES[field], (
            f"policy_fields['{field}'].value = {pf['value']}; "
            f"expected {_POLICY_VALUES[field]}"
        )
        assert pf.get("rationale") == _POLICY_RATIONALES[field], (
            f"policy_fields['{field}'].rationale = '{pf.get('rationale')}'; "
            f"expected '{_POLICY_RATIONALES[field]}'"
        )


# ---------------------------------------------------------------------------
# 3. Enrichment is idempotent — calling twice yields no duplicate entries
# ---------------------------------------------------------------------------

def test_enrich_is_idempotent():
    """Calling enrich_ocsf_headers twice must not produce duplicate
    policy_fields entries and must not change field values."""
    mapper = OCSFMapper()
    raw = _bare_mapping_result()
    once = mapper.enrich_ocsf_headers({}, raw)
    twice = mapper.enrich_ocsf_headers({}, once)

    # Field values unchanged
    for field, expected_val in _POLICY_VALUES.items():
        assert twice[field] == expected_val

    # No duplicate provenance entries
    seen = {}
    for pf in twice.policy_fields:
        assert pf["field"] not in seen, (
            f"Duplicate policy_fields entry for '{pf['field']}' after double enrichment"
        )
        seen[pf["field"]] = pf


# ---------------------------------------------------------------------------
# 4. Caller-supplied fields are not overwritten
# ---------------------------------------------------------------------------

def test_enrich_does_not_overwrite_caller_supplied_policy_fields():
    """If the caller already placed a policy field in the MappingResult,
    enrichment must not replace it."""
    mapper = OCSFMapper()
    # Caller explicitly sets severity_id = 3 (Medium) before enrichment
    raw = _bare_mapping_result(severity_id=3)
    enriched = mapper.enrich_ocsf_headers({"severity_id": 3}, raw)

    assert enriched["severity_id"] == 3, (
        "Caller-supplied severity_id=3 must not be overwritten by enrichment policy default"
    )
    # The policy provenance entry for severity_id must NOT be added because
    # the field was already present
    pf_fields = {pf["field"] for pf in enriched.policy_fields}
    assert "severity_id" not in pf_fields, (
        "severity_id must not appear in policy_fields when it was caller-supplied"
    )


# ---------------------------------------------------------------------------
# 5. injected_fields list is preserved through enrichment
# ---------------------------------------------------------------------------

def test_enrich_preserves_injected_fields():
    """injected_fields added before enrichment must survive the enrichment call."""
    mapper = OCSFMapper()
    raw = _bare_mapping_result()
    raw.injected_fields = [
        {"field": "metadata", "source": "source_profile", "profile_id": "test-001"}
    ]
    enriched = mapper.enrich_ocsf_headers({}, raw)

    assert len(enriched.injected_fields) == 1, (
        "injected_fields must be preserved by enrich_ocsf_headers"
    )
    assert enriched.injected_fields[0]["field"] == "metadata"
    assert enriched.injected_fields[0]["source"] == "source_profile"


# ---------------------------------------------------------------------------
# 6. policy_fields entries have required keys
# ---------------------------------------------------------------------------

def test_policy_fields_entries_have_required_keys():
    """Every entry in policy_fields must have 'field', 'source', and 'value'."""
    mapper = OCSFMapper()
    raw = _bare_mapping_result()
    enriched = mapper.enrich_ocsf_headers({}, raw)

    for pf in enriched.policy_fields:
        assert "field" in pf, f"policy_fields entry missing 'field': {pf}"
        assert "source" in pf, f"policy_fields entry missing 'source': {pf}"
        assert "value" in pf, f"policy_fields entry missing 'value': {pf}"
