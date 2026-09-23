from pathlib import Path

from traceroot.data.loader import load_incident_dataset
from traceroot.data.models import DeploymentEntry


def query_deployments(
    incident_id: str,
    service: str | None = None,
) -> list[DeploymentEntry]:

    incident_dir = Path("data/incidents") / incident_id

    dataset = load_incident_dataset(incident_dir)
    deployments = dataset.deployments

    if service is not None:
        deployments = [entry for entry in deployments if entry.service == service]

    return deployments
