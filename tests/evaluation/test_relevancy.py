from unittest.mock import patch

from traceroot.evaluation.relevancy import evaluate_relevancy


@patch("traceroot.evaluation.relevancy.AnswerRelevancyMetric")
def test_relevancy_uses_input(mock_metric_class):
    metric = mock_metric_class.return_value
    metric.score = 0.9
    metric.reason = "Relevant answer."
    metric.is_successful.return_value = True

    evaluate_relevancy(
        input_text="What caused the checkout incident?",
        actual_output="Database connection contention caused checkout timeouts.",
    )

    test_case = metric.measure.call_args.args[0]

    assert test_case.input == "What caused the checkout incident?"


@patch("traceroot.evaluation.relevancy.AnswerRelevancyMetric")
def test_relevancy_uses_actual_output(mock_metric_class):
    metric = mock_metric_class.return_value
    metric.score = 0.9
    metric.reason = "Relevant answer."
    metric.is_successful.return_value = True

    evaluate_relevancy(
        input_text="What caused the checkout incident?",
        actual_output="Database connection contention caused checkout timeouts.",
    )

    test_case = metric.measure.call_args.args[0]

    assert (
        test_case.actual_output
        == "Database connection contention caused checkout timeouts."
    )


@patch("traceroot.evaluation.relevancy.AnswerRelevancyMetric")
def test_relevancy_calls_metric_once(mock_metric_class):
    metric = mock_metric_class.return_value
    metric.score = 0.9
    metric.reason = "Relevant answer."
    metric.is_successful.return_value = True

    evaluate_relevancy(
        input_text="What caused the checkout incident?",
        actual_output="Database connection contention caused checkout timeouts.",
    )

    metric.measure.assert_called_once()


@patch("traceroot.evaluation.relevancy.AnswerRelevancyMetric")
def test_relevancy_returns_metric_result(mock_metric_class):
    metric = mock_metric_class.return_value
    metric.score = 0.85
    metric.reason = "The response directly addresses the incident."
    metric.is_successful.return_value = True

    result = evaluate_relevancy(
        input_text="What caused the checkout incident?",
        actual_output="Database connection contention caused checkout timeouts.",
    )

    assert result.name == "Relevancy"
    assert result.score == 0.85
    assert result.passed is True
    assert result.reason == "The response directly addresses the incident."
