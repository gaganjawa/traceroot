from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

import httpx
import pytest

from traceroot.data.models import DeploymentEntry
from traceroot.domain.incident import Incident
from traceroot.integrations.live_deployments import GitHubDeploymentsProvider


def make_incident() -> Incident:
    return Incident(
        id="INC-RUNTIME-001",
        title="Checkout failures",
        description="Checkout requests are failing.",
        start_time=datetime(2026, 9, 29, 12, 0, tzinfo=UTC),
        suspected_services=["checkout-service"],
    )


def make_release(**overrides) -> dict:
    return {
        "id": 123,
        "tag_name": "v1.2.3",
        "published_at": "2026-09-29T12:00:00Z",
        "created_at": "2026-09-29T11:30:00Z",
        "name": "Checkout fix",
        "body": "Release notes",
        **overrides,
    }


def make_provider(**kwargs) -> GitHubDeploymentsProvider:
    return GitHubDeploymentsProvider("example/checkout", "checkout-service", **kwargs)


def set_response(mock_get, payload):
    response = Mock()
    response.json.return_value = payload
    mock_get.return_value = response
    return response


@patch("traceroot.integrations.live_deployments.httpx.get")
def test_live_deployments_provider_returns_deployment_entries(mock_get):
    response = set_response(mock_get, [make_release()])
    result = make_provider().query(make_incident())
    assert len(result) == 1
    assert isinstance(result[0], DeploymentEntry)
    response.raise_for_status.assert_called_once_with()


@pytest.mark.parametrize("window_minutes", [60, 15])
@patch("traceroot.integrations.live_deployments.httpx.get")
def test_live_deployments_provider_uses_incident_time_window(mock_get, window_minutes):
    incident = make_incident()
    start = incident.start_time - timedelta(minutes=window_minutes)
    end = incident.start_time + timedelta(minutes=window_minutes)
    timestamps = [
        start - timedelta(seconds=1),
        start,
        incident.start_time,
        end,
        end + timedelta(seconds=1),
    ]
    set_response(
        mock_get, [make_release(published_at=t.isoformat()) for t in timestamps]
    )
    result = make_provider(window_minutes=window_minutes).query(incident)
    assert [entry.timestamp for entry in result] == [start, incident.start_time, end]


@pytest.mark.parametrize(
    "service, expected", [(None, 1), ("checkout-service", 1), ("other", 0), ("", 0)]
)
@patch("traceroot.integrations.live_deployments.httpx.get")
def test_live_deployments_provider_filters_service(mock_get, service, expected):
    set_response(mock_get, [make_release()])
    result = make_provider().query(make_incident(), service=service)
    assert len(result) == expected
    if not expected:
        mock_get.assert_not_called()


@pytest.mark.parametrize(
    "name, body, expected",
    [
        ("Checkout fix", "Notes", "Checkout fix"),
        (None, "Notes", "Notes"),
        ("", "Notes", "Notes"),
        (None, None, None),
        ("", "", None),
    ],
)
@patch("traceroot.integrations.live_deployments.httpx.get")
def test_live_deployments_provider_maps_release_fields(mock_get, name, body, expected):
    set_response(mock_get, [make_release(name=name, body=body)])
    entry = make_provider().query(make_incident())[0]
    assert entry.version == "v1.2.3"
    assert entry.service == "checkout-service"
    assert entry.description == expected
    assert entry.timestamp == make_incident().start_time
    assert entry.timestamp.tzinfo is UTC


@patch("traceroot.integrations.live_deployments.httpx.get")
def test_live_deployments_provider_prefers_published_at(mock_get):
    set_response(mock_get, [make_release(published_at="2026-09-29T17:30:00+05:30")])
    assert (
        make_provider().query(make_incident())[0].timestamp
        == make_incident().start_time
    )


@pytest.mark.parametrize("missing", [False, True])
@patch("traceroot.integrations.live_deployments.httpx.get")
def test_live_deployments_provider_falls_back_to_created_at(mock_get, missing):
    release = make_release(published_at=None)
    if missing:
        del release["published_at"]
    set_response(mock_get, [release])
    assert make_provider().query(make_incident())[0].timestamp == datetime(
        2026, 9, 29, 11, 30, tzinfo=UTC
    )


@patch("traceroot.integrations.live_deployments.httpx.get")
def test_live_deployments_provider_generates_stable_evidence_ids(mock_get):
    release = make_release()
    set_response(mock_get, [release, make_release(tag_name="v1.2.4")])
    first = make_provider().query(make_incident())
    release["name"] = "Edited title"
    release["body"] = "Edited notes"
    second = make_provider().query(make_incident(), service="checkout-service")
    assert [entry.id for entry in first] == [entry.id for entry in second]
    assert first[0].id.startswith("DEPLOY-LIVE-")
    assert first[0].id != first[1].id
    other_repo = GitHubDeploymentsProvider("example/other", "checkout-service")
    assert other_repo.query(make_incident())[0].id != first[0].id


@patch("traceroot.integrations.live_deployments.httpx.get")
def test_live_deployments_provider_sorts_by_timestamp(mock_get):
    set_response(
        mock_get,
        [
            make_release(published_at=f"2026-09-29T{hour}:00:00Z")
            for hour in (13, 11, 12)
        ],
    )
    result = make_provider().query(make_incident())
    assert [entry.timestamp.hour for entry in result] == [11, 12, 13]


@pytest.mark.parametrize(
    "payload", [[], [make_release(published_at="2020-01-01T00:00:00Z")]]
)
@patch("traceroot.integrations.live_deployments.httpx.get")
def test_live_deployments_provider_returns_empty_list_when_source_has_no_releases(
    mock_get, payload
):
    set_response(mock_get, payload)
    assert make_provider().query(make_incident()) == []


@patch("traceroot.integrations.live_deployments.httpx.get")
def test_live_deployments_provider_raises_for_http_failure(mock_get):
    response = set_response(mock_get, [])
    response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "HTTP failure",
        request=httpx.Request("GET", "https://api.github.com"),
        response=httpx.Response(403),
    )
    with pytest.raises(httpx.HTTPStatusError, match="HTTP failure"):
        make_provider().query(make_incident())
    response.json.assert_not_called()


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"message": "Not Found"},
        None,
        "releases",
        [None],
        [[]],
        [{}],
        [make_release(tag_name=None)],
        [make_release(tag_name=123)],
        [make_release(tag_name="")],
        [make_release(published_at=None, created_at=None)],
        [make_release(published_at="invalid")],
        [make_release(published_at="")],
        [make_release(published_at=123)],
        [make_release(published_at="2026-09-29T12:00:00")],
        [make_release(name=[])],
        [make_release(body={})],
        [
            make_release(),
            make_release(tag_name=None, published_at="2020-01-01T00:00:00Z"),
        ],
    ],
)
@patch("traceroot.integrations.live_deployments.httpx.get")
def test_live_deployments_provider_rejects_malformed_payload(mock_get, payload):
    set_response(mock_get, payload)
    with pytest.raises((TypeError, ValueError), match="Malformed GitHub"):
        make_provider().query(make_incident())


@patch("traceroot.integrations.live_deployments.httpx.get")
def test_live_deployments_provider_sends_auth_header_when_token_provided(mock_get):
    set_response(mock_get, [])
    make_provider(token="test-token", timeout_seconds=3.0).query(make_incident())
    mock_get.assert_called_once_with(
        "https://api.github.com/repos/example/checkout/releases",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer test-token",
        },
        params={"per_page": 100, "page": 1},
        timeout=3.0,
    )


@patch("traceroot.integrations.live_deployments.httpx.get")
def test_live_deployments_provider_omits_auth_header_when_token_missing(mock_get):
    set_response(mock_get, [])
    make_provider().query(make_incident())
    assert mock_get.call_args.kwargs["headers"] == {
        "Accept": "application/vnd.github+json"
    }
    assert mock_get.call_args.kwargs["timeout"] == 10.0


@patch("traceroot.integrations.live_deployments.httpx.get")
def test_live_deployments_provider_reads_later_pages(mock_get):
    first = Mock()
    first.json.return_value = [
        make_release(tag_name=f"v{i}", published_at="2020-01-01T00:00:00Z")
        for i in range(100)
    ]
    second = Mock()
    second.json.return_value = [make_release()]
    mock_get.side_effect = [first, second]
    result = make_provider().query(make_incident())
    assert len(result) == 1
    assert result[0].version == "v1.2.3"
    assert [call.kwargs["params"]["page"] for call in mock_get.call_args_list] == [1, 2]
    first.raise_for_status.assert_called_once_with()
    second.raise_for_status.assert_called_once_with()


@patch("traceroot.integrations.live_deployments.httpx.get")
def test_live_deployments_provider_rejects_invalid_json(mock_get):
    response = set_response(mock_get, [])
    response.json.side_effect = ValueError("Invalid JSON")
    with pytest.raises(ValueError, match="Invalid JSON"):
        make_provider().query(make_incident())
