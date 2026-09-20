from datetime import datetime

from pydantic import BaseModel, Field


class Incident(BaseModel):
    id: str
    title: str
    description: str
    start_time: datetime
    suspected_services: list[str] = Field(default_factory=list)