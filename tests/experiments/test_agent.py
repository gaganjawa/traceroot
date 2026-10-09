import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from traceroot.agent.grounding import ClaimAssessment, ClaimVerificationReport
from traceroot.agent.investigation import ToolSelection
from traceroot.agent.rca import GeneratedFinalRCA
from traceroot.agent.state import (
    Hypothesis,
    HypothesisStatus,
    InvestigationState,
    ToolCallRecord,
)
from traceroot.bootstrap import build_live_runtime
from traceroot.config import LiveEvidenceConfig
from traceroot.data.models import LogEntry
from traceroot.domain.incident import Incident
from traceroot.domain.rca import RCAResult
from traceroot.experiments.agent import run_agent_experiment
from traceroot.llm.client import LLM_MODEL_GPT_5_4_MINI
from traceroot.llm.usage import LLMUsage
from traceroot.tools import interface
from traceroot.tools.models import ToolName


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


@patch("traceroot.experiments.agent.save_agent_experiment_record")
@patch("traceroot.experiments.agent.generate_final_rca")
@patch("traceroot.experiments.agent.verify_hypotheses")
@patch("traceroot.experiments.agent.investigate")
@patch("traceroot.experiments.agent.generate_hypotheses")
def test_run_agent_experiment_preserves_default_investigate_call(
    mock_generate_hypotheses,
    mock_investigate,
    mock_verify_hypotheses,
    mock_generate_final_rca,
    mock_save,
):
    incident = create_test_incident()
    mock_generate_hypotheses.return_value = create_test_hypotheses()
    mock_investigate.side_effect = lambda state, max_tool_calls, llm_usage: state
    mock_verify_hypotheses.side_effect = lambda state, llm_usage: state
    mock_generate_final_rca.return_value = create_final_state()

    record = run_agent_experiment(incident, Path("agent.json"), 4)

    assert set(mock_investigate.call_args.kwargs) == {
        "state",
        "max_tool_calls",
        "llm_usage",
    }
    assert mock_investigate.call_args.kwargs["max_tool_calls"] == 4
    assert mock_investigate.call_args.kwargs["state"].incident is incident
    mock_save.assert_called_once_with(record, Path("agent.json"))


@patch("traceroot.experiments.agent.save_agent_experiment_record")
@patch("traceroot.experiments.agent.generate_final_rca")
@patch("traceroot.experiments.agent.verify_hypotheses")
@patch("traceroot.experiments.agent.investigate")
@patch("traceroot.experiments.agent.generate_hypotheses")
def test_run_agent_experiment_forwards_injected_tool_executor(
    mock_generate_hypotheses,
    mock_investigate,
    mock_verify_hypotheses,
    mock_generate_final_rca,
    mock_save,
):
    incident = create_test_incident()
    executor = MagicMock()
    mock_generate_hypotheses.return_value = create_test_hypotheses()
    mock_investigate.side_effect = (
        lambda state, max_tool_calls, llm_usage, tool_executor: state
    )
    mock_verify_hypotheses.side_effect = lambda state, llm_usage: state
    mock_generate_final_rca.return_value = create_final_state()

    record = run_agent_experiment(
        incident,
        Path("agent.json"),
        4,
        tool_executor=executor,
    )

    assert mock_investigate.call_args.kwargs["tool_executor"] is executor
    assert mock_investigate.call_args.kwargs["state"].incident is incident
    usage = mock_generate_hypotheses.call_args.kwargs["llm_usage"]
    assert mock_investigate.call_args.kwargs["llm_usage"] is usage
    assert mock_verify_hypotheses.call_args.kwargs["llm_usage"] is usage
    assert mock_generate_final_rca.call_args.kwargs["llm_usage"] is usage
    mock_save.assert_called_once_with(record, Path("agent.json"))


@patch("httpx.get", side_effect=AssertionError("Unexpected external HTTP call"))
@patch("traceroot.agent.investigation.execute_tool")
@patch("traceroot.agent.investigation.get_llm_client")
@patch("traceroot.experiments.agent.save_agent_experiment_record")
@patch("traceroot.experiments.agent.generate_final_rca")
@patch("traceroot.experiments.agent.verify_hypotheses")
@patch("traceroot.experiments.agent.generate_hypotheses")
def test_run_agent_experiment_keeps_runtime_router_executors_isolated(
    mock_generate_hypotheses,
    mock_verify_hypotheses,
    mock_generate_final_rca,
    mock_save,
    mock_get_llm_client,
    mock_execute_tool,
    mock_http_get,
):
    incident = create_test_incident()
    config = LiveEvidenceConfig(
        loki_base_url="http://loki.example",
        prometheus_base_url="http://prometheus.example",
        github_repo="example/app",
        github_service="checkout-service",
    )
    mock_generate_hypotheses.side_effect = lambda incident, llm_usage: (
        create_test_hypotheses()
    )
    mock_verify_hypotheses.side_effect = lambda state, llm_usage: state

    def set_final_rca(state, llm_usage):
        state.final_result = RCAResult(
            incident_id=state.incident.id,
            root_cause="Database connection timeout",
            affected_service="checkout-service",
            evidence_ids=state.evidence_ids,
            explanation="The log records a database connection timeout.",
        )
        return state

    mock_generate_final_rca.side_effect = set_final_rca
    mock_get_llm_client.return_value.responses.parse.return_value = MagicMock(
        output_parsed=ToolSelection(
            tool_name=ToolName.LOGS,
            service="checkout-service",
            reasoning="Inspect connection timeouts.",
        ),
        usage=None,
    )
    original_backend = interface._default_backend
    runtimes = [build_live_runtime(config), build_live_runtime(config)]

    for index, runtime in enumerate(runtimes):
        runtime.incident_registry.register(incident)
        entry = LogEntry(
            id=f"LOG-LIVE-SESSION-{index}",
            timestamp=incident.start_time,
            service="checkout-service",
            level="ERROR",
            message="Database connection timeout",
        )
        output_path = Path(f"session-{index}.json")
        with patch.object(
            runtime.live_backend.logs_provider, "query", return_value=[entry]
        ) as provider_query:
            record = run_agent_experiment(
                incident,
                output_path,
                max_tool_calls=1,
                tool_executor=runtime.router.query,
            )

        provider_query.assert_called_once_with(
            incident=incident, service="checkout-service"
        )
        assert record.evidence_ids == [entry.id]
        assert record.tool_history[0].evidence_ids == [entry.id]
        assert record.tool_history[0].service == "checkout-service"
        assert record.tool_history[0].observations == [str(entry)]
        assert record.result.evidence_ids == [entry.id]
        assert record.stop_reason == "tool_budget_exhausted"
        assert record.llm_calls == 1
        assert interface._default_backend is original_backend
        mock_save.assert_called_with(record, output_path)

    assert runtimes[0].incident_registry is not runtimes[1].incident_registry
    assert mock_save.call_count == 2
    mock_execute_tool.assert_not_called()
    mock_http_get.assert_not_called()


@patch("httpx.get", side_effect=AssertionError("Unexpected external HTTP call"))
@patch("traceroot.agent.investigation.execute_tool")
@patch("traceroot.agent.investigation.get_llm_client")
@patch("traceroot.experiments.agent.save_agent_experiment_record")
@patch("traceroot.experiments.agent.generate_final_rca")
@patch("traceroot.experiments.agent.verify_hypotheses")
@patch("traceroot.experiments.agent.generate_hypotheses")
def test_run_agent_experiment_propagates_injected_executor_failure(
    mock_generate_hypotheses,
    mock_verify_hypotheses,
    mock_generate_final_rca,
    mock_save,
    mock_get_llm_client,
    mock_execute_tool,
    mock_http_get,
):
    incident = create_test_incident()
    executor = MagicMock(side_effect=RuntimeError("Live provider unavailable"))
    mock_generate_hypotheses.return_value = create_test_hypotheses()
    mock_get_llm_client.return_value.responses.parse.return_value = MagicMock(
        output_parsed=ToolSelection(
            tool_name=ToolName.LOGS,
            service="checkout-service",
            reasoning="Inspect timeouts.",
        ),
        usage=None,
    )
    original_backend = interface._default_backend

    with pytest.raises(RuntimeError, match="Live provider unavailable"):
        run_agent_experiment(
            incident,
            Path("agent.json"),
            max_tool_calls=1,
            tool_executor=executor,
        )

    executor.assert_called_once_with(
        tool_name=ToolName.LOGS,
        incident_id=incident.id,
        service="checkout-service",
    )
    assert interface._default_backend is original_backend
    mock_execute_tool.assert_not_called()
    mock_http_get.assert_not_called()
    mock_verify_hypotheses.assert_not_called()
    mock_generate_final_rca.assert_not_called()
    mock_save.assert_not_called()


@pytest.mark.parametrize("final_status", ["supported", "unsupported"])
@patch("traceroot.agent.grounding.get_llm_client")
@patch("traceroot.agent.rca.get_llm_client")
@patch("traceroot.experiments.agent.verify_hypotheses")
@patch("traceroot.experiments.agent.investigate")
@patch("traceroot.experiments.agent.generate_hypotheses")
def test_grounded_rca_preserves_experiment_record_and_usage(
    mock_hypotheses,
    mock_investigate,
    mock_verify_hypotheses,
    mock_generator,
    mock_verifier,
    final_status,
    tmp_path,
):
    state = create_final_state()
    candidate = GeneratedFinalRCA(
        **state.final_result.model_dump(exclude={"incident_id"})
    )
    state.final_result = None
    mock_hypotheses.return_value = state.hypotheses
    mock_investigate.return_value = state
    mock_verify_hypotheses.side_effect = lambda state, llm_usage: state
    mock_generator.return_value.responses.parse.return_value = MagicMock(
        output_parsed=candidate,
        usage=MagicMock(input_tokens=100, output_tokens=10),
    )
    mock_verifier.return_value.responses.parse.side_effect = [
        MagicMock(
            output_parsed=ClaimVerificationReport(
                claims=[
                    ClaimAssessment(
                        field="root_cause",
                        claim=candidate.root_cause,
                        is_major_causal_claim=True,
                        status=status,
                        supporting_evidence_ids=["LOG-001-02"],
                        reasoning="Assess observed connection acquisition timeouts.",
                    )
                ]
            ),
            usage=MagicMock(input_tokens=200, output_tokens=20),
        )
        for status in ["unsupported", final_status]
    ]
    output_path = tmp_path / "grounded-agent.json"

    record = run_agent_experiment(state.incident, output_path)

    persisted = json.loads(output_path.read_text())
    assert persisted == record.model_dump(mode="json")
    assert set(persisted) == {
        "incident_id",
        "approach",
        "model",
        "hypotheses",
        "evidence_ids",
        "tool_history",
        "stop_reason",
        "stop_reasoning",
        "result",
        "latency_ms",
        "input_tokens",
        "output_tokens",
        "llm_calls",
        "estimated_cost_usd",
        "timestamp",
    }
    assert set(persisted["result"]) == {
        "incident_id",
        "root_cause",
        "affected_service",
        "evidence_ids",
        "explanation",
        "confidence",
    }
    assert record.llm_calls == 4
    assert record.input_tokens == 600
    assert record.output_tokens == 60
    assert isinstance(record.result, RCAResult)
    if final_status == "supported":
        assert record.result.root_cause == candidate.root_cause
    else:
        assert (
            record.result.root_cause
            == "Root cause could not be established from the gathered evidence."
        )
        assert record.result.confidence is None
        assert record.result.evidence_ids == []


@pytest.fixture(autouse=True)
def failure_save():
    # Existing exception tests must not create diagnostic files in the checkout.
    with patch(
        "traceroot.experiments.agent.save_failed_agent_experiment_record",
        return_value=Path("failures/agent-failed-test.json"),
    ) as save:
        yield save


@pytest.fixture
def pipeline():
    from contextlib import ExitStack

    with ExitStack() as stack:
        mocks = {
            name: stack.enter_context(patch(f"traceroot.experiments.agent.{name}"))
            for name in (
                "generate_hypotheses",
                "investigate",
                "verify_hypotheses",
                "generate_final_rca",
                "save_agent_experiment_record",
            )
        }
        mocks["generate_hypotheses"].return_value = create_test_hypotheses()
        state = create_final_state()
        state.final_result = None
        mocks["investigate"].return_value = state
        mocks["verify_hypotheses"].side_effect = lambda state, **kwargs: state

        def finish(state, **kwargs):
            state.final_result = create_final_state().final_result
            return state

        mocks["generate_final_rca"].side_effect = finish
        yield mocks


def failed_snapshot(failure_save):
    failure_save.assert_called_once()
    return failure_save.call_args.args[0]


def run_failure(pipeline, stage, error=None):
    error = error if error is not None else RuntimeError("test failure")
    pipeline[stage].side_effect = error
    with pytest.raises(type(error)) as caught:
        run_agent_experiment(create_test_incident(), Path("agent.json"))
    assert caught.value is error
    return error


def test_successful_run_preserves_record_and_output_contract(pipeline, failure_save):
    from traceroot.experiments.models import AgentExperimentRecord

    record = run_agent_experiment(create_test_incident(), Path("agent.json"))
    assert type(record) is AgentExperimentRecord
    assert record.result == create_final_state().final_result
    assert "status" not in record.model_dump()
    pipeline["save_agent_experiment_record"].assert_called_once_with(
        record, Path("agent.json")
    )
    failure_save.assert_not_called()


def test_hypothesis_generation_failure_persists_incident_snapshot(
    pipeline, failure_save
):
    run_failure(pipeline, "generate_hypotheses")
    record = failed_snapshot(failure_save)
    assert record.state == InvestigationState(incident=create_test_incident())
    assert record.failure_stage == "hypothesis_generation"
    assert record.timestamp.utcoffset().total_seconds() == 0
    assert record.latency_ms >= 0


@pytest.fixture
def failed_second_call(pipeline, failure_save):
    from traceroot.agent.investigation import investigate

    pipeline["investigate"].side_effect = investigate
    log = LogEntry(
        id="LOG-001",
        timestamp=datetime(2026, 9, 25, tzinfo=UTC),
        service="checkout-service",
        level="ERROR",
        message="timeout",
    )
    executor = MagicMock(side_effect=[[log], RuntimeError("provider failure")])
    with patch("traceroot.agent.investigation.get_llm_client") as client:
        client.return_value.responses.parse.side_effect = [
            MagicMock(
                output_parsed=ToolSelection(
                    tool_name=tool, reasoning="Inspect evidence"
                ),
                usage=MagicMock(input_tokens=10, output_tokens=2),
            )
            for tool in (ToolName.LOGS, ToolName.METRICS)
        ]
        with pytest.raises(RuntimeError, match="provider failure"):
            run_agent_experiment(
                create_test_incident(), Path("agent.json"), tool_executor=executor
            )
    return failed_snapshot(failure_save), log


def test_investigation_failure_persists_completed_prior_tool_history(
    failed_second_call,
):
    record, log = failed_second_call
    assert record.failure_stage == "investigation"
    assert record.state.hypotheses == create_test_hypotheses()
    assert record.state.evidence_ids == [log.id]
    assert record.state.tool_history[0].observations == [str(log)]
    assert record.state.tool_history[0].reasoning == "Inspect evidence"


def test_failed_executor_call_does_not_create_tool_call_record(failed_second_call):
    record, _ = failed_second_call
    assert [call.tool_name for call in record.state.tool_history] == ["logs"]
    assert record.llm_calls == 2


def test_verification_failure_persists_gathered_evidence_and_stop_information(
    pipeline, failure_save
):
    def fail(state, **kwargs):
        state.hypotheses[0].status = HypothesisStatus.REJECTED
        raise RuntimeError("verification failure")

    pipeline["verify_hypotheses"].side_effect = fail
    with pytest.raises(RuntimeError):
        run_agent_experiment(create_test_incident(), Path("agent.json"))
    record = failed_snapshot(failure_save)
    assert record.failure_stage == "hypothesis_verification"
    assert record.state.hypotheses[0].status == HypothesisStatus.REJECTED
    assert record.state.evidence_ids == create_final_state().evidence_ids
    assert record.state.tool_history == create_final_state().tool_history
    assert record.state.stop_reason == "tool_budget_exhausted"
    assert record.state.stop_reasoning == create_final_state().stop_reasoning


def test_rca_generation_failure_persists_full_pre_rca_state(pipeline, failure_save):
    run_failure(pipeline, "generate_final_rca")
    record = failed_snapshot(failure_save)
    expected = create_final_state()
    expected.final_result = None
    assert record.failure_stage == "final_rca"
    assert record.state == expected


def run_claim_verifier_failure(pipeline, error):
    from traceroot.agent.rca import generate_final_rca

    pipeline["generate_final_rca"].side_effect = generate_final_rca
    with (
        patch(
            "traceroot.agent.rca._generate_candidate",
            return_value=create_final_state().final_result,
        ),
        patch("traceroot.agent.rca.verify_rca_claims", side_effect=error),
    ):
        return run_agent_experiment(create_test_incident(), Path("agent.json"))


def test_unhandled_claim_verifier_failure_persists_final_rca_stage(
    pipeline, failure_save
):
    error = RuntimeError("unexpected verifier error")
    with pytest.raises(RuntimeError) as caught:
        run_claim_verifier_failure(pipeline, error)
    assert caught.value is error
    record = failed_snapshot(failure_save)
    assert record.failure_stage == "final_rca"
    assert record.state.final_result is None
    assert record.state.tool_history == create_final_state().tool_history


def test_expected_claim_verifier_failure_remains_completed(pipeline, failure_save):
    from traceroot.agent.grounding import MissingClaimAssessmentsError

    record = run_claim_verifier_failure(
        pipeline, MissingClaimAssessmentsError("missing")
    )
    assert record.result is not None
    pipeline["save_agent_experiment_record"].assert_called_once()
    failure_save.assert_not_called()


def test_missing_final_rca_persists_failure_record(pipeline, failure_save):
    pipeline["generate_final_rca"].side_effect = lambda state, **kwargs: state
    with pytest.raises(RuntimeError, match="did not produce a final RCA"):
        run_agent_experiment(create_test_incident(), Path("agent.json"))
    assert failed_snapshot(failure_save).failure_stage == "final_rca"


@pytest.mark.parametrize("unknown", [False, True])
def test_failed_run_persists_partial_llm_usage(pipeline, failure_save, unknown):
    def fail(incident, llm_usage):
        llm_usage.add(10, 2)
        llm_usage.add(None if unknown else 20, 3)
        raise RuntimeError("response parsed unsuccessfully")

    pipeline["generate_hypotheses"].side_effect = fail
    with pytest.raises(RuntimeError):
        run_agent_experiment(create_test_incident(), Path("agent.json"))
    record = failed_snapshot(failure_save)
    assert record.input_tokens == (None if unknown else 30)
    assert record.output_tokens == 5
    assert record.llm_calls == 2


def test_failed_run_preserves_unknown_token_usage(pipeline, failure_save):
    def fail(incident, llm_usage):
        llm_usage.add(None, None)
        llm_usage.add(10, 2)
        raise RuntimeError("failure")

    pipeline["generate_hypotheses"].side_effect = fail
    with pytest.raises(RuntimeError):
        run_agent_experiment(create_test_incident(), Path("agent.json"))
    record = failed_snapshot(failure_save)
    assert record.input_tokens is record.output_tokens is None
    assert record.llm_calls == 2


def test_failed_run_reraises_original_exception_instance(pipeline, failure_save):
    error = run_failure(pipeline, "generate_hypotheses")
    assert error.__notes__ == [
        "Partial investigation trace saved to: failures/agent-failed-test.json"
    ]
    assert error.__traceback__ is not None


def test_failure_persistence_error_does_not_mask_original_exception(
    pipeline, failure_save, caplog
):
    failure_save.side_effect = OSError("secret storage details")
    error = run_failure(pipeline, "generate_hypotheses")
    assert not getattr(error, "__notes__", [])
    assert len(caplog.records) == 1
    assert "Could not save partial investigation trace" in caplog.text
    assert "secret storage details" not in caplog.text
    failure_save.assert_called_once()


def test_success_persistence_failure_retains_final_rca_in_failure_snapshot(
    pipeline, failure_save
):
    run_failure(pipeline, "save_agent_experiment_record", OSError("disk failure"))
    record = failed_snapshot(failure_save)
    assert record.failure_stage == "persistence"
    assert record.state.final_result == create_final_state().final_result


@pytest.mark.parametrize(
    "message",
    [
        "token=secret https://private.example/ " * 1000,
        "body={secret}",
        "Traceback\nsecret",
    ],
)
def test_failed_run_sanitizes_and_bounds_exception_message(
    pipeline, failure_save, message
):
    run_failure(pipeline, "generate_hypotheses", RuntimeError(message))
    record = failed_snapshot(failure_save)
    assert len(record.failure_message) <= 240
    assert record.failure_type == "RuntimeError"
    assert (
        record.failure_message
        == "Failure during hypothesis_generation; exception details omitted for safety."
    )
    assert "secret" not in record.model_dump_json()


def test_failed_run_preserves_safe_diagnostic(pipeline, failure_save):
    run_failure(
        pipeline,
        "generate_hypotheses",
        RuntimeError("LLM did not return structured hypotheses"),
    )
    assert (
        failed_snapshot(failure_save).failure_message
        == "LLM did not return structured hypotheses"
    )


@pytest.mark.parametrize("error", [KeyboardInterrupt(), SystemExit(2)])
def test_nonordinary_exception_is_not_persisted(pipeline, failure_save, error):
    pipeline["generate_hypotheses"].side_effect = error
    with pytest.raises(type(error)):
        run_agent_experiment(create_test_incident(), Path("agent.json"))
    failure_save.assert_not_called()


def test_record_construction_failure_preserves_latest_state(pipeline, failure_save):
    with (
        patch(
            "traceroot.experiments.agent.AgentExperimentRecord",
            side_effect=ValueError("invalid"),
        ),
        pytest.raises(ValueError),
    ):
        run_agent_experiment(create_test_incident(), Path("agent.json"))
    record = failed_snapshot(failure_save)
    assert record.failure_stage == "record_construction"
    assert record.state.final_result is not None


def test_failure_snapshot_is_persisted_before_original_exception_propagates(
    pipeline, failure_save, tmp_path
):
    from traceroot.experiments.models import FailedAgentExperimentRecord
    from traceroot.experiments.persistence import save_failed_agent_experiment_record

    failure_save.side_effect = save_failed_agent_experiment_record
    error = RuntimeError("model unavailable")
    pipeline["generate_final_rca"].side_effect = error
    with pytest.raises(RuntimeError) as caught:
        run_agent_experiment(create_test_incident(), tmp_path / "live" / "agent.json")
    paths = list((tmp_path / "live" / "failures").glob("*.json"))
    assert len(paths) == 1
    record = FailedAgentExperimentRecord.model_validate_json(paths[0].read_text())
    assert record.failure_stage == "final_rca"
    assert record.state.tool_history == create_final_state().tool_history
    assert caught.value is error
    assert str(paths[0]) in error.__notes__[0]


def test_failure_record_construction_error_does_not_mask_original_exception(
    pipeline, failure_save, caplog
):
    with patch(
        "traceroot.experiments.agent.FailedAgentExperimentRecord",
        side_effect=ValueError("snapshot invalid"),
    ):
        run_failure(pipeline, "generate_hypotheses")
    failure_save.assert_not_called()
    assert len(caplog.records) == 1


@pytest.mark.parametrize("kind", ["http", "openai", "validation", "custom"])
def test_provider_failure_messages_do_not_persist_payloads(
    pipeline, failure_save, kind
):
    import httpx
    from openai import APIError
    from pydantic import ValidationError

    request = httpx.Request("GET", "https://private.example/?token=secret")
    if kind == "http":
        error = httpx.HTTPStatusError(
            "secret response body",
            request=request,
            response=httpx.Response(500, request=request, text="secret"),
        )
    elif kind == "openai":
        error = APIError("secret request body", request, body={"token": "secret"})
    elif kind == "validation":
        try:
            Hypothesis.model_validate({"description": {"token": "secret"}})
        except ValidationError as exc:
            error = exc
    else:

        class UnprintableError(Exception):
            def __str__(self):
                raise AssertionError("must not stringify")

        error = UnprintableError()
    run_failure(pipeline, "generate_hypotheses", error)
    record = failed_snapshot(failure_save)
    assert "secret" not in record.model_dump_json()
    assert "private.example" not in record.model_dump_json()
    assert len(record.failure_message) <= 240
