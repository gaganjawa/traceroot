from pathlib import Path

from traceroot.data.loader import load_incident_dataset
from traceroot.data.models import CodeChangeEntry


def query_code_changes(
    incident_id: str,
    service: str | None = None,
) -> list[CodeChangeEntry]:
    incident_dir = Path("data/incidents") / incident_id

    dataset = load_incident_dataset(incident_dir)
    code_changes = dataset.changes

    if service is not None:
        code_changes = [entry for entry in code_changes if entry.service == service]

    return code_changes
