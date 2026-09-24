from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Mapping
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


class EvidenceClassification(str, Enum):
    RAW = "raw"
    PARSED = "parsed"
    NORMALIZED = "normalized"
    VALIDATED = "validated"
    REJECTED = "rejected"


class IntegrityStatus(str, Enum):
    VERIFIED = "verified"
    CORRUPTED = "corrupted"
    MISSING = "missing"
    UNAVAILABLE = "unavailable"
    NOT_CAPTURED = "not_captured"


class IntegrityDetail(BaseModel):
    status: IntegrityStatus
    reason: Optional[str] = None
    chain_verified: Optional[bool] = None


class FailureCategory(str, Enum):
    """Allowed failure categories for quarantined records."""
    PARSE_FAILED = "parse_failed"
    NORMALIZATION_FAILED = "normalization_failed"
    VALIDATION_FAILED = "validation_failed"
    INTEGRITY_CORRUPTED = "integrity_corrupted"
    INTEGRITY_MISSING = "integrity_missing"
    INTEGRITY_UNAVAILABLE = "integrity_unavailable"
    INTEGRITY_NOT_CAPTURED = "integrity_not_captured"


class RawRef(BaseModel):
    """Reference to the original raw log in the vault."""
    store: str = Field(..., description="Storage backend type, e.g. 'vault'")
    locator: str = Field(..., description="Content-addressed locator, e.g. 'sha256:<hex>'")
    raw_hash: str = Field(..., description="Bare SHA-256 hex digest of the raw log payload")


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


# ---------------------------------------------------------------------------
# ULPF Event Contract Envelope (Phase 2)
# Matches the structure defined in contracts/event_contract.schema.json
# ---------------------------------------------------------------------------


class InjectedField(BaseModel):
    """Describes a single OCSF field injected from the source profile."""
    field: str
    source: str  # e.g. "source_profile"
    profile_id: Optional[str] = None


class PolicyField(BaseModel):
    """Describes a single OCSF field set by normalization policy."""
    field: str
    source: str  # e.g. "normalization_policy"
    value: Any
    rationale: Optional[str] = None


class ProvenanceDetail(BaseModel):
    """Provenance metadata for the normalization pipeline."""
    detection_method: str = Field(default="dsl_parser")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source_profile_id: Optional[str] = None
    source_profile_version: Optional[str] = None
    injected_fields: List[InjectedField] = Field(default_factory=list)
    policy_fields: List[PolicyField] = Field(default_factory=list)
    parser_fields_traced: bool = False


class ULPFEventEnvelope(BaseModel):
    """
    Complete ULPF event wrapper, conforming to contracts/event_contract.schema.json.
    Stores all pipeline-level metadata alongside the OCSF payload.

    All canonical contract keys are always present (ocsf_event may be null but
    the key itself is required). Use build_event_envelope() to construct
    envelopes so the trust gate is applied consistently.
    """
    event_id: str
    source_id: str
    ingest_timestamp: str
    raw_ref: RawRef
    integrity: IntegrityDetail = Field(
        default_factory=lambda: IntegrityDetail(status=IntegrityStatus.UNAVAILABLE),
        description="Verification state of the raw record and integrity chain.",
    )
    evidence_classification: EvidenceClassification = Field(
        default=EvidenceClassification.RAW,
        description="Explicit evidence state for the event payload."
    )
    parser_id: str
    parser_version: str
    schema_version: str
    ocsf_event: Optional[Dict[str, Any]] = None
    provenance: ProvenanceDetail = Field(
        default_factory=ProvenanceDetail,
        description="Normalization provenance; always present (empty when unknown).",
    )
    trusted: bool = Field(
        default=False,
        description=(
            "Trust gate: true only when evidence is validated AND raw integrity "
            "is verified AND the chain was not reported broken at capture time."
        ),
    )
    # Presentation/debug fields (not in the formal contract; used for dashboard projection)
    raw_log: str = ""
    parsed_dict: Optional[Dict[str, Any]] = None
    validation: Optional[ValidationResultDetail] = None

    def to_event_detail(self) -> 'EventDetail':
        """Project a dashboard-facing EventDetail from this envelope."""
        return EventDetail(
            event_id=self.event_id,
            raw_log=self.raw_log,
            parsed_dict=self.parsed_dict,
            ocsf_event=self.ocsf_event,
            validation=self.validation,
        )


# Canonical contract keys that must always be present on an envelope
# (ocsf_event included even when its value is null).
CANONICAL_ENVELOPE_KEYS = frozenset({
    "event_id",
    "source_id",
    "ingest_timestamp",
    "raw_ref",
    "integrity",
    "evidence_classification",
    "parser_id",
    "parser_version",
    "schema_version",
    "ocsf_event",
    "provenance",
    "trusted",
})


def is_canonical_envelope(candidate: Any) -> bool:
    """Structural guard distinguishing a canonical envelope from look-alike mappings."""
    if isinstance(candidate, ULPFEventEnvelope):
        return True
    if isinstance(candidate, Mapping):
        return CANONICAL_ENVELOPE_KEYS.issubset(candidate.keys())
    return False


def compute_trusted(
    evidence_classification: EvidenceClassification,
    integrity: IntegrityDetail,
) -> bool:
    """Trust gate: validated evidence + verified raw integrity + chain not broken."""
    return (
        evidence_classification == EvidenceClassification.VALIDATED
        and integrity.status == IntegrityStatus.VERIFIED
        and integrity.chain_verified is not False
    )


def build_event_envelope(
    *,
    event_id: str,
    source_id: str,
    ingest_timestamp: str,
    raw_ref: Any,
    evidence_classification: EvidenceClassification,
    parser_id: str,
    parser_version: str,
    schema_version: str,
    integrity: Any = None,
    provenance: Any = None,
    ocsf_event: Optional[Dict[str, Any]] = None,
    raw_log: str = "",
    parsed_dict: Optional[Dict[str, Any]] = None,
    validation: Optional[ValidationResultDetail] = None,
) -> ULPFEventEnvelope:
    """Construct a canonical envelope with the trust gate applied."""
    if not isinstance(raw_ref, RawRef):
        raw_ref = RawRef(**raw_ref)
    if integrity is None:
        integrity = IntegrityDetail(status=IntegrityStatus.UNAVAILABLE)
    elif not isinstance(integrity, IntegrityDetail):
        integrity = IntegrityDetail(**integrity)
    if provenance is None:
        provenance = ProvenanceDetail()
    elif not isinstance(provenance, ProvenanceDetail):
        provenance = ProvenanceDetail(**provenance)

    trusted = compute_trusted(evidence_classification, integrity)

    envelope = ULPFEventEnvelope(
        event_id=event_id,
        source_id=source_id,
        ingest_timestamp=ingest_timestamp,
        raw_ref=raw_ref,
        integrity=integrity,
        evidence_classification=evidence_classification,
        parser_id=parser_id,
        parser_version=parser_version,
        schema_version=schema_version,
        ocsf_event=ocsf_event,
        provenance=provenance,
        trusted=trusted,
        raw_log=raw_log,
        parsed_dict=parsed_dict,
        validation=validation,
    )
    assert is_canonical_envelope(envelope)
    return envelope


class FailureRecord(BaseModel):
    """Quarantined failure metadata. Never carries raw log content."""
    failure_id: str
    category: FailureCategory
    reason: str
    timestamp: str
    raw_ref: Optional[RawRef] = None
    raw_hash: Optional[str] = None
    source_id: Optional[str] = None
    source_context: Optional[Dict[str, Any]] = None
    event_id: Optional[str] = None


class PaginatedFailures(BaseModel):
    items: List[FailureRecord]
    total: int
    page: int
    page_size: int


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
