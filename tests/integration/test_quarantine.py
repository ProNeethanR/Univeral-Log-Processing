"""Quarantine store: failure records without raw content."""

import json

import jsonschema
import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.models import (
    EventStatus,
    FailureCategory,
    FailureRecord,
    RawRef,
)
from src.api.services import event_service, quarantine_service

client = TestClient(app)

FAILURE_SCHEMA = json.load(
    open("contracts/failure_record.schema.json", encoding="utf-8")
)

ALLOWED_CATEGORIES = {c.value for c in FailureCategory}


@pytest.fixture
def isolated_failures():
    snapshot = list(quarantine_service._failures)
    quarantine_service.clear_failures()
    try:
        yield quarantine_service
    finally:
        quarantine_service._failures[:] = snapshot


def test_record_failure_creates_contract_conformant_record(isolated_failures):
    raw_ref = RawRef(
        store="vault",
        locator="sha256:" + "a" * 64,
        raw_hash="a" * 64,
    )
    record = isolated_failures.record_failure(
        category=FailureCategory.PARSE_FAILED,
        reason="Parser rejected input: unexpected token",
        source_id="syslog-001",
        source_context={"record_index": 3, "byte_offset_start": 40, "byte_offset_end": 80},
        raw_ref=raw_ref,
        event_id="evt-1",
    )

    payload = record.model_dump(mode="json")
    jsonschema.validate(instance=payload, schema=FAILURE_SCHEMA)
    assert record.category == FailureCategory.PARSE_FAILED
    assert record.raw_hash == "a" * 64

    # Failure records never carry raw log content.
    forbidden = {"raw_log", "raw_content", "raw", "payload", "line", "message_raw"}
    assert not (set(payload) & forbidden)


def test_query_filters_and_pagination(isolated_failures):
    isolated_failures.record_failure(
        category=FailureCategory.PARSE_FAILED, reason="parse broke", source_id="a"
    )
    second = isolated_failures.record_failure(
        category=FailureCategory.VALIDATION_FAILED, reason="bad ocsf", source_id="b",
        event_id="evt-2",
    )
    isolated_failures.record_failure(
        category=FailureCategory.PARSE_FAILED, reason="parse broke again", source_id="c",
        event_id="evt-2",
    )

    assert isolated_failures.get_failures().total == 3
    page1 = isolated_failures.get_failures(page=1, page_size=2)
    assert len(page1.items) == 2 and page1.total == 3
    page2 = isolated_failures.get_failures(page=2, page_size=2)
    assert len(page2.items) == 1

    parse_only = isolated_failures.get_failures(category="parse_failed")
    assert parse_only.total == 2

    by_event = isolated_failures.get_failures(event_id="evt-2")
    assert by_event.total == 2
    assert all(f.event_id == "evt-2" for f in by_event.items)

    # Filtered page still paginates.
    tiny = isolated_failures.get_failures(page_size=1, category="parse_failed")
    assert len(tiny.items) == 1 and tiny.total == 2

    assert second.category == FailureCategory.VALIDATION_FAILED


def test_integrity_category_mapping(isolated_failures):
    assert isolated_failures.integrity_failure_category("verified") is None
    assert isolated_failures.integrity_failure_category("corrupted") == FailureCategory.INTEGRITY_CORRUPTED
    assert isolated_failures.integrity_failure_category("missing") == FailureCategory.INTEGRITY_MISSING
    assert isolated_failures.integrity_failure_category("unavailable") == FailureCategory.INTEGRITY_UNAVAILABLE
    assert isolated_failures.integrity_failure_category("not_captured") == FailureCategory.INTEGRITY_NOT_CAPTURED
    assert isolated_failures.integrity_failure_category("bogus") is None


def test_empty_reason_is_rejected(isolated_failures):
    with pytest.raises(ValueError):
        isolated_failures.record_failure(
            category=FailureCategory.PARSE_FAILED, reason=""
        )


def test_quarantine_endpoint_structure(demo_data):
    response = client.get("/api/quarantine")
    assert response.status_code == 200
    data = response.json()
    assert set(data) == {"items", "total", "page", "page_size"}
    assert data["total"] > 0, "demo pipeline failures must be quarantined"
    for item in data["items"]:
        assert item["category"] in ALLOWED_CATEGORIES
        # Never raw content in API responses.
        assert "raw_log" not in item
        assert "raw_content" not in item


def test_failed_demo_events_have_quarantine_records(demo_data):
    # Demo fixtures are the source of truth: every non-SUCCESS demo summary
    # must have a quarantine record, so this is never vacuous.
    assert event_service._summaries, "demo summaries must be available"
    failed_ids = {
        s.event_id
        for s in event_service._summaries
        if s.status != EventStatus.SUCCESS
    }
    assert failed_ids, "demo data must contain non-SUCCESS events"
    quarantined_ids = {
        f.event_id for f in quarantine_service._failures if f.event_id
    }
    assert failed_ids.issubset(quarantined_ids)
    assert quarantine_service._failures, "demo failures must be recorded"
    for f in quarantine_service._failures:
        assert f.category.value in ALLOWED_CATEGORIES
        assert f.reason
        payload = f.model_dump(mode="json")
        assert "raw_log" not in payload
        jsonschema.validate(instance=payload, schema=FAILURE_SCHEMA)
