from datetime import UTC, datetime

from traceroot.agent.state import ToolCallRecord
from traceroot.domain.ground_truth import GroundTruth
from traceroot.domain.rca import RCAResult
from traceroot.evaluation.agent_trace import evaluate_agent_trace
from traceroot.experiments.models import AgentExperimentRecord


def make_ground_truth() -> GroundTruth:
    return GroundTruth(
        incident_id="INC-001",
        root_cause="Database connection pool regression",
        root_cause_category="configuration_regression",
        affected_service="checkout-service",
        supporting_evidence_ids=[
            "LOG-001",
            "METRIC-001",
            "CHANGE-001",
        ],
    )


def make_record(
    tool_history: list[ToolCallRecord],
    evidence_ids: list[str],
    stop_reason: str | None = "model_stop",
) -> AgentExperimentRecord:
    return AgentExperimentRecord(
        incident_id="INC-001",
        model="gpt-5.4-mini",
        hypotheses=[],
        evidence_ids=evidence_ids,
        tool_history=tool_history,
        stop_reason=stop_reason,
        stop_reasoning=None,
        result=RCAResult(
            incident_id="INC-001",
            root_cause="Database connection pool regression",
            affected_service="checkout-service",
            evidence_ids=evidence_ids,
            explanation="Test RCA",
            confidence=0.9,
        ),
        latency_ms=100.0,
        timestamp=datetime(2026, 9, 26, tzinfo=UTC),
    )


def get_metric(results, name):
    return next(result for result in results if result.name == name)


def test_agent_trace_tool_efficiency_perfect():
    record = make_record(
        tool_history=[
            ToolCallRecord(tool_name="logs", service="checkout-service"),
            ToolCallRecord(tool_name="metrics", service="checkout-service"),
        ],
        evidence_ids=[],
    )

    results = evaluate_agent_trace(record, make_ground_truth())

    metric = get_metric(results, "Tool Efficiency")

    assert metric.score == 1.0
    assert metric.passed is True


def test_agent_trace_tool_efficiency_with_duplicate():
    record = make_record(
        tool_history=[
            ToolCallRecord(tool_name="logs", service="checkout-service"),
            ToolCallRecord(tool_name="logs", service="checkout-service"),
        ],
        evidence_ids=[],
    )

    results = evaluate_agent_trace(record, make_ground_truth())

    metric = get_metric(results, "Tool Efficiency")

    assert metric.score == 0.5
    assert metric.passed is False


def test_agent_trace_empty_tool_rate():
    record = make_record(
        tool_history=[
            ToolCallRecord(
                tool_name="logs",
                service="checkout-service",
                evidence_ids=["LOG-001"],
            ),
            ToolCallRecord(
                tool_name="metrics",
                service="checkout-service",
                evidence_ids=[],
            ),
        ],
        evidence_ids=["LOG-001"],
    )

    results = evaluate_agent_trace(record, make_ground_truth())

    metric = get_metric(results, "Empty Tool Rate")

    assert metric.score == 0.5
    assert metric.passed is False


def test_agent_trace_evidence_coverage():
    record = make_record(
        tool_history=[],
        evidence_ids=["LOG-001", "METRIC-001"],
    )

    results = evaluate_agent_trace(record, make_ground_truth())

    metric = get_metric(results, "Evidence Coverage")

    assert metric.score == 2 / 3
    assert metric.passed is False


def test_agent_trace_stop_quality_model_stop():
    record = make_record(
        tool_history=[],
        evidence_ids=[],
        stop_reason="model_stop",
    )

    results = evaluate_agent_trace(record, make_ground_truth())

    metric = get_metric(results, "Stop Quality")

    assert metric.score == 1.0
    assert metric.passed is True


def test_agent_trace_stop_quality_budget_exhausted():
    record = make_record(
        tool_history=[],
        evidence_ids=[],
        stop_reason="tool_budget_exhausted",
    )

    results = evaluate_agent_trace(record, make_ground_truth())

    metric = get_metric(results, "Stop Quality")

    assert metric.score == 0.0
    assert metric.passed is False


def test_agent_trace_handles_empty_tool_history():
    record = make_record(
        tool_history=[],
        evidence_ids=[],
    )

    results = evaluate_agent_trace(record, make_ground_truth())

    tool_efficiency = get_metric(results, "Tool Efficiency")
    empty_tool_rate = get_metric(results, "Empty Tool Rate")

    assert tool_efficiency.score == 0.0
    assert empty_tool_rate.score == 0.0
