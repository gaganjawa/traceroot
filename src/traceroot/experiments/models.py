from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

from traceroot.agent.state import Hypothesis, InvestigationState, ToolCallRecord
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


class FailureStage(StrEnum):
    HYPOTHESIS_GENERATION = "hypothesis_generation"
    INVESTIGATION = "investigation"
    HYPOTHESIS_VERIFICATION = "hypothesis_verification"
    FINAL_RCA = "final_rca"
    RECORD_CONSTRUCTION = "record_construction"
    PERSISTENCE = "persistence"


class FailedAgentExperimentRecord(BaseModel):
    status: Literal["failed"] = "failed"
    approach: Literal["agent"] = "agent"
    model: str
    state: InvestigationState
    failure_stage: FailureStage
    failure_type: str
    failure_message: str = Field(max_length=240)
    latency_ms: float = Field(ge=0)
    timestamp: datetime
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    llm_calls: int = Field(default=0, ge=0)
