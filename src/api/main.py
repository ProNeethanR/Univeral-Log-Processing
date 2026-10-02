import os
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from src.api.models import (
    DashboardSummary, EventDetail, ValidationResultDetail,
    PipelineRun, PaginatedRuns, PaginatedEvents, PaginatedFailures,
    ULPFEventEnvelope,
)
from src.api.services import event_service, run_service, quarantine_service
from src.vault import store as vault


def bootstrap_demo() -> None:
    """Initialize state on server startup.

    If prior pipeline state was persisted in SQLite and fresh start is not forced,
    restores state across restarts. Otherwise initializes in clean nil genesis state.
    """
    from src.storage import persistence
    fresh_start = os.environ.get("ULPF_FRESH_START", "").lower() == "true"
    if not fresh_start and persistence.has_persisted_state():
        if persistence.sync_from_persistence():
            return

    from src.vault import store as vault_store
    vault_store.clear()
    event_service._events.clear()
    event_service._summaries.clear()
    quarantine_service._failures.clear()
    run_service._runs.clear()
    run_service._run_event_ids.clear()
    event_service._active_parsers = 0


@asynccontextmanager
async def lifespan(_: FastAPI):
    bootstrap_demo()
    yield


app = FastAPI(title="ULPF Dashboard API", lifespan=lifespan)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(STATIC_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def serve_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


# ------------------------------------------------------------------
# Summary / Overview
# ------------------------------------------------------------------

@app.get("/api/summary", response_model=DashboardSummary)
def get_summary():
    summary = event_service.get_summary()
    # Enrich with latest run info if available
    runs = run_service.get_runs(page=1, page_size=1)
    if runs["items"]:
        latest = runs["items"][0]
        summary.latest_run_id = latest.run_id
        summary.latest_run_status = latest.status
        summary.historical_runs_available = True
    else:
        summary.latest_run_id = None
        summary.latest_run_status = None
        summary.historical_runs_available = False
    return summary


# ------------------------------------------------------------------
# Events
# ------------------------------------------------------------------

@app.get("/api/events")
def get_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    search: Optional[str] = None,
    format: Optional[str] = None,
    status: Optional[str] = None,
    validation_status: Optional[str] = None,
):
    return event_service.get_events(page, page_size, search, format, status, validation_status)


@app.get("/api/events/{event_id}", response_model=EventDetail)
def get_event(event_id: str):
    detail = event_service.get_event_detail(event_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Event not found")
    return detail


@app.get("/api/events/{event_id}/envelope", response_model=ULPFEventEnvelope)
def get_event_envelope(event_id: str):
    envelope = event_service.get_event_envelope(event_id)
    if not envelope:
        raise HTTPException(status_code=404, detail="Event envelope not found")
    return envelope


@app.get("/api/events/{event_id}/raw")
def get_event_raw(event_id: str):
    raw = event_service.get_event_raw(event_id)
    if raw is None:
        raise HTTPException(status_code=404, detail="Raw data unavailable")
    return {"raw_log": raw}


@app.get("/api/events/{event_id}/parsed")
def get_event_parsed(event_id: str):
    parsed = event_service.get_event_parsed(event_id)
    if parsed is None:
        raise HTTPException(status_code=404, detail="Parsed data unavailable")
    return parsed


@app.get("/api/events/{event_id}/normalized")
def get_event_normalized(event_id: str):
    normalized = event_service.get_event_normalized(event_id)
    if normalized is None:
        raise HTTPException(status_code=404, detail="Normalized data unavailable")
    return normalized


@app.get("/api/events/{event_id}/validation", response_model=ValidationResultDetail)
def get_event_validation(event_id: str):
    validation = event_service.get_event_validation(event_id)
    if validation is None:
        raise HTTPException(status_code=404, detail="Validation data unavailable")
    return validation


@app.get("/api/integrity/verify")
def verify_integrity():
    """Return an air-gapped vault verification summary without raw content.

    The report includes an explicit checkpoint anchor block. Overall status
    is 'verified' only when the chain verifies AND a checkpoint validly
    anchors the current chain head.
    """
    return vault.verification_report()


@app.post("/api/integrity/checkpoint")
def create_integrity_checkpoint():
    """Create a verification checkpoint anchoring the current chain head."""
    try:
        return vault.create_checkpoint()
    except vault.IntegrityError as exc:
        if "does not support checkpoints" in str(exc):
            raise HTTPException(status_code=503, detail=str(exc))
        raise HTTPException(status_code=409, detail=str(exc))


# ------------------------------------------------------------------
# Quarantine (failure records; never raw content)
# ------------------------------------------------------------------

@app.get("/api/quarantine", response_model=PaginatedFailures)
def get_quarantine(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    category: Optional[str] = None,
    event_id: Optional[str] = None,
):
    return quarantine_service.get_failures(page, page_size, category, event_id)


# ------------------------------------------------------------------
# Pipeline Runs
# ------------------------------------------------------------------

@app.get("/api/runs")
def get_runs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    status: Optional[str] = None,
    source: Optional[str] = None,
    input_format: Optional[str] = None,
):
    return run_service.get_runs(page, page_size, status, source, input_format)


@app.get("/api/runs/{run_id}", response_model=PipelineRun)
def get_run(run_id: str):
    run = run_service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@app.get("/api/runs/{run_id}/events")
def get_run_events(
    run_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    status: Optional[str] = None,
    validation_status: Optional[str] = None,
):
    result = run_service.get_run_events(run_id, page, page_size, status, validation_status)
    if result is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return result


# ------------------------------------------------------------------
# Interactive Operations & Demo Harness
# ------------------------------------------------------------------

@app.post("/api/demo/run")
def run_demo():
    """Trigger the complete ULPF demo pipeline across synthetic and historical fixtures."""
    return event_service.run_demo_pipeline()


@app.post("/api/test-parse")
def test_parse(payload: dict):
    raw_log = payload.get("raw_log", "")
    if not raw_log:
        raise HTTPException(status_code=400, detail="raw_log payload is required")
    return event_service.test_parse_log(raw_log)


@app.post("/api/quarantine/reprocess")
def reprocess_quarantine():
    return quarantine_service.reprocess_failures()


@app.get("/api/sources")
def get_sources():
    """Return active source profiles from the registry alongside configured connectors."""
    from src.registry import list_source_profiles
    profiles = []
    try:
        profiles = list_source_profiles()
    except Exception:
        pass

    has_active_syslog = any(str(p[2]).upper().endswith("ACTIVE") for p in profiles) if profiles else False

    return [
        {
            "id": "src-syslog-netfilter",
            "name": "Linux Netfilter / iptables",
            "cluster": "Synthetic & Historical Fixtures",
            "type": "File / Syslog UDP 514",
            "eps": 7000 if has_active_syslog else 0,
            "last_seen": "Active" if has_active_syslog else "Idle (Pending Run)",
            "status": "live" if has_active_syslog else "idle",
            "tag": "ACTIVE REGISTRY",
        },
        {
            "id": "src-cisco-asa",
            "name": "Cisco ASA Firewall",
            "cluster": "Edge Gateway cluster-us-east",
            "type": "Syslog UDP 514",
            "eps": 14240,
            "last_seen": "120ms ago",
            "status": "live",
            "tag": "DEMO CONNECTOR",
        },
        {
            "id": "src-panos",
            "name": "Palo Alto Networks NGFW",
            "cluster": "PAN-OS v11.1 Series",
            "type": "Syslog TCP 5514 (TLS)",
            "eps": 18210,
            "last_seen": "45ms ago",
            "status": "live",
            "tag": "DEMO CONNECTOR",
        },
        {
            "id": "src-fortigate",
            "name": "Fortinet FortiGate",
            "cluster": "Internal DC Core Segment",
            "type": "Syslog UDP 514",
            "eps": 8410,
            "last_seen": "310ms ago",
            "status": "live",
            "tag": "DEMO CONNECTOR",
        },
        {
            "id": "src-checkpoint",
            "name": "Check Point Quantum Security",
            "cluster": "R81.20 Take 79",
            "type": "Kafka spool (secops.cp)",
            "eps": 4890,
            "last_seen": "180ms ago",
            "status": "live",
            "tag": "DEMO CONNECTOR",
        },
        {
            "id": "src-webhook",
            "name": "Custom Appliance (Bespoke TLS)",
            "cluster": "Air-gapped telemetry relay",
            "type": "Webhook /api/ingest",
            "eps": 2450,
            "last_seen": "890ms ago",
            "status": "live",
            "tag": "DEMO CONNECTOR",
        },
    ]


@app.get("/api/plugins")
def get_plugins():
    """Return active DSL parsers from the registry with clear provenance and sandbox validation."""
    from src.registry import _registry
    is_syslog_registered = ("syslog-001", "1.0.0") in _registry

    return [
        {
            "name": "syslog_netfilter_dsl",
            "version": "v1.0.0",
            "binary": "parsers/syslog.yaml",
            "format": "Linux Netfilter RFC 3164",
            "sandbox": "Native AST Sandbox",
            "latency_p50": "0.22ms",
            "status": "AST Validated • Active" if is_syslog_registered else "AST Validated • Ready",
            "tag": "ACTIVE REGISTRY",
        },
        {
            "name": "cisco_asa_parser",
            "version": "v2.4.1",
            "binary": "libparser_cisco.so",
            "format": "Syslog RFC 3164/5424",
            "sandbox": "Isolated WASM Enclave",
            "latency_p50": "0.32ms",
            "status": "AST Validated",
            "tag": "DEMO CONNECTOR",
        },
        {
            "name": "paloalto_panos_parser",
            "version": "v3.1.0",
            "binary": "libparser_panos.so",
            "format": "CSV Delimited Syslog",
            "sandbox": "Isolated WASM Enclave",
            "latency_p50": "0.41ms",
            "status": "AST Validated",
            "tag": "DEMO CONNECTOR",
        },
        {
            "name": "aws_cloudtrail_json",
            "version": "v1.8.4",
            "binary": "libparser_cloudtrail.so",
            "format": "NDJSON / Gzip Bundles",
            "sandbox": "Isolated WASM Enclave",
            "latency_p50": "0.28ms",
            "status": "AST Validated",
            "tag": "DEMO CONNECTOR",
        },
    ]


@app.get("/api/persistence/status")
def get_persistence_status():
    """Return status of SQLite persistence layer."""
    from src.storage import persistence
    return {
        "persisted": persistence.has_persisted_state(),
        "db_path": persistence.get_db_path(),
        "total_events": len(event_service._events),
        "total_summaries": len(event_service._summaries),
        "total_quarantined": len(quarantine_service._failures),
        "total_runs": len(run_service._runs)
    }


@app.post("/api/pipeline/reset")
def reset_pipeline_state():
    """Reset all in-memory and persisted pipeline state to clean genesis nil state."""
    from src.storage import persistence
    from src.vault import store as vault_store
    persistence.clear_pipeline_state()
    vault_store.clear()
    event_service._events.clear()
    event_service._summaries.clear()
    quarantine_service._failures.clear()
    run_service._runs.clear()
    run_service._run_event_ids.clear()
    event_service._active_parsers = 0
    return {
        "status": "success",
        "message": "Pipeline state and SQLite database reset to clean genesis nil state."
    }

