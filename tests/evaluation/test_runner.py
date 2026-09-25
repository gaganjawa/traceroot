from datetime import UTC, datetime
from unittest.mock import patch

from traceroot.agent.state import ToolCallRecord
from traceroot.domain.ground_truth import GroundTruth
from traceroot.domain.rca import RCAResult
from traceroot.evaluation.runner import evaluate_agent_record, evaluate_rag_record
from traceroot.evaluation.schemas import (
    EvaluationResult,
    EvaluatorType,
    MetricResult,
)
from traceroot.experiments.models import (
    AgentExperimentRecord,
    BaselineExperimentRecord,
    RetrievedKnowledge,
)


def make_metric(name: str) -> MetricResult:
    return MetricResult(
        name=name,
        score=1.0,
        passed=True,
        evaluator_type=EvaluatorType.DETERMINISTIC,
        reason="test",
    )


def make_ground_truth() -> GroundTruth:
    return GroundTruth(
        incident_id="INC-001",
        root_cause="Database connection pool regression",
        root_cause_category="configuration_regression",
        affected_service="checkout-service",
        supporting_evidence_ids=["EVIDENCE-001"],
    )


def make_rca_result() -> RCAResult:
    return RCAResult(
        incident_id="INC-001",
        root_cause="Database connection pool regression",
        affected_service="checkout-service",
        evidence_ids=["EVIDENCE-001"],
        explanation="Connection pool capacity was reduced.",
        confidence=0.9,
    )


def make_rag_record() -> BaselineExperimentRecord:
    return BaselineExperimentRecord(
        incident_id="INC-001",
        model="gpt-5.4-mini",
        top_k=3,
        retrieved_knowledge=[
            RetrievedKnowledge(
                chunk_id="chunk-001",
                source="checkout-runbook.md",
                score=0.9,
            )
        ],
        result=make_rca_result(),
        latency_ms=500.0,
        timestamp=datetime.now(UTC),
    )


def make_agent_record() -> AgentExperimentRecord:
    return AgentExperimentRecord(
        incident_id="INC-001",
        model="gpt-5.4-mini",
        hypotheses=[],
        evidence_ids=["EVIDENCE-001"],
        tool_history=[
            ToolCallRecord(
                tool_name="logs",
                service="checkout-service",
                evidence_ids=["EVIDENCE-001"],
                observations=["Database connections exhausted"],
                reasoning="Check checkout errors",
            ),
            ToolCallRecord(
                tool_name="metrics",
                service="checkout-service",
                evidence_ids=[],
                observations=["Connection usage reached 100%"],
                reasoning="Check connection utilization",
            ),
        ],
        stop_reason="model_stop",
        result=make_rca_result(),
        latency_ms=800.0,
        timestamp=datetime.now(UTC),
    )


# RAG
@patch("traceroot.evaluation.runner.evaluate_relevancy")
@patch("traceroot.evaluation.runner.evaluate_faithfulness")
@patch("traceroot.evaluation.runner.evaluate_root_cause_accuracy")
def test_evaluate_rag_record_returns_evaluation_result(
    mock_accuracy,
    mock_faithfulness,
    mock_relevancy,
):
    mock_accuracy.return_value = make_metric("Root Cause Accuracy")
    mock_faithfulness.return_value = make_metric("Faithfulness")
    mock_relevancy.return_value = make_metric("Relevancy")

    result = evaluate_rag_record(
        record=make_rag_record(),
        ground_truth=make_ground_truth(),
        retrieval_context=["Database pool exhaustion troubleshooting"],
    )

    assert isinstance(result, EvaluationResult)
    assert result.incident_id == "INC-001"
    assert result.approach == "rag_baseline"


@patch("traceroot.evaluation.runner.evaluate_relevancy")
@patch("traceroot.evaluation.runner.evaluate_faithfulness")
@patch("traceroot.evaluation.runner.evaluate_root_cause_accuracy")
def test_evaluate_rag_record_runs_expected_metrics(
    mock_accuracy,
    mock_faithfulness,
    mock_relevancy,
):
    mock_accuracy.return_value = make_metric("Root Cause Accuracy")
    mock_faithfulness.return_value = make_metric("Faithfulness")
    mock_relevancy.return_value = make_metric("Relevancy")

    record = make_rag_record()
    ground_truth = make_ground_truth()
    context = ["Database pool exhaustion troubleshooting"]

    result = evaluate_rag_record(
        record=record,
        ground_truth=ground_truth,
        retrieval_context=context,
    )

    assert len(result.metrics) == 3

    mock_accuracy.assert_called_once_with(
        record.result,
        ground_truth,
    )

    mock_faithfulness.assert_called_once_with(
        input_text="What caused incident INC-001?",
        actual_output=record.result.root_cause,
        context=context,
    )

    mock_relevancy.assert_called_once_with(
        input_text="What caused incident INC-001?",
        actual_output=record.result.root_cause,
    )


@patch("traceroot.evaluation.runner.evaluate_relevancy")
@patch("traceroot.evaluation.runner.evaluate_faithfulness")
@patch("traceroot.evaluation.runner.evaluate_root_cause_accuracy")
def test_evaluate_rag_record_sets_execution_metrics(
    mock_accuracy,
    mock_faithfulness,
    mock_relevancy,
):
    mock_accuracy.return_value = make_metric("Root Cause Accuracy")
    mock_faithfulness.return_value = make_metric("Faithfulness")
    mock_relevancy.return_value = make_metric("Relevancy")

    result = evaluate_rag_record(
        record=make_rag_record(),
        ground_truth=make_ground_truth(),
        retrieval_context=["context"],
    )

    assert result.execution is not None
    assert result.execution.latency_ms == 500.0
    assert result.execution.tool_calls == 0


# AGENT
@patch("traceroot.evaluation.runner.evaluate_agent_trace")
@patch("traceroot.evaluation.runner.evaluate_relevancy")
@patch("traceroot.evaluation.runner.evaluate_faithfulness")
@patch("traceroot.evaluation.runner.evaluate_evidence_precision_recall")
@patch("traceroot.evaluation.runner.evaluate_root_cause_accuracy")
def test_evaluate_agent_record_returns_evaluation_result(
    mock_accuracy,
    mock_evidence,
    mock_faithfulness,
    mock_relevancy,
    mock_trace,
):
    mock_accuracy.return_value = make_metric("Root Cause Accuracy")
    mock_evidence.return_value = (
        make_metric("Evidence Precision"),
        make_metric("Evidence Recall"),
    )
    mock_faithfulness.return_value = make_metric("Faithfulness")
    mock_relevancy.return_value = make_metric("Relevancy")
    mock_trace.return_value = []

    result = evaluate_agent_record(
        make_agent_record(),
        make_ground_truth(),
    )

    assert isinstance(result, EvaluationResult)
    assert result.incident_id == "INC-001"
    assert result.approach == "agent"


@patch("traceroot.evaluation.runner.evaluate_agent_trace")
@patch("traceroot.evaluation.runner.evaluate_relevancy")
@patch("traceroot.evaluation.runner.evaluate_faithfulness")
@patch("traceroot.evaluation.runner.evaluate_evidence_precision_recall")
@patch("traceroot.evaluation.runner.evaluate_root_cause_accuracy")
def test_evaluate_agent_record_runs_expected_metrics(
    mock_accuracy,
    mock_evidence,
    mock_faithfulness,
    mock_relevancy,
    mock_trace,
):
    mock_accuracy.return_value = make_metric("Root Cause Accuracy")
    mock_evidence.return_value = (
        make_metric("Evidence Precision"),
        make_metric("Evidence Recall"),
    )
    mock_faithfulness.return_value = make_metric("Faithfulness")
    mock_relevancy.return_value = make_metric("Relevancy")
    mock_trace.return_value = [
        make_metric("Tool Efficiency"),
        make_metric("Empty Tool Rate"),
        make_metric("Evidence Coverage"),
        make_metric("Stop Quality"),
    ]

    record = make_agent_record()
    ground_truth = make_ground_truth()

    result = evaluate_agent_record(record, ground_truth)

    assert len(result.metrics) == 9

    mock_accuracy.assert_called_once_with(record.result, ground_truth)
    mock_evidence.assert_called_once_with(record.result, ground_truth)
    mock_trace.assert_called_once_with(record, ground_truth)


@patch("traceroot.evaluation.runner.evaluate_agent_trace")
@patch("traceroot.evaluation.runner.evaluate_relevancy")
@patch("traceroot.evaluation.runner.evaluate_faithfulness")
@patch("traceroot.evaluation.runner.evaluate_evidence_precision_recall")
@patch("traceroot.evaluation.runner.evaluate_root_cause_accuracy")
def test_evaluate_agent_record_flattens_tool_observations_for_faithfulness(
    mock_accuracy,
    mock_evidence,
    mock_faithfulness,
    mock_relevancy,
    mock_trace,
):
    mock_accuracy.return_value = make_metric("Root Cause Accuracy")
    mock_evidence.return_value = (
        make_metric("Evidence Precision"),
        make_metric("Evidence Recall"),
    )
    mock_faithfulness.return_value = make_metric("Faithfulness")
    mock_relevancy.return_value = make_metric("Relevancy")
    mock_trace.return_value = []

    record = make_agent_record()

    evaluate_agent_record(
        record,
        make_ground_truth(),
    )

    mock_faithfulness.assert_called_once_with(
        input_text="What caused incident INC-001?",
        actual_output=record.result.root_cause,
        context=[
            "Database connections exhausted",
            "Connection usage reached 100%",
        ],
    )


@patch("traceroot.evaluation.runner.evaluate_agent_trace")
@patch("traceroot.evaluation.runner.evaluate_relevancy")
@patch("traceroot.evaluation.runner.evaluate_faithfulness")
@patch("traceroot.evaluation.runner.evaluate_evidence_precision_recall")
@patch("traceroot.evaluation.runner.evaluate_root_cause_accuracy")
def test_evaluate_agent_record_sets_execution_metrics(
    mock_accuracy,
    mock_evidence,
    mock_faithfulness,
    mock_relevancy,
    mock_trace,
):
    mock_accuracy.return_value = make_metric("Root Cause Accuracy")
    mock_evidence.return_value = (
        make_metric("Evidence Precision"),
        make_metric("Evidence Recall"),
    )
    mock_faithfulness.return_value = make_metric("Faithfulness")
    mock_relevancy.return_value = make_metric("Relevancy")
    mock_trace.return_value = []

    result = evaluate_agent_record(
        make_agent_record(),
        make_ground_truth(),
    )

    assert result.execution is not None
    assert result.execution.latency_ms == 800.0
    assert result.execution.tool_calls == 2
    assert result.execution.investigation_steps == 2
