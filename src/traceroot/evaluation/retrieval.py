import json
from pathlib import Path

from pydantic import BaseModel, Field


class RetrievalEvaluationCase(BaseModel):
    id: str
    query: str
    relevant_sources: list[str] = Field(min_length=1)


def load_retrieval_evaluation_cases(
        path: Path,
    ) -> list[RetrievalEvaluationCase]:
    with open(path, "r") as f:
        data = json.load(f)

    return [RetrievalEvaluationCase(**case) for case in data]