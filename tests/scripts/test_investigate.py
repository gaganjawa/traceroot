from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.investigate import (
    build_parser,
    build_paths,
    print_agent_result,
    run_investigation,
)
from traceroot.agent.state import Hypothesis, HypothesisStatus, ToolCallRecord
from traceroot.domain.incident import Incident
from traceroot.domain.rca import RCAResult
from traceroot.experiments.models import AgentExperimentRecord


def create_record() -> AgentExperimentRecord:
    return AgentExperimentRecord(
        incident_id="INC-001",
        approach="agent",
        model="gpt-5.4-mini",
        hypotheses=[
            Hypothesis(
                description="Database connection pool exhaustion",
                status=HypothesisStatus.SUPPORTED,
            )
        ],
        evidence_ids=["LOG-001-02", "METRIC-001-02"],
        tool_history=[
            ToolCallRecord(
                tool_name="logs",
                service="checkout-service",
                evidence_ids=["LOG-001-02"],
                observations=["Database connection timeout"],
                reasoning="Check checkout logs",
            )
        ],
        stop_reason="model_stop",
        stop_reasoning="Enough evidence gathered",
        result=RCAResult(
            incident_id="INC-001",
            root_cause="Database connection pool exhaustion",
            affected_service="checkout-service",
            evidence_ids=["LOG-001-02", "METRIC-001-02"],
            explanation="Database connections were exhausted.",
            confidence=0.95,
        ),
        latency_ms=1000,
        timestamp=datetime.now(UTC),
    )


def test_parser_requires_incident_id():
    parser = build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args([])


def test_parser_uses_default_max_tool_calls():
    parser = build_parser()

    args = parser.parse_args(["--incident-id", "INC-001"])

    assert args.incident_id == "INC-001"
    assert args.max_tool_calls == 6


def test_parser_accepts_custom_max_tool_calls():
    parser = build_parser()

    args = parser.parse_args(
        [
            "--incident-id",
            "INC-001",
            "--max-tool-calls",
            "4",
        ]
    )

    assert args.max_tool_calls == 4


def test_build_paths_returns_correct_paths():
    incident_path, output_path = build_paths("INC-001")

    assert incident_path == Path("data/incidents/INC-001/incident.json")
    assert output_path == Path("experiments/results/INC-001-agent.json")


def test_run_investigation_fails_for_missing_incident(tmp_path):
    incident_path = tmp_path / "missing.json"
    output_path = tmp_path / "result.json"

    with patch(
        "scripts.investigate.build_paths",
        return_value=(incident_path, output_path),
    ), pytest.raises(
        FileNotFoundError,
        match="Incident not found: INC-999",
    ):
        run_investigation("INC-999", 6)


def test_run_investigation_loads_incident(tmp_path):
    incident_path = tmp_path / "incident.json"
    incident_path.write_text("{}", encoding="utf-8")
    output_path = tmp_path / "result.json"

    incident = Incident(
        id="INC-001",
        title="Checkout failure",
        description="Checkout requests are timing out.",
        start_time=datetime(2026, 9, 25, tzinfo=UTC),
        suspected_services=["checkout-service"],
    )

    record = create_record()

    with (
        patch(
            "scripts.investigate.build_paths",
            return_value=(incident_path, output_path),
        ),
        patch(
            "scripts.investigate.load_incident",
            return_value=incident,
        ) as mock_load,
        patch(
            "scripts.investigate.run_agent_experiment",
            return_value=record,
        ),
    ):
        run_investigation("INC-001", 6)

    mock_load.assert_called_once_with(incident_path)


def test_run_investigation_calls_agent_experiment(tmp_path):
    incident_path = tmp_path / "incident.json"
    incident_path.write_text("{}", encoding="utf-8")
    output_path = tmp_path / "result.json"

    incident = Incident(
        id="INC-001",
        title="Checkout failure",
        description="Checkout requests are timing out.",
        start_time=datetime(2026, 9, 25, tzinfo=UTC),
        suspected_services=["checkout-service"],
    )

    record = create_record()

    with (
        patch(
            "scripts.investigate.build_paths",
            return_value=(incident_path, output_path),
        ),
        patch(
            "scripts.investigate.load_incident",
            return_value=incident,
        ),
        patch(
            "scripts.investigate.run_agent_experiment",
            return_value=record,
        ) as mock_run,
    ):
        result = run_investigation("INC-001", 4)

    mock_run.assert_called_once_with(
        incident=incident,
        output_path=output_path,
        max_tool_calls=4,
    )

    assert result == record


def test_print_agent_result_prints_expected_output(capsys):
    record = create_record()
    output_path = Path("experiments/results/INC-001-agent.json")

    print_agent_result(record, output_path)

    output = capsys.readouterr().out

    assert "INC-001" in output
    assert "gpt-5.4-mini" in output
    assert "Database connection pool exhaustion" in output
    assert "supported" in output
    assert "logs / checkout-service" in output
    assert "LOG-001-02" in output
    assert "model_stop" in output
    assert "Enough evidence gathered" in output
    assert "checkout-service" in output
    assert "0.95" in output
    assert str(output_path) in output
