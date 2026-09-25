from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from traceroot.agent.state import (
    Hypothesis,
    HypothesisStatus,
    InvestigationState,
    ToolCallRecord,
)
from traceroot.domain.incident import Incident
from traceroot.domain.rca import RCAResult
from traceroot.experiments.agent import run_agent_experiment
from traceroot.llm.client import LLM_MODEL_GPT_5_4_MINI


def create_test_incident() -> Incident:
    return Incident(
        id="INC-001",
        title="Checkout latency",
        description="Checkout requests are slow.",
        start_time=datetime(2026, 9, 25, tzinfo=UTC),
        suspected_services=["checkout-service"],
    )


def create_test_hypotheses() -> list[Hypothesis]:
    return [
        Hypothesis(
            description="Database connection pool exhaustion",
            status=HypothesisStatus.OPEN,
        )
    ]


def create_final_state() -> InvestigationState:
    incident = create_test_incident()

    return InvestigationState(
        incident=incident,
        hypotheses=[
            Hypothesis(
                description="Database connection pool exhaustion",
                status=HypothesisStatus.SUPPORTED,
            )
        ],
        evidence_ids=[
            "LOG-001-02",
            "CHANGE-001-01",
        ],
        tool_history=[
            ToolCallRecord(
                tool_name="logs",
                service="checkout-service",
                evidence_ids=["LOG-001-02"],
                observations=["Database connection acquisition timeout"],
                reasoning="Check database-related failures.",
            )
        ],
        stop_reason="tool_budget_exhausted",
        stop_reasoning="Maximum number of tool calls reached.",
        final_result=RCAResult(
            incident_id="INC-001",
            root_cause="Database connection pool was undersized.",
            affected_service="checkout-service",
            evidence_ids=[
                "LOG-001-02",
                "CHANGE-001-01",
            ],
            explanation=("Evidence indicates database connection pool exhaustion."),
            confidence=0.95,
        ),
    )


@patch("traceroot.experiments.agent.save_agent_experiment_record")
@patch("traceroot.experiments.agent.generate_final_rca")
@patch("traceroot.experiments.agent.verify_hypotheses")
@patch("traceroot.experiments.agent.investigate")
@patch("traceroot.experiments.agent.generate_hypotheses")
def test_run_agent_experiment_generates_hypotheses(
    mock_generate_hypotheses,
    mock_investigate,
    mock_verify_hypotheses,
    mock_generate_final_rca,
    mock_save,
):
    incident = create_test_incident()
    hypotheses = create_test_hypotheses()
    final_state = create_final_state()

    mock_generate_hypotheses.return_value = hypotheses
    mock_investigate.side_effect = lambda state, max_tool_calls: state
    mock_verify_hypotheses.side_effect = lambda state: state
    mock_generate_final_rca.return_value = final_state

    run_agent_experiment(
        incident=incident,
        output_path=Path("agent.json"),
    )

    mock_generate_hypotheses.assert_called_once_with(incident)


@patch("traceroot.experiments.agent.save_agent_experiment_record")
@patch("traceroot.experiments.agent.generate_final_rca")
@patch("traceroot.experiments.agent.verify_hypotheses")
@patch("traceroot.experiments.agent.investigate")
@patch("traceroot.experiments.agent.generate_hypotheses")
def test_run_agent_experiment_creates_initial_state(
    mock_generate_hypotheses,
    mock_investigate,
    mock_verify_hypotheses,
    mock_generate_final_rca,
    mock_save,
):
    incident = create_test_incident()
    hypotheses = create_test_hypotheses()
    final_state = create_final_state()

    mock_generate_hypotheses.return_value = hypotheses
    mock_investigate.side_effect = lambda state, max_tool_calls: state
    mock_verify_hypotheses.side_effect = lambda state: state
    mock_generate_final_rca.return_value = final_state

    run_agent_experiment(
        incident=incident,
        output_path=Path("agent.json"),
    )

    investigation_state = mock_investigate.call_args.kwargs["state"]

    assert investigation_state.incident == incident
    assert investigation_state.hypotheses == hypotheses


@patch("traceroot.experiments.agent.save_agent_experiment_record")
@patch("traceroot.experiments.agent.generate_final_rca")
@patch("traceroot.experiments.agent.verify_hypotheses")
@patch("traceroot.experiments.agent.investigate")
@patch("traceroot.experiments.agent.generate_hypotheses")
def test_run_agent_experiment_calls_investigate_with_max_tool_calls(
    mock_generate_hypotheses,
    mock_investigate,
    mock_verify_hypotheses,
    mock_generate_final_rca,
    mock_save,
):
    incident = create_test_incident()
    final_state = create_final_state()

    mock_generate_hypotheses.return_value = create_test_hypotheses()
    mock_investigate.side_effect = lambda state, max_tool_calls: state
    mock_verify_hypotheses.side_effect = lambda state: state
    mock_generate_final_rca.return_value = final_state

    run_agent_experiment(
        incident=incident,
        output_path=Path("agent.json"),
        max_tool_calls=4,
    )

    assert mock_investigate.call_args.kwargs["max_tool_calls"] == 4


@patch("traceroot.experiments.agent.save_agent_experiment_record")
@patch("traceroot.experiments.agent.generate_final_rca")
@patch("traceroot.experiments.agent.verify_hypotheses")
@patch("traceroot.experiments.agent.investigate")
@patch("traceroot.experiments.agent.generate_hypotheses")
def test_run_agent_experiment_verifies_hypotheses(
    mock_generate_hypotheses,
    mock_investigate,
    mock_verify_hypotheses,
    mock_generate_final_rca,
    mock_save,
):
    incident = create_test_incident()
    final_state = create_final_state()

    mock_generate_hypotheses.return_value = create_test_hypotheses()
    mock_investigate.side_effect = lambda state, max_tool_calls: state
    mock_verify_hypotheses.side_effect = lambda state: state
    mock_generate_final_rca.return_value = final_state

    run_agent_experiment(
        incident=incident,
        output_path=Path("agent.json"),
    )

    mock_verify_hypotheses.assert_called_once()


@patch("traceroot.experiments.agent.save_agent_experiment_record")
@patch("traceroot.experiments.agent.generate_final_rca")
@patch("traceroot.experiments.agent.verify_hypotheses")
@patch("traceroot.experiments.agent.investigate")
@patch("traceroot.experiments.agent.generate_hypotheses")
def test_run_agent_experiment_generates_final_rca(
    mock_generate_hypotheses,
    mock_investigate,
    mock_verify_hypotheses,
    mock_generate_final_rca,
    mock_save,
):
    incident = create_test_incident()
    final_state = create_final_state()

    mock_generate_hypotheses.return_value = create_test_hypotheses()
    mock_investigate.side_effect = lambda state, max_tool_calls: state
    mock_verify_hypotheses.side_effect = lambda state: state
    mock_generate_final_rca.return_value = final_state

    run_agent_experiment(
        incident=incident,
        output_path=Path("agent.json"),
    )

    mock_generate_final_rca.assert_called_once()


@patch("traceroot.experiments.agent.save_agent_experiment_record")
@patch("traceroot.experiments.agent.generate_final_rca")
@patch("traceroot.experiments.agent.verify_hypotheses")
@patch("traceroot.experiments.agent.investigate")
@patch("traceroot.experiments.agent.generate_hypotheses")
def test_run_agent_experiment_sets_agent_approach(
    mock_generate_hypotheses,
    mock_investigate,
    mock_verify_hypotheses,
    mock_generate_final_rca,
    mock_save,
):
    incident = create_test_incident()
    final_state = create_final_state()

    mock_generate_hypotheses.return_value = create_test_hypotheses()
    mock_investigate.side_effect = lambda state, max_tool_calls: state
    mock_verify_hypotheses.side_effect = lambda state: state
    mock_generate_final_rca.return_value = final_state

    record = run_agent_experiment(
        incident=incident,
        output_path=Path("agent.json"),
    )

    assert record.approach == "agent"


@patch("traceroot.experiments.agent.save_agent_experiment_record")
@patch("traceroot.experiments.agent.generate_final_rca")
@patch("traceroot.experiments.agent.verify_hypotheses")
@patch("traceroot.experiments.agent.investigate")
@patch("traceroot.experiments.agent.generate_hypotheses")
def test_run_agent_experiment_records_model(
    mock_generate_hypotheses,
    mock_investigate,
    mock_verify_hypotheses,
    mock_generate_final_rca,
    mock_save,
):
    incident = create_test_incident()
    final_state = create_final_state()

    mock_generate_hypotheses.return_value = create_test_hypotheses()
    mock_investigate.side_effect = lambda state, max_tool_calls: state
    mock_verify_hypotheses.side_effect = lambda state: state
    mock_generate_final_rca.return_value = final_state

    record = run_agent_experiment(
        incident=incident,
        output_path=Path("agent.json"),
    )

    assert record.model == LLM_MODEL_GPT_5_4_MINI


@patch("traceroot.experiments.agent.save_agent_experiment_record")
@patch("traceroot.experiments.agent.generate_final_rca")
@patch("traceroot.experiments.agent.verify_hypotheses")
@patch("traceroot.experiments.agent.investigate")
@patch("traceroot.experiments.agent.generate_hypotheses")
def test_run_agent_experiment_persists_hypotheses(
    mock_generate_hypotheses,
    mock_investigate,
    mock_verify_hypotheses,
    mock_generate_final_rca,
    mock_save,
):
    incident = create_test_incident()
    final_state = create_final_state()

    mock_generate_hypotheses.return_value = create_test_hypotheses()
    mock_investigate.side_effect = lambda state, max_tool_calls: state
    mock_verify_hypotheses.side_effect = lambda state: state
    mock_generate_final_rca.return_value = final_state

    record = run_agent_experiment(
        incident=incident,
        output_path=Path("agent.json"),
    )

    assert record.hypotheses == final_state.hypotheses


@patch("traceroot.experiments.agent.save_agent_experiment_record")
@patch("traceroot.experiments.agent.generate_final_rca")
@patch("traceroot.experiments.agent.verify_hypotheses")
@patch("traceroot.experiments.agent.investigate")
@patch("traceroot.experiments.agent.generate_hypotheses")
def test_run_agent_experiment_persists_evidence_ids(
    mock_generate_hypotheses,
    mock_investigate,
    mock_verify_hypotheses,
    mock_generate_final_rca,
    mock_save,
):
    incident = create_test_incident()
    final_state = create_final_state()

    mock_generate_hypotheses.return_value = create_test_hypotheses()
    mock_investigate.side_effect = lambda state, max_tool_calls: state
    mock_verify_hypotheses.side_effect = lambda state: state
    mock_generate_final_rca.return_value = final_state

    record = run_agent_experiment(
        incident=incident,
        output_path=Path("agent.json"),
    )

    assert record.evidence_ids == final_state.evidence_ids


@patch("traceroot.experiments.agent.save_agent_experiment_record")
@patch("traceroot.experiments.agent.generate_final_rca")
@patch("traceroot.experiments.agent.verify_hypotheses")
@patch("traceroot.experiments.agent.investigate")
@patch("traceroot.experiments.agent.generate_hypotheses")
def test_run_agent_experiment_persists_tool_history(
    mock_generate_hypotheses,
    mock_investigate,
    mock_verify_hypotheses,
    mock_generate_final_rca,
    mock_save,
):
    incident = create_test_incident()
    final_state = create_final_state()

    mock_generate_hypotheses.return_value = create_test_hypotheses()
    mock_investigate.side_effect = lambda state, max_tool_calls: state
    mock_verify_hypotheses.side_effect = lambda state: state
    mock_generate_final_rca.return_value = final_state

    record = run_agent_experiment(
        incident=incident,
        output_path=Path("agent.json"),
    )

    assert record.tool_history == final_state.tool_history


@patch("traceroot.experiments.agent.save_agent_experiment_record")
@patch("traceroot.experiments.agent.generate_final_rca")
@patch("traceroot.experiments.agent.verify_hypotheses")
@patch("traceroot.experiments.agent.investigate")
@patch("traceroot.experiments.agent.generate_hypotheses")
def test_run_agent_experiment_persists_stop_information(
    mock_generate_hypotheses,
    mock_investigate,
    mock_verify_hypotheses,
    mock_generate_final_rca,
    mock_save,
):
    incident = create_test_incident()
    final_state = create_final_state()

    mock_generate_hypotheses.return_value = create_test_hypotheses()
    mock_investigate.side_effect = lambda state, max_tool_calls: state
    mock_verify_hypotheses.side_effect = lambda state: state
    mock_generate_final_rca.return_value = final_state

    record = run_agent_experiment(
        incident=incident,
        output_path=Path("agent.json"),
    )

    assert record.stop_reason == final_state.stop_reason
    assert record.stop_reasoning == final_state.stop_reasoning


@patch("traceroot.experiments.agent.save_agent_experiment_record")
@patch("traceroot.experiments.agent.generate_final_rca")
@patch("traceroot.experiments.agent.verify_hypotheses")
@patch("traceroot.experiments.agent.investigate")
@patch("traceroot.experiments.agent.generate_hypotheses")
def test_run_agent_experiment_persists_final_result(
    mock_generate_hypotheses,
    mock_investigate,
    mock_verify_hypotheses,
    mock_generate_final_rca,
    mock_save,
):
    incident = create_test_incident()
    final_state = create_final_state()

    mock_generate_hypotheses.return_value = create_test_hypotheses()
    mock_investigate.side_effect = lambda state, max_tool_calls: state
    mock_verify_hypotheses.side_effect = lambda state: state
    mock_generate_final_rca.return_value = final_state

    record = run_agent_experiment(
        incident=incident,
        output_path=Path("agent.json"),
    )

    assert record.result == final_state.final_result


@patch("traceroot.experiments.agent.save_agent_experiment_record")
@patch("traceroot.experiments.agent.generate_final_rca")
@patch("traceroot.experiments.agent.verify_hypotheses")
@patch("traceroot.experiments.agent.investigate")
@patch("traceroot.experiments.agent.generate_hypotheses")
def test_run_agent_experiment_records_nonnegative_latency(
    mock_generate_hypotheses,
    mock_investigate,
    mock_verify_hypotheses,
    mock_generate_final_rca,
    mock_save,
):
    incident = create_test_incident()
    final_state = create_final_state()

    mock_generate_hypotheses.return_value = create_test_hypotheses()
    mock_investigate.side_effect = lambda state, max_tool_calls: state
    mock_verify_hypotheses.side_effect = lambda state: state
    mock_generate_final_rca.return_value = final_state

    record = run_agent_experiment(
        incident=incident,
        output_path=Path("agent.json"),
    )

    assert record.latency_ms >= 0


@patch("traceroot.experiments.agent.save_agent_experiment_record")
@patch("traceroot.experiments.agent.generate_final_rca")
@patch("traceroot.experiments.agent.verify_hypotheses")
@patch("traceroot.experiments.agent.investigate")
@patch("traceroot.experiments.agent.generate_hypotheses")
def test_run_agent_experiment_uses_timezone_aware_timestamp(
    mock_generate_hypotheses,
    mock_investigate,
    mock_verify_hypotheses,
    mock_generate_final_rca,
    mock_save,
):
    incident = create_test_incident()
    final_state = create_final_state()

    mock_generate_hypotheses.return_value = create_test_hypotheses()
    mock_investigate.side_effect = lambda state, max_tool_calls: state
    mock_verify_hypotheses.side_effect = lambda state: state
    mock_generate_final_rca.return_value = final_state

    record = run_agent_experiment(
        incident=incident,
        output_path=Path("agent.json"),
    )

    assert record.timestamp.tzinfo is not None
    assert record.timestamp.utcoffset() is not None


@patch("traceroot.experiments.agent.save_agent_experiment_record")
@patch("traceroot.experiments.agent.generate_final_rca")
@patch("traceroot.experiments.agent.verify_hypotheses")
@patch("traceroot.experiments.agent.investigate")
@patch("traceroot.experiments.agent.generate_hypotheses")
def test_run_agent_experiment_calls_persistence(
    mock_generate_hypotheses,
    mock_investigate,
    mock_verify_hypotheses,
    mock_generate_final_rca,
    mock_save,
):
    incident = create_test_incident()
    final_state = create_final_state()
    output_path = Path("experiments/results/agent.json")

    mock_generate_hypotheses.return_value = create_test_hypotheses()
    mock_investigate.side_effect = lambda state, max_tool_calls: state
    mock_verify_hypotheses.side_effect = lambda state: state
    mock_generate_final_rca.return_value = final_state

    record = run_agent_experiment(
        incident=incident,
        output_path=output_path,
    )

    mock_save.assert_called_once_with(
        record,
        output_path,
    )


@patch("traceroot.experiments.agent.save_agent_experiment_record")
@patch("traceroot.experiments.agent.generate_final_rca")
@patch("traceroot.experiments.agent.verify_hypotheses")
@patch("traceroot.experiments.agent.investigate")
@patch("traceroot.experiments.agent.generate_hypotheses")
def test_run_agent_experiment_raises_when_final_result_missing(
    mock_generate_hypotheses,
    mock_investigate,
    mock_verify_hypotheses,
    mock_generate_final_rca,
    mock_save,
):
    incident = create_test_incident()

    state = InvestigationState(
        incident=incident,
        evidence_ids=["LOG-001-02"],
    )

    mock_generate_hypotheses.return_value = []
    mock_investigate.return_value = state
    mock_verify_hypotheses.return_value = state
    mock_generate_final_rca.return_value = state

    with pytest.raises(
        RuntimeError,
        match="did not produce a final RCA",
    ):
        run_agent_experiment(
            incident=incident,
            output_path=Path("agent.json"),
        )

    mock_save.assert_not_called()
