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
    latency_ms: float | None = Field(default=None, ge=0)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    llm_calls: int | None = Field(default=None, ge=0)
    tool_calls: int | None = Field(default=None, ge=0)
    investigation_steps: int | None = Field(default=None, ge=0)
    estimated_cost_usd: float | None = Field(default=None, ge=0)


class EvaluationResult(BaseModel):
    incident_id: str
    approach: str
    metrics: list[MetricResult] = Field(default_factory=list)
    execution: ExecutionMetrics | None = None
