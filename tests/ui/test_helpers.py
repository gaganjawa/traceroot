from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from traceroot.data.loader import load_incident_dataset
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
