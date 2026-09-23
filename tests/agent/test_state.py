from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from traceroot.agent.state import (
    Hypothesis,
    HypothesisStatus,
    InvestigationState,
    ToolCallRecord,
)
from traceroot.domain.incident import Incident
from traceroot.domain.rca import RCAResult


def create_test_incident() -> Incident:
    return Incident(
        id="INC-TEST",
        title="Test incident",
        description="Test incident description",
        start_time=datetime.now(UTC),
        suspected_services=["checkout-service"],
    )


def test_investigation_state_requires_incident():
    with pytest.raises(ValidationError):
        InvestigationState()


def test_investigation_state_defaults_to_empty_hypotheses():
    state = InvestigationState(
        incident=create_test_incident(),
    )

    assert state.hypotheses == []


def test_investigation_state_defaults_to_empty_evidence_ids():
    state = InvestigationState(
        incident=create_test_incident(),
    )

    assert state.evidence_ids == []


def test_investigation_state_defaults_to_empty_tool_history():
    state = InvestigationState(
        incident=create_test_incident(),
    )

    assert state.tool_history == []


def test_investigation_state_defaults_to_no_final_result():
    state = InvestigationState(
        incident=create_test_incident(),
    )

    assert state.final_result is None


def test_investigation_state_instances_do_not_share_mutable_defaults():
    state_one = InvestigationState(
        incident=create_test_incident(),
    )
    state_two = InvestigationState(
        incident=create_test_incident(),
    )

    state_one.evidence_ids.append("LOG-TEST-01")
    state_one.hypotheses.append(Hypothesis(description="Database connection issue"))
    state_one.tool_history.append(
        ToolCallRecord(
            tool_name="logs",
            evidence_ids=["LOG-TEST-01"],
        )
    )

    assert state_two.evidence_ids == []
    assert state_two.hypotheses == []
    assert state_two.tool_history == []


def test_investigation_state_accepts_hypothesis():
    hypothesis = Hypothesis(description="Database connection exhaustion")

    state = InvestigationState(
        incident=create_test_incident(),
        hypotheses=[hypothesis],
    )

    assert len(state.hypotheses) == 1
    assert state.hypotheses[0].description == "Database connection exhaustion"


def test_hypothesis_defaults_to_open_status():
    hypothesis = Hypothesis(description="Database connection exhaustion")

    assert hypothesis.status == HypothesisStatus.OPEN


def test_tool_call_record_preserves_evidence_ids():
    record = ToolCallRecord(
        tool_name="logs",
        evidence_ids=["LOG-001-01", "LOG-001-02"],
    )

    assert record.tool_name == "logs"
    assert record.evidence_ids == [
        "LOG-001-01",
        "LOG-001-02",
    ]


def test_investigation_state_accepts_final_result():
    result = RCAResult(
        incident_id="INC-TEST",
        root_cause="Database connection pool exhaustion",
        affected_service="checkout-service",
        evidence_ids=["LOG-TEST-01"],
        explanation="Checkout requests were blocked waiting for database connections.",
        confidence=0.9,
    )

    state = InvestigationState(
        incident=create_test_incident(),
        final_result=result,
    )

    assert state.final_result == result
    assert state.final_result.incident_id == "INC-TEST"
    assert state.final_result.evidence_ids == ["LOG-TEST-01"]


def test_investigation_state_does_not_expose_ground_truth():
    state = InvestigationState(
        incident=create_test_incident(),
    )

    assert not hasattr(state, "ground_truth")
