from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from traceroot.agent.hypothesis import GeneratedHypotheses, generate_hypotheses
from traceroot.agent.state import Hypothesis, HypothesisStatus
from traceroot.domain.incident import Incident
from traceroot.llm.usage import LLMUsage


def create_test_incident() -> Incident:
    return Incident(
        id="INC-TEST",
        title="Checkout latency",
        description="Checkout requests are slow and timing out.",
        start_time=datetime(2026, 9, 23, 11, 11, 11, 11, tzinfo=UTC),
        suspected_services=["checkout-service"],
    )


@patch("traceroot.agent.hypothesis.get_llm_client")
def test_generate_hypotheses_returns_hypotheses(mock_get_llm_client):
    mock_response = MagicMock()
    mock_response.output_parsed = GeneratedHypotheses(
        hypotheses=[
            "Database connection exhaustion",
            "Downstream payment-service latency",
        ]
    )

    mock_client = MagicMock()
    mock_client.responses.parse.return_value = mock_response
    mock_get_llm_client.return_value = mock_client

    result = generate_hypotheses(
        incident=create_test_incident(),
        max_hypotheses=3,
    )

    assert len(result) == 2
    assert result[0].description == "Database connection exhaustion"
    assert result[1].description == "Downstream payment-service latency"


@patch("traceroot.agent.hypothesis.get_llm_client")
def test_generate_hypotheses_returns_typed_hypotheses(mock_get_llm_client):
    mock_response = MagicMock()
    mock_response.output_parsed = GeneratedHypotheses(
        hypotheses=[
            "Database connection exhaustion",
        ]
    )

    mock_client = MagicMock()
    mock_client.responses.parse.return_value = mock_response
    mock_get_llm_client.return_value = mock_client

    result = generate_hypotheses(
        incident=create_test_incident(),
    )

    assert result
    assert all(isinstance(hypothesis, Hypothesis) for hypothesis in result)


@patch("traceroot.agent.hypothesis.get_llm_client")
def test_generate_hypotheses_defaults_status_to_open(mock_get_llm_client):
    mock_response = MagicMock()
    mock_response.output_parsed = GeneratedHypotheses(
        hypotheses=[
            "Database connection exhaustion",
        ]
    )

    mock_client = MagicMock()
    mock_client.responses.parse.return_value = mock_response
    mock_get_llm_client.return_value = mock_client

    result = generate_hypotheses(
        incident=create_test_incident(),
    )

    assert result[0].status == HypothesisStatus.OPEN


@patch("traceroot.agent.hypothesis.get_llm_client")
def test_generate_hypotheses_respects_max_hypotheses(mock_get_llm_client):
    mock_response = MagicMock()
    mock_response.output_parsed = GeneratedHypotheses(
        hypotheses=[
            "Database connection exhaustion",
            "Downstream payment-service latency",
            "Recent deployment regression",
            "CPU saturation",
        ]
    )

    mock_client = MagicMock()
    mock_client.responses.parse.return_value = mock_response
    mock_get_llm_client.return_value = mock_client

    result = generate_hypotheses(
        incident=create_test_incident(),
        max_hypotheses=2,
    )

    assert len(result) == 2


def test_generate_hypotheses_rejects_invalid_max_hypotheses():
    incident = create_test_incident()

    with pytest.raises(ValueError):
        generate_hypotheses(
            incident=incident,
            max_hypotheses=0,
        )

    with pytest.raises(ValueError):
        generate_hypotheses(
            incident=incident,
            max_hypotheses=-1,
        )


@patch("traceroot.agent.hypothesis.get_llm_client")
def test_generate_hypotheses_maps_structured_llm_output(mock_get_llm_client):
    mock_response = MagicMock()
    mock_response.output_parsed = GeneratedHypotheses(
        hypotheses=[
            "Database connection exhaustion",
            "Payment dependency latency",
        ]
    )

    mock_client = MagicMock()
    mock_client.responses.parse.return_value = mock_response
    mock_get_llm_client.return_value = mock_client

    result = generate_hypotheses(
        incident=create_test_incident(),
    )

    descriptions = [hypothesis.description for hypothesis in result]

    assert descriptions == [
        "Database connection exhaustion",
        "Payment dependency latency",
    ]


@patch("traceroot.agent.hypothesis.get_llm_client")
def test_generate_hypotheses_prompt_contains_only_incident_context(
    mock_get_llm_client,
):
    mock_response = MagicMock()
    mock_response.output_parsed = GeneratedHypotheses(
        hypotheses=["Database connection exhaustion"]
    )

    mock_client = MagicMock()
    mock_client.responses.parse.return_value = mock_response
    mock_get_llm_client.return_value = mock_client

    incident = create_test_incident()

    generate_hypotheses(
        incident=incident,
        max_hypotheses=3,
    )

    call_args = mock_client.responses.parse.call_args
    prompt = call_args.kwargs["input"]

    assert incident.id in prompt
    assert incident.title in prompt
    assert incident.description in prompt
    assert "checkout-service" in prompt

    assert "LOG-" not in prompt
    assert "METRIC-" not in prompt
    assert "DEPLOY-" not in prompt
    assert "CHANGE-" not in prompt


@patch("traceroot.agent.hypothesis.get_llm_client")
def test_generate_hypotheses_does_not_include_ground_truth(
    mock_get_llm_client,
):
    mock_response = MagicMock()
    mock_response.output_parsed = GeneratedHypotheses(
        hypotheses=["Database connection exhaustion"]
    )

    mock_client = MagicMock()
    mock_client.responses.parse.return_value = mock_response
    mock_get_llm_client.return_value = mock_client

    generate_hypotheses(
        incident=create_test_incident(),
    )

    call_args = mock_client.responses.parse.call_args
    prompt = call_args.kwargs["input"]

    assert "ground_truth" not in prompt.lower()
    assert "root cause:" not in prompt.lower()


@patch("traceroot.agent.hypothesis.get_llm_client")
def test_generate_hypotheses_raises_when_structured_output_is_missing(
    mock_get_llm_client,
):
    mock_response = MagicMock()
    mock_response.output_parsed = None

    mock_client = MagicMock()
    mock_client.responses.parse.return_value = mock_response
    mock_get_llm_client.return_value = mock_client

    with pytest.raises(RuntimeError):
        generate_hypotheses(
            incident=create_test_incident(),
        )


@patch("traceroot.agent.hypothesis.get_llm_client")
def test_generate_hypotheses_records_llm_usage(
    mock_get_llm_client,
):
    usage = LLMUsage()

    mock_response = MagicMock()
    mock_response.output_parsed = GeneratedHypotheses(
        hypotheses=[
            "Database connection exhaustion",
        ]
    )
    mock_response.usage.input_tokens = 120
    mock_response.usage.output_tokens = 30

    mock_client = MagicMock()
    mock_client.responses.parse.return_value = mock_response
    mock_get_llm_client.return_value = mock_client

    result = generate_hypotheses(
        incident=create_test_incident(),
        llm_usage=usage,
    )

    assert len(result) == 1
    assert result[0].description == "Database connection exhaustion"

    assert usage.input_tokens == 120
    assert usage.output_tokens == 30
    assert usage.total_tokens == 150
    assert usage.llm_calls == 1


@patch("traceroot.agent.hypothesis.get_llm_client")
def test_generate_hypotheses_records_call_when_token_usage_unavailable(
    mock_get_llm_client,
):
    usage = LLMUsage()

    mock_response = MagicMock()
    mock_response.output_parsed = GeneratedHypotheses(
        hypotheses=[
            "Database connection exhaustion",
        ]
    )
    mock_response.usage = None

    mock_client = MagicMock()
    mock_client.responses.parse.return_value = mock_response
    mock_get_llm_client.return_value = mock_client

    result = generate_hypotheses(
        incident=create_test_incident(),
        llm_usage=usage,
    )

    assert len(result) == 1

    assert usage.input_tokens is None
    assert usage.output_tokens is None
    assert usage.total_tokens is None
    assert usage.llm_calls == 1
