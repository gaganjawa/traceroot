from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from traceroot.baseline.rag import (
    GeneratedRCA,
    build_context,
    generate_rag_rca,
    generate_rca,
)
from traceroot.domain.incident import Incident
from traceroot.rag.models import KnowledgeChunk, RetrievalResult


def create_incident() -> Incident:
    return Incident(
        id="INC-001",
        title="Database Latency",
        description="High latency observed.",
        start_time=datetime(
            2026,
            9,
            21,
            10,
            15,
            tzinfo=UTC,
        ),
    )


def create_retrieval_result() -> RetrievalResult:
    return RetrievalResult(
        chunk=KnowledgeChunk(
            id="checkout::0",
            content=(
                "Checkout requests wait on the database connection pool "
                "when it is saturated."
            ),
            source="checkout-runbook.md",
            document_type="runbook",
            service="checkout-service",
            topic="latency",
            chunk_index=0,
        ),
        score=0.91,
    )


def create_generated_rca() -> GeneratedRCA:
    return GeneratedRCA(
        root_cause="Database connection pool exhaustion",
        affected_service="checkout-service",
        explanation=("Checkout requests are waiting for database connections."),
        confidence=0.8,
    )


def test_build_context_includes_chunk_id_source_and_content():
    retrieval_result = create_retrieval_result()

    context = build_context([retrieval_result])

    assert "[CHUNK_ID: checkout::0]" in context
    assert "[SOURCE: checkout-runbook.md]" in context
    assert (
        "Checkout requests wait on the database connection pool "
        "when it is saturated." in context
    )


def test_build_context_with_multiple_results():
    first = create_retrieval_result()

    second = RetrievalResult(
        chunk=KnowledgeChunk(
            id="architecture::0",
            content="Checkout service communicates with payment-service.",
            source="architecture.md",
            document_type="architecture",
            service="platform",
            topic="service-topology",
            chunk_index=0,
        ),
        score=0.82,
    )

    context = build_context([first, second])

    assert "[CHUNK_ID: checkout::0]" in context
    assert "[SOURCE: checkout-runbook.md]" in context

    assert "[CHUNK_ID: architecture::0]" in context
    assert "[SOURCE: architecture.md]" in context

    assert context.index("[CHUNK_ID: checkout::0]") < context.index(
        "[CHUNK_ID: architecture::0]"
    )


def test_build_context_with_no_results_returns_empty_string():
    context = build_context([])

    assert context == ""


@patch("traceroot.baseline.rag.get_llm_client")
def test_generate_rca_returns_structured_result(mock_get_llm_client):
    mock_client = MagicMock()
    mock_get_llm_client.return_value = mock_client

    expected = create_generated_rca()

    mock_response = MagicMock()
    mock_response.output_parsed = expected

    mock_client.responses.parse.return_value = mock_response

    incident = create_incident()

    context = (
        "[CHUNK_ID: checkout::0]\n"
        "[SOURCE: checkout-runbook.md]\n"
        "Checkout requests wait on the database connection pool."
    )

    result = generate_rca(
        incident=incident,
        context=context,
    )

    assert result == expected

    mock_client.responses.parse.assert_called_once()

    call_kwargs = mock_client.responses.parse.call_args.kwargs

    assert call_kwargs["text_format"] is GeneratedRCA

    messages = call_kwargs["input"]

    system_prompt = messages[0]["content"]
    user_prompt = messages[1]["content"]

    assert "production incident investigator" in system_prompt
    assert "only the supplied engineering knowledge" in system_prompt

    assert incident.title in user_prompt
    assert incident.description in user_prompt

    assert "[CHUNK_ID: checkout::0]" in user_prompt
    assert "[SOURCE: checkout-runbook.md]" in user_prompt
    assert "Checkout requests wait on the database connection pool." in user_prompt


@patch("traceroot.baseline.rag.get_llm_client")
def test_generate_rca_raises_when_structured_output_is_missing(
    mock_get_llm_client,
):
    mock_client = MagicMock()
    mock_get_llm_client.return_value = mock_client

    mock_response = MagicMock()
    mock_response.output_parsed = None

    mock_client.responses.parse.return_value = mock_response

    incident = create_incident()

    with pytest.raises(
        RuntimeError,
        match="LLM did not return a valid structured RCA response",
    ):
        generate_rca(
            incident=incident,
            context="Some retrieved engineering knowledge.",
        )


@patch("traceroot.baseline.rag.generate_rca")
@patch("traceroot.baseline.rag.retrieve")
def test_generate_rag_rca_wires_retrieval_and_generation(
    mock_retrieve,
    mock_generate_rca,
):
    incident = create_incident()
    retrieval_result = create_retrieval_result()
    generated = create_generated_rca()

    mock_retrieve.return_value = [retrieval_result]
    mock_generate_rca.return_value = generated

    qdrant_client = MagicMock()

    result = generate_rag_rca(
        qdrant_client=qdrant_client,
        incident=incident,
        top_k=5,
    )

    expected_query = f"{incident.title}\n{incident.description}"

    mock_retrieve.assert_called_once_with(
        qdrant_client,
        expected_query,
        top_k=5,
    )

    mock_generate_rca.assert_called_once()

    generate_call = mock_generate_rca.call_args

    assert generate_call.args[0] == incident

    generated_context = generate_call.args[1]

    assert "[CHUNK_ID: checkout::0]" in generated_context
    assert "[SOURCE: checkout-runbook.md]" in generated_context
    assert (
        "Checkout requests wait on the database connection pool "
        "when it is saturated." in generated_context
    )

    assert result.incident_id == "INC-001"
    assert result.root_cause == generated.root_cause
    assert result.affected_service == generated.affected_service
    assert result.explanation == generated.explanation
    assert result.confidence == generated.confidence

    # Knowledge chunks are retrieval provenance, not operational
    # evidence IDs.
    assert result.evidence_ids == []


@patch("traceroot.baseline.rag.get_llm_client")
@patch("traceroot.baseline.rag.retrieve")
def test_generate_rag_rca_end_to_end_with_mocked_dependencies(
    mock_retrieve,
    mock_get_llm_client,
):
    incident = create_incident()
    retrieval_result = create_retrieval_result()
    expected = create_generated_rca()

    mock_retrieve.return_value = [retrieval_result]

    mock_client = MagicMock()
    mock_get_llm_client.return_value = mock_client

    mock_response = MagicMock()
    mock_response.output_parsed = expected

    mock_client.responses.parse.return_value = mock_response

    qdrant_client = MagicMock()

    result = generate_rag_rca(
        qdrant_client=qdrant_client,
        incident=incident,
        top_k=5,
    )

    assert result.incident_id == incident.id
    assert result.root_cause == expected.root_cause
    assert result.affected_service == expected.affected_service
    assert result.explanation == expected.explanation
    assert result.confidence == expected.confidence
    assert result.evidence_ids == []

    mock_retrieve.assert_called_once_with(
        qdrant_client,
        f"{incident.title}\n{incident.description}",
        top_k=5,
    )

    mock_client.responses.parse.assert_called_once()

    call_kwargs = mock_client.responses.parse.call_args.kwargs
    user_prompt = call_kwargs["input"][1]["content"]

    assert incident.title in user_prompt
    assert incident.description in user_prompt
    assert "[CHUNK_ID: checkout::0]" in user_prompt
    assert "[SOURCE: checkout-runbook.md]" in user_prompt
    assert (
        "Checkout requests wait on the database connection pool "
        "when it is saturated." in user_prompt
    )
