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
from traceroot.llm.usage import LLMUsage


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
    mock_investigate.side_effect = lambda state, max_tool_calls, llm_usage: state
    mock_verify_hypotheses.side_effect = lambda state, llm_usage: state
    mock_generate_final_rca.return_value = final_state

    run_agent_experiment(
        incident=incident,
        output_path=Path("agent.json"),
    )

    mock_generate_hypotheses.assert_called_once()

    call_args = mock_generate_hypotheses.call_args

    mock_generate_hypotheses.assert_called_once()

    call_args = mock_generate_hypotheses.call_args

    assert call_args.kwargs["incident"] == incident
    assert isinstance(
        call_args.kwargs["llm_usage"],
        LLMUsage,
    )


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
    mock_investigate.side_effect = lambda state, max_tool_calls, llm_usage: state
    mock_verify_hypotheses.side_effect = lambda state, llm_usage: state
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
    mock_investigate.side_effect = lambda state, max_tool_calls, llm_usage: state
    mock_verify_hypotheses.side_effect = lambda state, llm_usage: state
    mock_generate_final_rca.return_value = final_state

    run_agent_experiment(
        incident=incident,
        output_path=Path("agent.json"),
        max_tool_calls=4,
    )

    assert mock_investigate.call_args.kwargs["max_tool_calls"] == 4
    assert isinstance(
        mock_investigate.call_args.kwargs["llm_usage"],
        LLMUsage,
    )


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
    mock_investigate.side_effect = lambda state, max_tool_calls, llm_usage: state
    mock_verify_hypotheses.side_effect = lambda state, llm_usage: state
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
    mock_investigate.side_effect = lambda state, max_tool_calls, llm_usage: state
    mock_verify_hypotheses.side_effect = lambda state, llm_usage: state
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
    mock_investigate.side_effect = lambda state, max_tool_calls, llm_usage: state
    mock_verify_hypotheses.side_effect = lambda state, llm_usage: state
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
    mock_investigate.side_effect = lambda state, max_tool_calls, llm_usage: state
    mock_verify_hypotheses.side_effect = lambda state, llm_usage: state
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
    mock_investigate.side_effect = lambda state, max_tool_calls, llm_usage: state
    mock_verify_hypotheses.side_effect = lambda state, llm_usage: state
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
    mock_investigate.side_effect = lambda state, max_tool_calls, llm_usage: state
    mock_verify_hypotheses.side_effect = lambda state, llm_usage: state
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
    mock_investigate.side_effect = lambda state, max_tool_calls, llm_usage: state
    mock_verify_hypotheses.side_effect = lambda state, llm_usage: state
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
    mock_investigate.side_effect = lambda state, max_tool_calls, llm_usage: state
    mock_verify_hypotheses.side_effect = lambda state, llm_usage: state
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
    mock_investigate.side_effect = lambda state, max_tool_calls, llm_usage: state
    mock_verify_hypotheses.side_effect = lambda state, llm_usage: state
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
    mock_investigate.side_effect = lambda state, max_tool_calls, llm_usage: state
    mock_verify_hypotheses.side_effect = lambda state, llm_usage: state
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
    mock_investigate.side_effect = lambda state, max_tool_calls, llm_usage: state
    mock_verify_hypotheses.side_effect = lambda state, llm_usage: state
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
    mock_investigate.side_effect = lambda state, max_tool_calls, llm_usage: state
    mock_verify_hypotheses.side_effect = lambda state, llm_usage: state
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


@patch("traceroot.experiments.agent.save_agent_experiment_record")
@patch("traceroot.experiments.agent.generate_final_rca")
@patch("traceroot.experiments.agent.verify_hypotheses")
@patch("traceroot.experiments.agent.investigate")
@patch("traceroot.experiments.agent.generate_hypotheses")
def test_run_agent_experiment_shares_llm_usage_across_agent_stages(
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
    mock_investigate.side_effect = lambda state, max_tool_calls, llm_usage: state
    mock_verify_hypotheses.side_effect = lambda state, llm_usage: state
    mock_generate_final_rca.return_value = final_state

    run_agent_experiment(
        incident=incident,
        output_path=Path("agent.json"),
    )

    hypothesis_usage = mock_generate_hypotheses.call_args.kwargs["llm_usage"]
    investigation_usage = mock_investigate.call_args.kwargs["llm_usage"]
    verification_usage = mock_verify_hypotheses.call_args.kwargs["llm_usage"]
    final_rca_usage = mock_generate_final_rca.call_args.kwargs["llm_usage"]

    assert isinstance(hypothesis_usage, LLMUsage)

    assert investigation_usage is hypothesis_usage
    assert verification_usage is hypothesis_usage
    assert final_rca_usage is hypothesis_usage


@patch("traceroot.experiments.agent.save_agent_experiment_record")
@patch("traceroot.experiments.agent.generate_final_rca")
@patch("traceroot.experiments.agent.verify_hypotheses")
@patch("traceroot.experiments.agent.investigate")
@patch("traceroot.experiments.agent.generate_hypotheses")
@patch("traceroot.experiments.agent.LLM_MODEL_GPT_5_4_MINI", "gpt-5.4-mini")
def test_run_agent_experiment_persists_accumulated_llm_usage(
    mock_generate_hypotheses,
    mock_investigate,
    mock_verify_hypotheses,
    mock_generate_final_rca,
    mock_save,
):
    incident = create_test_incident()
    hypotheses = create_test_hypotheses()
    final_state = create_final_state()

    def generate_hypotheses_side_effect(
        incident,
        llm_usage,
    ):
        llm_usage.add(
            input_tokens=100,
            output_tokens=20,
        )
        return hypotheses

    def investigate_side_effect(
        state,
        max_tool_calls,
        llm_usage,
    ):
        llm_usage.add(
            input_tokens=200,
            output_tokens=40,
        )
        return state

    def verify_side_effect(
        state,
        llm_usage,
    ):
        llm_usage.add(
            input_tokens=150,
            output_tokens=30,
        )
        return state

    def final_rca_side_effect(
        state,
        llm_usage,
    ):
        llm_usage.add(
            input_tokens=250,
            output_tokens=50,
        )
        return final_state

    mock_generate_hypotheses.side_effect = generate_hypotheses_side_effect
    mock_investigate.side_effect = investigate_side_effect
    mock_verify_hypotheses.side_effect = verify_side_effect
    mock_generate_final_rca.side_effect = final_rca_side_effect

    record = run_agent_experiment(
        incident=incident,
        output_path=Path("agent.json"),
    )

    assert record.input_tokens == 700
    assert record.output_tokens == 140
    assert record.llm_calls == 4
    assert record.estimated_cost_usd == pytest.approx(0.001155)


@patch("traceroot.experiments.agent.save_agent_experiment_record")
@patch("traceroot.experiments.agent.generate_final_rca")
@patch("traceroot.experiments.agent.verify_hypotheses")
@patch("traceroot.experiments.agent.investigate")
@patch("traceroot.experiments.agent.generate_hypotheses")
@pytest.mark.parametrize(
    "input_tokens, output_tokens",
    [(None, None), (None, 20), (100, None)],
)
def test_run_agent_experiment_preserves_unavailable_llm_usage(
    mock_generate_hypotheses,
    mock_investigate,
    mock_verify_hypotheses,
    mock_generate_final_rca,
    mock_save,
    input_tokens,
    output_tokens,
):
    incident = create_test_incident()
    hypotheses = create_test_hypotheses()
    final_state = create_final_state()

    def generate_hypotheses_side_effect(
        incident,
        llm_usage,
    ):
        llm_usage.add(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        return hypotheses

    mock_generate_hypotheses.side_effect = generate_hypotheses_side_effect

    mock_investigate.side_effect = lambda state, max_tool_calls, llm_usage: state
    mock_verify_hypotheses.side_effect = lambda state, llm_usage: state
    mock_generate_final_rca.return_value = final_state

    record = run_agent_experiment(
        incident=incident,
        output_path=Path("agent.json"),
    )

    assert record.input_tokens == input_tokens
    assert record.output_tokens == output_tokens
    assert record.llm_calls == 1
    assert record.estimated_cost_usd is None
