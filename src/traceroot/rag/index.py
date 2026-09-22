from uuid import NAMESPACE_URL, uuid5

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from traceroot.rag.embeddings import embed_text, embed_texts
from traceroot.rag.models import KnowledgeChunk

COLLECTION_NAME = "traceroot_knowledge"
VECTOR_SIZE = 1536


def create_knowledge_collection(client: QdrantClient) -> None:
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=VECTOR_SIZE,
            distance=Distance.COSINE,
        ),
    )


def index_chunk(
    client: QdrantClient,
    chunk: KnowledgeChunk,
) -> None:
    vector = embed_text(chunk.content)
    point_id = str(uuid5(NAMESPACE_URL, chunk.id))

    point = PointStruct(
        id=point_id,
        vector=vector,
        payload={
            "chunk_id": chunk.id,
            "content": chunk.content,
            "source": chunk.source,
            "document_type": chunk.document_type,
            "service": chunk.service,
            "topic": chunk.topic,
            "chunk_index": chunk.chunk_index,
        },
    )

    client.upsert(
        collection_name=COLLECTION_NAME,
        points=[point],
    )


# [chunk1, chunk2, chunk3, chunk4]
#              ↓
#        one API request
#              ↓
# [vector1, vector2, vector3, vector4]
def index_chunks(
    client: QdrantClient,
    chunks: list[KnowledgeChunk],
) -> None:

    if not chunks:
        return

    points = []
    texts = [chunk.content for chunk in chunks]

    vectors = embed_texts(texts)

    if len(vectors) != len(chunks):
        raise ValueError("Embedding count does not match chunk count")

    for i, chunk in enumerate(chunks):
        point_id = str(uuid5(NAMESPACE_URL, chunk.id))

        point = PointStruct(
            id=point_id,
            vector=vectors[i],
            payload={
                "chunk_id": chunk.id,
                "content": chunk.content,
                "source": chunk.source,
                "document_type": chunk.document_type,
                "service": chunk.service,
                "topic": chunk.topic,
                "chunk_index": chunk.chunk_index,
            },
        )
        points.append(point)

    client.upsert(
        collection_name=COLLECTION_NAME,
        points=points,
    )
