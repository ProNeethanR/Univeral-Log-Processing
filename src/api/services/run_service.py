"""
run_service.py
--------------
Read-only service exposing pipeline run data to the API layer.

IMPORTANT: The ULPF architecture does not persist run history between process
restarts. There is no database or disk-based run store.

When ULPF_DEMO_DATA=true: a single deterministic demo run is synthesised from
the in-memory events already loaded by event_service.  It is explicitly marked
as demo data (is_demo=True, status=DEMO).  The run is (re)built by calling
ensure_demo_run(); there is no module-import side effect.

When ULPF_DEMO_DATA is not set: the run list is empty.  The API returns an
empty result and the UI must say so explicitly.
"""

import os
from typing import Dict, List, Optional, Any

from src.api.models import PipelineRun, RunStatus, EventSummary


# In-memory run store (at most one demo run when demo mode is active)
_runs: Dict[str, PipelineRun] = {}
# Map run_id -> list of event_ids belonging to that run
_run_event_ids: Dict[str, List[str]] = {}


def _build_demo_run() -> None:
    """
    Synthesise one demo run from the events already loaded by event_service.
    Invoked explicitly via ensure_demo_run(); never a module-import side effect.
    """
    from src.api.services import event_service
    from src.api.models import EventStatus

    summaries: List[EventSummary] = event_service._summaries
    if not summaries:
        return

    run_id = "demo-run-001"

    events_total = len(summaries)
    events_parsed = sum(1 for s in summaries if s.status != EventStatus.PARSE_FAILED)
    events_normalized = sum(
        1 for s in summaries
        if s.status in (EventStatus.SUCCESS, EventStatus.VALIDATION_FAILED)
    )
    events_valid = sum(1 for s in summaries if s.status == EventStatus.SUCCESS)
    events_invalid = sum(1 for s in summaries if s.status == EventStatus.VALIDATION_FAILED)

    # Use the timestamps from the first and last event summaries
    started_at = summaries[0].timestamp
    completed_at = summaries[-1].timestamp

    # Estimate a plausible duration from event count (demo only)
    duration_ms = events_total * 12  # ~12 ms per event, purely illustrative

    run = PipelineRun(
        run_id=run_id,
        status=RunStatus.DEMO,
        source="fixtures/raw/syslog/syslog-001.log",
        input_format="syslog",
        started_at=started_at,
        completed_at=completed_at,
        duration_ms=duration_ms,
        events_total=events_total,
        events_parsed=events_parsed,
        events_normalized=events_normalized,
        events_valid=events_valid,
        events_invalid=events_invalid,
        errors=[],
        warnings=[
            "Demo run: data originates from fixture file, not a production pipeline execution."
        ],
        is_demo=True,
    )

    _runs[run_id] = run
    _run_event_ids[run_id] = [s.event_id for s in summaries]


def ensure_demo_run() -> None:
    """Explicitly (re)build the demo run from current event summaries.

    Deterministic and idempotent: prior run state is cleared before rebuilding
    and the run is only synthesised when ULPF_DEMO_DATA=true. Invoked by the
    API entrypoint and test fixtures; never a module-import side effect.
    """
    _runs.clear()
    _run_event_ids.clear()
    if os.environ.get("ULPF_DEMO_DATA", "").lower() != "true":
        return
    _build_demo_run()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_runs(
    page: int = 1,
    page_size: int = 50,
    status: Optional[str] = None,
    source: Optional[str] = None,
    input_format: Optional[str] = None,
) -> Dict[str, Any]:
    runs = list(_runs.values())

    if status:
        runs = [r for r in runs if r.status == status]
    if source:
        runs = [r for r in runs if source.lower() in r.source.lower()]
    if input_format:
        runs = [r for r in runs if r.input_format == input_format]

    total = len(runs)
    start = (page - 1) * page_size
    items = runs[start: start + page_size]

    return {"items": items, "total": total, "page": page, "page_size": page_size}


def get_run(run_id: str) -> Optional[PipelineRun]:
    return _runs.get(run_id)


def get_run_events(
    run_id: str,
    page: int = 1,
    page_size: int = 50,
    status: Optional[str] = None,
    validation_status: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    if run_id not in _runs:
        return None

    from src.api.services import event_service
    from src.api.models import EventStatus

    event_ids = _run_event_ids.get(run_id, [])
    id_set = set(event_ids)

    summaries = [s for s in event_service._summaries if s.event_id in id_set]

    if status:
        summaries = [s for s in summaries if s.status == status]

    if validation_status:
        if validation_status == "passed":
            summaries = [s for s in summaries if s.status == EventStatus.SUCCESS]
        elif validation_status == "failed":
            summaries = [s for s in summaries if s.status == EventStatus.VALIDATION_FAILED]

    total = len(summaries)
    start = (page - 1) * page_size
    items = summaries[start: start + page_size]

    return {"items": items, "total": total, "page": page, "page_size": page_size}
