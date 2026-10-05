"""Durable persistence layer for pipeline state across server restarts.

Maintains transactional SQLite storage for:
- Event envelopes and raw evidence references
- Event summaries for high-throughput pagination
- Quarantine FailureRecords (Dead-Letter Queue)
- PipelineRun execution history and associations
"""

import os
import sqlite3
import json
from typing import Dict, List, Optional, Tuple, Any

DEFAULT_DB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "ulpf_state.db")
)


def get_db_path(custom_path: Optional[str] = None) -> str:
    path = custom_path or os.environ.get("ULPF_DB_PATH", DEFAULT_DB_PATH)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    return path


def get_connection(custom_path: Optional[str] = None) -> sqlite3.Connection:
    path = get_db_path(custom_path)
    conn = sqlite3.connect(path, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    _init_schema(conn)
    return conn


def _init_schema(conn: sqlite3.Connection) -> None:
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                source_id TEXT,
                timestamp TEXT,
                status TEXT,
                data TEXT NOT NULL
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_events_status ON events(status);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_events_source ON events(source_id);")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS summaries (
                event_id TEXT PRIMARY KEY,
                timestamp TEXT,
                source_format TEXT,
                status TEXT,
                data TEXT NOT NULL
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_summaries_status ON summaries(status);")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS failures (
                failure_id TEXT PRIMARY KEY,
                category TEXT,
                event_id TEXT,
                timestamp TEXT,
                data TEXT NOT NULL
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_failures_category ON failures(category);")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                status TEXT,
                started_at TEXT,
                completed_at TEXT,
                data TEXT NOT NULL,
                event_ids TEXT NOT NULL
            );
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
        """)


def has_persisted_state(custom_path: Optional[str] = None) -> bool:
    try:
        conn = get_connection(custom_path)
        with conn:
            cur = conn.execute("SELECT COUNT(*) as cnt FROM summaries;")
            row = cur.fetchone()
            return bool(row and row["cnt"] > 0)
    except Exception:
        return False


def save_pipeline_state(
    events: List[Any],
    summaries: List[Any],
    failures: List[Any],
    runs: Dict[str, Any],
    run_event_ids: Dict[str, List[str]],
    custom_path: Optional[str] = None
) -> None:
    conn = get_connection(custom_path)
    with conn:
        conn.execute("DELETE FROM events;")
        conn.execute("DELETE FROM summaries;")
        conn.execute("DELETE FROM failures;")
        conn.execute("DELETE FROM runs;")

        # Save events
        for e in events:
            e_dict = e.model_dump() if hasattr(e, "model_dump") else (e.dict() if hasattr(e, "dict") else dict(e))
            conn.execute(
                "INSERT INTO events (event_id, source_id, timestamp, status, data) VALUES (?, ?, ?, ?, ?);",
                (
                    e_dict.get("event_id"),
                    e_dict.get("source_id"),
                    e_dict.get("ingest_timestamp"),
                    e_dict.get("integrity", {}).get("status") if isinstance(e_dict.get("integrity"), dict) else "unknown",
                    json.dumps(e_dict)
                )
            )

        # Save summaries
        for s in summaries:
            s_dict = s.model_dump() if hasattr(s, "model_dump") else (s.dict() if hasattr(s, "dict") else dict(s))
            conn.execute(
                "INSERT INTO summaries (event_id, timestamp, source_format, status, data) VALUES (?, ?, ?, ?, ?);",
                (
                    s_dict.get("event_id"),
                    s_dict.get("timestamp"),
                    s_dict.get("source_format"),
                    s_dict.get("status"),
                    json.dumps(s_dict)
                )
            )

        # Save failures
        for f in failures:
            f_dict = f.model_dump() if hasattr(f, "model_dump") else (f.dict() if hasattr(f, "dict") else dict(f))
            conn.execute(
                "INSERT INTO failures (failure_id, category, event_id, timestamp, data) VALUES (?, ?, ?, ?, ?);",
                (
                    f_dict.get("failure_id"),
                    str(f_dict.get("category")),
                    f_dict.get("event_id"),
                    f_dict.get("timestamp"),
                    json.dumps(f_dict)
                )
            )

        # Save runs
        for r_id, r in runs.items():
            r_dict = r.model_dump() if hasattr(r, "model_dump") else (r.dict() if hasattr(r, "dict") else dict(r))
            e_ids = run_event_ids.get(r_id, [])
            conn.execute(
                "INSERT INTO runs (run_id, status, started_at, completed_at, data, event_ids) VALUES (?, ?, ?, ?, ?, ?);",
                (
                    r_id,
                    str(r_dict.get("status")),
                    r_dict.get("started_at"),
                    r_dict.get("completed_at"),
                    json.dumps(r_dict),
                    json.dumps(e_ids)
                )
            )


def load_pipeline_state(custom_path: Optional[str] = None) -> Dict[str, Any]:
    from src.api.models import ULPFEventEnvelope, EventSummary, FailureRecord, PipelineRun

    conn = get_connection(custom_path)
    result = {
        "events": [],
        "summaries": [],
        "failures": [],
        "runs": {},
        "run_event_ids": {}
    }

    with conn:
        for row in conn.execute("SELECT data FROM events;"):
            try:
                result["events"].append(ULPFEventEnvelope(**json.loads(row["data"])))
            except Exception:
                pass

        for row in conn.execute("SELECT data FROM summaries;"):
            try:
                result["summaries"].append(EventSummary(**json.loads(row["data"])))
            except Exception:
                pass

        for row in conn.execute("SELECT data FROM failures;"):
            try:
                result["failures"].append(FailureRecord(**json.loads(row["data"])))
            except Exception:
                pass

        for row in conn.execute("SELECT run_id, data, event_ids FROM runs;"):
            try:
                r_id = row["run_id"]
                result["runs"][r_id] = PipelineRun(**json.loads(row["data"]))
                result["run_event_ids"][r_id] = json.loads(row["event_ids"])
            except Exception:
                pass

    return result


def clear_pipeline_state(custom_path: Optional[str] = None) -> None:
    conn = get_connection(custom_path)
    with conn:
        conn.execute("DELETE FROM events;")
        conn.execute("DELETE FROM summaries;")
        conn.execute("DELETE FROM failures;")
        conn.execute("DELETE FROM runs;")
        conn.execute("DELETE FROM meta;")


def persist_current_state(custom_path: Optional[str] = None) -> None:
    from src.api.services import event_service, quarantine_service, run_service
    save_pipeline_state(
        events=event_service._events,
        summaries=event_service._summaries,
        failures=quarantine_service._failures,
        runs=run_service._runs,
        run_event_ids=run_service._run_event_ids,
        custom_path=custom_path
    )


def sync_from_persistence(custom_path: Optional[str] = None) -> bool:
    from src.api.services import event_service, quarantine_service, run_service

    if not has_persisted_state(custom_path):
        return False

    state = load_pipeline_state(custom_path)
    if not state["summaries"]:
        return False

    event_service._events.clear()
    event_service._events.extend(state["events"])

    event_service._summaries.clear()
    event_service._summaries.extend(state["summaries"])

    quarantine_service._failures.clear()
    quarantine_service._failures.extend(state["failures"])

    run_service._runs.clear()
    run_service._runs.update(state["runs"])

    run_service._run_event_ids.clear()
    run_service._run_event_ids.update(state["run_event_ids"])

    if state["summaries"]:
        event_service._active_parsers = 1

    return True
