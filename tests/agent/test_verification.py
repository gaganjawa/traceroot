from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from traceroot.agent.state import (
    Hypothesis,
    HypothesisStatus,
    InvestigationState,
    ToolCallRecord,
)
from traceroot.agent.verification import (
    HypothesisAssessment,
    HypothesisAssessments,
    verify_hypotheses,
)
from traceroot.domain.incident import Incident


def create_test_incident() -> Incident:
    return Incident(
        id="INC-TEST",
        title="Checkout latency",
        description="Checkout requests are slow and timing out.",
        start_time=datetime(2026, 9, 25, tzinfo=UTC),
        suspected_services=["checkout-service"],
    )


def create_test_state() -> InvestigationState:
    return InvestigationState(
        incident=create_test_incident(),
        hypotheses=[
            Hypothesis(
                description="Database connection exhaustion",
            ),
            Hypothesis(
                description="Downstream payment-service latency",
            ),
        ],
        evidence_ids=[
            "METRIC-TEST-01",
            "LOG-TEST-01",
        ],
        tool_history=[
            ToolCallRecord(
                tool_name="metrics",
                evidence_ids=["METRIC-TEST-01"],
                observations=["db_connection_waiters value=37"],
                reasoning="Check whether checkout is waiting on database connections.",
            ),
            ToolCallRecord(
                tool_name="logs",
                evidence_ids=["LOG-TEST-01"],
                observations=["Timed out waiting for database connection"],
                reasoning="Confirm whether request failures are database-related.",
            ),
        ],
    )


def create_mock_response(
    assessments: list[HypothesisAssessment],
):
    response = MagicMock()
    response.output_parsed = HypothesisAssessments(
        assessments=assessments,
    )
    return response


@patch("traceroot.agent.verification.get_llm_client")
def test_verify_hypotheses_updates_supported_status(
    mock_get_llm_client,
):
    mock_client = MagicMock()
    mock_client.responses.parse.return_value = create_mock_response(
        [
            HypothesisAssessment(
                description="Database connection exhaustion",
                status=HypothesisStatus.SUPPORTED,
                reasoning="Metrics and logs support connection exhaustion.",
            ),
        ]
    )
    mock_get_llm_client.return_value = mock_client

    state = create_test_state()

    result = verify_hypotheses(state)

    assert result.hypotheses[0].status == HypothesisStatus.SUPPORTED


@patch("traceroot.agent.verification.get_llm_client")
def test_verify_hypotheses_updates_rejected_status(
    mock_get_llm_client,
):
    mock_client = MagicMock()
    mock_client.responses.parse.return_value = create_mock_response(
        [
            HypothesisAssessment(
                description="Downstream payment-service latency",
                status=HypothesisStatus.REJECTED,
                reasoning="Available evidence points to database connection waits instead.",
            ),
        ]
    )
    mock_get_llm_client.return_value = mock_client

    state = create_test_state()

    result = verify_hypotheses(state)

    assert result.hypotheses[1].status == HypothesisStatus.REJECTED


@patch("traceroot.agent.verification.get_llm_client")
def test_verify_hypotheses_keeps_open_when_evidence_is_insufficient(
    mock_get_llm_client,
):
    mock_client = MagicMock()
    mock_client.responses.parse.return_value = create_mock_response(
        [
            HypothesisAssessment(
                description="Downstream payment-service latency",
                status=HypothesisStatus.OPEN,
                reasoning="There is not enough evidence to confirm or reject it.",
            ),
        ]
    )
    mock_get_llm_client.return_value = mock_client

    state = create_test_state()

    result = verify_hypotheses(state)

    assert result.hypotheses[1].status == HypothesisStatus.OPEN


@patch("traceroot.agent.verification.get_llm_client")
def test_verify_hypotheses_preserves_descriptions(
    mock_get_llm_client,
):
    mock_client = MagicMock()
    mock_client.responses.parse.return_value = create_mock_response(
        [
            HypothesisAssessment(
                description="Database connection exhaustion",
                status=HypothesisStatus.SUPPORTED,
                reasoning="Supported by evidence.",
            ),
            HypothesisAssessment(
                description="Downstream payment-service latency",
                status=HypothesisStatus.REJECTED,
                reasoning="Not supported by gathered evidence.",
            ),
        ]
    )
    mock_get_llm_client.return_value = mock_client

    state = create_test_state()

    original_descriptions = [hypothesis.description for hypothesis in state.hypotheses]

    result = verify_hypotheses(state)

    result_descriptions = [hypothesis.description for hypothesis in result.hypotheses]

    assert result_descriptions == original_descriptions


@patch("traceroot.agent.verification.get_llm_client")
def test_verify_hypotheses_preserves_evidence_ids(
    mock_get_llm_client,
):
    mock_client = MagicMock()
    mock_client.responses.parse.return_value = create_mock_response([])
    mock_get_llm_client.return_value = mock_client

    state = create_test_state()

    original_evidence_ids = list(state.evidence_ids)

    result = verify_hypotheses(state)

    assert result.evidence_ids == original_evidence_ids


@patch("traceroot.agent.verification.get_llm_client")
def test_verify_hypotheses_preserves_tool_history(
    mock_get_llm_client,
):
    mock_client = MagicMock()
    mock_client.responses.parse.return_value = create_mock_response([])
    mock_get_llm_client.return_value = mock_client

    state = create_test_state()

    original_tool_history = list(state.tool_history)

    result = verify_hypotheses(state)

    assert result.tool_history == original_tool_history


@patch("traceroot.agent.verification.get_llm_client")
def test_verify_hypotheses_preserves_incident(
    mock_get_llm_client,
):
    mock_client = MagicMock()
    mock_client.responses.parse.return_value = create_mock_response([])
    mock_get_llm_client.return_value = mock_client

    state = create_test_state()

    original_incident = state.incident

    result = verify_hypotheses(state)

    assert result.incident == original_incident


@patch("traceroot.agent.verification.get_llm_client")
def test_verify_hypotheses_does_not_add_new_hypotheses(
    mock_get_llm_client,
):
    mock_client = MagicMock()
    mock_client.responses.parse.return_value = create_mock_response(
        [
            HypothesisAssessment(
                description="Completely new hypothesis",
                status=HypothesisStatus.SUPPORTED,
                reasoning="This should be ignored.",
            ),
        ]
    )
    mock_get_llm_client.return_value = mock_client

    state = create_test_state()

    original_count = len(state.hypotheses)

    result = verify_hypotheses(state)

    assert len(result.hypotheses) == original_count

    descriptions = [hypothesis.description for hypothesis in result.hypotheses]

    assert "Completely new hypothesis" not in descriptions


@patch("traceroot.agent.verification.get_llm_client")
def test_verify_hypotheses_raises_when_structured_output_is_missing(
    mock_get_llm_client,
):
    response = MagicMock()
    response.output_parsed = None

    mock_client = MagicMock()
    mock_client.responses.parse.return_value = response
    mock_get_llm_client.return_value = mock_client

    with pytest.raises(RuntimeError):
        verify_hypotheses(create_test_state())


@patch("traceroot.agent.verification.get_llm_client")
def test_verify_hypotheses_prompt_uses_only_allowed_state(
    mock_get_llm_client,
):
    mock_client = MagicMock()
    mock_client.responses.parse.return_value = create_mock_response([])
    mock_get_llm_client.return_value = mock_client

    state = create_test_state()

    verify_hypotheses(state)

    call_args = mock_client.responses.parse.call_args
    prompt = call_args.kwargs["input"]

    assert state.incident.id in prompt
    assert state.incident.title in prompt
    assert state.incident.description in prompt

    assert "Database connection exhaustion" in prompt
    assert "Downstream payment-service latency" in prompt

    assert "METRIC-TEST-01" in prompt
    assert "LOG-TEST-01" in prompt
    assert "db_connection_waiters value=37" in prompt
    assert "Timed out waiting for database connection" in prompt

    assert "ground_truth" not in prompt.lower()
