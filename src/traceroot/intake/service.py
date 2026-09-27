from datetime import datetime
from uuid import uuid4

from traceroot.domain.incident import Incident


def create_incident(
    title: str,
    description: str,
    start_time: datetime,
    suspected_services: list[str] | None = None,
    incident_id: str | None = None,
) -> Incident:
    if not title.strip():
        raise ValueError("title is required")

    if not description.strip():
        raise ValueError("description is required")

    if start_time.tzinfo is None or start_time.utcoffset() is None:
        raise ValueError("start_time must be timezone-aware")

    if incident_id is not None and not incident_id.strip():
        raise ValueError("incident_id cannot be blank")

    services = suspected_services or []

    if any(not service.strip() for service in services):
        raise ValueError("suspected_services cannot contain blank values")

    resolved_incident_id = (
        incident_id.strip()
        if incident_id is not None
        else f"INC-RUNTIME-{uuid4().hex[:8].upper()}"
    )

    return Incident(
        id=resolved_incident_id,
        title=title.strip(),
        description=description.strip(),
        start_time=start_time,
        suspected_services=services,
    )
