from traceroot.domain.ground_truth import GroundTruth
from traceroot.evaluation.agent_trace import evaluate_agent_trace
from traceroot.evaluation.efficiency import create_execution_metrics
from traceroot.evaluation.evidence import evaluate_evidence_precision_recall
from traceroot.evaluation.faithfulness import evaluate_faithfulness
from traceroot.evaluation.relevancy import evaluate_relevancy
from traceroot.evaluation.root_cause_accuracy import evaluate_root_cause_accuracy
from traceroot.evaluation.schemas import EvaluationResult, EvaluatorType, MetricResult
from traceroot.evaluation.service_accuracy import evaluate_service_accuracy
from traceroot.experiments.models import AgentExperimentRecord, BaselineExperimentRecord


def _evaluate_explanation_faithfulness(
    input_text: str, explanation: str, context: list[str]
) -> MetricResult:
    usable_context = [text for text in context if text.strip()]
    if not explanation.strip() or not usable_context:
        return MetricResult(
            name="Explanation Faithfulness",
            score=0.0,
            passed=False,
            evaluator_type=EvaluatorType.DETERMINISTIC,
            reason=(
                "No explanation available."
                if not explanation.strip()
                else "No usable context available."
            ),
        )
    metric = evaluate_faithfulness(
        input_text=input_text, actual_output=explanation, context=usable_context
    )
    return metric.model_copy(update={"name": "Explanation Faithfulness"})


def evaluate_rag_record(
    record: BaselineExperimentRecord,
    ground_truth: GroundTruth,
    retrieval_context: list[str],
) -> EvaluationResult:
    input_text = f"What caused incident {record.incident_id}?"
    actual_output = record.result.root_cause

    metrics = [
        evaluate_root_cause_accuracy(
            record.result,
            ground_truth,
        ),
        evaluate_faithfulness(
            input_text=input_text,
            actual_output=actual_output,
            context=retrieval_context,
        ),
        evaluate_relevancy(
            input_text=input_text,
            actual_output=actual_output,
        ),
    ]

    metrics.extend(
        [
            evaluate_service_accuracy(record.result, ground_truth),
            _evaluate_explanation_faithfulness(
                input_text, record.result.explanation, retrieval_context
            ),
        ]
    )

    execution_metrics = create_execution_metrics(
        latency_ms=record.latency_ms,
        input_tokens=record.input_tokens,
        output_tokens=record.output_tokens,
        llm_calls=record.llm_calls,
        estimated_cost_usd=record.estimated_cost_usd,
        tool_calls=0,
    )

    return EvaluationResult(
        incident_id=record.incident_id,
        approach=record.approach,
        metrics=metrics,
        execution=execution_metrics,
    )


def evaluate_agent_record(
    record: AgentExperimentRecord,
    ground_truth: GroundTruth,
) -> EvaluationResult:
    input_text = f"What caused incident {record.incident_id}?"
    actual_output = record.result.root_cause

    agent_context = [
        observation for call in record.tool_history for observation in call.observations
    ]

    precision, recall = evaluate_evidence_precision_recall(
        record.result,
        ground_truth,
    )

    metrics = [
        evaluate_root_cause_accuracy(
            record.result,
            ground_truth,
        ),
        precision,
        recall,
        evaluate_faithfulness(
            input_text=input_text,
            actual_output=actual_output,
            context=agent_context,
        ),
        evaluate_relevancy(
            input_text=input_text,
            actual_output=actual_output,
        ),
    ]

    metrics.extend(
        evaluate_agent_trace(
            record,
            ground_truth,
        )
    )

    metrics.extend(
        [
            evaluate_service_accuracy(record.result, ground_truth),
            _evaluate_explanation_faithfulness(
                input_text, record.result.explanation, agent_context
            ),
        ]
    )

    execution_metrics = create_execution_metrics(
        latency_ms=record.latency_ms,
        input_tokens=record.input_tokens,
        output_tokens=record.output_tokens,
        llm_calls=record.llm_calls,
        estimated_cost_usd=record.estimated_cost_usd,
        tool_calls=len(record.tool_history),
        investigation_steps=len(record.tool_history),
    )

    return EvaluationResult(
        incident_id=record.incident_id,
        approach=record.approach,
        metrics=metrics,
        execution=execution_metrics,
    )
