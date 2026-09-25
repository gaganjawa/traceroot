from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, SingleTurnParams

from traceroot.domain.ground_truth import GroundTruth
from traceroot.domain.rca import RCAResult
from traceroot.evaluation.schemas import EvaluatorType, MetricResult


def evaluate_root_cause_accuracy(
    result: RCAResult,
    ground_truth: GroundTruth,
) -> MetricResult:
    test_case = LLMTestCase(
        input="Identify the root cause of the production incident.",
        actual_output=result.root_cause,
        expected_output=ground_truth.root_cause,
    )

    metric = GEval(
        name="Root Cause Accuracy",
        criteria=(
            "Determine whether the actual root cause is semantically correct "
            "according to the expected root cause. Do not require exact wording."
        ),
        evaluation_params=[
            SingleTurnParams.ACTUAL_OUTPUT,
            SingleTurnParams.EXPECTED_OUTPUT,
        ],
    )

    metric.measure(test_case)

    return MetricResult(
        name="Root Cause Accuracy",
        score=metric.score,
        passed=metric.is_successful(),
        evaluator_type=EvaluatorType.DEEPEVAL,
        reason=metric.reason,
    )
