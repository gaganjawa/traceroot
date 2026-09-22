from pydantic import BaseModel


class KnowledgeDocument(BaseModel):
    source: str
    content: str
    document_type: str
    service: str
    topic: str


class KnowledgeChunk(BaseModel):
    id: str
    content: str
    source: str
    document_type: str
    service: str
    topic: str
    chunk_index: int


class RetrievalResult(BaseModel):
    chunk: KnowledgeChunk
    score: float
