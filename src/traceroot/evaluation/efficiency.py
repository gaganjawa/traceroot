from traceroot.evaluation.schemas import ExecutionMetrics


def calculate_llm_cost(
    input_tokens: int,
    output_tokens: int,
    input_cost_per_million: float,
    output_cost_per_million: float,
) -> float:
    input_cost = (input_tokens / 1_000_000) * input_cost_per_million
    output_cost = (output_tokens / 1_000_000) * output_cost_per_million

    total_cost = input_cost + output_cost
    return total_cost


def create_execution_metrics(
    latency_ms: float,
    llm_calls: int | None,
    tool_calls: int,
    input_tokens: int | None,
    output_tokens: int | None,
    estimated_cost_usd: float | None,
    investigation_steps: int | None = None,
) -> ExecutionMetrics:
    return ExecutionMetrics(
        latency_ms=latency_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=(
            input_tokens + output_tokens
            if input_tokens is not None and output_tokens is not None
            else None
        ),
        llm_calls=llm_calls,
        tool_calls=tool_calls,
        investigation_steps=investigation_steps,
        estimated_cost_usd=estimated_cost_usd,
    )
