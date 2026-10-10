import pytest

from traceroot.domain.ground_truth import GroundTruth
from traceroot.domain.rca import RCAResult
from traceroot.evaluation.schemas import EvaluatorType
from traceroot.evaluation.service_accuracy import evaluate_service_accuracy


@pytest.mark.parametrize(
    "service, expected",
    [
        ("checkout-service", True),
        ("payment-service", False),
        (None, False),
        ("", False),
        ("Checkout-service", False),
        ("checkout-service ", False),
    ],
)
def test_service_accuracy_requires_exact_identifier(service, expected):
    result = RCAResult(
        incident_id="INC-001",
        root_cause="cause",
        explanation="explanation",
        affected_service=service,
    )
    truth = GroundTruth(
        incident_id="INC-001",
        root_cause="cause",
        root_cause_category="configuration_regression",
        affected_service="checkout-service",
    )
    metric = evaluate_service_accuracy(result, truth)
    assert metric.name == "Affected Service Accuracy"
    assert metric.score == float(expected)
    assert metric.passed is expected
    assert metric.evaluator_type == EvaluatorType.DETERMINISTIC
