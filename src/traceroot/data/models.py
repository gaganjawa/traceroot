from datetime import datetime

from pydantic import BaseModel, Field

from traceroot.domain.incident import Incident


class LogEntry(BaseModel):
    id: str
    timestamp: datetime
    service: str
    level: str
    message: str


class MetricEntry(BaseModel):
    id: str
    timestamp: datetime
    service: str
    metric: str
    value: float
    unit: str


class DeploymentEntry(BaseModel):
    id: str
    timestamp: datetime
    service: str
    version: str
    description: str | None = None


class CodeChangeEntry(BaseModel):
    id: str
    timestamp: datetime
    service: str
    commit_sha: str
    files: list[str]
    description: str
    diff: str | None = None


class IncidentDataset(BaseModel):
    incident: Incident
    logs: list[LogEntry] = Field(default_factory=list)
    metrics: list[MetricEntry] = Field(default_factory=list)
    deployments: list[DeploymentEntry] = Field(default_factory=list)
    changes: list[CodeChangeEntry] = Field(default_factory=list)
