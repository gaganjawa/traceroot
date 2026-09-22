from pathlib import Path

from qdrant_client import QdrantClient

from traceroot.baseline.rag import generate_rag_rca
from traceroot.data.loader import load_incident
from traceroot.rag.chunker import chunk_document
from traceroot.rag.index import create_knowledge_collection, index_chunks
from traceroot.rag.loader import load_knowledge_corpus


def main():
    # 1. Load engineering knowledge
    documents = load_knowledge_corpus(Path("data/knowledge"))

    # 2. Chunk documents
    chunks = []

    for document in documents:
        chunks.extend(chunk_document(document))

    # 3. Create local in-memory Qdrant
    qdrant_client = QdrantClient(":memory:")

    # 4. Create collection and index knowledge
    create_knowledge_collection(qdrant_client)
    index_chunks(qdrant_client, chunks)

    # 5. Load INC-001
    incident = load_incident(Path("data/incidents/INC-001/incident.json"))

    # 6. Run the real RAG baseline
    result = generate_rag_rca(
        qdrant_client=qdrant_client,
        incident=incident,
        top_k=5,
    )

    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
