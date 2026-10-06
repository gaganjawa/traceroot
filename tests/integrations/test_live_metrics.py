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
def test_live_metrics_provider_returns_empty_list_for_valid_empty_result(mock_get):
    set_response(
        mock_get, {"status": "success", "data": {"resultType": "matrix", "result": []}}
    )
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


@pytest.mark.parametrize("payload", [{"status": "error"}])
@patch("traceroot.integrations.live_metrics.httpx.get")
def test_live_metrics_provider_rejects_failed_prometheus_response(mock_get, payload):
    set_response(mock_get, payload)
    with pytest.raises(RuntimeError, match="Prometheus query failed"):
        PrometheusMetricsProvider("http://localhost:9090").query(make_incident())


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        "success",
        {},
        {"status": None},
        {"status": "unknown"},
        {"status": "success"},
        *[{"status": "success", "data": data} for data in [None, [], "data", {}]],
        {"status": "success", "data": {"resultType": "matrix"}},
        *[
            {"status": "success", "data": {"resultType": "matrix", "result": result}}
            for result in [None, {}, "", ()]
        ],
    ],
)
@patch("traceroot.integrations.live_metrics.httpx.get")
def test_live_metrics_provider_rejects_malformed_success_payload(mock_get, payload):
    mock_get.return_value.json.return_value = payload
    with pytest.raises(ValueError, match="Invalid Prometheus response"):
        PrometheusMetricsProvider("http://localhost").query(make_incident())


@pytest.mark.parametrize("result_type", [None, "vector", "scalar", "string", "streams"])
@patch("traceroot.integrations.live_metrics.httpx.get")
def test_live_metrics_provider_rejects_unsupported_result_type(mock_get, result_type):
    payload = prometheus_response()
    payload["data"]["resultType"] = result_type
    payload["data"]["result"] = []
    mock_get.return_value.json.return_value = payload
    with pytest.raises(ValueError, match="data.resultType"):
        PrometheusMetricsProvider("http://localhost").query(make_incident())


@pytest.mark.parametrize("error_type", [httpx.ConnectError, httpx.ReadTimeout])
@patch("traceroot.integrations.live_metrics.httpx.get")
def test_live_metrics_provider_propagates_transport_errors(mock_get, error_type):
    error = error_type("transport failure")
    mock_get.side_effect = error
    with pytest.raises(error_type) as caught:
        PrometheusMetricsProvider("http://localhost").query(make_incident())
    assert caught.value is error


@patch("traceroot.integrations.live_metrics.httpx.get")
def test_live_metrics_provider_propagates_invalid_json(mock_get):
    from json import JSONDecodeError

    error = JSONDecodeError("Invalid JSON", "", 0)
    mock_get.return_value.json.side_effect = error
    with pytest.raises(JSONDecodeError) as caught:
        PrometheusMetricsProvider("http://localhost").query(make_incident())
    assert caught.value is error


@patch("traceroot.integrations.live_metrics.httpx.get")
def test_live_metrics_provider_accepts_extra_fields_and_empty_values(mock_get):
    payload = prometheus_response()
    payload["extra"] = {"anything": True}
    payload["data"]["stats"] = {}
    payload["data"]["result"][0]["extra"] = True
    payload["data"]["result"][0]["values"] = []
    mock_get.return_value.json.return_value = payload
    assert PrometheusMetricsProvider("http://localhost").query(make_incident()) == []


@pytest.mark.parametrize(
    "series",
    [
        None,
        [],
        "series",
        {},
        {"values": []},
        *[
            {"metric": labels, "values": []}
            for labels in [None, [], {"service": 1}, {1: "x"}]
        ],
        {"metric": {}},
        *[{"metric": {}, "values": values} for values in [None, {}, "", ()]],
        {"metric": {}, "histograms": []},
        {"metric": {}, "values": [], "histograms": [[0, {}]]},
        {"metric": {}, "value": [0, "1"]},
    ],
)
@patch("traceroot.integrations.live_metrics.httpx.get")
def test_live_metrics_provider_fails_query_for_malformed_series(mock_get, series):
    payload = prometheus_response()
    payload["data"]["result"].append(series)
    set_response(mock_get, payload)
    with pytest.raises(ValueError, match=r"data\.result\[1\]"):
        PrometheusMetricsProvider("http://localhost").query(make_incident())


@pytest.mark.parametrize("sample", [None, {}, "12", [], [0], [0, "1", {}]])
@patch("traceroot.integrations.live_metrics.httpx.get")
def test_live_metrics_provider_fails_query_for_malformed_sample(mock_get, sample):
    payload = prometheus_response()
    payload["data"]["result"][0]["values"].append(sample)
    set_response(mock_get, payload)
    with pytest.raises(ValueError, match=r"data\.result\[0\]\.values\[2\]"):
        PrometheusMetricsProvider("http://localhost").query(make_incident())


@pytest.mark.parametrize("value", [None, True, False, {}, [], "", "invalid"])
@patch("traceroot.integrations.live_metrics.httpx.get")
def test_live_metrics_provider_rejects_non_numeric_sample_values(mock_get, value):
    payload = prometheus_response()
    payload["data"]["result"][0]["values"].append([1790683200, value])
    set_response(mock_get, payload)
    with pytest.raises(
        ValueError, match=r"values\[2\]\[1\] must be numeric and finite"
    ):
        PrometheusMetricsProvider("http://localhost").query(make_incident())


@pytest.mark.parametrize(
    "value",
    [
        "NaN",
        "+Inf",
        "-Inf",
        float("nan"),
        float("inf"),
        -float("inf"),
        "1e999",
        10**400,
    ],
)
@patch("traceroot.integrations.live_metrics.httpx.get")
def test_live_metrics_provider_rejects_non_finite_sample_values(mock_get, value):
    payload = prometheus_response()
    payload["data"]["result"][0]["values"].append([1790683200, value])
    set_response(mock_get, payload)
    with pytest.raises(
        ValueError, match=r"values\[2\]\[1\] must be numeric and finite"
    ):
        PrometheusMetricsProvider("http://localhost").query(make_incident())


@pytest.mark.parametrize(
    "timestamp",
    [
        None,
        True,
        False,
        {},
        [],
        "1790683200",
        "bad",
        float("nan"),
        float("inf"),
        -float("inf"),
        1e100,
        10**400,
    ],
)
@patch("traceroot.integrations.live_metrics.httpx.get")
def test_live_metrics_provider_rejects_invalid_sample_timestamps(mock_get, timestamp):
    payload = prometheus_response()
    payload["data"]["result"][0]["values"].append([timestamp, "1"])
    set_response(mock_get, payload)
    with pytest.raises(ValueError, match=r"values\[2\]\[0\]"):
        PrometheusMetricsProvider("http://localhost").query(make_incident())


@pytest.mark.parametrize("value", [0, -1, 0.125, "0.125", "1e-3"])
@patch("traceroot.integrations.live_metrics.httpx.get")
def test_live_metrics_provider_accepts_finite_numeric_values(mock_get, value):
    payload = prometheus_response()
    payload["data"]["result"][0]["values"] = [(1790683200.25, value)]
    set_response(mock_get, payload)
    result = PrometheusMetricsProvider("http://localhost").query(make_incident())
    assert result[0].value == float(value)


@patch("traceroot.integrations.live_metrics.httpx.get")
def test_live_metrics_provider_preserves_complete_labels(mock_get):
    payload = prometheus_response()
    labels = {
        "__name__": "request_duration",
        "service": "checkout-service",
        "route": "/checkout",
        "status": "500",
        "method": "POST",
        "instance": "a",
        "quantile": "0.95",
        "le": "+Inf",
        "custom": 'café "quoted" \\path\nnext',
        "empty": "",
    }
    payload["data"]["result"][0]["metric"] = labels
    set_response(mock_get, payload)
    metrics = PrometheusMetricsProvider("http://localhost").query(make_incident())
    assert all(metric.labels == labels for metric in metrics)
    assert list(metrics[0].labels) == sorted(labels)
    metrics[0].labels["instance"] = "changed"
    assert metrics[1].labels["instance"] == labels["instance"] == "a"


@pytest.mark.parametrize("labels", [{}, {"instance": "a"}])
@pytest.mark.parametrize("service", [None, "requested"])
@patch("traceroot.integrations.live_metrics.httpx.get")
def test_live_metrics_provider_allows_empty_labels_and_missing_metric_name(
    mock_get, labels, service
):
    payload = prometheus_response()
    payload["data"]["result"][0]["metric"] = labels
    set_response(mock_get, payload)
    metrics = PrometheusMetricsProvider(
        "http://localhost", metric_name="latency"
    ).query(make_incident(), service=service)
    assert all(metric.labels == labels for metric in metrics)
    assert all(metric.service == (service or "unknown") for metric in metrics)
    assert all(metric.metric == "latency" for metric in metrics)
    assert all(
        not ({"service", "service_name", "__name__"} & metric.labels.keys())
        for metric in metrics
    )


@patch("traceroot.integrations.live_metrics.httpx.get")
def test_live_metrics_provider_distinguishes_series_with_different_labels(mock_get):
    payload = prometheus_response()
    first = payload["data"]["result"][0]
    first["metric"]["route"] = "/checkout"
    payload["data"]["result"].append(
        {"metric": {**first["metric"], "route": "/cart"}, "values": first["values"]}
    )
    set_response(mock_get, payload)
    metrics = PrometheusMetricsProvider("http://localhost").query(make_incident())
    assert metrics[0].timestamp == metrics[2].timestamp
    assert metrics[0].value == metrics[2].value
    assert metrics[0].metric == metrics[2].metric
    assert len({metric.id for metric in metrics}) == 4


@patch("traceroot.integrations.live_metrics.httpx.get")
def test_live_metrics_provider_preserves_existing_finite_sample_ids(mock_get):
    payload = prometheus_response()
    set_response(mock_get, payload)
    provider = PrometheusMetricsProvider("http://localhost")
    first = provider.query(make_incident())
    # Captured from the Pass 1 provider before adding labels to evidence.
    expected = ["METRIC-LIVE-479E43902C7D", "METRIC-LIVE-6B478B2573FC"]
    assert [metric.id for metric in first] == expected
    series = payload["data"]["result"][0]
    series["metric"] = dict(reversed(list(series["metric"].items())))
    second = provider.query(make_incident())
    assert [metric.id for metric in second] == expected
    assert [str(metric) for metric in first] == [str(metric) for metric in second]
