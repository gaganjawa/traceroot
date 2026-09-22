import pytest
from traceroot.rag.chunker import chunk_document
from traceroot.rag.models import KnowledgeDocument


def create_document(content: str) -> KnowledgeDocument:
    return KnowledgeDocument(
        source="test.md",
        content=content,
        document_type="runbook",
        service="test-service",
        topic="testing",
    )


def test_chunk_document_with_overlap():
    document = create_document(
        "one two three four five six seven"
    )

    chunks = chunk_document(
        document,
        chunk_size=4,
        overlap=2,
    )

    assert len(chunks) == 3

    assert chunks[0].content == "one two three four"
    assert chunks[1].content == "three four five six"
    assert chunks[2].content == "five six seven"

    assert chunks[0].id == "test.md::0"
    assert chunks[1].id == "test.md::1"
    assert chunks[2].id == "test.md::2"


def test_chunk_preserves_metadata():
    document = create_document("one two three")

    chunks = chunk_document(document, chunk_size=2, overlap=0)

    chunk = chunks[0]

    assert chunk.source == "test.md"
    assert chunk.document_type == "runbook"
    assert chunk.service == "test-service"
    assert chunk.topic == "testing"
    assert chunk.chunk_index == 0


def test_invalid_chunk_size():
    document = create_document("one two three")

    with pytest.raises(ValueError):
        chunk_document(document, chunk_size=0)


def test_overlap_cannot_equal_chunk_size():
    document = create_document("one two three")

    with pytest.raises(ValueError):
        chunk_document(
            document,
            chunk_size=2,
            overlap=2,
        )


def test_overlap_cannot_be_negative():
    document = create_document("one two three")

    with pytest.raises(ValueError):
        chunk_document(
            document,
            chunk_size=2,
            overlap=-1,
        )