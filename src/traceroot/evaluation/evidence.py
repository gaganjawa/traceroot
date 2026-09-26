from traceroot.domain.ground_truth import GroundTruth
from traceroot.domain.rca import RCAResult
from traceroot.evaluation.schemas import EvaluatorType, MetricResult

PRECISION_THRESHOLD = 0.5
RECALL_THRESHOLD = 0.5


def evaluate_evidence_precision_recall(
    result: RCAResult,
    ground_truth: GroundTruth,
) -> tuple[MetricResult, MetricResult]:

    predicted = set(result.evidence_ids)
    relevant = set(ground_truth.supporting_evidence_ids)

    correct = predicted & relevant

    precision = len(correct) / len(predicted) if predicted else 0.0
    recall = len(correct) / len(relevant) if relevant else 0.0

    precision_result = MetricResult(
        name="Evidence Precision",
        score=precision,
        passed=precision >= PRECISION_THRESHOLD,
        evaluator_type=EvaluatorType.DETERMINISTIC,
        reason="Fraction of cited evidence that is relevant.",
    )

    recall_result = MetricResult(
        name="Evidence Recall",
        score=recall,
        passed=recall >= RECALL_THRESHOLD,
        evaluator_type=EvaluatorType.DETERMINISTIC,
        reason="Fraction of relevant evidence that was cited.",
    )

    return precision_result, recall_result
