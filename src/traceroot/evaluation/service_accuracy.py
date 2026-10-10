from traceroot.domain.ground_truth import GroundTruth
from traceroot.domain.rca import RCAResult
from traceroot.evaluation.schemas import EvaluatorType, MetricResult


def evaluate_service_accuracy(
    result: RCAResult, ground_truth: GroundTruth
) -> MetricResult:
    matched = (
        bool(result.affected_service)
        and result.affected_service == ground_truth.affected_service
    )
    return MetricResult(
        name="Affected Service Accuracy",
        score=1.0 if matched else 0.0,
        passed=matched,
        evaluator_type=EvaluatorType.DETERMINISTIC,
        reason="Predicted affected service exactly matches ground truth."
        if matched
        else "Predicted affected service is missing or does not exactly match ground truth.",
    )
