from unittest.mock import patch

from traceroot.evaluation.faithfulness import evaluate_faithfulness


@patch("traceroot.evaluation.faithfulness.FaithfulnessMetric")
def test_faithfulness_uses_input(metric_class):
    metric = metric_class.return_value
    metric.score = 0.9
    metric.reason = "Supported by context."
    metric.is_successful.return_value = True

    evaluate_faithfulness(
        input_text="What caused the incident?",
        actual_output="Database contention caused the failure.",
        context=["Database connections were exhausted."],
    )

    test_case = metric.measure.call_args.args[0]
    assert test_case.input == "What caused the incident?"


@patch("traceroot.evaluation.faithfulness.FaithfulnessMetric")
def test_faithfulness_uses_actual_output(metric_class):
    metric = metric_class.return_value
    metric.score = 0.9
    metric.reason = "Supported by context."
    metric.is_successful.return_value = True

    evaluate_faithfulness(
        input_text="What caused the incident?",
        actual_output="Database contention caused the failure.",
        context=["Database connections were exhausted."],
    )

    test_case = metric.measure.call_args.args[0]
    assert test_case.actual_output == "Database contention caused the failure."


@patch("traceroot.evaluation.faithfulness.FaithfulnessMetric")
def test_faithfulness_uses_retrieval_context(metric_class):
    context = [
        "Database connections were exhausted.",
        "Checkout latency increased.",
    ]

    metric = metric_class.return_value
    metric.score = 0.9
    metric.reason = "Supported by context."
    metric.is_successful.return_value = True

    evaluate_faithfulness(
        input_text="What caused the incident?",
        actual_output="Database contention caused the failure.",
        context=context,
    )

    test_case = metric.measure.call_args.args[0]
    assert test_case.retrieval_context == context


@patch("traceroot.evaluation.faithfulness.FaithfulnessMetric")
def test_faithfulness_calls_metric_once(metric_class):
    metric = metric_class.return_value
    metric.score = 0.9
    metric.reason = "Supported by context."
    metric.is_successful.return_value = True

    evaluate_faithfulness(
        input_text="What caused the incident?",
        actual_output="Database contention caused the failure.",
        context=["Database connections were exhausted."],
    )

    metric.measure.assert_called_once()


@patch("traceroot.evaluation.faithfulness.FaithfulnessMetric")
def test_faithfulness_returns_metric_result(metric_class):
    metric = metric_class.return_value
    metric.score = 0.85
    metric.reason = "The RCA is supported by the supplied evidence."
    metric.is_successful.return_value = True

    result = evaluate_faithfulness(
        input_text="What caused the incident?",
        actual_output="Database contention caused the failure.",
        context=["Database connections were exhausted."],
    )

    assert result.name == "Faithfulness"
    assert result.score == 0.85
    assert result.passed is True
    assert result.reason == "The RCA is supported by the supplied evidence."
