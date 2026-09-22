from unittest.mock import patch

import pytest
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from traceroot.rag.index import COLLECTION_NAME, create_knowledge_collection
from traceroot.rag.models import KnowledgeChunk, RetrievalResult
from traceroot.rag.retriever import retrieve


@patch("traceroot.rag.retriever.embed_text")
def test_retrieve(mock_embed_text):
    mock_embed_text.return_value = [1.0] + [0.0] * 1535

    client = QdrantClient(":memory:")
    create_knowledge_collection(client)

    client.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            PointStruct(
                id=1,
                vector=[1.0] + [0.0] * 1535,
                payload={
                    "chunk_id": "test.md::0",
                    "content": "Database connection pool saturation can cause request latency.",
                    "source": "test.md",
                    "document_type": "runbook",
                    "service": "checkout-service",
                    "topic": "latency",
                    "chunk_index": 0,
                },
            )
        ],
    )

    results = retrieve(
        client,
        query="checkout latency",
        top_k=1,
    )

    assert len(results) == 1

    result = results[0]

    assert isinstance(result, RetrievalResult)
    assert isinstance(result.chunk, KnowledgeChunk)
    assert result.chunk.id == "test.md::0"
    assert result.chunk.service == "checkout-service"
    assert result.chunk.topic == "latency"
    assert result.score == pytest.approx(1.0)


@patch("traceroot.rag.retriever.embed_text")
def test_verify_top_k_propagated_to_qdrant(mock_embed_text):
    mock_embed_text.return_value = [1.0] + [0.0] * 1535

    client = QdrantClient(":memory:")
    create_knowledge_collection(client)

    client.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            PointStruct(
                id=1,
                vector=[1.0] + [0.0] * 1535,
                payload={
                    "chunk_id": "test.md::0",
                    "content": "Checkout database latency",
                    "source": "test.md",
                    "document_type": "runbook",
                    "service": "checkout-service",
                    "topic": "latency",
                    "chunk_index": 0,
                },
            ),
            PointStruct(
                id=2,
                vector=[0.9, 0.1] + [0.0] * 1534,
                payload={
                    "chunk_id": "test.md::1",
                    "content": "Payment processing",
                    "source": "test.md",
                    "document_type": "runbook",
                    "service": "payment-service",
                    "topic": "payments",
                    "chunk_index": 1,
                },
            ),
        ],
    )

    results = retrieve(client, "checkout latency", top_k=1)

    assert len(results) == 1
    assert results[0].chunk.id == "test.md::0"


def test_retrieve_rejects_empty_query():
    client = QdrantClient(":memory:")

    with pytest.raises(ValueError):
        retrieve(client, "", top_k=5)


def test_retrieve_rejects_whitespace_query():
    client = QdrantClient(":memory:")

    with pytest.raises(ValueError):
        retrieve(client, "   ", top_k=5)


def test_retrieve_rejects_invalid_top_k():
    client = QdrantClient(":memory:")

    with pytest.raises(ValueError):
        retrieve(client, "checkout latency", top_k=0)