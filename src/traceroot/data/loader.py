import json

from pathlib import Path

from traceroot.data.models import IncidentDataset, LogEntry, MetricEntry, DeploymentEntry, CodeChangeEntry
from traceroot.domain.incident import Incident


def load_incident(path: Path) -> Incident:
    """
    Load an incident from a JSON file.

    Args:
        path (Path): The path to the JSON file containing the incident data.

    Returns:
        Incident: The loaded incident.
    """
    # Implementation for loading incident from JSON file
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
    logs = [LogEntry(**json.loads(line)) for line in open(logs_file, "r")]
    metrics = [MetricEntry(**data) for data in json.load(open(metrics_file, "r"))]
    deployments = [DeploymentEntry(**data) for data in json.load(open(deployments_file, "r"))]
    changes = [CodeChangeEntry(**data) for data in json.load(open(changes_file, "r"))]

    return IncidentDataset(incident=incident, logs=logs, metrics=metrics, deployments=deployments, changes=changes)