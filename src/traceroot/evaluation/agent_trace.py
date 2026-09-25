from traceroot.domain.ground_truth import GroundTruth
from traceroot.evaluation.schemas import EvaluatorType, MetricResult
from traceroot.experiments.models import AgentExperimentRecord


def evaluate_agent_trace(
    record: AgentExperimentRecord,
    ground_truth: GroundTruth,
) -> list[MetricResult]:

    unique_selections = {(call.tool_name, call.service) for call in record.tool_history}

    tool_efficiency = (
        len(unique_selections) / len(record.tool_history)
        if record.tool_history
        else 0.0
    )

    tool_efficiency_metric = MetricResult(
        name="Tool Efficiency",
        score=tool_efficiency,
        passed=tool_efficiency >= 0.7,
        evaluator_type=EvaluatorType.DETERMINISTIC,
        reason=(
            f"{len(unique_selections)} unique tool/service selections "
            f"across {len(record.tool_history)} tool calls."
        ),
    )

    empty_calls = sum(1 for call in record.tool_history if not call.evidence_ids)

    empty_tool_rate = (
        empty_calls / len(record.tool_history) if record.tool_history else 0.0
    )

    empty_tool_rate_metric = MetricResult(
        name="Empty Tool Rate",
        score=empty_tool_rate,
        passed=empty_tool_rate <= 0.3,
        evaluator_type=EvaluatorType.DETERMINISTIC,
        reason=(
            f"{empty_calls} empty-result tool calls "
            f"across {len(record.tool_history)} total tool calls."
        ),
    )

    relevant = set(ground_truth.supporting_evidence_ids)
    gathered = set(record.evidence_ids)

    evidence_coverage = len(gathered & relevant) / len(relevant) if relevant else 0.0

    evidence_coverage_metric = MetricResult(
        name="Evidence Coverage",
        score=evidence_coverage,
        passed=evidence_coverage >= 0.7,
        evaluator_type=EvaluatorType.DETERMINISTIC,
        reason=(
            f"{len(gathered & relevant)} relevant evidence items gathered "
            f"out of {len(relevant)} expected supporting evidence items."
        ),
    )

    stop_scores = {
        "model_stop": 1.0,
        "duplicate_selection": 0.5,
        "two_empty_results": 0.5,
        "tool_budget_exhausted": 0.0,
    }

    stop_quality = stop_scores.get(record.stop_reason, 0.0)

    stop_quality_metric = MetricResult(
        name="Stop Quality",
        score=stop_quality,
        passed=stop_quality >= 0.5,
        evaluator_type=EvaluatorType.DETERMINISTIC,
        reason=f"Investigation stopped with reason: {record.stop_reason}.",
    )

    return [
        tool_efficiency_metric,
        empty_tool_rate_metric,
        evidence_coverage_metric,
        stop_quality_metric,
    ]
