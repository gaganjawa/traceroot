from pathlib import Path

import yaml

from traceroot.rag.models import KnowledgeDocument


def load_knowledge_document(path: Path) -> KnowledgeDocument:
    content = path.read_text()

    if not content.startswith("---"):
        raise ValueError("Knowledge document must contain YAML front matter")

    parts = content.split("---", 2)

    if len(parts) != 3:
        raise ValueError("Knowledge document has invalid YAML front matter")

    _, front_matter, body = parts
    metadata = yaml.safe_load(front_matter)

    return KnowledgeDocument(
        source=path.name,
        document_type=metadata["document_type"],
        service=metadata["service"],
        topic=metadata["topic"],
        content=body.strip(),
    )


def load_knowledge_corpus(
    directory: Path,
) -> list[KnowledgeDocument]:
    documents = []

    for path in sorted(directory.glob("*.md")):
        document = load_knowledge_document(path)
        documents.append(document)

    return documents
