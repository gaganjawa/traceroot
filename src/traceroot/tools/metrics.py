from pathlib import Path

from traceroot.data.loader import load_incident_dataset
from traceroot.data.models import MetricEntry


def query_metrics(
    incident_id: str,
    service: str | None = None,
    metric: str | None = None,
) -> list[MetricEntry]:
    incident_dir = Path("data/incidents") / incident_id

    dataset = load_incident_dataset(incident_dir)
    metrics = dataset.metrics

    if service is not None:
        metrics = [entry for entry in metrics if entry.service == service]

    if metric is not None:
        metrics = [entry for entry in metrics if entry.metric == metric]

    return metrics
