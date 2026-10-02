import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_get_summary(demo_data):
    response = client.get("/api/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_ingested" in data
    assert "parse_successes" in data
    assert data["total_ingested"] > 0, "summary must reflect loaded demo events"

    # Demo run enrichment: a live demo run must be reported.
    assert "latest_run_id" in data
    assert "latest_run_status" in data
    assert data["historical_runs_available"] is True


def test_get_events(demo_data):
    response = client.get("/api/events")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert data["total"] > 0, "endpoint must return loaded demo events"
    assert len(data["items"]) > 0


def test_get_events_pagination(demo_data):
    response = client.get("/api/events?page=1&page_size=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) <= 5
    assert data["total"] > 0


def test_get_events_filtering(demo_data):
    # format filter is applied and returns the loaded syslog events.
    response = client.get("/api/events?format=syslog")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0, "format filter must return loaded demo events"
    for item in data["items"]:
        assert item["source_format"] == "syslog"

    # validation_status=failed covers the demo events (RFC3164: no year or
    # timezone, so OCSF validation is honestly failing) and must be applied.
    failed = client.get("/api/events?format=syslog&validation_status=failed")
    assert failed.status_code == 200
    failed_data = failed.json()
    assert failed_data["total"] > 0
    for item in failed_data["items"]:
        assert item["status"] == "VALIDATION_FAILED"
        assert item["source_format"] == "syslog"

    # The status filter, where applied, is respected.
    success = client.get("/api/events?format=syslog&status=SUCCESS")
    assert success.status_code == 200
    for item in success.json()["items"]:
        assert item["status"] == "SUCCESS"


def test_get_event_endpoints(demo_data):
    # Get a list of events to find a valid ID
    response = client.get("/api/events?page=1&page_size=1")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0, "demo events must be available for endpoint checks"
    assert len(data["items"]) > 0
    event_id = data["items"][0]["event_id"]

    # Test Detail
    res_detail = client.get(f"/api/events/{event_id}")
    assert res_detail.status_code == 200
    assert res_detail.json()["event_id"] == event_id

    # Test Raw
    res_raw = client.get(f"/api/events/{event_id}/raw")
    assert res_raw.status_code == 200
    assert "raw_log" in res_raw.json()
    assert res_raw.json()["raw_log"], "raw log must be populated"

    # Test Parsed
    res_parsed = client.get(f"/api/events/{event_id}/parsed")
    assert res_parsed.status_code == 200

    # Test Normalized
    res_normalized = client.get(f"/api/events/{event_id}/normalized")
    assert res_normalized.status_code == 200

    # Test Validation
    res_validation = client.get(f"/api/events/{event_id}/validation")
    assert res_validation.status_code == 200
    assert "status" in res_validation.json()
    assert "errors" in res_validation.json()

    # Test Envelope
    res_envelope = client.get(f"/api/events/{event_id}/envelope")
    assert res_envelope.status_code == 200
    env_data = res_envelope.json()
    assert "event_id" in env_data
    assert "source_id" in env_data
    assert "ingest_timestamp" in env_data
    assert "raw_ref" in env_data
    assert "store" in env_data["raw_ref"]
    assert "locator" in env_data["raw_ref"]
    assert "raw_hash" in env_data["raw_ref"]
    assert "evidence_classification" in env_data
    assert env_data["evidence_classification"] in {"raw", "parsed", "normalized", "validated", "rejected"}
    assert "parser_id" in env_data
    assert "parser_version" in env_data
    assert "schema_version" in env_data
    assert "ocsf_event" in env_data
    assert "provenance" in env_data
    assert "trusted" in env_data
    assert isinstance(env_data["trusted"], bool)
    assert "integrity" in env_data
    assert env_data["integrity"]["status"] in {
        "verified", "corrupted", "missing", "unavailable", "not_captured"
    }

def test_get_event_not_found():
    res = client.get("/api/events/invalid-event-id")
    assert res.status_code == 404

def test_get_event_raw_not_found():
    res = client.get("/api/events/invalid-event-id/raw")
    assert res.status_code == 404


def test_integrity_verification_endpoint_is_structured():
    response = client.get("/api/integrity/verify")
    assert response.status_code == 200
    data = response.json()
    # Checkpoint policy: overall status is verified only with a valid anchor;
    # anchor problems are reported explicitly as missing/stale/invalid.
    assert data["status"] in {
        "verified", "corrupted", "missing", "unavailable", "stale", "invalid"
    }
    assert "reason" in data
    assert "records" in data
    assert "checkpoint" in data
    checkpoint = data["checkpoint"]
    assert checkpoint["status"] in {"valid", "missing", "stale", "invalid", "unavailable"}
    assert "sequence" in checkpoint
    assert "head_hash" in checkpoint
    assert "checkpoint_hash" in checkpoint
    if data["status"] == "verified":
        assert checkpoint["status"] == "valid"


def test_post_demo_run(demo_data):
    response = client.post("/api/demo/run")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["total_events"] > 0
    assert data["passed"] > 0
    assert "message" in data
    assert "run_id" in data


def test_post_test_parse_cisco():
    raw_cisco = "%ASA-6-302013: Built outbound TCP connection 984712 for outside:198.51.100.22/443 (198.51.100.22/443) to inside:10.0.12.84/51234 (10.0.12.84/51234)"
    response = client.post("/api/test-parse", json={"raw_log": raw_cisco})
    assert response.status_code == 200
    data = response.json()
    assert "format" in data
    assert "confidence" in data
    assert "parsed_fields" in data
    assert "extracted_rows" in data
    assert data["validation_status"] == "PASS"


def test_post_test_parse_empty():
    response = client.post("/api/test-parse", json={"raw_log": ""})
    assert response.status_code == 400


def test_post_quarantine_reprocess():
    response = client.post("/api/quarantine/reprocess")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "dispatched"
    assert "count" in data


def test_get_sources_and_plugins():
    res_sources = client.get("/api/sources")
    assert res_sources.status_code == 200
    sources = res_sources.json()
    assert len(sources) > 0
    assert "name" in sources[0]

    res_plugins = client.get("/api/plugins")
    assert res_plugins.status_code == 200
    plugins = res_plugins.json()
    assert len(plugins) > 0
    assert "binary" in plugins[0]