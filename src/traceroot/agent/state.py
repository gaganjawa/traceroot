from enum import StrEnum

from pydantic import BaseModel, Field

from traceroot.domain.incident import Incident
from traceroot.domain.rca import RCAResult


class HypothesisStatus(StrEnum):
    OPEN = "open"
    SUPPORTED = "supported"
    REJECTED = "rejected"


class Hypothesis(BaseModel):
    description: str
    status: HypothesisStatus = HypothesisStatus.OPEN


class ToolCallRecord(BaseModel):
    tool_name: str
    evidence_ids: list[str] = Field(default_factory=list)


class InvestigationState(BaseModel):
    incident: Incident
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    tool_history: list[ToolCallRecord] = Field(default_factory=list)
    final_result: RCAResult | None = None
