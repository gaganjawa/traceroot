from unittest.mock import patch

from qdrant_client import QdrantClient

from traceroot.rag.index import (
    COLLECTION_NAME,
    create_knowledge_collection,
    index_chunks,
)
from traceroot.rag.models import KnowledgeChunk


def create_test_chunk() -> KnowledgeChunk:
    return KnowledgeChunk(
        id="test.md::0",
        content="Database connection pool saturation can cause request latency.",
        source="test.md",
        document_type="runbook",
        service="checkout-service",
        topic="latency",
        chunk_index=0,
    )


def test_create_knowledge_collection():
    client = QdrantClient(":memory:")

    create_knowledge_collection(client)

    assert client.collection_exists(COLLECTION_NAME)


@patch("traceroot.rag.index.embed_texts")
def test_index_chunks(mock_embed_texts):
    # Pretend OpenAI returned one 1536-dimensional embedding.
    mock_embed_texts.return_value = [[0.1] * 1536]

    client = QdrantClient(":memory:")
    create_knowledge_collection(client)

    chunk = create_test_chunk()

    index_chunks(client, [chunk])

    points, _ = client.scroll(
        collection_name=COLLECTION_NAME,
        limit=10,
        with_vectors=True,
    )

    assert len(points) == 1

    point = points[0]

    assert point.payload["chunk_id"] == "test.md::0"
    assert point.payload["content"] == (
        "Database connection pool saturation can cause request latency."
    )
    assert point.payload["source"] == "test.md"
    assert point.payload["document_type"] == "runbook"
    assert point.payload["service"] == "checkout-service"
    assert point.payload["topic"] == "latency"
    assert point.payload["chunk_index"] == 0

    assert len(point.vector) == 1536


@patch("traceroot.rag.index.embed_texts")
def test_reindexing_same_chunk_does_not_duplicate(mock_embed_texts):
    mock_embed_texts.return_value = [[0.1] * 1536]

    client = QdrantClient(":memory:")
    create_knowledge_collection(client)

    chunk = create_test_chunk()

    index_chunks(client, [chunk])
    index_chunks(client, [chunk])

    points, _ = client.scroll(
        collection_name=COLLECTION_NAME,
        limit=10,
    )

    assert len(points) == 1


@patch("traceroot.rag.index.embed_texts")
def test_index_chunks_with_empty_list(mock_embed_texts):
    client = QdrantClient(":memory:")
    create_knowledge_collection(client)

    index_chunks(client, [])

    points, _ = client.scroll(
        collection_name=COLLECTION_NAME,
        limit=10,
    )

    assert len(points) == 0
    mock_embed_texts.assert_not_called()