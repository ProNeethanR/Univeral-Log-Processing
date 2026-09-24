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
    """Deterministically load the demo fixtures when ULPF_DEMO_DATA=true.

    Invoked from the ASGI startup path so a live server loads demo state
    without depending on module import order. No-op otherwise.
    """
    if os.environ.get("ULPF_DEMO_DATA", "").lower() != "true":
        return
    event_service.load_demo_data()
    run_service.ensure_demo_run()


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
