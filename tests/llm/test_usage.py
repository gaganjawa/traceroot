from unittest.mock import MagicMock

from traceroot.llm.usage import LLMUsage, record_response_usage


def test_llm_usage_starts_at_zero():
    usage = LLMUsage()

    assert usage.input_tokens == 0
    assert usage.output_tokens == 0
    assert usage.total_tokens == 0
    assert usage.llm_calls == 0


def test_llm_usage_records_single_call():
    usage = LLMUsage()

    usage.add(
        input_tokens=100,
        output_tokens=25,
    )

    assert usage.input_tokens == 100
    assert usage.output_tokens == 25
    assert usage.total_tokens == 125
    assert usage.llm_calls == 1


def test_llm_usage_accumulates_multiple_calls():
    usage = LLMUsage()

    usage.add(
        input_tokens=100,
        output_tokens=20,
    )

    usage.add(
        input_tokens=200,
        output_tokens=30,
    )

    assert usage.input_tokens == 300
    assert usage.output_tokens == 50
    assert usage.total_tokens == 350
    assert usage.llm_calls == 2


def test_llm_usage_counts_call_when_usage_is_unavailable():
    usage = LLMUsage()

    usage.add(
        input_tokens=None,
        output_tokens=None,
    )

    assert usage.llm_calls == 1
    assert usage.input_tokens is None
    assert usage.output_tokens is None
    assert usage.total_tokens is None


def test_llm_usage_remains_unknown_after_missing_input_usage():
    usage = LLMUsage()

    usage.add(
        input_tokens=100,
        output_tokens=20,
    )

    usage.add(
        input_tokens=None,
        output_tokens=30,
    )

    assert usage.input_tokens is None
    assert usage.output_tokens == 50
    assert usage.total_tokens is None
    assert usage.llm_calls == 2


def test_llm_usage_remains_unknown_after_missing_output_usage():
    usage = LLMUsage()

    usage.add(
        input_tokens=100,
        output_tokens=20,
    )

    usage.add(
        input_tokens=50,
        output_tokens=None,
    )

    assert usage.input_tokens == 150
    assert usage.output_tokens is None
    assert usage.total_tokens is None
    assert usage.llm_calls == 2


def test_llm_usage_unknown_value_is_not_replaced_by_later_usage():
    usage = LLMUsage()

    usage.add(
        input_tokens=None,
        output_tokens=None,
    )

    usage.add(
        input_tokens=100,
        output_tokens=20,
    )

    assert usage.input_tokens is None
    assert usage.output_tokens is None
    assert usage.total_tokens is None
    assert usage.llm_calls == 2


def test_record_response_usage_does_nothing_without_accumulator():
    response = MagicMock()

    record_response_usage(
        None,
        response,
    )


def test_record_response_usage_records_tokens():
    usage = LLMUsage()

    response = MagicMock()
    response.usage.input_tokens = 100
    response.usage.output_tokens = 20

    record_response_usage(
        usage,
        response,
    )

    assert usage.input_tokens == 100
    assert usage.output_tokens == 20
    assert usage.total_tokens == 120
    assert usage.llm_calls == 1


def test_record_response_usage_records_unknown_tokens():
    usage = LLMUsage()

    response = MagicMock()
    response.usage = None

    record_response_usage(
        usage,
        response,
    )

    assert usage.input_tokens is None
    assert usage.output_tokens is None
    assert usage.total_tokens is None
    assert usage.llm_calls == 1
