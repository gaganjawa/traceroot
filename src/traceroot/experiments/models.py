from datetime import datetime

from pydantic import BaseModel, Field

from traceroot.agent.state import Hypothesis, ToolCallRecord
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
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    llm_calls: int | None = Field(default=None, ge=0)
    estimated_cost_usd: float | None = Field(default=None, ge=0)

    timestamp: datetime


class AgentExperimentRecord(BaseModel):
    incident_id: str
    approach: str = "agent"
    model: str

    hypotheses: list[Hypothesis]
    evidence_ids: list[str]
    tool_history: list[ToolCallRecord]

    stop_reason: str | None = None
    stop_reasoning: str | None = None

    result: RCAResult

    latency_ms: float = Field(ge=0)

    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    llm_calls: int | None = Field(default=None, ge=0)
    estimated_cost_usd: float | None = Field(default=None, ge=0)

    timestamp: datetime
