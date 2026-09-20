from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class EvidenceType(StrEnum):
    LOG = "log"
    METRIC = "metric"
    DEPLOYMENT = "deployment"
    GIT_CHANGE = "git_change"
    KNOWLEDGE = "knowledge"


class Evidence(BaseModel):
    id: str
    type: EvidenceType
    source: str
    content: str
    service: str | None = None
    timestamp: datetime | None = None