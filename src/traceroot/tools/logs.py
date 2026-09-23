from pathlib import Path

from traceroot.data.loader import load_incident_dataset
from traceroot.data.models import LogEntry


def query_logs(
    incident_id: str,
    service: str | None = None,
    level: str | None = None,
    contains: str | None = None,
) -> list[LogEntry]:
    incident_dir = Path("data/incidents") / incident_id

    dataset = load_incident_dataset(incident_dir)
    logs = dataset.logs

    if service is not None:
        logs = [log for log in logs if log.service == service]

    if level is not None:
        logs = [log for log in logs if log.level == level]

    if contains is not None:
        logs = [log for log in logs if contains in log.message]

    return logs
