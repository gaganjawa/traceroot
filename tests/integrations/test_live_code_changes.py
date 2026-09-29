from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

import httpx
import pytest

from traceroot.data.models import CodeChangeEntry
from traceroot.domain.incident import Incident
from traceroot.integrations.live_code_changes import GitHubCodeChangesProvider

COMMITS_URL = "https://api.github.com/repos/example/checkout/commits"
SHA = "a" * 40


def make_incident() -> Incident:
    return Incident(
        id="INC-RUNTIME-001",
        title="Checkout failures",
        description="Checkout requests are failing.",
        start_time=datetime(2026, 9, 29, 12, 0, tzinfo=UTC),
        suspected_services=["checkout-service"],
    )


def make_commit(sha=SHA, timestamp="2026-09-29T12:00:00Z") -> dict:
    return {
        "sha": sha,
        "commit": {
            "committer": {"date": timestamp},
            "author": {"date": "2026-09-29T11:30:00Z"},
            "message": "Fix checkout\n\nHandle missing cart.",
        },
    }


def make_provider(**kwargs) -> GitHubCodeChangesProvider:
    return GitHubCodeChangesProvider("example/checkout", "checkout-service", **kwargs)


def make_response(payload):
    response = Mock()
    response.json.return_value = payload
    return response


def set_responses(mock_get, commits=None, detail=None):
    listing = make_response([make_commit()] if commits is None else commits)
    details = make_response(
        {"files": [{"filename": "checkout.py"}]} if detail is None else detail
    )
    mock_get.side_effect = lambda url, **kwargs: (
        listing if url == COMMITS_URL else details
    )
    return listing, details


@patch("traceroot.integrations.live_code_changes.httpx.get")
def test_live_code_changes_provider_returns_code_change_entries(mock_get):
    listing, details = set_responses(mock_get)
    result = make_provider().query(make_incident())
    assert len(result) == 1
    assert isinstance(result[0], CodeChangeEntry)
    listing.raise_for_status.assert_called_once_with()
    details.raise_for_status.assert_called_once_with()


@pytest.mark.parametrize("window", [60, 15])
@patch("traceroot.integrations.live_code_changes.httpx.get")
def test_live_code_changes_provider_uses_incident_time_window(mock_get, window):
    incident = make_incident()
    start = incident.start_time - timedelta(minutes=window)
    end = incident.start_time + timedelta(minutes=window)
    times = [
        start - timedelta(seconds=1),
        start,
        incident.start_time,
        end,
        end + timedelta(seconds=1),
    ]
    set_responses(
        mock_get, [make_commit(f"{i:040x}", t.isoformat()) for i, t in enumerate(times)]
    )
    result = make_provider(window_minutes=window).query(incident)
    assert [entry.timestamp for entry in result] == [start, incident.start_time, end]
    assert mock_get.call_args_list[0].kwargs["params"] == {
        "since": start.isoformat(),
        "until": end.isoformat(),
        "per_page": 100,
        "page": 1,
    }
    assert mock_get.call_count == 4  # Out-of-window commits need no detail request.


@pytest.mark.parametrize(
    "service, expected", [(None, 1), ("checkout-service", 1), ("other", 0), ("", 0)]
)
@patch("traceroot.integrations.live_code_changes.httpx.get")
def test_live_code_changes_provider_filters_service(mock_get, service, expected):
    set_responses(mock_get)
    assert len(make_provider().query(make_incident(), service=service)) == expected
    if not expected:
        mock_get.assert_not_called()


@patch("traceroot.integrations.live_code_changes.httpx.get")
def test_live_code_changes_provider_maps_commit_fields(mock_get):
    set_responses(mock_get)
    entry = make_provider().query(make_incident())[0]
    assert entry.timestamp == make_incident().start_time
    assert entry.timestamp.tzinfo is UTC
    assert entry.service == "checkout-service"
    assert entry.commit_sha == SHA
    assert entry.files == ["checkout.py"]
    assert entry.description == "Fix checkout\n\nHandle missing cart."
    assert entry.diff is None


@patch("traceroot.integrations.live_code_changes.httpx.get")
def test_live_code_changes_provider_prefers_committer_timestamp(mock_get):
    set_responses(mock_get, [make_commit(timestamp="2026-09-29T17:30:00+05:30")])
    assert (
        make_provider().query(make_incident())[0].timestamp
        == make_incident().start_time
    )


@pytest.mark.parametrize("committer", [None, {}, {"date": None}])
@patch("traceroot.integrations.live_code_changes.httpx.get")
def test_live_code_changes_provider_falls_back_to_author_timestamp(mock_get, committer):
    commit = make_commit()
    commit["commit"]["committer"] = committer
    set_responses(mock_get, [commit])
    assert make_provider().query(make_incident())[0].timestamp == datetime(
        2026, 9, 29, 11, 30, tzinfo=UTC
    )


@patch("traceroot.integrations.live_code_changes.httpx.get")
def test_live_code_changes_provider_fetches_changed_files(mock_get):
    set_responses(
        mock_get,
        detail={
            "files": [
                {"filename": "checkout.py"},
                {"filename": "tests/test_checkout.py"},
            ]
        },
    )
    entry = make_provider(timeout_seconds=3.0).query(make_incident())[0]
    assert entry.files == ["checkout.py", "tests/test_checkout.py"]
    assert mock_get.call_args_list[1].args == (f"{COMMITS_URL}/{SHA}",)
    assert mock_get.call_args_list[1].kwargs == {
        "headers": {"Accept": "application/vnd.github+json"},
        "params": {"per_page": 100, "page": 1},
        "timeout": 3.0,
    }


@patch("traceroot.integrations.live_code_changes.httpx.get")
def test_live_code_changes_provider_generates_stable_evidence_ids(mock_get):
    commit = make_commit()
    detail = {"files": [{"filename": "a.py"}, {"filename": "b.py"}]}
    set_responses(mock_get, [commit], detail)
    first = make_provider().query(make_incident())[0]
    commit["commit"]["message"] = "Changed description"
    detail["files"].reverse()
    second = make_provider().query(make_incident(), service="checkout-service")[0]
    assert first.id == second.id
    assert first.id.startswith("CHANGE-LIVE-")
    assert first.files != second.files
    commit["sha"] = "b" * 40
    assert make_provider().query(make_incident())[0].id != first.id
    commit["sha"] = SHA
    other_service = GitHubCodeChangesProvider("example/checkout", "other-service")
    assert other_service.query(make_incident())[0].id != first.id
    other_repo = GitHubCodeChangesProvider("example/other", "checkout-service")
    mock_get.side_effect = [make_response([commit]), make_response(detail)]
    assert other_repo.query(make_incident())[0].id != first.id


@patch("traceroot.integrations.live_code_changes.httpx.get")
def test_live_code_changes_provider_sorts_by_timestamp(mock_get):
    set_responses(
        mock_get,
        [
            make_commit(f"{hour:040x}", f"2026-09-29T{hour}:00:00Z")
            for hour in (13, 11, 12)
        ],
    )
    assert [
        entry.timestamp.hour for entry in make_provider().query(make_incident())
    ] == [11, 12, 13]


@pytest.mark.parametrize(
    "commits", [[], [make_commit(timestamp="2020-01-01T00:00:00Z")]]
)
@patch("traceroot.integrations.live_code_changes.httpx.get")
def test_live_code_changes_provider_returns_empty_list_when_source_has_no_commits(
    mock_get, commits
):
    set_responses(mock_get, commits)
    assert make_provider().query(make_incident()) == []
    assert mock_get.call_count == 1


def http_failure():
    return httpx.HTTPStatusError(
        "HTTP failure",
        request=httpx.Request("GET", COMMITS_URL),
        response=httpx.Response(403),
    )


@patch("traceroot.integrations.live_code_changes.httpx.get")
def test_live_code_changes_provider_raises_for_list_http_failure(mock_get):
    listing, details = set_responses(mock_get)
    listing.raise_for_status.side_effect = http_failure()
    with pytest.raises(httpx.HTTPStatusError, match="HTTP failure"):
        make_provider().query(make_incident())
    listing.json.assert_not_called()
    details.raise_for_status.assert_not_called()


@patch("traceroot.integrations.live_code_changes.httpx.get")
def test_live_code_changes_provider_raises_for_detail_http_failure(mock_get):
    _, details = set_responses(mock_get)
    details.raise_for_status.side_effect = http_failure()
    with pytest.raises(httpx.HTTPStatusError, match="HTTP failure"):
        make_provider().query(make_incident())
    details.json.assert_not_called()


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {},
        "commits",
        [None],
        [[]],
        [{}],
        [{"sha": None, "commit": {}}],
        [{"sha": 12, "commit": {}}],
        [{"sha": "", "commit": {}}],
        [{"sha": SHA}],
        [{"sha": SHA, "commit": []}],
    ],
)
@patch("traceroot.integrations.live_code_changes.httpx.get")
def test_live_code_changes_provider_rejects_malformed_commit_list(mock_get, payload):
    mock_get.return_value = make_response(payload)
    with pytest.raises((TypeError, ValueError), match="Malformed GitHub"):
        make_provider().query(make_incident())


@pytest.mark.parametrize(
    "metadata",
    [
        {},
        {"committer": []},
        {"committer": None, "author": []},
        {"committer": {"date": 123}},
        {"committer": {"date": "invalid"}},
        {"committer": {"date": ""}},
        {"committer": {"date": "2026-09-29T12:00:00"}},
        {"committer": {"date": "2026-09-29T12:00:00Z"}, "message": []},
    ],
)
@patch("traceroot.integrations.live_code_changes.httpx.get")
def test_live_code_changes_provider_rejects_malformed_commit_metadata(
    mock_get, metadata
):
    set_responses(mock_get, [{"sha": SHA, "commit": metadata}])
    with pytest.raises((TypeError, ValueError), match="Malformed GitHub"):
        make_provider().query(make_incident())


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        "detail",
        {},
        {"files": None},
        {"files": {}},
        {"files": [None]},
        {"files": [{}]},
        {"files": [{"filename": None}]},
        {"files": [{"filename": 123}]},
        {"files": [{"filename": ""}]},
    ],
)
@patch("traceroot.integrations.live_code_changes.httpx.get")
def test_live_code_changes_provider_rejects_malformed_commit_detail(mock_get, payload):
    mock_get.side_effect = [make_response([make_commit()]), make_response(payload)]
    with pytest.raises((TypeError, ValueError), match="Malformed GitHub"):
        make_provider().query(make_incident())


@patch("traceroot.integrations.live_code_changes.httpx.get")
def test_live_code_changes_provider_sends_auth_header_when_token_provided(mock_get):
    set_responses(mock_get)
    make_provider(token="test-token").query(make_incident())
    assert mock_get.call_count == 2
    for call in mock_get.call_args_list:
        assert call.kwargs["headers"] == {
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer test-token",
        }


@patch("traceroot.integrations.live_code_changes.httpx.get")
def test_live_code_changes_provider_omits_auth_header_when_token_missing(mock_get):
    set_responses(mock_get)
    make_provider().query(make_incident())
    for call in mock_get.call_args_list:
        assert call.kwargs["headers"] == {"Accept": "application/vnd.github+json"}


@pytest.mark.parametrize("last_page", [[], [make_commit("f" * 40)]])
@patch("traceroot.integrations.live_code_changes.httpx.get")
def test_live_code_changes_provider_handles_pagination(mock_get, last_page):
    first_page = [make_commit(f"{i:040x}") for i in range(100)]

    def respond(url, **kwargs):
        if url == COMMITS_URL:
            return make_response(
                first_page if kwargs["params"]["page"] == 1 else last_page
            )
        return make_response({"files": []})

    mock_get.side_effect = respond
    result = make_provider().query(make_incident())
    assert len(result) == 100 + len(last_page)
    calls = [call for call in mock_get.call_args_list if call.args[0] == COMMITS_URL]
    assert [call.kwargs["params"]["page"] for call in calls] == [1, 2]
    assert calls[0].kwargs["params"]["since"] == calls[1].kwargs["params"]["since"]


@patch("traceroot.integrations.live_code_changes.httpx.get")
def test_live_code_changes_provider_stops_pagination_when_results_are_older_than_window(
    mock_get,
):
    set_responses(
        mock_get, [make_commit(f"{i:040x}", "2020-01-01T00:00:00Z") for i in range(100)]
    )
    assert make_provider().query(make_incident()) == []
    assert mock_get.call_count == 1


@patch("traceroot.integrations.live_code_changes.httpx.get")
def test_live_code_changes_provider_does_not_stop_at_one_old_commit(mock_get):
    set_responses(
        mock_get, [make_commit("b" * 40, "2020-01-01T00:00:00Z"), make_commit()]
    )
    result = make_provider().query(make_incident())
    assert [entry.commit_sha for entry in result] == [SHA]


@patch("traceroot.integrations.live_code_changes.httpx.get")
def test_live_code_changes_provider_rejects_nonadvancing_pagination(mock_get):
    set_responses(mock_get, [make_commit(f"{i:040x}") for i in range(100)])
    with pytest.raises(RuntimeError, match="made no progress"):
        make_provider().query(make_incident())
    assert mock_get.call_count == 102


@patch("traceroot.integrations.live_code_changes.httpx.get")
def test_live_code_changes_provider_bounds_commit_pagination(mock_get):
    set_responses(mock_get, [make_commit(f"{i:040x}") for i in range(100)])
    provider = make_provider()
    provider._MAX_COMMIT_PAGES = 1
    with pytest.raises(RuntimeError, match="commit pagination limit"):
        provider.query(make_incident())


@patch("traceroot.integrations.live_code_changes.httpx.get")
def test_live_code_changes_provider_paginates_changed_files(mock_get):
    files = [{"filename": f"file{i}.py"} for i in range(100)]
    mock_get.side_effect = [
        make_response([make_commit()]),
        make_response({"files": files}),
        make_response({"files": [{"filename": "last.py"}]}),
    ]
    result = make_provider().query(make_incident())
    assert result[0].files == [file["filename"] for file in files] + ["last.py"]
    assert mock_get.call_args.kwargs["params"] == {"per_page": 100, "page": 2}


@patch("traceroot.integrations.live_code_changes.httpx.get")
def test_live_code_changes_provider_bounds_file_pagination(mock_get):
    set_responses(
        mock_get, detail={"files": [{"filename": f"file{i}.py"} for i in range(100)]}
    )
    provider = make_provider()
    provider._MAX_FILE_PAGES = 1
    with pytest.raises(RuntimeError, match="file pagination limit"):
        provider.query(make_incident())


@patch("traceroot.integrations.live_code_changes.httpx.get")
def test_live_code_changes_provider_accepts_empty_files_and_absent_message(mock_get):
    commit = make_commit()
    del commit["commit"]["message"]
    set_responses(mock_get, [commit], {"files": []})
    entry = make_provider().query(make_incident())[0]
    assert entry.files == []
    assert entry.description == ""


@patch("traceroot.integrations.live_code_changes.httpx.get")
def test_live_code_changes_provider_rejects_naive_incident_time(mock_get):
    incident = make_incident()
    incident.start_time = incident.start_time.replace(tzinfo=None)
    with pytest.raises(ValueError, match="Incident start_time must have a timezone"):
        make_provider().query(incident)
    mock_get.assert_not_called()
