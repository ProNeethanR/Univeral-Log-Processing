import pytest
import os
from fastapi.testclient import TestClient

# Must set the env var BEFORE importing the app or event_service
os.environ["ULPF_DEMO_DATA"] = "true"

from src.api.main import app

client = TestClient(app)

def test_get_summary():
    response = client.get("/api/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_ingested" in data
    assert "parse_successes" in data
    assert data["total_ingested"] >= 0

def test_get_events():
    response = client.get("/api/events")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    
def test_get_events_pagination():
    response = client.get("/api/events?page=1&page_size=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) <= 5

def test_get_events_filtering():
    response = client.get("/api/events?format=syslog&status=SUCCESS")
    assert response.status_code == 200
    data = response.json()
    for item in data["items"]:
        assert item["source_format"] == "syslog"
        assert item["status"] == "SUCCESS"

def test_get_event_endpoints():
    # Get a list of events to find a valid ID
    response = client.get("/api/events?page=1&page_size=1")
    assert response.status_code == 200
    data = response.json()
    
    if len(data["items"]) > 0:
        event_id = data["items"][0]["event_id"]
        
        # Test Detail
        res_detail = client.get(f"/api/events/{event_id}")
        assert res_detail.status_code == 200
        assert res_detail.json()["event_id"] == event_id
        
        # Test Raw
        res_raw = client.get(f"/api/events/{event_id}/raw")
        assert res_raw.status_code == 200
        assert "raw_log" in res_raw.json()
        
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

def test_get_event_not_found():
    res = client.get("/api/events/invalid-event-id")
    assert res.status_code == 404

def test_get_event_raw_not_found():
    res = client.get("/api/events/invalid-event-id/raw")
    assert res.status_code == 404
