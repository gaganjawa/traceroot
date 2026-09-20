from traceroot.evaluation.schemas import EvaluatorType, MetricResult, EvaluationResult, ExecutionMetrics


def test_create_metric_result():
    metric_result = MetricResult(
        name="evidence_recall",
        score=0.67,
        passed=False,
        evaluator_type=EvaluatorType.DETERMINISTIC,
        reason="2 of 3 expected evidence items identified",
    )
    assert metric_result.name == "evidence_recall"
    assert metric_result.score == 0.67
    assert metric_result.passed is False
    assert metric_result.evaluator_type == EvaluatorType.DETERMINISTIC
    assert metric_result.reason == "2 of 3 expected evidence items identified"


def test_create_evaluation_result():
    evaluation_result = EvaluationResult(
        incident_id="INC-001",
        approach="root_cause_accuracy",
        metrics=[
            MetricResult(
                name="evidence_recall",
                score=0.67,
                passed=False,
                evaluator_type=EvaluatorType.DETERMINISTIC,
                reason="2 of 3 expected evidence items identified",
            ),
            MetricResult(
                name="root_cause_accuracy",
                score=1.0,
                passed=True,
                evaluator_type=EvaluatorType.DEEPEVAL,
                reason="2 of 3 expected evidence items identified",
            ),
        ],
    )
    assert evaluation_result.incident_id == "INC-001"
    assert len(evaluation_result.metrics) == 2
    assert evaluation_result.metrics[0].name == "evidence_recall"
    assert evaluation_result.metrics[0].evaluator_type == EvaluatorType.DETERMINISTIC
    assert evaluation_result.metrics[1].name == "root_cause_accuracy"
    assert evaluation_result.metrics[1].evaluator_type == EvaluatorType.DEEPEVAL


def test_create_evaluation_result_with_empty_metrics():
    evaluation_result = EvaluationResult(
        incident_id="INC-002",
        approach="root_cause_accuracy",
        metrics=[],
    )
    assert evaluation_result.incident_id == "INC-002"
    assert len(evaluation_result.metrics) == 0
    assert evaluation_result.metrics == []


def test_create_execution_metrics():
    execution_metrics = ExecutionMetrics(
        latency_ms=1250.5,
        input_tokens=1200,
        output_tokens=350,
        tool_calls=4,
        investigation_steps=3,
    )
    assert execution_metrics.latency_ms == 1250.5
    assert execution_metrics.input_tokens == 1200
    assert execution_metrics.output_tokens == 350
    assert execution_metrics.tool_calls == 4
    assert execution_metrics.investigation_steps == 3


def test_evaluation_result_with_execution_metrics():
    evaluation_result = EvaluationResult(
        incident_id="INC-001",
        approach="root_cause_accuracy",
        metrics=[
            MetricResult(
                name="evidence_recall",
                score=0.67,
                passed=False,
                evaluator_type=EvaluatorType.DEEPEVAL,
                reason="2 of 3 expected evidence items identified",
            ),
            MetricResult(
                name="root_cause_accuracy",
                score=1.0,
                passed=True,
                evaluator_type=EvaluatorType.DEEPEVAL,
                reason="2 of 3 expected evidence items identified",
            ),
        ],
        execution=ExecutionMetrics(
            latency_ms=1250.5,
            input_tokens=1200,
            output_tokens=350,
            tool_calls=4,
            investigation_steps=3,
        ),
    )
    assert evaluation_result.incident_id == "INC-001"
    assert len(evaluation_result.metrics) == 2
    assert evaluation_result.metrics[0].name == "evidence_recall"
    assert evaluation_result.metrics[0].evaluator_type == EvaluatorType.DEEPEVAL
    assert evaluation_result.metrics[1].name == "root_cause_accuracy"
    assert evaluation_result.metrics[1].evaluator_type == EvaluatorType.DEEPEVAL
    assert evaluation_result.execution.latency_ms == 1250.5
    assert evaluation_result.execution.input_tokens == 1200
    assert evaluation_result.execution.output_tokens == 350
    assert evaluation_result.execution.tool_calls == 4
    assert evaluation_result.execution.investigation_steps == 3