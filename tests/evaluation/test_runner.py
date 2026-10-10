from datetime import UTC, datetime
from unittest.mock import call, patch

import pytest

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

    assert len(result.metrics) == 5

    mock_accuracy.assert_called_once_with(
        record.result,
        ground_truth,
    )

    mock_faithfulness.assert_any_call(
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
def test_evaluate_rag_record_preserves_execution_usage(
    mock_accuracy,
    mock_faithfulness,
    mock_relevancy,
):
    mock_accuracy.return_value = make_metric("Root Cause Accuracy")
    mock_faithfulness.return_value = make_metric("Faithfulness")
    mock_relevancy.return_value = make_metric("Relevancy")

    record = make_rag_record()
    record.input_tokens = 100
    record.output_tokens = 25
    record.llm_calls = 1
    record.estimated_cost_usd = 0.01

    result = evaluate_rag_record(
        record=record,
        ground_truth=make_ground_truth(),
        retrieval_context=["context"],
    )

    assert result.execution is not None
    assert result.execution.latency_ms == 500.0
    assert result.execution.tool_calls == 0
    assert result.execution.investigation_steps is None
    assert result.execution.input_tokens == 100
    assert result.execution.output_tokens == 25
    assert result.execution.total_tokens == 125
    assert result.execution.llm_calls == 1
    assert result.execution.estimated_cost_usd == 0.01


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

    assert len(result.metrics) == 11

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

    mock_faithfulness.assert_any_call(
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
def test_evaluate_agent_record_preserves_execution_usage(
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
    record.input_tokens = 400
    record.output_tokens = 80
    record.llm_calls = 4
    record.estimated_cost_usd = 0.02

    result = evaluate_agent_record(
        record,
        make_ground_truth(),
    )

    assert result.execution is not None
    assert result.execution.latency_ms == 800.0
    assert result.execution.tool_calls == 2
    assert result.execution.investigation_steps == 2

    assert result.execution.input_tokens == 400
    assert result.execution.output_tokens == 80
    assert result.execution.total_tokens == 480
    assert result.execution.llm_calls == 4
    assert result.execution.estimated_cost_usd == 0.02


@patch("traceroot.evaluation.runner.evaluate_relevancy")
@patch("traceroot.evaluation.runner.evaluate_faithfulness")
@patch("traceroot.evaluation.runner.evaluate_root_cause_accuracy")
def test_evaluate_rag_record_preserves_unavailable_usage(
    mock_accuracy,
    mock_faithfulness,
    mock_relevancy,
):
    mock_accuracy.return_value = make_metric("Root Cause Accuracy")
    mock_faithfulness.return_value = make_metric("Faithfulness")
    mock_relevancy.return_value = make_metric("Relevancy")

    record = make_rag_record()
    record.input_tokens = None
    record.output_tokens = None
    record.llm_calls = 1

    result = evaluate_rag_record(
        record=record,
        ground_truth=make_ground_truth(),
        retrieval_context=["context"],
    )

    assert result.execution is not None
    assert result.execution.input_tokens is None
    assert result.execution.output_tokens is None
    assert result.execution.total_tokens is None
    assert result.execution.llm_calls == 1
    assert result.execution.estimated_cost_usd is None


@pytest.mark.parametrize("approach", ["rag", "agent"])
@patch("traceroot.evaluation.runner.evaluate_relevancy")
@patch("traceroot.evaluation.runner.evaluate_faithfulness")
@patch("traceroot.evaluation.runner.evaluate_root_cause_accuracy")
def test_runners_append_service_and_explanation_metrics(
    accuracy, faithfulness, relevancy, approach
):
    accuracy.return_value = make_metric("Root Cause Accuracy")
    relevancy.return_value = make_metric("Relevancy")
    judge_metric = MetricResult(
        name="Faithfulness",
        score=0.65,
        passed=False,
        evaluator_type=EvaluatorType.DEEPEVAL,
        reason="Partial support",
    )
    faithfulness.return_value = judge_metric
    if approach == "rag":
        record = make_rag_record()
        context = ["Retrieved knowledge"]
        evaluation = evaluate_rag_record(record, make_ground_truth(), context)
        original_names = ["Root Cause Accuracy", "Faithfulness", "Relevancy"]
    else:
        record = make_agent_record()
        context = [
            observation
            for entry in record.tool_history
            for observation in entry.observations
        ]
        evaluation = evaluate_agent_record(record, make_ground_truth())
        original_names = [
            "Root Cause Accuracy",
            "Evidence Precision",
            "Evidence Recall",
            "Faithfulness",
            "Relevancy",
            "Tool Efficiency",
            "Empty Tool Rate",
            "Evidence Coverage",
            "Stop Quality",
        ]
    assert [metric.name for metric in evaluation.metrics] == original_names + [
        "Affected Service Accuracy",
        "Explanation Faithfulness",
    ]
    assert faithfulness.call_args_list == [
        call(
            input_text="What caused incident INC-001?",
            actual_output=record.result.root_cause,
            context=context,
        ),
        call(
            input_text="What caused incident INC-001?",
            actual_output=record.result.explanation,
            context=context,
        ),
    ]
    explanation_metric = evaluation.metrics[-1]
    assert explanation_metric.model_dump(exclude={"name"}) == judge_metric.model_dump(
        exclude={"name"}
    )
    assert judge_metric.name == "Faithfulness"
    assert evaluation.metrics[-2].score == 1.0


@pytest.mark.parametrize(
    "explanation, context, reason",
    [
        ("", ["evidence"], "No explanation available."),
        ("   ", ["evidence"], "No explanation available."),
        ("explanation", [], "No usable context available."),
        ("explanation", ["", "  "], "No usable context available."),
    ],
)
@patch("traceroot.evaluation.runner.evaluate_faithfulness")
def test_explanation_unavailable_input_avoids_judge(
    judge, explanation, context, reason
):
    from traceroot.evaluation.runner import _evaluate_explanation_faithfulness

    metric = _evaluate_explanation_faithfulness("question", explanation, context)
    judge.assert_not_called()
    assert metric.name == "Explanation Faithfulness"
    assert metric.score == 0.0
    assert metric.passed is False
    assert metric.reason == reason


@patch("traceroot.evaluation.runner.evaluate_faithfulness")
def test_explanation_uses_only_usable_context(judge):
    from traceroot.evaluation.runner import _evaluate_explanation_faithfulness

    judge.return_value = make_metric("Faithfulness")
    _evaluate_explanation_faithfulness(
        "question", "explanation", ["", " observation ", "  "]
    )
    judge.assert_called_once_with(
        input_text="question", actual_output="explanation", context=[" observation "]
    )
