from datetime import UTC, datetime
from unittest.mock import Mock, patch

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
            ]
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
def test_live_logs_provider_returns_empty_list_when_source_has_no_logs(
    mock_get,
):
    response = Mock()
    response.json.return_value = {
        "status": "success",
        "data": {
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
    response.raise_for_status.side_effect = RuntimeError("HTTP failure")
    mock_get.return_value = response

    provider = LokiLogsProvider("http://localhost:3100")

    with pytest.raises(RuntimeError, match="HTTP failure"):
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
