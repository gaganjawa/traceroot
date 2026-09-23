from datetime import datetime

from pydantic import BaseModel, Field

from traceroot.domain.rca import RCAResult


class RetrievedKnowledge(BaseModel):
    chunk_id: str
    source: str
    score: float


class BaselineExperimentRecord(BaseModel):
    incident_id: str
    approach: str = "rag_baseline"
    model: str
    top_k: int = Field(gt=0)

    retrieved_knowledge: list[RetrievedKnowledge]

    result: RCAResult

    latency_ms: float = Field(ge=0)
    timestamp: datetime
