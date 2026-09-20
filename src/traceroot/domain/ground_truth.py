from pydantic import BaseModel, Field


class GroundTruth(BaseModel):
    incident_id: str
    root_cause: str
    root_cause_category: str
    affected_service: str
    supporting_evidence_ids: list[str] = Field(default_factory=list)