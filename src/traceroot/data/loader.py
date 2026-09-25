import json
from pathlib import Path

from traceroot.data.models import (
    CodeChangeEntry,
    DeploymentEntry,
    IncidentDataset,
    LogEntry,
    MetricEntry,
)
from traceroot.domain.incident import Incident


def load_incident(path: Path) -> Incident:
    """
    Load an incident from a JSON file.

    Args:
        path (Path): The path to the JSON file containing the incident data.

    Returns:
        Incident: The loaded incident.
    """
    with open(path, "r") as f:
        data = json.load(f)
    return Incident(**data)


def load_incident_dataset(incident_dir: Path) -> IncidentDataset:
    # Implementation for loading incident dataset from directory
    incident_file = incident_dir / "incident.json"
    logs_file = incident_dir / "logs.jsonl"
    metrics_file = incident_dir / "metrics.json"
    deployments_file = incident_dir / "deployments.json"
    changes_file = incident_dir / "changes.json"

    incident = load_incident(incident_file)
    with open(logs_file, "r") as logs_handle:
        logs = [LogEntry(**json.loads(line)) for line in logs_handle]

    with open(metrics_file, "r") as metrics_handle:
        metrics = [MetricEntry(**data) for data in json.load(metrics_handle)]

    with open(deployments_file, "r") as deployments_handle:
        deployments = [
            DeploymentEntry(**data) for data in json.load(deployments_handle)
        ]

    with open(changes_file, "r") as changes_handle:
        changes = [CodeChangeEntry(**data) for data in json.load(changes_handle)]

    return IncidentDataset(
        incident=incident,
        logs=logs,
        metrics=metrics,
        deployments=deployments,
        changes=changes,
    )
