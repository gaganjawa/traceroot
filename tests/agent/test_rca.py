from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from traceroot.agent.rca import (
    GeneratedFinalRCA,
    build_context_from_state,
    generate_final_rca,
)
from traceroot.agent.state import (
    Hypothesis,
    HypothesisStatus,
    InvestigationState,
    ToolCallRecord,
)
from traceroot.domain.incident import Incident


def create_test_state() -> InvestigationState:
    incident = Incident(
        id="INC-001",
        title="Checkout latency",
        description="Checkout requests are slow.",
        start_time=datetime(2026, 9, 25, tzinfo=UTC),
        suspected_services=["checkout-service"],
    )

    return InvestigationState(
        incident=incident,
        hypotheses=[
            Hypothesis(
                description="Database connection pool exhaustion",
                status=HypothesisStatus.SUPPORTED,
            )
        ],
        evidence_ids=[
            "LOG-001-02",
            "METRIC-001-02",
            "CHANGE-001-01",
        ],
        tool_history=[
            ToolCallRecord(
                tool_name="logs",
                service="checkout-service",
                evidence_ids=["LOG-001-02"],
                observations=["Database connection acquisition timeout"],
                reasoning="Check database-related failures.",
            )
        ],
    )


def create_generated_rca(
    evidence_ids=None,
) -> GeneratedFinalRCA:
    return GeneratedFinalRCA(
        root_cause="Checkout database connection pool was undersized.",
        affected_service="checkout-service",
        evidence_ids=evidence_ids or ["LOG-001-02", "CHANGE-001-01"],
        explanation=(
            "Logs show connection acquisition failures and the "
            "configuration change reduced the pool size."
        ),
        confidence=0.91,
    )


@patch("traceroot.agent.rca.get_llm_client")
def test_generate_final_rca_sets_incident_id_from_state(
    mock_get_llm_client,
):
    state = create_test_state()

    mock_client = MagicMock()
    mock_client.responses.parse.return_value = MagicMock(
        output_parsed=create_generated_rca()
    )
    mock_get_llm_client.return_value = mock_client

    result = generate_final_rca(state)

    assert result.final_result.incident_id == "INC-001"


@patch("traceroot.agent.rca.get_llm_client")
def test_generate_final_rca_stores_result_in_state(
    mock_get_llm_client,
):
    state = create_test_state()

    mock_client = MagicMock()
    mock_client.responses.parse.return_value = MagicMock(
        output_parsed=create_generated_rca()
    )
    mock_get_llm_client.return_value = mock_client

    result = generate_final_rca(state)

    assert result.final_result is not None
    assert result is state


@patch("traceroot.agent.rca.get_llm_client")
def test_generate_final_rca_rejects_unknown_evidence_ids(
    mock_get_llm_client,
):
    state = create_test_state()

    mock_client = MagicMock()
    mock_client.responses.parse.return_value = MagicMock(
        output_parsed=create_generated_rca(
            evidence_ids=[
                "LOG-001-02",
                "FAKE-999",
            ]
        )
    )
    mock_get_llm_client.return_value = mock_client

    with pytest.raises(
        RuntimeError,
        match="evidence that was not gathered",
    ):
        generate_final_rca(state)


@patch("traceroot.agent.rca.get_llm_client")
def test_generate_final_rca_raises_when_llm_output_missing(
    mock_get_llm_client,
):
    state = create_test_state()

    mock_client = MagicMock()
    mock_client.responses.parse.return_value = MagicMock(output_parsed=None)
    mock_get_llm_client.return_value = mock_client

    with pytest.raises(
        RuntimeError,
        match="valid final RCA",
    ):
        generate_final_rca(state)


def test_generate_final_rca_requires_evidence():
    state = create_test_state()
    state.evidence_ids = []

    with pytest.raises(
        ValueError,
        match="No evidence gathered",
    ):
        generate_final_rca(state)


def test_generate_final_rca_prompt_contains_incident():
    state = create_test_state()

    prompt = build_context_from_state(state)

    assert "Checkout latency" in prompt
    assert "Checkout requests are slow." in prompt


def test_generate_final_rca_prompt_contains_hypotheses():
    state = create_test_state()

    prompt = build_context_from_state(state)

    assert "Database connection pool exhaustion" in prompt
    assert "supported" in prompt.lower()


def test_generate_final_rca_prompt_contains_tool_observations():
    state = create_test_state()

    prompt = build_context_from_state(state)

    assert "Database connection acquisition timeout" in prompt


def test_generate_final_rca_prompt_does_not_include_ground_truth():
    state = create_test_state()

    prompt = build_context_from_state(state)

    assert "ground_truth" not in prompt.lower()
