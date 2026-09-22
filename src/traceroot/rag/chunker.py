from traceroot.rag.models import KnowledgeChunk, KnowledgeDocument


def chunk_document(
    document: KnowledgeDocument,
    chunk_size: int = 600,
    overlap: int = 100,
) -> list[KnowledgeChunk]:

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")

    if overlap < 0:
        raise ValueError("overlap cannot be negative")

    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    words = document.content.split()

    chunks = []
    start = 0
    chunk_index = 0

    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk_words = words[start:end]

        chunks.append(
            KnowledgeChunk(
                id=f"{document.source}::{chunk_index}",
                content=" ".join(chunk_words),
                source=document.source,
                document_type=document.document_type,
                service=document.service,
                topic=document.topic,
                chunk_index=chunk_index,
            )
        )

        if end == len(words):
            break

        start += chunk_size - overlap
        chunk_index += 1

    return chunks