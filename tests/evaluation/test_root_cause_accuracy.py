from unittest.mock import MagicMock, patch

from traceroot.evaluation.root_cause_accuracy import evaluate_root_cause_accuracy
from traceroot.evaluation.schemas import EvaluatorType


@patch("traceroot.evaluation.root_cause_accuracy.GEval")
def test_root_cause_accuracy_uses_generated_and_expected_root_cause(mock_geval):
    result = MagicMock()
    result.root_cause = "Database connection contention"

    ground_truth = MagicMock()
    ground_truth.root_cause = "Database connection pool configuration regression"

    metric = mock_geval.return_value
    metric.score = 0.9
    metric.reason = "Root causes are semantically aligned."
    metric.is_successful.return_value = True

    evaluate_root_cause_accuracy(result, ground_truth)

    test_case = metric.measure.call_args.args[0]

    assert test_case.actual_output == result.root_cause
    assert test_case.expected_output == ground_truth.root_cause


@patch("traceroot.evaluation.root_cause_accuracy.GEval")
def test_root_cause_accuracy_returns_metric_result(mock_geval):
    result = MagicMock(root_cause="Database contention")
    ground_truth = MagicMock(root_cause="Database pool regression")

    metric = mock_geval.return_value
    metric.score = 0.85
    metric.reason = "Semantically correct."
    metric.is_successful.return_value = True

    evaluation = evaluate_root_cause_accuracy(result, ground_truth)

    assert evaluation.name == "Root Cause Accuracy"
    assert evaluation.score == 0.85
    assert evaluation.passed is True
    assert evaluation.evaluator_type == EvaluatorType.DEEPEVAL
    assert evaluation.reason == "Semantically correct."


@patch("traceroot.evaluation.root_cause_accuracy.GEval")
def test_root_cause_accuracy_preserves_failed_result(mock_geval):
    result = MagicMock(root_cause="Payment timeout")
    ground_truth = MagicMock(root_cause="Database pool regression")

    metric = mock_geval.return_value
    metric.score = 0.2
    metric.reason = "Root cause does not match."
    metric.is_successful.return_value = False

    evaluation = evaluate_root_cause_accuracy(result, ground_truth)

    assert evaluation.score == 0.2
    assert evaluation.passed is False
    assert evaluation.reason == "Root cause does not match."


@patch("traceroot.evaluation.root_cause_accuracy.GEval")
def test_root_cause_accuracy_calls_measure_once(mock_geval):
    result = MagicMock(root_cause="Database contention")
    ground_truth = MagicMock(root_cause="Database regression")

    metric = mock_geval.return_value
    metric.score = 1.0
    metric.reason = "Correct."
    metric.is_successful.return_value = True

    evaluate_root_cause_accuracy(result, ground_truth)

    metric.measure.assert_called_once()


@patch("traceroot.evaluation.root_cause_accuracy.GEval")
def test_root_cause_accuracy_does_not_modify_inputs(mock_geval):
    result = MagicMock(root_cause="Database contention")
    ground_truth = MagicMock(root_cause="Database regression")

    original_result = result.root_cause
    original_truth = ground_truth.root_cause

    metric = mock_geval.return_value
    metric.score = 0.8
    metric.reason = "Mostly correct."
    metric.is_successful.return_value = True

    evaluate_root_cause_accuracy(result, ground_truth)

    assert result.root_cause == original_result
    assert ground_truth.root_cause == original_truth
