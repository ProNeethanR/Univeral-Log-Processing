"""In-memory quarantine store for pipeline failure records.

FailureRecord never carries raw log content: only references (locator/hash),
categorical metadata, and the failure reason are retained so operators can
trace rejected events back to vaulted evidence without duplicating payloads.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from src.api.models import (
    FailureCategory,
    FailureRecord,
    PaginatedFailures,
    RawRef,
)

_failures: List[FailureRecord] = []


def integrity_failure_category(status: str) -> Optional[FailureCategory]:
    """Map a non-verified integrity status to its quarantine category."""
    if status == "verified":
        return None
    try:
        return FailureCategory(f"integrity_{status}")
    except ValueError:
        return None


def record_failure(
    *,
    category: FailureCategory,
    reason: str,
    source_id: Optional[str] = None,
    source_context: Optional[Dict[str, Any]] = None,
    raw_ref: Optional[Any] = None,
    raw_hash: Optional[str] = None,
    event_id: Optional[str] = None,
) -> FailureRecord:
    if not isinstance(category, FailureCategory):
        category = FailureCategory(category)
    if not reason:
        raise ValueError("Failure reason must not be empty")

    if raw_ref is not None and not isinstance(raw_ref, RawRef):
        raw_ref = RawRef(**raw_ref)
    if raw_hash is None and raw_ref is not None:
        raw_hash = raw_ref.raw_hash

    record = FailureRecord(
        failure_id=uuid.uuid4().hex,
        category=category,
        reason=reason,
        timestamp=datetime.now(timezone.utc).isoformat(),
        raw_ref=raw_ref,
        raw_hash=raw_hash,
        source_id=source_id,
        source_context=source_context,
        event_id=event_id,
    )
    _failures.append(record)
    return record


def get_failures(
    page: int = 1,
    page_size: int = 50,
    category: Optional[str] = None,
    event_id: Optional[str] = None,
) -> PaginatedFailures:
    filtered = _failures
    if category:
        filtered = [f for f in filtered if f.category.value == category]
    if event_id:
        filtered = [f for f in filtered if f.event_id == event_id]

    start = (page - 1) * page_size
    end = start + page_size
    return PaginatedFailures(
        items=filtered[start:end],
        total=len(filtered),
        page=page,
        page_size=page_size,
    )


def clear_failures() -> None:
    _failures.clear()
