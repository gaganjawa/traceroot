from datetime import UTC, datetime
from unittest.mock import Mock, patch

import httpx
import pytest

from traceroot.data.models import MetricEntry
from traceroot.domain.incident import Incident
from traceroot.integrations.live_metrics import PrometheusMetricsProvider


def make_incident() -> Incident:
    return Incident(
        id="INC-RUNTIME-001",
        title="Checkout failures",
        description="Checkout requests are failing.",
        start_time=datetime(2026, 9, 29, 12, 0, tzinfo=UTC),
        suspected_services=["checkout-service"],
    )


def prometheus_response() -> dict:
    return {
        "status": "success",
        "data": {
            "resultType": "matrix",
            "result": [
                {
                    "metric": {
                        "__name__": "request_duration",
                        "service": "checkout-service",
                    },
                    "values": [[1790683200.25, "0.125"], [1790683230, "0.25"]],
                }
            ],
        },
    }


def set_response(mock_get, payload=None):
    response = Mock()
    response.json.return_value = prometheus_response() if payload is None else payload
    mock_get.return_value = response
    return response


@patch("traceroot.integrations.live_metrics.httpx.get")
def test_live_metrics_provider_returns_metric_entries(mock_get):
    response = set_response(mock_get)
    result = PrometheusMetricsProvider("http://localhost:9090").query(make_incident())
    assert len(result) == 2
    assert all(isinstance(entry, MetricEntry) for entry in result)
    response.raise_for_status.assert_called_once_with()


@patch("traceroot.integrations.live_metrics.httpx.get")
def test_live_metrics_provider_uses_incident_start_time(mock_get):
    set_response(mock_get)
    provider = PrometheusMetricsProvider(
        "http://localhost:9090/",
        window_minutes=7,
        step_seconds=15,
        timeout_seconds=3.0,
    )
    provider.query(make_incident())
    mock_get.assert_called_once_with(
        "http://localhost:9090/api/v1/query_range",
        params={
            "query": "http_server_request_duration_seconds",
            "start": datetime(2026, 9, 29, 11, 53, tzinfo=UTC).timestamp(),
            "end": datetime(2026, 9, 29, 12, 7, tzinfo=UTC).timestamp(),
            "step": 15,
        },
        timeout=3.0,
    )


@pytest.mark.parametrize(
    "service, expected",
    [
        ("checkout-service", 'latency{service="checkout-service"}'),
        (None, "latency"),
        ('a"b\\c\nd', 'latency{service="a\\"b\\\\c\\nd"}'),
    ],
)
@patch("traceroot.integrations.live_metrics.httpx.get")
def test_live_metrics_provider_passes_service_filter(mock_get, service, expected):
    set_response(mock_get)
    PrometheusMetricsProvider("http://localhost:9090", metric_name="latency").query(
        make_incident(),
        service=service,
    )
    assert mock_get.call_args.kwargs["params"]["query"] == expected


@patch("traceroot.integrations.live_metrics.httpx.get")
def test_live_metrics_provider_maps_source_fields(mock_get):
    set_response(mock_get)
    result = PrometheusMetricsProvider("http://localhost:9090", unit="custom").query(
        make_incident()
    )
    assert result[0].timestamp == datetime(2026, 9, 29, 12, 0, 0, 250000, tzinfo=UTC)
    assert result[0].timestamp.tzinfo is UTC
    assert result[0].service == "checkout-service"
    assert result[0].metric == "request_duration"
    assert result[0].value == 0.125
    assert result[0].unit == "custom"
    assert result[1].value == 0.25


@pytest.mark.parametrize(
    "labels, requested, expected",
    [
        ({"service": "first", "service_name": "second"}, "requested", "first"),
        ({"service_name": "second"}, "requested", "second"),
        ({}, "requested", "requested"),
        ({}, None, "unknown"),
    ],
)
@patch("traceroot.integrations.live_metrics.httpx.get")
def test_live_metrics_provider_label_fallbacks(mock_get, labels, requested, expected):
    payload = prometheus_response()
    payload["data"]["result"][0]["metric"] = labels
    set_response(mock_get, payload)
    result = PrometheusMetricsProvider(
        "http://localhost:9090", metric_name="latency"
    ).query(
        make_incident(),
        service=requested,
    )
    assert result[0].service == expected
    assert result[0].metric == "latency"
    assert result[0].unit == "seconds"


@patch("traceroot.integrations.live_metrics.httpx.get")
def test_live_metrics_provider_generates_stable_evidence_ids(mock_get):
    payload = prometheus_response()
    first_series = payload["data"]["result"][0]
    payload["data"]["result"].append(
        {
            "metric": {**first_series["metric"], "instance": "another"},
            "values": first_series["values"],
        }
    )
    set_response(mock_get, payload)
    provider = PrometheusMetricsProvider("http://localhost:9090")
    first = provider.query(make_incident())
    first_series["metric"] = dict(reversed(list(first_series["metric"].items())))
    second = provider.query(make_incident())
    assert [entry.id for entry in first] == [entry.id for entry in second]
    assert all(entry.id.startswith("METRIC-LIVE-") for entry in first)
    assert len({entry.id for entry in first}) == 4


@patch("traceroot.integrations.live_metrics.httpx.get")
def test_live_metrics_provider_returns_empty_list_when_source_has_no_metrics(mock_get):
    set_response(mock_get, {"status": "success", "data": {"result": []}})
    assert (
        PrometheusMetricsProvider("http://localhost:9090").query(make_incident()) == []
    )


@patch("traceroot.integrations.live_metrics.httpx.get")
def test_live_metrics_provider_raises_for_http_failure(mock_get):
    response = set_response(mock_get)
    response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "HTTP failure",
        request=httpx.Request("GET", "http://localhost:9090"),
        response=httpx.Response(503),
    )
    with pytest.raises(httpx.HTTPStatusError, match="HTTP failure"):
        PrometheusMetricsProvider("http://localhost:9090").query(make_incident())
    response.json.assert_not_called()


@pytest.mark.parametrize("payload", [{"status": "error"}, {}])
@patch("traceroot.integrations.live_metrics.httpx.get")
def test_live_metrics_provider_rejects_failed_prometheus_response(mock_get, payload):
    set_response(mock_get, payload)
    with pytest.raises(RuntimeError, match="Prometheus query failed"):
        PrometheusMetricsProvider("http://localhost:9090").query(make_incident())
