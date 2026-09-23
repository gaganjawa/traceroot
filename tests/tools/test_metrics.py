from traceroot.data.models import MetricEntry
from traceroot.tools.metrics import query_metrics


def test_query_metrics_returns_all_incident_metrics():
    metrics = query_metrics(incident_id="INC-001")
    assert len(metrics) > 0  # Ensure that some metrics are returned
    for metric in metrics:
        assert isinstance(
            metric, MetricEntry
        )  # Ensure each metric is a MetricEntry instance


def test_query_metrics_filters_by_service():
    service = "checkout-service"
    metrics = query_metrics(incident_id="INC-001", service=service)
    for metric in metrics:
        assert (
            metric.service == service
        )  # Ensure each metric is from the specified service


def test_query_metrics_filters_by_metric():
    metric = "response_time"
    metrics = query_metrics(incident_id="INC-001", metric=metric)
    for metric in metrics:
        assert metric.metric == metric  # Ensure each metric is the specified metric


def test_query_metrics_combines_filters_with_and_semantics():
    service = "checkout-service"
    metric = "response_time"
    metrics = query_metrics(
        incident_id="INC-001",
        service=service,
        metric=metric,
    )
    for metric in metrics:
        assert metric.service == service
        assert (
            metric.metric == metric
        )  # Ensure all filters are applied with AND semantics


def test_query_metrics_returns_empty_list_when_no_metrics_match():
    metrics = query_metrics(incident_id="INC-001", service="non-existent-service")
    assert len(metrics) == 0  # Ensure an empty list is returned when no metrics match


def test_query_metrics_returns_typed_metric_entries():
    metrics = query_metrics(
        incident_id="INC-001",
        service="checkout-service",
    )
    for metric in metrics:
        assert isinstance(
            metric, MetricEntry
        )  # Ensure each metric is a MetricEntry instance


def test_query_metrics_preserves_evidence_ids():
    metrics = query_metrics(incident_id="INC-001")

    metric_ids = {metric.id for metric in metrics}

    assert "METRIC-001-01" in metric_ids
    assert "METRIC-001-02" in metric_ids
    assert "METRIC-001-03" in metric_ids


def test_query_metrics_does_not_return_metrics_from_other_incidents():
    metrics_incident_1 = query_metrics(incident_id="INC-001")
    metrics_incident_2 = query_metrics(incident_id="INC-002")
    ids_incident_1 = {metric.id for metric in metrics_incident_1}
    ids_incident_2 = {metric.id for metric in metrics_incident_2}
    assert ids_incident_1.isdisjoint(
        ids_incident_2
    )  # Ensure no metrics from INC-001 are in INC-002
