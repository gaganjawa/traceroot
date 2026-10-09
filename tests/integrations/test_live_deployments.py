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


def release_page(start=0, count=100, **overrides):
    return [
        make_release(tag_name=f"v{i}", **overrides) for i in range(start, start + count)
    ]


def set_pages(mock_get, *pages):
    responses = []
    for page in pages:
        response = Mock()
        response.json.return_value = page
        responses.append(response)
    mock_get.side_effect = responses
    return responses


def requested_pages(mock_get):
    return [call.kwargs["params"]["page"] for call in mock_get.call_args_list]


@patch("traceroot.integrations.live_deployments.httpx.get")
def test_live_deployments_provider_preserves_single_page_results(mock_get):
    payload = [make_release()]
    set_response(mock_get, payload)
    provider = make_provider()
    assert provider.query(make_incident()) == [provider._map_release(payload[0])]


@patch("traceroot.integrations.live_deployments.httpx.get")
def test_live_deployments_provider_stops_on_empty_first_page(mock_get):
    set_pages(mock_get, [])
    assert make_provider().query(make_incident()) == []
    assert requested_pages(mock_get) == [1]


@patch("traceroot.integrations.live_deployments.httpx.get")
def test_live_deployments_provider_stops_on_short_page(mock_get):
    set_pages(mock_get, release_page(count=99))
    assert len(make_provider().query(make_incident())) == 99
    assert requested_pages(mock_get) == [1]


@patch("traceroot.integrations.live_deployments.httpx.get")
def test_live_deployments_provider_stops_on_empty_final_page(mock_get):
    set_pages(mock_get, release_page(), [])
    assert len(make_provider().query(make_incident())) == 100
    assert requested_pages(mock_get) == [1, 2]


@patch("traceroot.integrations.live_deployments.httpx.get")
def test_live_deployments_provider_collects_in_window_evidence_across_pages(mock_get):
    first = release_page(count=99, published_at="2020-01-01T00:00:00Z")
    first.append(make_release(tag_name="start", published_at="2026-09-29T11:00:00Z"))
    second = [
        make_release(tag_name="end", published_at="2026-09-29T13:00:00Z"),
        make_release(tag_name="future", published_at="2026-09-29T13:00:01Z"),
    ]
    set_pages(mock_get, first, second)
    assert [entry.version for entry in make_provider().query(make_incident())] == [
        "start",
        "end",
    ]


@patch("traceroot.integrations.live_deployments.httpx.get")
def test_live_deployments_provider_bounds_release_pagination(mock_get, monkeypatch):
    monkeypatch.setattr(GitHubDeploymentsProvider, "_MAX_RELEASE_PAGES", 2)
    set_pages(mock_get, release_page(), release_page(start=100))
    with pytest.raises(
        RuntimeError,
        match="^GitHub release pagination limit reached; results may be incomplete$",
    ):
        make_provider().query(make_incident())
    assert requested_pages(mock_get) == [1, 2]
    assert all(
        call.kwargs["params"]["per_page"] == 100 for call in mock_get.call_args_list
    )


@patch("traceroot.integrations.live_deployments.httpx.get")
def test_live_deployments_provider_accepts_short_page_at_page_limit(
    mock_get, monkeypatch
):
    monkeypatch.setattr(GitHubDeploymentsProvider, "_MAX_RELEASE_PAGES", 2)
    # Even a wholly repeated short page is a valid terminal page.
    set_pages(mock_get, release_page(), release_page(count=50))
    assert len(make_provider().query(make_incident())) == 150
    assert requested_pages(mock_get) == [1, 2]


@patch("traceroot.integrations.live_deployments.httpx.get")
def test_live_deployments_provider_accepts_empty_page_at_page_limit(
    mock_get, monkeypatch
):
    monkeypatch.setattr(GitHubDeploymentsProvider, "_MAX_RELEASE_PAGES", 2)
    set_pages(mock_get, release_page(), [])
    assert len(make_provider().query(make_incident())) == 100
    assert requested_pages(mock_get) == [1, 2]


@patch("traceroot.integrations.live_deployments.httpx.get")
def test_live_deployments_provider_rejects_repeated_full_pages(mock_get):
    # The source ignores page and returns the same content on every request.
    set_response(mock_get, release_page())
    with pytest.raises(
        RuntimeError, match="^GitHub release pagination made no progress$"
    ):
        make_provider().query(make_incident())
    assert requested_pages(mock_get) == [1, 2]


@patch("traceroot.integrations.live_deployments.httpx.get")
def test_live_deployments_provider_rejects_nonadvancing_out_of_window_pages(mock_get):
    set_response(mock_get, release_page(published_at="2020-01-01T00:00:00Z"))
    with pytest.raises(RuntimeError, match="made no progress"):
        make_provider().query(make_incident())
    assert requested_pages(mock_get) == [1, 2]


@patch("traceroot.integrations.live_deployments.httpx.get")
def test_live_deployments_provider_preserves_duplicates_on_overlapping_pages(mock_get):
    first = release_page()
    second = first[:99] + [make_release(tag_name="new")]
    set_pages(mock_get, first, second, [])
    result = make_provider().query(make_incident())
    assert [entry.version for entry in result] == [
        item["tag_name"] for item in first + second
    ]
    assert result[0].id == result[100].id
    assert requested_pages(mock_get) == [1, 2, 3]


@patch("traceroot.integrations.live_deployments.httpx.get")
def test_live_deployments_provider_filters_without_assuming_timestamp_order(mock_get):
    set_pages(
        mock_get,
        release_page(published_at="2020-01-01T00:00:00Z"),
        release_page(start=100, published_at="2020-01-01T00:00:00Z"),
        [make_release()],
    )
    result = make_provider().query(make_incident())
    assert [entry.version for entry in result] == ["v1.2.3"]
    assert requested_pages(mock_get) == [1, 2, 3]


@pytest.mark.parametrize(
    "link", ["malformed", '<https://api.github.com/releases?page=1>; rel="next"']
)
@patch("traceroot.integrations.live_deployments.httpx.get")
def test_live_deployments_provider_ignores_pagination_link_headers(mock_get, link):
    responses = set_pages(mock_get, release_page(), [])
    for response in responses:
        response.headers = {"Link": link}
    assert len(make_provider().query(make_incident())) == 100
    assert requested_pages(mock_get) == [1, 2]


@pytest.mark.parametrize("status", [403, 429, 500])
@patch("traceroot.integrations.live_deployments.httpx.get")
def test_live_deployments_provider_propagates_mid_pagination_http_errors(
    mock_get, status
):
    responses = set_pages(mock_get, release_page(), [])
    error = httpx.HTTPStatusError(
        "HTTP failure",
        request=httpx.Request(
            "GET", "https://api.github.com/repos/example/checkout/releases"
        ),
        response=httpx.Response(status),
    )
    responses[1].raise_for_status.side_effect = error
    with pytest.raises(httpx.HTTPStatusError) as caught:
        make_provider().query(make_incident())
    assert caught.value is error
    responses[1].json.assert_not_called()
    assert requested_pages(mock_get) == [1, 2]


@patch("traceroot.integrations.live_deployments.httpx.get")
def test_live_deployments_provider_preserves_ids_and_order_across_pages(mock_get):
    first = release_page()
    second = [
        make_release(tag_name="earlier", published_at="2026-09-29T11:00:00Z"),
        make_release(tag_name="same-time"),
    ]
    # Numeric GitHub IDs are not required for progress detection.
    for release in first + second:
        del release["id"]
    set_pages(mock_get, first, second)
    provider = make_provider()
    result = provider.query(make_incident())
    expected = [second[0], *first, second[1]]
    assert result == [provider._map_release(release) for release in expected]
    assert [entry.version for entry in result] == [
        item["tag_name"] for item in expected
    ]
