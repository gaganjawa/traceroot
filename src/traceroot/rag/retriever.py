from qdrant_client import QdrantClient

from traceroot.rag.embeddings import embed_text
from traceroot.rag.index import COLLECTION_NAME
from traceroot.rag.models import KnowledgeChunk, RetrievalResult


def retrieve(
    client: QdrantClient,
    query: str,
    top_k: int = 5,
) -> list[RetrievalResult]:

    if not query.strip():
        raise ValueError("Query cannot be empty")

    if top_k <= 0:
        raise ValueError("top_k must be greater than 0")

    query_vector = embed_text(query)

    search_result = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=top_k,
        with_payload=True,
    )

    retrieval_results = []
    for result in search_result.points:
        payload = result.payload

        chunk = KnowledgeChunk(
            id=payload["chunk_id"],
            content=payload["content"],
            source=payload["source"],
            document_type=payload["document_type"],
            service=payload["service"],
            topic=payload["topic"],
            chunk_index=payload["chunk_index"],
        )

        retrieval_results.append(
            RetrievalResult(
                chunk=chunk,
                score=result.score,
            )
        )

    return retrieval_results
