import pytest
from pydantic import ValidationError

from traceroot.evaluation.efficiency import (
    calculate_llm_cost,
    create_execution_metrics,
)


def test_calculate_llm_cost():
    cost = calculate_llm_cost(
        input_tokens=1_000_000,
        output_tokens=500_000,
        input_cost_per_million=1.0,
        output_cost_per_million=2.0,
    )

    assert cost == 2.0


def test_calculate_llm_cost_with_zero_tokens():
    cost = calculate_llm_cost(
        input_tokens=0,
        output_tokens=0,
        input_cost_per_million=1.0,
        output_cost_per_million=2.0,
    )

    assert cost == 0.0


def test_calculate_llm_cost_input_only():
    cost = calculate_llm_cost(
        input_tokens=500_000,
        output_tokens=0,
        input_cost_per_million=2.0,
        output_cost_per_million=4.0,
    )

    assert cost == 1.0


def test_calculate_llm_cost_output_only():
    cost = calculate_llm_cost(
        input_tokens=0,
        output_tokens=250_000,
        input_cost_per_million=2.0,
        output_cost_per_million=4.0,
    )

    assert cost == 1.0


def test_create_execution_metrics():
    metrics = create_execution_metrics(
        latency_ms=125.5,
        llm_calls=3,
        tool_calls=4,
        input_tokens=1000,
        output_tokens=500,
        estimated_cost_usd=0.01,
    )

    assert metrics.latency_ms == 125.5
    assert metrics.llm_calls == 3
    assert metrics.tool_calls == 4
    assert metrics.input_tokens == 1000
    assert metrics.output_tokens == 500
    assert metrics.estimated_cost_usd == 0.01


def test_create_execution_metrics_total_tokens():
    metrics = create_execution_metrics(
        latency_ms=100.0,
        llm_calls=2,
        tool_calls=1,
        input_tokens=1200,
        output_tokens=300,
        estimated_cost_usd=0.02,
    )

    assert metrics.total_tokens == 1500


def test_execution_metrics_rejects_negative_values():
    with pytest.raises(ValidationError):
        create_execution_metrics(
            latency_ms=-1.0,
            llm_calls=-1,
            tool_calls=-1,
            input_tokens=-1,
            output_tokens=-1,
            estimated_cost_usd=-0.01,
        )
