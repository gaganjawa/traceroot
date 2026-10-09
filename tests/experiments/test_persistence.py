import json
from datetime import UTC, datetime

import pytest

from traceroot.domain.rca import RCAResult
from traceroot.experiments.models import (
    AgentExperimentRecord,
    BaselineExperimentRecord,
    RetrievedKnowledge,
)
from traceroot.experiments.persistence import (
    save_agent_experiment_record,
    save_baseline_record,
)
from traceroot.llm.client import LLM_MODEL_GPT_5_4_MINI


@pytest.fixture
def baseline_record() -> BaselineExperimentRecord:
    return BaselineExperimentRecord(
        incident_id="INC-001",
        model="gpt-5.4-mini",
        top_k=5,
        retrieved_knowledge=[
            RetrievedKnowledge(
                chunk_id="checkout-runbook.md::0",
                source="checkout-runbook.md",
                score=0.573,
            )
        ],
        result=RCAResult(
            incident_id="INC-001",
            root_cause="Insufficient evidence to confirm root cause",
            affected_service="checkout-service",
            evidence_ids=[],
            explanation="Knowledge-only baseline explanation.",
            confidence=0.22,
        ),
        latency_ms=125.5,
        timestamp=datetime(
            2026,
            9,
            23,
            12,
            0,
            tzinfo=UTC,
        ),
    )


def test_save_baseline_record_creates_json_file(
    tmp_path,
    baseline_record,
):
    file_path = tmp_path / "baseline.json"

    save_baseline_record(
        record=baseline_record,
        file_path=str(file_path),
    )

    assert file_path.exists()
    assert file_path.is_file()
    assert file_path.stat().st_size > 0


def test_save_baseline_record_creates_missing_parent_directory(
    tmp_path,
    baseline_record,
):
    file_path = tmp_path / "results" / "baseline" / "INC-001-rag_baseline.json"

    assert not file_path.parent.exists()

    save_baseline_record(
        record=baseline_record,
        file_path=str(file_path),
    )

    assert file_path.parent.exists()
    assert file_path.exists()


def test_save_baseline_record_persists_complete_record(
    tmp_path,
    baseline_record,
):
    file_path = tmp_path / "baseline.json"

    save_baseline_record(
        record=baseline_record,
        file_path=str(file_path),
    )

    with file_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    assert data["incident_id"] == "INC-001"
    assert data["approach"] == "rag_baseline"
    assert data["model"] == "gpt-5.4-mini"
    assert data["top_k"] == 5
    assert data["latency_ms"] == 125.5

    assert len(data["retrieved_knowledge"]) == 1
    assert data["retrieved_knowledge"][0]["chunk_id"] == "checkout-runbook.md::0"
    assert data["retrieved_knowledge"][0]["source"] == "checkout-runbook.md"
    assert data["retrieved_knowledge"][0]["score"] == 0.573

    assert data["result"]["incident_id"] == "INC-001"
    assert data["result"]["root_cause"] == "Insufficient evidence to confirm root cause"
    assert data["result"]["affected_service"] == "checkout-service"
    assert data["result"]["evidence_ids"] == []
    assert data["result"]["confidence"] == 0.22

    assert data["timestamp"] == "2026-09-23T12:00:00Z"


def test_save_baseline_record_returns_output_path(
    tmp_path,
    baseline_record,
):
    file_path = tmp_path / "INC-001-rag_baseline.json"

    returned_path = save_baseline_record(
        record=baseline_record,
        file_path=str(file_path),
    )

    assert returned_path == file_path
    assert returned_path.exists()


def test_save_agent_experiment_record_writes_json(
    tmp_path,
):
    record = AgentExperimentRecord(
        incident_id="INC-001",
        model=LLM_MODEL_GPT_5_4_MINI,
        hypotheses=[],
        evidence_ids=["LOG-001-02"],
        tool_history=[],
        stop_reason="tool_budget_exhausted",
        stop_reasoning="Maximum number of tool calls reached.",
        result=RCAResult(
            incident_id="INC-001",
            root_cause="Database connection pool exhaustion.",
            affected_service="checkout-service",
            evidence_ids=["LOG-001-02"],
            explanation="Connection acquisition timed out.",
            confidence=0.9,
        ),
        latency_ms=100.0,
        timestamp=datetime(
            2026,
            9,
            25,
            tzinfo=UTC,
        ),
    )

    output_path = tmp_path / "agent.json"

    result_path = save_agent_experiment_record(
        record,
        output_path,
    )

    assert result_path == output_path
    assert output_path.exists()

    content = output_path.read_text(encoding="utf-8")

    assert '"incident_id": "INC-001"' in content
    assert '"approach": "agent"' in content


def test_save_agent_experiment_record_creates_parent_directory(
    tmp_path,
):
    record = AgentExperimentRecord(
        incident_id="INC-001",
        model=LLM_MODEL_GPT_5_4_MINI,
        hypotheses=[],
        evidence_ids=["LOG-001-02"],
        tool_history=[],
        result=RCAResult(
            incident_id="INC-001",
            root_cause="Database connection pool exhaustion.",
            affected_service="checkout-service",
            evidence_ids=["LOG-001-02"],
            explanation="Connection acquisition timed out.",
            confidence=0.9,
        ),
        latency_ms=100.0,
        timestamp=datetime(
            2026,
            9,
            25,
            tzinfo=UTC,
        ),
    )

    output_path = tmp_path / "nested" / "results" / "agent.json"

    save_agent_experiment_record(
        record,
        output_path,
    )

    assert output_path.exists()
    assert output_path.parent.exists()


@pytest.fixture
def failed_record():
    from traceroot.agent.state import InvestigationState
    from traceroot.domain.incident import Incident
    from traceroot.experiments.models import FailedAgentExperimentRecord, FailureStage

    return FailedAgentExperimentRecord(
        model=LLM_MODEL_GPT_5_4_MINI,
        state=InvestigationState(
            incident=Incident(
                id="INC-001",
                title="Latency",
                description="Requests slow",
                start_time=datetime(2026, 9, 25, tzinfo=UTC),
                suspected_services=[],
            )
        ),
        failure_stage=FailureStage.HYPOTHESIS_GENERATION,
        failure_type="RuntimeError",
        failure_message="Model output unavailable",
        latency_ms=12,
        timestamp=datetime(2026, 9, 25, tzinfo=UTC),
        input_tokens=None,
        output_tokens=5,
        llm_calls=1,
    )


def test_historical_successful_agent_record_loads_unchanged():
    from pathlib import Path

    path = (
        Path(__file__).resolve().parents[2]
        / "experiments/comparison/raw/INC-001-agent.json"
    )
    payload = json.loads(path.read_text())
    record = AgentExperimentRecord.model_validate(payload)
    assert record.result.incident_id == payload["incident_id"]
    assert "status" not in record.model_dump()
    assert AgentExperimentRecord.model_fields["result"].is_required()


def test_failed_agent_record_round_trips(tmp_path, failed_record):
    from traceroot.experiments.models import FailedAgentExperimentRecord
    from traceroot.experiments.persistence import save_failed_agent_experiment_record

    path = save_failed_agent_experiment_record(failed_record, tmp_path / "agent.json")
    assert (
        FailedAgentExperimentRecord.model_validate_json(path.read_text())
        == failed_record
    )
    assert set(json.loads(path.read_text())) == {
        "status",
        "approach",
        "model",
        "state",
        "failure_stage",
        "failure_type",
        "failure_message",
        "latency_ms",
        "timestamp",
        "input_tokens",
        "output_tokens",
        "llm_calls",
    }


def test_failed_agent_record_cannot_load_as_successful_record(failed_record):
    from pydantic import ValidationError

    with pytest.raises(ValidationError) as error:
        AgentExperimentRecord.model_validate_json(failed_record.model_dump_json())
    assert any(item["loc"] == ("result",) for item in error.value.errors())


def test_failure_save_preserves_existing_successful_trace(tmp_path, failed_record):
    from traceroot.experiments.persistence import save_failed_agent_experiment_record

    target = tmp_path / "INC-001-agent.json"
    target.write_text("original success")
    failure_path = save_failed_agent_experiment_record(failed_record, target)
    assert target.read_text() == "original success"
    assert failure_path.parent == tmp_path / "failures"
    assert failure_path.name.startswith("INC-001-agent-failed-")


def test_repeated_failure_saves_use_distinct_paths(tmp_path, failed_record):
    from traceroot.experiments.persistence import save_failed_agent_experiment_record

    paths = [
        save_failed_agent_experiment_record(failed_record, tmp_path / "agent.json")
        for _ in range(2)
    ]
    assert paths[0] != paths[1]
    assert all(path.exists() for path in paths)


@pytest.mark.parametrize("directory", ["results", "results/live", "results/ui"])
def test_failure_save_preserves_caller_directory_routing(
    tmp_path, failed_record, directory
):
    from traceroot.experiments.persistence import save_failed_agent_experiment_record

    target = tmp_path / directory / "agent.json"
    path = save_failed_agent_experiment_record(failed_record, str(target))
    assert path.parent == target.parent / "failures"
    assert not target.exists()


def test_failure_save_publishes_complete_json_atomically(tmp_path, failed_record):
    from pathlib import Path
    from unittest.mock import patch

    from traceroot.experiments.persistence import save_failed_agent_experiment_record

    replace = Path.replace
    publications = []

    def inspect_replace(source, destination):
        assert source.parent == destination.parent
        assert not destination.exists()
        assert json.loads(source.read_text()) == failed_record.model_dump(mode="json")
        publications.append(destination)
        return replace(source, destination)

    with patch.object(Path, "replace", inspect_replace):
        path = save_failed_agent_experiment_record(
            failed_record, tmp_path / "agent.json"
        )
    assert publications == [path]
    assert list(path.parent.iterdir()) == [path]


@pytest.mark.parametrize("failure_point", ["write", "replace"])
def test_failure_save_error_does_not_publish_partial_json(
    tmp_path, failed_record, failure_point
):
    from pathlib import Path
    from unittest.mock import patch

    from traceroot.experiments import persistence

    error = OSError("write failed")
    if failure_point == "replace":
        failing_patch = patch.object(Path, "replace", side_effect=error)
    else:
        original = persistence.NamedTemporaryFile

        def broken_file(**kwargs):
            temporary = original(**kwargs)

            def write_partial(text):
                temporary.file.write(text[:5])
                raise error

            temporary.write = write_partial
            return temporary

        failing_patch = patch.object(
            persistence, "NamedTemporaryFile", side_effect=broken_file
        )
    with failing_patch, pytest.raises(OSError) as caught:
        persistence.save_failed_agent_experiment_record(
            failed_record, tmp_path / "agent.json"
        )
    assert caught.value is error
    assert list((tmp_path / "failures").iterdir()) == []


def test_failure_serialization_precedes_directory_creation(tmp_path, failed_record):
    from unittest.mock import patch

    from traceroot.experiments.models import FailedAgentExperimentRecord
    from traceroot.experiments.persistence import save_failed_agent_experiment_record

    with (
        patch.object(
            FailedAgentExperimentRecord,
            "model_dump_json",
            side_effect=ValueError("bad serialization"),
        ),
        pytest.raises(ValueError),
    ):
        save_failed_agent_experiment_record(failed_record, tmp_path / "agent.json")
    assert not (tmp_path / "failures").exists()
