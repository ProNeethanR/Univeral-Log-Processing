import os
import json
import uuid
import hashlib
from typing import List, Dict, Any, Optional

from src.api.models import EventSummary, EventDetail, EventStatus, DashboardSummary, ValidationResultDetail

# In-memory storage for events
_events: List[EventDetail] = []
_summaries: List[EventSummary] = []
_active_parsers = 0

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
    import datetime

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

            event_id = f"demo-event-{i+1}-{uuid.uuid4().hex[:8]}"
            
            try:
                parsed_fields = engine.parse(line)
                status = EventStatus.SUCCESS
            except Exception as e:
                parsed_fields = None
                status = EventStatus.PARSE_FAILED

            ocsf = None
            validation_detail = ValidationResultDetail(status="UNAVAILABLE", errors=[], warnings=[])
            
            if parsed_fields:
                try:
                    ocsf = mapper.map_syslog(parsed_fields)
                    if 'unmapped' in ocsf and 'tracing' in ocsf['unmapped']:
                        ocsf['unmapped']['tracing'] = sorted(ocsf['unmapped']['tracing'], key=lambda x: x['source_field'])
                    
                    # Validate OCSF
                    val_res = validate_ocsf_event(ocsf)
                    if val_res.is_valid:
                        validation_detail = ValidationResultDetail(status="PASS", errors=[], warnings=[])
                        status = EventStatus.SUCCESS
                    else:
                        validation_detail = ValidationResultDetail(
                            status="FAIL",
                            errors=[e.to_dict() for e in val_res.errors],
                            warnings=[]
                        )
                        status = EventStatus.VALIDATION_FAILED
                except Exception as e:
                    status = EventStatus.NORM_FAILED
                    validation_detail = None

            # Determine timestamp
            timestamp = datetime.datetime.utcnow().isoformat() + "Z"
            if ocsf and "time" in ocsf:
                timestamp = str(ocsf["time"])

            detail = EventDetail(
                event_id=event_id,
                raw_log=line,
                parsed_dict=parsed_fields,
                ocsf_event=ocsf,
                validation=validation_detail
            )
            _events.append(detail)

            summary = EventSummary(
                event_id=event_id,
                timestamp=timestamp,
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

def get_event_detail(event_id: str) -> Optional[EventDetail]:
    for e in _events:
        if e.event_id == event_id:
            return e
    return None

def get_event_raw(event_id: str) -> Optional[str]:
    detail = get_event_detail(event_id)
    return detail.raw_log if detail else None

def get_event_parsed(event_id: str) -> Optional[Dict[str, Any]]:
    detail = get_event_detail(event_id)
    return detail.parsed_dict if detail else None

def get_event_normalized(event_id: str) -> Optional[Dict[str, Any]]:
    detail = get_event_detail(event_id)
    return detail.ocsf_event if detail else None

def get_event_validation(event_id: str) -> Optional[ValidationResultDetail]:
    detail = get_event_detail(event_id)
    return detail.validation if detail else None
