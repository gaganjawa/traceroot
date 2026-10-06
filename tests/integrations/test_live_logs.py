from datetime import UTC, datetime
from unittest.mock import Mock, patch

import httpx
import pytest

from traceroot.data.models import LogEntry
from traceroot.domain.incident import Incident
from traceroot.integrations.live_logs import LokiLogsProvider


def make_incident() -> Incident:
    return Incident(
        id="INC-RUNTIME-001",
        title="Checkout failures",
        description="Checkout requests are failing.",
        start_time=datetime(2026, 9, 29, 12, 0, tzinfo=UTC),
        suspected_services=["checkout-service"],
    )


def loki_response() -> dict:
    return {
        "status": "success",
        "data": {
            "resultType": "streams",
            "result": [
                {
                    "stream": {
                        "service_name": "checkout-service",
                        "level": "ERROR",
                    },
                    "values": [
                        [
                            "1790683200000000000",
                            "payment authorization failed",
                        ]
                    ],
                }
            ],
        },
    }


@patch("traceroot.integrations.live_logs.httpx.get")
def test_live_logs_provider_returns_log_entries(mock_get):
    response = Mock()
    response.json.return_value = loki_response()
    mock_get.return_value = response

    provider = LokiLogsProvider("http://localhost:3100")

    result = provider.query(
        incident=make_incident(),
        service="checkout-service",
    )

    assert len(result) == 1
    assert isinstance(result[0], LogEntry)


@patch("traceroot.integrations.live_logs.httpx.get")
def test_live_logs_provider_uses_incident_start_time(mock_get):
    response = Mock()
    response.json.return_value = loki_response()
    mock_get.return_value = response

    incident = make_incident()

    provider = LokiLogsProvider(
        "http://localhost:3100",
        window_minutes=15,
    )

    provider.query(
        incident=incident,
        service="checkout-service",
    )

    _, kwargs = mock_get.call_args
    params = kwargs["params"]

    expected_start = int(
        datetime(2026, 9, 29, 11, 45, tzinfo=UTC).timestamp() * 1_000_000_000
    )
    expected_end = int(
        datetime(2026, 9, 29, 12, 15, tzinfo=UTC).timestamp() * 1_000_000_000
    )

    assert params["start"] == str(expected_start)
    assert params["end"] == str(expected_end)


@patch("traceroot.integrations.live_logs.httpx.get")
def test_live_logs_provider_passes_service_filter(mock_get):
    response = Mock()
    response.json.return_value = loki_response()
    mock_get.return_value = response

    provider = LokiLogsProvider("http://localhost:3100")

    provider.query(
        incident=make_incident(),
        service="checkout-service",
    )

    _, kwargs = mock_get.call_args

    assert kwargs["params"]["query"] == ('{service_name="checkout-service"}')


@patch("traceroot.integrations.live_logs.httpx.get")
def test_live_logs_provider_maps_source_fields(mock_get):
    response = Mock()
    response.json.return_value = loki_response()
    mock_get.return_value = response

    provider = LokiLogsProvider("http://localhost:3100")

    result = provider.query(
        incident=make_incident(),
        service="checkout-service",
    )

    log = result[0]

    assert log.service == "checkout-service"
    assert log.level == "ERROR"
    assert log.message == "payment authorization failed"
    assert log.timestamp.tzinfo is not None


@patch("traceroot.integrations.live_logs.httpx.get")
def test_live_logs_provider_generates_stable_evidence_ids(mock_get):
    response = Mock()
    response.json.return_value = loki_response()
    mock_get.return_value = response

    provider = LokiLogsProvider("http://localhost:3100")

    first = provider.query(
        incident=make_incident(),
        service="checkout-service",
    )
    second = provider.query(
        incident=make_incident(),
        service="checkout-service",
    )

    assert first[0].id == second[0].id
    assert first[0].id.startswith("LOG-LIVE-")


@patch("traceroot.integrations.live_logs.httpx.get")
def test_live_logs_provider_returns_empty_list_for_valid_empty_result(
    mock_get,
):
    response = Mock()
    response.json.return_value = {
        "status": "success",
        "data": {
            "resultType": "streams",
            "result": [],
        },
    }
    mock_get.return_value = response

    provider = LokiLogsProvider("http://localhost:3100")

    result = provider.query(
        incident=make_incident(),
        service="checkout-service",
    )

    assert result == []


@patch("traceroot.integrations.live_logs.httpx.get")
def test_live_logs_provider_raises_for_http_failure(mock_get):
    response = Mock()
    response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "HTTP failure",
        request=httpx.Request("GET", "http://localhost:3100"),
        response=httpx.Response(503),
    )
    mock_get.return_value = response

    provider = LokiLogsProvider("http://localhost:3100")

    with pytest.raises(httpx.HTTPStatusError, match="HTTP failure"):
        provider.query(
            incident=make_incident(),
            service="checkout-service",
        )


@patch("traceroot.integrations.live_logs.httpx.get")
def test_live_logs_provider_rejects_failed_loki_response(mock_get):
    response = Mock()
    response.json.return_value = {
        "status": "error",
    }
    mock_get.return_value = response

    provider = LokiLogsProvider("http://localhost:3100")

    with pytest.raises(RuntimeError, match="Loki query failed"):
        provider.query(
            incident=make_incident(),
            service="checkout-service",
        )


def test_build_query_without_service_uses_non_empty_matcher():
    provider = LokiLogsProvider(base_url="http://localhost:3100")

    query = provider._build_query(None)

    assert query == '{service_name=~".+"}'


def test_build_query_with_service_uses_exact_service_matcher():
    provider = LokiLogsProvider(base_url="http://localhost:3100")

    query = provider._build_query("checkout-service")

    assert query == '{service_name="checkout-service"}'


@patch("traceroot.integrations.live_logs.httpx.get")
def test_query_without_service_uses_non_empty_loki_matcher(mock_get):
    mock_response = Mock()
    mock_response.json.return_value = {
        "status": "success",
        "data": {
            "resultType": "streams",
            "result": [],
        },
    }
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    incident = Incident(
        id="INC-TEST",
        title="Test incident",
        description="Test incident description",
        start_time=datetime(2026, 10, 3, 12, 0, tzinfo=UTC),
        suspected_services=[],
    )

    provider = LokiLogsProvider(
        base_url="http://localhost:3100",
    )

    provider.query(
        incident=incident,
        service=None,
    )

    _, kwargs = mock_get.call_args

    assert kwargs["params"]["query"] == '{service_name=~".+"}'


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
        {"status": "success", "data": {"resultType": "streams"}},
        *[
            {"status": "success", "data": {"resultType": "streams", "result": result}}
            for result in [None, {}, "", ()]
        ],
    ],
)
@patch("traceroot.integrations.live_logs.httpx.get")
def test_live_logs_provider_rejects_malformed_success_payload(mock_get, payload):
    mock_get.return_value.json.return_value = payload
    with pytest.raises(ValueError, match="Invalid Loki response"):
        LokiLogsProvider("http://localhost").query(make_incident())


@pytest.mark.parametrize("result_type", [None, "vector", "scalar", "string", "matrix"])
@patch("traceroot.integrations.live_logs.httpx.get")
def test_live_logs_provider_rejects_unsupported_result_type(mock_get, result_type):
    payload = loki_response()
    payload["data"]["resultType"] = result_type
    payload["data"]["result"] = []
    mock_get.return_value.json.return_value = payload
    with pytest.raises(ValueError, match="data.resultType"):
        LokiLogsProvider("http://localhost").query(make_incident())


@pytest.mark.parametrize("error_type", [httpx.ConnectError, httpx.ReadTimeout])
@patch("traceroot.integrations.live_logs.httpx.get")
def test_live_logs_provider_propagates_transport_errors(mock_get, error_type):
    error = error_type("transport failure")
    mock_get.side_effect = error
    with pytest.raises(error_type) as caught:
        LokiLogsProvider("http://localhost").query(make_incident())
    assert caught.value is error


@patch("traceroot.integrations.live_logs.httpx.get")
def test_live_logs_provider_propagates_invalid_json(mock_get):
    from json import JSONDecodeError

    error = JSONDecodeError("Invalid JSON", "", 0)
    mock_get.return_value.json.side_effect = error
    with pytest.raises(JSONDecodeError) as caught:
        LokiLogsProvider("http://localhost").query(make_incident())
    assert caught.value is error


@patch("traceroot.integrations.live_logs.httpx.get")
def test_live_logs_provider_accepts_extra_fields_and_empty_values(mock_get):
    payload = loki_response()
    payload["extra"] = {"anything": True}
    payload["data"]["stats"] = {}
    payload["data"]["result"][0]["extra"] = True
    payload["data"]["result"][0]["values"] = []
    mock_get.return_value.json.return_value = payload
    assert LokiLogsProvider("http://localhost").query(make_incident()) == []


@pytest.mark.parametrize(
    "stream",
    [
        None,
        [],
        "stream",
        {},
        {"values": []},
        *[
            {"stream": labels, "values": []}
            for labels in [None, [], {"level": 1}, {1: "x"}]
        ],
        {"stream": {}},
        *[{"stream": {}, "values": values} for values in [None, {}, "", ()]],
    ],
)
@patch("traceroot.integrations.live_logs.httpx.get")
def test_live_logs_provider_fails_query_for_malformed_stream(mock_get, stream):
    payload = loki_response()
    payload["data"]["result"].append(stream)
    mock_get.return_value.json.return_value = payload
    with pytest.raises(ValueError, match=r"data\.result\[1\]"):
        LokiLogsProvider("http://localhost").query(make_incident())


@pytest.mark.parametrize(
    "sample",
    [
        None,
        {},
        "12",
        [],
        ["1"],
        ["1", "message", {}],
        *[
            [stamp, "message"]
            for stamp in [
                None,
                True,
                1,
                1.5,
                "",
                "1.5",
                "1e9",
                " 1",
                "1_000",
                "NaN",
                "9" * 400,
            ]
        ],
        *[["1790683200000000000", message] for message in [None, 1, {}, []]],
    ],
)
@patch("traceroot.integrations.live_logs.httpx.get")
def test_live_logs_provider_fails_query_for_malformed_sample(mock_get, sample):
    payload = loki_response()
    payload["data"]["result"][0]["values"].append(sample)
    mock_get.return_value.json.return_value = payload
    with pytest.raises(ValueError, match=r"data\.result\[0\]\.values\[1\]"):
        LokiLogsProvider("http://localhost").query(make_incident())


@pytest.mark.parametrize(
    "service, expected",
    [
        ('a"b', '{service_name="a\\"b"}'),
        ("a\\b", '{service_name="a\\\\b"}'),
        ("a\nb", '{service_name="a\\nb"}'),
        ('x",level="ERROR', '{service_name="x\\",level=\\"ERROR"}'),
        ("café", '{service_name="café"}'),
    ],
)
def test_build_query_escapes_service_literal(service, expected):
    assert LokiLogsProvider("http://localhost")._build_query(service) == expected


def test_build_query_preserves_braces_and_regex_metacharacters():
    service = "{checkout}.*+?^$()[]|"
    assert LokiLogsProvider("http://localhost")._build_query(service) == (
        '{service_name="{checkout}.*+?^$()[]|"}'
    )


@patch("traceroot.integrations.live_logs.httpx.get")
def test_live_logs_provider_accepts_tuple_sample_and_empty_labels(mock_get):
    payload = loki_response()
    payload["data"]["result"] = [{"stream": {}, "values": [("0", "")]}]
    mock_get.return_value.json.return_value = payload
    result = LokiLogsProvider("http://localhost").query(make_incident())
    assert result[0].message == ""
    assert result[0].service == "unknown"
    assert result[0].level == "unknown"
    assert result[0].timestamp == datetime(1970, 1, 1, tzinfo=UTC)


@patch("traceroot.integrations.live_logs.httpx.get")
def test_live_logs_provider_preserves_stream_labels(mock_get):
    payload = loki_response()
    labels = {
        "service_name": "checkout-service",
        "level": "ERROR",
        "instance": "a",
        "namespace": "production",
        "pod": "checkout-123",
        "job": "checkout",
        "container": "app",
        "custom": 'café "quoted" \\path\nnext',
        "empty": "",
    }
    payload["data"]["result"][0]["stream"] = labels
    mock_get.return_value.json.return_value = payload
    log = LokiLogsProvider("http://localhost").query(make_incident())[0]
    assert log.labels == labels
    assert list(log.labels) == sorted(labels)
    assert log.service == "checkout-service"
    assert log.level == "ERROR"
    assert log.labels is not labels
    log.labels["instance"] = "changed"
    assert labels["instance"] == "a"


@patch("traceroot.integrations.live_logs.httpx.get")
def test_live_logs_provider_distinguishes_streams_with_identical_samples(mock_get):
    payload = loki_response()
    first = payload["data"]["result"][0]
    first["stream"]["instance"] = "a"
    payload["data"]["result"].append(
        {"stream": {**first["stream"], "instance": "b"}, "values": first["values"]}
    )
    mock_get.return_value.json.return_value = payload
    logs = LokiLogsProvider("http://localhost").query(make_incident())
    assert logs[0].timestamp == logs[1].timestamp
    assert logs[0].message == logs[1].message
    assert logs[0].service == logs[1].service
    assert logs[0].id != logs[1].id
    assert all(log.id.startswith("LOG-LIVE-") and len(log.id) == 21 for log in logs)


@patch("traceroot.integrations.live_logs.httpx.get")
def test_live_logs_provider_ids_ignore_label_order(mock_get):
    payload = loki_response()
    stream = payload["data"]["result"][0]
    mock_get.return_value.json.return_value = payload
    provider = LokiLogsProvider("http://localhost")
    first = provider.query(make_incident())[0]
    stream["stream"] = dict(reversed(list(stream["stream"].items())))
    second = provider.query(make_incident())[0]
    assert first.id == second.id
    assert str(first) == str(second)


@patch("traceroot.integrations.live_logs.httpx.get")
def test_live_logs_provider_ids_ignore_requested_service_fallback(mock_get):
    payload = loki_response()
    payload["data"]["result"][0]["stream"] = {"instance": "a"}
    mock_get.return_value.json.return_value = payload
    provider = LokiLogsProvider("http://localhost")
    logs = [
        provider.query(make_incident(), service=service)[0]
        for service in [None, "a", "b"]
    ]
    assert [log.service for log in logs] == ["unknown", "a", "b"]
    assert len({log.id for log in logs}) == 1
    assert all(log.labels == {"instance": "a"} for log in logs)


@pytest.mark.parametrize(
    "second_timestamp", ["1790683200000000001", "+1790683200000000000"]
)
@patch("traceroot.integrations.live_logs.httpx.get")
def test_live_logs_provider_ids_preserve_exact_raw_timestamp(
    mock_get, second_timestamp
):
    payload = loki_response()
    samples = payload["data"]["result"][0]["values"]
    samples.append([second_timestamp, samples[0][1]])
    mock_get.return_value.json.return_value = payload
    logs = LokiLogsProvider("http://localhost").query(make_incident())
    assert logs[0].timestamp == logs[1].timestamp
    assert logs[0].id != logs[1].id
    assert "timestamp_ns" not in logs[0].model_dump()
