from enum import StrEnum

from pydantic import BaseModel, Field


class EvaluatorType(StrEnum):
    DETERMINISTIC = "deterministic"
    DEEPEVAL = "deepeval"
    LLM_JUDGE = "llm_judge"


class MetricResult(BaseModel):
    name: str
    score: float
    passed: bool
    evaluator_type: EvaluatorType
    reason: str | None = None


class ExecutionMetrics(BaseModel):
    latency_ms: float | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    tool_calls: int | None = None
    investigation_steps: int | None = None


class EvaluationResult(BaseModel):
    incident_id: str
    approach: str
    metrics: list[MetricResult] = Field(default_factory=list)
    execution: ExecutionMetrics | None = None
