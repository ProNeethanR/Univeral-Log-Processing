import os
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from src.api.models import (
    EventSummary, EventDetail, EventStatus, DashboardSummary,
    ValidationResultDetail, ULPFEventEnvelope, RawRef, ProvenanceDetail,
    EvidenceClassification, IntegrityDetail, IntegrityStatus,
)

# In-memory storage for events as ULPF event contract envelopes.
_events: List[ULPFEventEnvelope] = []
_summaries: List[EventSummary] = []
_active_parsers = 0

# ULPF event contract schema version constant.
# Must be updated when event_contract.schema.json is versioned.
_SCHEMA_VERSION = "1.0"

def load_demo_data():
    """Load fixtures and process them if ULPF_DEMO_DATA is true."""
    global _active_parsers
    if os.environ.get("ULPF_DEMO_DATA", "").lower() != "true":
        return

    if _events:
        return

    from src.parsers.engine import ParserEngine
    from src.normalization.mapper import OCSFMapper
    from src.normalization.ocsf_validator import validate_ocsf_event
    from src.registry import register_parser, _clear_registry
    from src.ingestion.ingestor import ingest_bytes

    try:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        raw_path = os.path.join(base_dir, "fixtures", "raw", "syslog", "syslog-001.log")
        parser_path = os.path.join(base_dir, "parsers", "syslog.yaml")

        if not os.path.exists(raw_path) or not os.path.exists(parser_path):
            print(f"Warning: Demo data files not found at {raw_path} or {parser_path}")
            return

        _clear_registry()
        register_parser("syslog-001", "1.0.0", parser_path)
        _active_parsers = 1

        engine = ParserEngine("syslog-001", "1.0.0")
        mapper = OCSFMapper()

        with open(raw_path, 'rb') as f:
            raw_bytes = f.read()

        raw_lines = raw_bytes.decode('utf-8').strip().split('\n')

        for i, line in enumerate(raw_lines):
            line = line.strip()
            if not line:
                continue

            # Record ingest timestamp at the moment of processing this line.
            # datetime.utcnow() is deprecated since Python 3.12; use timezone-aware form.
            ingest_timestamp = datetime.now(timezone.utc).isoformat()

            # Vault each raw line individually to produce raw_ref.
            # This is intentionally per-line, not per-file (per event contract requirements).
            ingested = ingest_bytes(
                line.encode("utf-8"),
                source_label=raw_path,
                source_id="syslog-001",
                input_format="syslog",
            )

            event_id = f"demo-event-{i+1}-{uuid.uuid4().hex[:8]}"
            evidence_classification = EvidenceClassification.RAW

            try:
                parsed_fields = engine.parse(line)
                status = EventStatus.SUCCESS
                evidence_classification = EvidenceClassification.PARSED
            except Exception:
                parsed_fields = None
                status = EventStatus.PARSE_FAILED
                evidence_classification = EvidenceClassification.REJECTED

            ocsf = None
            validation_detail = ValidationResultDetail(status="UNAVAILABLE", errors=[], warnings=[])

            if parsed_fields:
                try:
                    ocsf = mapper.map_syslog(parsed_fields, source_id="syslog-001", profile_version=None)
                    ocsf = mapper.enrich_ocsf_headers(parsed_fields, ocsf)
                    evidence_classification = EvidenceClassification.NORMALIZED

                    if 'unmapped' in ocsf and 'tracing' in ocsf['unmapped']:
                        ocsf['unmapped']['tracing'] = sorted(ocsf['unmapped']['tracing'], key=lambda x: x['source_field'])

                    # Validate OCSF
                    val_res = validate_ocsf_event(ocsf)
                    if val_res.is_valid:
                        validation_detail = ValidationResultDetail(status="PASS", errors=[], warnings=[])
                        status = EventStatus.SUCCESS
                        evidence_classification = EvidenceClassification.VALIDATED
                    else:
                        validation_detail = ValidationResultDetail(
                            status="FAIL",
                            errors=[e.to_dict() for e in val_res.errors],
                            warnings=[]
                        )
                        status = EventStatus.VALIDATION_FAILED
                        evidence_classification = EvidenceClassification.REJECTED
                except Exception:
                    status = EventStatus.NORM_FAILED
                    validation_detail = None
                    evidence_classification = EvidenceClassification.REJECTED

            provenance = ProvenanceDetail(
                detection_method="dsl_parser",
                confidence=1.0 if parsed_fields else 0.0,
                source_profile_id=getattr(ocsf, "source_profile_id", None),
                source_profile_version=getattr(ocsf, "source_profile_version", None),
                injected_fields=getattr(ocsf, "injected_fields", []),
                policy_fields=getattr(ocsf, "policy_fields", []),
                parser_fields_traced=bool(ocsf and "unmapped" in ocsf and "tracing" in ocsf["unmapped"])
            )

            # Assemble the ULPF event contract envelope.
            envelope = ULPFEventEnvelope(
                event_id=event_id,
                source_id="syslog-001",
                ingest_timestamp=ingest_timestamp,
                raw_ref=RawRef(
                    store=ingested.raw_ref["store"],
                    locator=ingested.raw_ref["locator"],
                    raw_hash=ingested.raw_ref["raw_hash"],
                ),
                integrity=IntegrityDetail(
                    status=IntegrityStatus(ingested.integrity_status),
                    reason=ingested.integrity_reason,
                    chain_verified=ingested.chain_verified,
                ),
                evidence_classification=evidence_classification,
                parser_id="syslog-001",
                parser_version="1.0.0",
                schema_version=_SCHEMA_VERSION,
                ocsf_event=ocsf,
                provenance=provenance,
                raw_log=line,
                parsed_dict=parsed_fields,
                validation=validation_detail,
            )
            _events.append(envelope)

            # Summary uses ingest_timestamp for display; fall back to OCSF time if available.
            display_timestamp = ingest_timestamp
            if ocsf and "time" in ocsf:
                display_timestamp = str(ocsf["time"])

            summary = EventSummary(
                event_id=event_id,
                timestamp=display_timestamp,
                source_format="syslog",
                status=status
            )
            _summaries.append(summary)

    except Exception as e:
        print(f"Error loading demo data: {e}")

load_demo_data()


def get_summary() -> DashboardSummary:
    total = len(_summaries)
    parse_success = sum(1 for s in _summaries if s.status != EventStatus.PARSE_FAILED)
    norm_success = sum(1 for s in _summaries if s.status == EventStatus.SUCCESS or s.status == EventStatus.VALIDATION_FAILED)
    val_success = sum(1 for s in _summaries if s.status == EventStatus.SUCCESS)

    return DashboardSummary(
        total_ingested=total,
        parse_successes=parse_success,
        normalization_successes=norm_success,
        validation_successes=val_success,
        active_parsers=_active_parsers
    )

def get_events(
    page: int = 1,
    page_size: int = 50,
    search: str = None,
    format: str = None,
    status: str = None,
    validation_status: str = None
) -> Dict[str, Any]:
    
    filtered = _summaries
    
    if format:
        filtered = [e for e in filtered if e.source_format == format]
    
    if status:
        filtered = [e for e in filtered if e.status == status]
        
    if validation_status:
        if validation_status == "passed":
            filtered = [e for e in filtered if e.status == EventStatus.SUCCESS]
        elif validation_status == "failed":
            filtered = [e for e in filtered if e.status == EventStatus.VALIDATION_FAILED]

    if search:
        search = search.lower()
        filtered = [e for e in filtered if search in e.event_id.lower() or search in e.source_format.lower()]

    start = (page - 1) * page_size
    end = start + page_size
    
    items = filtered[start:end]
    
    return {
        "items": items,
        "total": len(filtered),
        "page": page,
        "page_size": page_size
    }

def _find_envelope(event_id: str) -> Optional[ULPFEventEnvelope]:
    """Internal: find an envelope by event_id."""
    for e in _events:
        if e.event_id == event_id:
            return e
    return None

def get_event_detail(event_id: str) -> Optional[EventDetail]:
    """Project EventDetail from the stored envelope."""
    envelope = _find_envelope(event_id)
    return envelope.to_event_detail() if envelope else None

def get_event_raw(event_id: str) -> Optional[str]:
    envelope = _find_envelope(event_id)
    return envelope.raw_log if envelope else None

def get_event_parsed(event_id: str) -> Optional[Dict[str, Any]]:
    envelope = _find_envelope(event_id)
    return envelope.parsed_dict if envelope else None

def get_event_normalized(event_id: str) -> Optional[Dict[str, Any]]:
    envelope = _find_envelope(event_id)
    return envelope.ocsf_event if envelope else None

def get_event_validation(event_id: str) -> Optional[ValidationResultDetail]:
    envelope = _find_envelope(event_id)
    return envelope.validation if envelope else None

def get_event_envelope(event_id: str) -> Optional[ULPFEventEnvelope]:
    """Return the complete ULPF event contract envelope for audit/replay use."""
    return _find_envelope(event_id)
