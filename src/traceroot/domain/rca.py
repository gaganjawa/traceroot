from pydantic import BaseModel, Field


class RCAResult(BaseModel):
    incident_id: str
    root_cause: str
    affected_service: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    explanation: str
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
