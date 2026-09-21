from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum


class EventStatus(str, Enum):
    SUCCESS = "SUCCESS"
    PARSE_FAILED = "PARSE_FAILED"
    NORM_FAILED = "NORM_FAILED"
    VALIDATION_FAILED = "VALIDATION_FAILED"


class RunStatus(str, Enum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    DEMO = "DEMO"


class DashboardSummary(BaseModel):
    total_ingested: int
    parse_successes: int
    normalization_successes: int
    validation_successes: int
    active_parsers: int
    latest_run_id: Optional[str] = None
    latest_run_status: Optional[str] = None
    historical_runs_available: bool = False


class EventSummary(BaseModel):
    event_id: str
    timestamp: str
    source_format: str
    status: EventStatus
    run_id: Optional[str] = None


class ValidationResultDetail(BaseModel):
    status: str
    errors: List[Any] = Field(default_factory=list)
    warnings: List[Any] = Field(default_factory=list)


class EventDetail(BaseModel):
    event_id: str
    raw_log: str
    parsed_dict: Optional[Dict[str, Any]] = None
    ocsf_event: Optional[Dict[str, Any]] = None
    validation: Optional[ValidationResultDetail] = None


class PipelineRun(BaseModel):
    run_id: str
    status: RunStatus
    source: str
    input_format: str
    started_at: str
    completed_at: str
    duration_ms: int
    events_total: int
    events_parsed: int
    events_normalized: int
    events_valid: int
    events_invalid: int
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    is_demo: bool = False


class PaginatedRuns(BaseModel):
    items: List[PipelineRun]
    total: int
    page: int
    page_size: int


class PaginatedEvents(BaseModel):
    items: List[EventSummary]
    total: int
    page: int
    page_size: int
