"""Contract alignment: envelopes must validate against contracts/event_contract.schema.json."""

import json

import jsonschema

from src.api.models import (
    CANONICAL_ENVELOPE_KEYS,
    EvidenceClassification,
    IntegrityDetail,
    IntegrityStatus,
    ULPFEventEnvelope,
    build_event_envelope,
    is_canonical_envelope,
)
from src.api.services import event_service

EVENT_SCHEMA = json.load(
    open("contracts/event_contract.schema.json", encoding="utf-8")
)

RAW_REF = {
    "store": "vault",
    "locator": "sha256:" + "ab" * 32,
    "raw_hash": "ab" * 32,
}


def _envelope_kwargs(**overrides):
    kwargs = {
        "event_id": "evt-1",
        "source_id": "syslog-001",
        "ingest_timestamp": "2026-09-23T00:00:00+00:00",
        "raw_ref": dict(RAW_REF),
        "evidence_classification": EvidenceClassification.VALIDATED,
        "parser_id": "syslog-001",
        "parser_version": "1.0.0",
        "schema_version": "1.1",
    }
    kwargs.update(overrides)
    return kwargs


def test_schema_required_fields_are_enforced():
    required = set(EVENT_SCHEMA["required"])
    assert required == CANONICAL_ENVELOPE_KEYS


def test_built_envelope_validates_against_contract():
    envelope = build_event_envelope(**_envelope_kwargs())
    jsonschema.validate(instance=envelope.model_dump(mode="json"), schema=EVENT_SCHEMA)
    assert envelope.schema_version == "1.1"
    # Default integrity is 'unavailable', so the gate must be False.
    assert envelope.trusted is False


def test_trust_gate_defaults_to_untrusted_without_verified_integrity():
    envelope = build_event_envelope(**_envelope_kwargs())
    assert envelope.trusted is False


def test_trust_gate_requires_all_three_conditions():
    verified = IntegrityDetail(status=IntegrityStatus.VERIFIED, chain_verified=True)
    broken_chain = IntegrityDetail(status=IntegrityStatus.VERIFIED, chain_verified=False)

    trusted = build_event_envelope(**_envelope_kwargs(integrity=verified))
    assert trusted.trusted is True
    jsonschema.validate(instance=trusted.model_dump(mode="json"), schema=EVENT_SCHEMA)

    # Chain reported broken at capture time -> not trusted.
    assert build_event_envelope(
        **_envelope_kwargs(integrity=broken_chain)
    ).trusted is False

    # Evidence not fully validated -> not trusted.
    parsed_only = build_event_envelope(
        **_envelope_kwargs(
            integrity=verified,
            evidence_classification=EvidenceClassification.PARSED,
        )
    )
    assert parsed_only.trusted is False

    # Integrity not verified -> not trusted.
    missing = build_event_envelope(
        **_envelope_kwargs(
            integrity=IntegrityDetail(status=IntegrityStatus.MISSING),
        )
    )
    assert missing.trusted is False

    # Verified integrity with chain_verified=None (never evaluated) still
    # passes the gate: the gate only fails on an explicit False.
    unknown_chain = build_event_envelope(
        **_envelope_kwargs(
            integrity=IntegrityDetail(
                status=IntegrityStatus.VERIFIED, chain_verified=None
            )
        )
    )
    assert unknown_chain.trusted is True


def test_null_ocsf_event_is_contract_valid():
    envelope = build_event_envelope(
        **_envelope_kwargs(
            ocsf_event=None,
            evidence_classification=EvidenceClassification.RAW,
        )
    )
    payload = envelope.model_dump(mode="json")
    assert payload["ocsf_event"] is None
    jsonschema.validate(instance=payload, schema=EVENT_SCHEMA)


def test_is_canonical_envelope_rejects_lookalike_mappings():
    envelope = build_event_envelope(**_envelope_kwargs())
    assert is_canonical_envelope(envelope) is True

    full = envelope.model_dump(mode="json")
    assert is_canonical_envelope(full) is True

    # MappingResult-style dict: parsed fields only.
    assert is_canonical_envelope({"timestamp": "x", "message": "y"}) is False
    assert is_canonical_envelope(None) is False
    assert is_canonical_envelope("evt-1") is False

    # Missing any canonical key (e.g. trusted or provenance) -> not canonical.
    for key in CANONICAL_ENVELOPE_KEYS:
        incomplete = dict(full)
        del incomplete[key]
        assert is_canonical_envelope(incomplete) is False, f"missing {key} accepted"


def test_raw_hash_pattern_is_bare_hex():
    prop = EVENT_SCHEMA["properties"]["raw_ref"]["properties"]
    assert prop["raw_hash"]["pattern"] == "^[0-9a-f]{64}$"
    assert prop["locator"]["pattern"] == "^sha256:[0-9a-f]{64}$"
    assert EVENT_SCHEMA["properties"]["ocsf_event"]["type"] == ["object", "null"]
    assert EVENT_SCHEMA["properties"]["trusted"]["type"] == "boolean"


def test_demo_envelopes_validate_against_contract(demo_data):
    assert demo_data, "demo events must be available"
    for envelope in event_service._events:
        assert isinstance(envelope, ULPFEventEnvelope)
        assert envelope.schema_version == "1.1"
        assert envelope.provenance is not None
        assert isinstance(envelope.trusted, bool)
        assert is_canonical_envelope(envelope)
        jsonschema.validate(
            instance=envelope.model_dump(mode="json"), schema=EVENT_SCHEMA
        )
        # Trust gate consistency on live demo data.
        expected = (
            envelope.evidence_classification == EvidenceClassification.VALIDATED
            and envelope.integrity.status == IntegrityStatus.VERIFIED
            and envelope.integrity.chain_verified is not False
        )
        assert envelope.trusted == expected
