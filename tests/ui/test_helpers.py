from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from traceroot.bootstrap import build_live_runtime
from traceroot.config import LiveEvidenceConfig
from traceroot.data.loader import load_incident_dataset
from traceroot.tools import interface
from traceroot.tools.models import ToolName
from traceroot.ui import helpers


def test_discover_only_incident_files(tmp_path):
    for name in ("INC-002", "INC-001", "NEW-session"):
        directory = tmp_path / name
        directory.mkdir()
        (directory / "incident.json").write_text("{}")
    assert [p.parent.name for p in helpers.discover_incidents(tmp_path)] == [
        "INC-001",
        "INC-002",
    ]
    assert helpers.discover_incidents(tmp_path / "missing") == []


def test_new_incident():
    incident = helpers.new_incident(
        " Title ", " Description ", "2026-09-26T10:00:00+00:00", " api, ,worker "
    )
    assert incident.id.startswith("NEW-")
    assert incident.title == "Title"
    assert incident.description == "Description"
    assert incident.start_time == datetime(2026, 9, 26, 10, tzinfo=UTC)
    assert incident.suspected_services == ["api", "worker"]
    assert helpers.new_incident("a", "b", "2026-09-26", "").suspected_services == []


@pytest.mark.parametrize(
    "title,description,time",
    [(" ", "b", "2026-09-26"), ("a", "", "2026-09-26"), ("a", "b", "invalid")],
)
def test_invalid_input(title, description, time):
    with pytest.raises(ValueError):
        helpers.new_incident(title, description, time, "")


def test_existing_workflow_delegation(monkeypatch):
    incident = helpers.new_incident("a", "b", "2026-09-26", "")
    runner = Mock(return_value=object())
    monkeypatch.setattr(helpers, "run_agent_experiment", runner)
    assert helpers.run_investigation(incident, 4) is runner.return_value
    args, kwargs = runner.call_args
    assert args[0] is incident
    assert args[1].parent == Path("experiments/results/ui")
    assert kwargs == {"max_tool_calls": 4}


@pytest.mark.parametrize("fail", [False, True])
def test_new_workflow_empty_dataset_and_cleanup(tmp_path, monkeypatch, fail):
    monkeypatch.chdir(tmp_path)
    incident = helpers.new_incident("a", "b", "2026-09-26", "api")
    result = object()

    def runner(actual, output, max_tool_calls):
        dataset = load_incident_dataset(Path("data/incidents") / actual.id)
        assert dataset.incident == actual
        assert actual.title == incident.title
        assert actual.suspected_services == ["api"]
        assert (
            not dataset.logs + dataset.metrics + dataset.deployments + dataset.changes
        )
        assert helpers.discover_incidents(Path("data/incidents")) == []
        assert max_tool_calls == 3
        if fail:
            raise RuntimeError("LLM failure")
        return result

    monkeypatch.setattr(helpers, "run_agent_experiment", runner)
    if fail:
        with pytest.raises(RuntimeError, match="LLM failure"):
            helpers.run_investigation(incident, 3, is_new=True)
    else:
        assert helpers.run_investigation(incident, 3, is_new=True) is result
    assert list(Path("data/incidents").iterdir()) == []


def test_evaluation_loads_labels_only_for_matching_frozen_result(tmp_path, monkeypatch):
    from traceroot.evaluation import runner

    monkeypatch.chdir(tmp_path)
    incident_path = Path("data/incidents/INC-001/incident.json")
    incident_path.parent.mkdir(parents=True)
    incident_path.write_text("{}")
    truth_path = Path("data/ground_truth/INC-001.json")
    truth_path.parent.mkdir(parents=True)
    truth_path.write_text(
        '{"incident_id":"INC-001","root_cause":"cause","root_cause_category":"code","affected_service":"api"}'
    )
    evaluator = Mock(return_value=object())
    monkeypatch.setattr(runner, "evaluate_agent_record", evaluator)
    record = SimpleNamespace(incident_id="INC-001")
    assert helpers.evaluate_result(record, incident_path) is evaluator.return_value
    assert evaluator.call_args.args[0] is record
    assert evaluator.call_args.args[1].root_cause == "cause"
    truth_path.unlink()
    with pytest.raises(ValueError, match="does not match"):
        helpers.evaluate_result(SimpleNamespace(incident_id="INC-002"), incident_path)
    with pytest.raises(ValueError, match="frozen"):
        helpers.evaluate_result(
            record, Path("data/incidents/NEW-session/incident.json")
        )


@pytest.fixture
def live_config():
    return LiveEvidenceConfig(
        loki_base_url="https://logs.example.test",
        prometheus_base_url="https://metrics.example.test",
        github_repo="example/checkout",
        github_service="checkout-service",
    )


@pytest.mark.parametrize(
    "timestamp",
    ["2026-10-03T10:00:00Z", "2026-10-03T15:30:00+05:30"],
)
def test_new_live_incident_validates_runtime_input(timestamp):
    incident = helpers.new_live_incident(
        " Title ", " Description ", f" {timestamp} ", " checkout-service, ,worker "
    )
    assert incident.id.startswith("INC-RUNTIME-")
    assert incident.title == "Title"
    assert incident.description == "Description"
    assert incident.start_time == datetime(2026, 10, 3, 10, tzinfo=UTC)
    assert incident.suspected_services == ["checkout-service", "worker"]


def test_new_live_incident_allows_no_suspected_services():
    incident = helpers.new_live_incident(
        "Title", "Description", "2026-10-03T10:00:00Z", " , "
    )
    assert incident.suspected_services == []


@pytest.mark.parametrize(
    "title,description,timestamp",
    [
        (" ", "Description", "2026-10-03T10:00:00Z"),
        ("Title", " ", "2026-10-03T10:00:00Z"),
        ("Title", "Description", "invalid"),
        ("Title", "Description", "2026-10-03"),
        ("Title", "Description", "2026-10-03T10:00:00"),
    ],
)
def test_new_live_incident_rejects_invalid_input(title, description, timestamp):
    with pytest.raises(ValueError):
        helpers.new_live_incident(title, description, timestamp, "")


@patch("traceroot.bootstrap.configure_backend")
@patch("httpx.get", side_effect=AssertionError("Unexpected external request"))
@patch("traceroot.ui.helpers.build_live_runtime")
@patch("traceroot.ui.helpers.run_agent_experiment")
@pytest.mark.parametrize("fail", [False, True])
def test_live_workflow_uses_registered_scoped_router_without_global_activation(
    mock_run,
    mock_build,
    mock_get,
    mock_configure,
    live_config,
    tmp_path,
    monkeypatch,
    fail,
):
    monkeypatch.chdir(tmp_path)
    incident = helpers.new_live_incident(
        "Checkout failures",
        "Requests time out",
        "2026-10-03T10:00:00Z",
        "checkout-service",
    )
    runtime = build_live_runtime(live_config)
    mock_build.return_value = runtime
    previous_backend = interface._default_backend
    record = object()
    expected_path = Path("experiments/results/live") / f"{incident.id}-agent.json"

    def run(*, incident, output_path, max_tool_calls, tool_executor):
        assert runtime.incident_registry.get(incident.id) is incident
        assert runtime.live_backend.incident_registry is runtime.incident_registry
        assert runtime.router._incident_registry is runtime.incident_registry
        assert tool_executor.__self__ is runtime.router
        assert output_path == expected_path
        assert max_tool_calls == 4
        assert interface._default_backend is previous_backend
        assert tool_executor(ToolName.LOGS, incident.id, "checkout-service") == [
            "LIVE-EVIDENCE"
        ]
        if fail:
            raise RuntimeError("Provider failure")
        return record

    mock_run.side_effect = run
    with (
        patch.object(
            runtime.live_backend.logs_provider, "query", return_value=["LIVE-EVIDENCE"]
        ) as query,
        patch.object(runtime.router._fixture_backend, "query") as fixture_query,
        patch("traceroot.ui.helpers.TemporaryDirectory") as temporary,
    ):
        if fail:
            with pytest.raises(RuntimeError, match="Provider failure"):
                helpers.run_live_investigation(incident, live_config, 4)
        else:
            result, output_path = helpers.run_live_investigation(
                incident, live_config, 4
            )
            assert result is record
            assert output_path == expected_path
        query.assert_called_once_with(incident=incident, service="checkout-service")
        fixture_query.assert_not_called()
        temporary.assert_not_called()

    assert interface._default_backend is previous_backend
    assert not Path("data").exists()
    mock_build.assert_called_once_with(live_config)
    mock_run.assert_called_once()
    assert mock_run.call_args.kwargs["incident"] is incident
    mock_get.assert_not_called()
    mock_configure.assert_not_called()


@patch("httpx.get", side_effect=AssertionError("Unexpected external request"))
@patch("traceroot.ui.helpers.run_agent_experiment")
def test_live_workflow_keeps_independent_runtimes_isolated(
    mock_run, mock_get, live_config
):
    first = helpers.new_live_incident(
        "First", "First failure", "2026-10-03T10:00:00Z", ""
    )
    second = helpers.new_live_incident(
        "Second", "Second failure", "2026-10-03T10:00:00Z", ""
    )
    executors = []
    previous_backend = interface._default_backend
    mock_run.side_effect = lambda **kwargs: executors.append(kwargs["tool_executor"])

    helpers.run_live_investigation(first, live_config, 3)
    helpers.run_live_investigation(second, live_config, 3)
    first_router, second_router = [executor.__self__ for executor in executors]
    assert first_router is not second_router
    assert first_router._incident_registry.contains(first.id)
    assert not first_router._incident_registry.contains(second.id)
    assert second_router._incident_registry.contains(second.id)
    assert not second_router._incident_registry.contains(first.id)
    with (
        patch.object(
            first_router._live_backend.logs_provider, "query", return_value=["first"]
        ) as first_query,
        patch.object(
            second_router._live_backend.logs_provider, "query", return_value=["second"]
        ) as second_query,
    ):
        assert executors[0](ToolName.LOGS, first.id) == ["first"]
        assert executors[1](ToolName.LOGS, second.id) == ["second"]
        assert executors[0](ToolName.LOGS, first.id) == ["first"]
        first_query.assert_called_with(incident=first, service=None)
        second_query.assert_called_once_with(incident=second, service=None)
    assert interface._default_backend is previous_backend
    mock_get.assert_not_called()


@patch("traceroot.ui.helpers.run_agent_experiment")
@patch("traceroot.ui.helpers.build_live_runtime")
@pytest.mark.parametrize("budget", [0, -1])
def test_live_workflow_rejects_nonpositive_budget_before_bootstrap(
    mock_build, mock_run, live_config, budget
):
    incident = helpers.new_live_incident(
        "Title", "Description", "2026-10-03T10:00:00Z", ""
    )
    with pytest.raises(ValueError, match="max_tool_calls must be a positive integer"):
        helpers.run_live_investigation(incident, live_config, budget)
    mock_build.assert_not_called()
    mock_run.assert_not_called()


@patch("traceroot.ui.helpers.run_agent_experiment")
@patch(
    "traceroot.ui.helpers.build_live_runtime",
    side_effect=RuntimeError("Bootstrap failure"),
)
def test_live_workflow_bootstrap_failure_preserves_active_backend(
    mock_build, mock_run, live_config
):
    incident = helpers.new_live_incident(
        "Title", "Description", "2026-10-03T10:00:00Z", ""
    )
    previous_backend = interface._default_backend
    with pytest.raises(RuntimeError, match="Bootstrap failure"):
        helpers.run_live_investigation(incident, live_config, 4)
    assert interface._default_backend is previous_backend
    mock_run.assert_not_called()
