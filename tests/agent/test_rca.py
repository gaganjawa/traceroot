import json
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import httpx
import pytest
from openai import APIConnectionError
from pydantic import ValidationError

from tests.agent.prompt_helpers import (
    add_large_history,
    assert_prompt_evidence,
    evidence_block,
)
from traceroot.agent.context import AgentContextConfig, build_evidence_presentation
from traceroot.agent.grounding import (
    ClaimAssessment,
    ClaimVerificationReport,
    validate_claim_report,
    verify_rca_claims,
)
from traceroot.agent.rca import (
    GeneratedFinalRCA,
    build_context_from_state,
    generate_final_rca,
)
from traceroot.agent.state import (
    Hypothesis,
    HypothesisStatus,
    InvestigationState,
    ToolCallRecord,
)
from traceroot.domain.incident import Incident
from traceroot.llm.usage import LLMUsage


def create_test_state() -> InvestigationState:
    incident = Incident(
        id="INC-001",
        title="Checkout latency",
        description="Checkout requests are slow.",
        start_time=datetime(2026, 9, 25, tzinfo=UTC),
        suspected_services=["checkout-service"],
    )

    return InvestigationState(
        incident=incident,
        hypotheses=[
            Hypothesis(
                description="Database connection pool exhaustion",
                status=HypothesisStatus.SUPPORTED,
            )
        ],
        evidence_ids=[
            "LOG-001-02",
            "METRIC-001-02",
            "CHANGE-001-01",
        ],
        tool_history=[
            ToolCallRecord(
                tool_name="logs",
                service="checkout-service",
                evidence_ids=["LOG-001-02"],
                observations=["Database connection acquisition timeout"],
                reasoning="Check database-related failures.",
            )
        ],
    )


def create_generated_rca(
    evidence_ids=None,
) -> GeneratedFinalRCA:
    return GeneratedFinalRCA(
        root_cause="Checkout database connection pool was undersized.",
        affected_service="checkout-service",
        evidence_ids=evidence_ids or ["LOG-001-02", "CHANGE-001-01"],
        explanation=(
            "Logs show connection acquisition failures and the "
            "configuration change reduced the pool size."
        ),
        confidence=0.91,
    )


def claim_report(candidate, status="supported"):
    return ClaimVerificationReport(
        claims=[
            ClaimAssessment(
                field="root_cause",
                claim=candidate.root_cause,
                is_major_causal_claim=True,
                status=status,
                supporting_evidence_ids=["LOG-001-02"],
                reasoning="Connection acquisition timeouts are observed.",
                missing_links=[] if status == "supported" else ["Causal link missing"],
            )
        ]
    )


def model_response(parsed, input_tokens=20, output_tokens=5):
    return MagicMock(
        output_parsed=parsed,
        usage=MagicMock(input_tokens=input_tokens, output_tokens=output_tokens),
    )


@patch("traceroot.agent.grounding.get_llm_client")
@patch("traceroot.agent.rca.get_llm_client")
def test_generate_final_rca_sets_incident_id_from_state(
    mock_get_llm_client,
    mock_verifier_client,
):
    mock_verifier_client.return_value.responses.parse.return_value = model_response(
        claim_report(create_generated_rca())
    )
    state = create_test_state()

    mock_client = MagicMock()
    mock_client.responses.parse.return_value = MagicMock(
        output_parsed=create_generated_rca()
    )
    mock_get_llm_client.return_value = mock_client

    result = generate_final_rca(state)

    assert result.final_result.incident_id == "INC-001"


@patch("traceroot.agent.grounding.get_llm_client")
@patch("traceroot.agent.rca.get_llm_client")
def test_generate_final_rca_stores_result_in_state(
    mock_get_llm_client,
    mock_verifier_client,
):
    mock_verifier_client.return_value.responses.parse.return_value = model_response(
        claim_report(create_generated_rca())
    )
    state = create_test_state()

    mock_client = MagicMock()
    mock_client.responses.parse.return_value = MagicMock(
        output_parsed=create_generated_rca()
    )
    mock_get_llm_client.return_value = mock_client

    result = generate_final_rca(state)

    assert result.final_result is not None
    assert result is state


@patch("traceroot.agent.rca.get_llm_client")
def test_generate_final_rca_rejects_unknown_evidence_ids(
    mock_get_llm_client,
):
    state = create_test_state()

    mock_client = MagicMock()
    mock_client.responses.parse.return_value = MagicMock(
        output_parsed=create_generated_rca(
            evidence_ids=[
                "LOG-001-02",
                "FAKE-999",
            ]
        )
    )
    mock_get_llm_client.return_value = mock_client

    with pytest.raises(
        RuntimeError,
        match="evidence that was not gathered",
    ):
        generate_final_rca(state)


@patch("traceroot.agent.rca.get_llm_client")
def test_generate_final_rca_raises_when_llm_output_missing(
    mock_get_llm_client,
):
    state = create_test_state()

    mock_client = MagicMock()
    mock_client.responses.parse.return_value = MagicMock(output_parsed=None)
    mock_get_llm_client.return_value = mock_client

    with pytest.raises(
        RuntimeError,
        match="valid final RCA",
    ):
        generate_final_rca(state)


def test_generate_final_rca_requires_evidence():
    state = create_test_state()
    state.evidence_ids = []

    with pytest.raises(
        ValueError,
        match="No evidence gathered",
    ):
        generate_final_rca(state)


def test_generate_final_rca_prompt_contains_incident():
    state = create_test_state()

    prompt = build_context_from_state(state)

    assert "Checkout latency" in prompt
    assert "Checkout requests are slow." in prompt


def test_generate_final_rca_prompt_contains_hypotheses():
    state = create_test_state()

    prompt = build_context_from_state(state)

    assert "Database connection pool exhaustion" in prompt
    assert "supported" in prompt.lower()


def test_generate_final_rca_prompt_contains_tool_observations():
    state = create_test_state()

    prompt = build_context_from_state(state)

    assert "Database connection acquisition timeout" in prompt


def test_generate_final_rca_prompt_does_not_include_ground_truth():
    state = create_test_state()

    prompt = build_context_from_state(state)

    assert "ground_truth" not in prompt.lower()


@patch("traceroot.agent.grounding.get_llm_client")
@patch("traceroot.agent.rca.get_llm_client")
def test_generate_final_rca_records_llm_usage(
    mock_get_llm_client,
    mock_verifier_client,
):
    mock_verifier_client.return_value.responses.parse.return_value = model_response(
        claim_report(create_generated_rca())
    )
    usage = LLMUsage()
    state = create_test_state()

    mock_response = MagicMock(output_parsed=create_generated_rca())
    mock_response.usage.input_tokens = 180
    mock_response.usage.output_tokens = 45

    mock_client = MagicMock()
    mock_client.responses.parse.return_value = mock_response
    mock_get_llm_client.return_value = mock_client

    result = generate_final_rca(
        state,
        llm_usage=usage,
    )

    assert result.final_result is not None

    assert usage.input_tokens == 200
    assert usage.output_tokens == 50
    assert usage.total_tokens == 250
    assert usage.llm_calls == 2


@patch("traceroot.agent.grounding.get_llm_client")
@patch("traceroot.agent.rca.get_llm_client")
def test_generate_final_rca_records_call_when_token_usage_unavailable(
    mock_get_llm_client,
    mock_verifier_client,
):
    mock_verifier_client.return_value.responses.parse.return_value = model_response(
        claim_report(create_generated_rca())
    )
    usage = LLMUsage()
    state = create_test_state()

    mock_response = MagicMock(output_parsed=create_generated_rca())
    mock_response.usage = None

    mock_client = MagicMock()
    mock_client.responses.parse.return_value = mock_response
    mock_get_llm_client.return_value = mock_client

    generate_final_rca(
        state,
        llm_usage=usage,
    )

    assert usage.input_tokens is None
    assert usage.output_tokens is None
    assert usage.total_tokens is None
    assert usage.llm_calls == 2


def setup_pipeline(generator_client, verifier_client, statuses):
    original = create_generated_rca()
    repaired = original.model_copy(
        update={"root_cause": "Connection exhaustion caused timeouts."}
    )
    candidates = [original, repaired][: len(statuses)]
    generator_client.return_value.responses.parse.side_effect = [
        model_response(candidate, 100, 10) for candidate in candidates
    ]
    verifier_client.return_value.responses.parse.side_effect = [
        model_response(claim_report(candidate, status), 200, 20)
        for candidate, status in zip(candidates, statuses, strict=True)
    ]
    return candidates


def assert_cautious(result):
    assert (
        result.root_cause
        == "Root cause could not be established from the gathered evidence."
    )
    assert result.affected_service is None
    assert result.confidence is None
    assert result.evidence_ids == []
    assert "insufficient to establish a supported root cause" in result.explanation


@patch("traceroot.agent.grounding.get_llm_client")
@patch("traceroot.agent.rca.get_llm_client")
def test_final_rca_accepts_first_grounded_candidate(generator, verifier):
    candidates = setup_pipeline(generator, verifier, ["supported"])
    state = create_test_state()
    result = generate_final_rca(state)
    assert result is state
    assert result.final_result.root_cause == candidates[0].root_cause
    assert generator.return_value.responses.parse.call_count == 1
    assert verifier.return_value.responses.parse.call_count == 1


@patch("traceroot.agent.grounding.get_llm_client")
@patch("traceroot.agent.rca.get_llm_client")
def test_final_rca_regenerates_once_with_claim_verification_feedback(
    generator, verifier
):
    candidates = setup_pipeline(generator, verifier, ["unsupported", "supported"])
    result = generate_final_rca(create_test_state())
    assert result.final_result.root_cause == candidates[1].root_cause
    repair_prompt = generator.return_value.responses.parse.call_args_list[1].kwargs[
        "input"
    ]
    assert "unsupported_major_claim" in repair_prompt
    assert candidates[0].root_cause in repair_prompt
    assert "Causal link missing" in repair_prompt
    assert generator.return_value.responses.parse.call_count == 2


@patch("traceroot.agent.grounding.get_llm_client")
@patch("traceroot.agent.rca.get_llm_client")
def test_regenerated_rca_is_verified_before_acceptance(generator, verifier):
    candidates = setup_pipeline(generator, verifier, ["unsupported", "supported"])
    result = generate_final_rca(create_test_state())
    verifier_prompts = [
        call.kwargs["input"]
        for call in verifier.return_value.responses.parse.call_args_list
    ]
    assert len(verifier_prompts) == 2
    assert candidates[1].root_cause in verifier_prompts[1]
    assert result.final_result.root_cause == candidates[1].root_cause


@patch("traceroot.agent.grounding.get_llm_client")
@patch("traceroot.agent.rca.get_llm_client")
def test_repeated_grounding_failure_returns_cautious_rca(generator, verifier):
    setup_pipeline(generator, verifier, ["unsupported", "contradicted"])
    state = create_test_state()
    state.tool_history.append(ToolCallRecord(tool_name="deployments"))
    result = generate_final_rca(state)
    assert_cautious(result.final_result)
    assert (
        "Of 2 completed queries, 1 returned no matching evidence"
        in result.final_result.explanation
    )
    assert (
        "do not prove that an event did not happen" in result.final_result.explanation
    )
    assert "undersized" not in result.final_result.explanation


@pytest.mark.parametrize("failure", ["missing_output", "api_error"])
@pytest.mark.parametrize("repair", [False, True])
@patch("traceroot.agent.grounding.get_llm_client")
@patch("traceroot.agent.rca.get_llm_client")
def test_claim_verifier_failure_returns_cautious_rca(
    generator, verifier, failure, repair
):
    candidates = setup_pipeline(
        generator, verifier, ["unsupported", "supported"] if repair else ["supported"]
    )
    failed_response = (
        model_response(None)
        if failure == "missing_output"
        else APIConnectionError(
            request=httpx.Request("POST", "https://example.invalid")
        )
    )
    verifier.return_value.responses.parse.side_effect = (
        [model_response(claim_report(candidates[0], "unsupported")), failed_response]
        if repair
        else [failed_response]
    )
    result = generate_final_rca(create_test_state())
    assert_cautious(result.final_result)
    assert generator.return_value.responses.parse.call_count == (2 if repair else 1)


@pytest.mark.parametrize(
    "statuses",
    [["supported"], ["unsupported", "supported"], ["unsupported", "unsupported"]],
)
@patch("traceroot.agent.grounding.get_llm_client")
@patch("traceroot.agent.rca.get_llm_client")
def test_claim_verification_records_all_response_usage(generator, verifier, statuses):
    setup_pipeline(generator, verifier, statuses)
    usage = LLMUsage()
    generate_final_rca(create_test_state(), llm_usage=usage)
    assert usage.llm_calls == 2 * len(statuses)
    assert usage.input_tokens == 300 * len(statuses)
    assert usage.output_tokens == 30 * len(statuses)


@patch("traceroot.agent.grounding.get_llm_client")
@patch("traceroot.agent.rca.get_llm_client")
def test_supported_rca_preserves_public_result_shape(generator, verifier):
    setup_pipeline(generator, verifier, ["supported"])
    result = generate_final_rca(create_test_state()).final_result
    assert set(result.model_dump()) == {
        "incident_id",
        "root_cause",
        "affected_service",
        "evidence_ids",
        "explanation",
        "confidence",
    }


@patch("traceroot.agent.grounding.get_llm_client")
@patch("traceroot.agent.rca.get_llm_client")
def test_final_rca_does_not_retry_more_than_once(generator, verifier):
    setup_pipeline(generator, verifier, ["unsupported", "unsupported"])
    result = generate_final_rca(create_test_state())
    assert_cautious(result.final_result)
    assert generator.return_value.responses.parse.call_count == 2
    assert verifier.return_value.responses.parse.call_count == 2


@patch("traceroot.agent.grounding.get_llm_client")
@patch("traceroot.agent.rca.get_llm_client")
def test_repair_generation_uses_grounding_feedback(generator, verifier):
    setup_pipeline(generator, verifier, ["unsupported", "supported"])
    generate_final_rca(create_test_state())
    original, repair = [
        call.kwargs["input"]
        for call in generator.return_value.responses.parse.call_args_list
    ]
    assert not repair.startswith(original)
    for instruction in [
        "Remove unsupported causal claims",
        "Preserve observed facts",
        "Do not invent evidence",
        "Use only IDs attached to visible evidence observations",
        "Strongest current hypothesis:",
        "at most 0.60",
        "unsupported_major_claim",
    ]:
        assert instruction in repair


@pytest.mark.parametrize(
    "failure", ["missing_output", "unknown_id", "invalid_confidence", "api_error"]
)
@patch("traceroot.agent.grounding.get_llm_client")
@patch("traceroot.agent.rca.get_llm_client")
def test_repair_generation_failure_returns_cautious_rca(generator, verifier, failure):
    candidates = setup_pipeline(generator, verifier, ["unsupported", "supported"])
    outputs = {
        "missing_output": model_response(None),
        "unknown_id": model_response(create_generated_rca(["UNKNOWN"])),
        "invalid_confidence": model_response(
            candidates[1].model_copy(update={"confidence": 2.0})
        ),
        "api_error": APIConnectionError(
            request=httpx.Request("POST", "https://example.invalid")
        ),
    }
    generator.return_value.responses.parse.side_effect = [
        model_response(candidates[0]),
        outputs[failure],
    ]
    result = generate_final_rca(create_test_state())
    assert_cautious(result.final_result)
    assert verifier.return_value.responses.parse.call_count == 1


@patch("traceroot.agent.grounding.get_llm_client")
@patch("traceroot.agent.rca.get_llm_client")
def test_initial_invalid_rca_fields_still_raise(generator, verifier):
    generator.return_value.responses.parse.return_value = model_response(
        create_generated_rca().model_copy(update={"confidence": 2.0})
    )
    with pytest.raises(ValidationError):
        generate_final_rca(create_test_state())
    verifier.assert_not_called()


@pytest.mark.parametrize("stage", ["verifier", "repair"])
@patch("traceroot.agent.grounding.get_llm_client")
@patch("traceroot.agent.rca.get_llm_client")
def test_final_rca_does_not_swallow_programming_errors(generator, verifier, stage):
    candidates = setup_pipeline(generator, verifier, ["unsupported", "supported"])
    if stage == "verifier":
        verifier.return_value.responses.parse.side_effect = RuntimeError(
            "programming bug"
        )
    else:
        generator.return_value.responses.parse.side_effect = [
            model_response(candidates[0]),
            TypeError("programming bug"),
        ]
    with pytest.raises((RuntimeError, TypeError), match="programming bug"):
        generate_final_rca(create_test_state())


@patch("traceroot.agent.grounding.get_llm_client")
@patch("traceroot.agent.rca.get_llm_client")
def test_repaired_candidate_cannot_use_stale_verification_report(generator, verifier):
    candidates = setup_pipeline(generator, verifier, ["unsupported", "supported"])
    verifier.return_value.responses.parse.side_effect = [
        model_response(claim_report(candidates[0], "unsupported")),
        model_response(claim_report(candidates[0], "supported")),
    ]

    result = generate_final_rca(create_test_state())

    assert_cautious(result.final_result)


@pytest.mark.parametrize("stage", ["verifier", "repair"])
@patch("traceroot.agent.grounding.get_llm_client")
@patch("traceroot.agent.rca.get_llm_client")
def test_model_json_parse_failure_returns_cautious_rca(generator, verifier, stage):
    candidates = setup_pipeline(generator, verifier, ["unsupported", "supported"])
    error = json.JSONDecodeError("Invalid model output", "{", 1)
    if stage == "verifier":
        verifier.return_value.responses.parse.side_effect = error
    else:
        generator.return_value.responses.parse.side_effect = [
            model_response(candidates[0]),
            error,
        ]

    result = generate_final_rca(create_test_state())

    assert_cautious(result.final_result)


@patch("traceroot.agent.grounding.get_llm_client")
@patch("traceroot.agent.rca.get_llm_client")
def test_initial_rca_prompt_uses_bounded_evidence(generator, verifier):
    setup_pipeline(generator, verifier, ["supported"])
    state = add_large_history(create_test_state())
    before = state.model_dump()
    generate_final_rca(state)
    prompt = generator.return_value.responses.parse.call_args_list[0].kwargs["input"]
    assert assert_prompt_evidence(prompt, state).budget_limited
    assert state.model_dump(exclude={"final_result"}) == {
        key: value for key, value in before.items() if key != "final_result"
    }


@patch("traceroot.agent.grounding.get_llm_client")
@patch("traceroot.agent.rca.get_llm_client")
def test_repair_prompt_contains_one_bounded_evidence_block(generator, verifier):
    candidates = setup_pipeline(generator, verifier, ["unsupported", "supported"])
    state = add_large_history(create_test_state())
    before = state.model_dump()
    generate_final_rca(state)
    repair = generator.return_value.responses.parse.call_args_list[1].kwargs["input"]
    assert_prompt_evidence(repair, state, priorities=set(candidates[0].evidence_ids))
    assert "unsupported_major_claim" in repair
    assert "Causal link missing" in repair
    assert candidates[0].root_cause in repair
    assert state.model_dump(exclude={"final_result"}) == {
        key: value for key, value in before.items() if key != "final_result"
    }


@patch("traceroot.agent.grounding.get_llm_client")
@patch("traceroot.agent.rca.get_llm_client")
def test_repair_prompt_does_not_append_full_original_history(generator, verifier):
    setup_pipeline(generator, verifier, ["unsupported", "supported"])
    state = add_large_history(create_test_state())
    # Sentinel proves repair is built afresh rather than reusing initial text.
    with patch(
        "traceroot.agent.rca.build_context_from_state",
        return_value="ORIGINAL-PROMPT-SENTINEL",
    ):
        generate_final_rca(state)
    repair = generator.return_value.responses.parse.call_args_list[1].kwargs["input"]
    assert "ORIGINAL-PROMPT-SENTINEL" not in repair
    assert "Grounding context and query limitations:" not in repair
    assert_prompt_evidence(
        repair, state, priorities=set(create_generated_rca().evidence_ids)
    )


@patch("traceroot.agent.grounding.get_llm_client")
@patch("traceroot.agent.rca.get_llm_client")
def test_small_rca_context_preserves_all_observations(generator, verifier):
    setup_pipeline(generator, verifier, ["supported"])
    state = create_test_state()
    generate_final_rca(state)
    prompt = generator.return_value.responses.parse.call_args_list[0].kwargs["input"]
    result = assert_prompt_evidence(prompt, state)
    assert not result.partial
    assert len(result.observations) == 1
    assert "CHANGE-001-01" not in prompt  # Global ID without an observation.


@pytest.mark.parametrize("budget", [0, 2, 40])
@patch("traceroot.agent.grounding.get_llm_client")
@patch("traceroot.agent.rca.get_llm_client")
def test_rca_pipeline_discloses_budget_pressure_with_minimal_rendering(
    generator, verifier, budget
):
    setup_pipeline(generator, verifier, ["unsupported", "unsupported"])
    state = create_test_state()
    before = state.model_dump()

    def tiny_presentation(state, *, prioritized_evidence_ids=None):
        return build_evidence_presentation(
            state,
            config=AgentContextConfig(max_evidence_chars=budget),
            prioritized_evidence_ids=prioritized_evidence_ids,
        )

    with patch(
        "traceroot.agent.prompt_context.build_evidence_presentation",
        side_effect=tiny_presentation,
    ):
        generate_final_rca(state)
    for client in (generator, verifier):
        assert client.return_value.responses.parse.call_count == 2
        for invocation in client.return_value.responses.parse.call_args_list:
            prompt = invocation.kwargs["input"]
            assert len(evidence_block(prompt)) <= budget
            assert (
                "Evidence view is partial because of context budget pressure." in prompt
            )
            assert "Omission does not imply absence." in prompt
            assert "Database connection acquisition timeout" not in prompt
    assert state.model_dump(exclude={"final_result"}) == {
        key: value for key, value in before.items() if key != "final_result"
    }


@patch("traceroot.agent.rca.validate_claim_report", wraps=validate_claim_report)
@patch("traceroot.agent.rca.verify_rca_claims", wraps=verify_rca_claims)
@patch(
    "traceroot.agent.prompt_context.build_evidence_presentation",
    wraps=build_evidence_presentation,
)
@patch("traceroot.agent.grounding.get_llm_client")
@patch("traceroot.agent.rca.get_llm_client")
def test_first_candidate_validation_uses_same_verifier_presentation(
    generator, verifier, builder, verify, validate
):
    setup_pipeline(generator, verifier, ["supported"])
    state = create_test_state()
    generate_final_rca(state)
    presentation = verify.call_args.kwargs["presentation"]
    assert validate.call_args.kwargs["presentation"] is presentation
    assert (
        evidence_block(verifier.return_value.responses.parse.call_args.kwargs["input"])
        == presentation.rendered
    )
    assert (
        builder.call_count == 2
    )  # Initial generation and verifier; validation never selects.
    assert builder.call_args.kwargs["prioritized_evidence_ids"] == set(
        create_generated_rca().evidence_ids
    )
    assert verify.call_count == validate.call_count == 1


@patch("traceroot.agent.rca.validate_claim_report", wraps=validate_claim_report)
@patch("traceroot.agent.rca.verify_rca_claims", wraps=verify_rca_claims)
@patch(
    "traceroot.agent.prompt_context.build_evidence_presentation",
    wraps=build_evidence_presentation,
)
@patch("traceroot.agent.grounding.get_llm_client")
@patch("traceroot.agent.rca.get_llm_client")
def test_repaired_candidate_validation_uses_same_verifier_presentation(
    generator, verifier, builder, verify, validate
):
    candidates = setup_pipeline(generator, verifier, ["unsupported", "supported"])
    candidates[1].evidence_ids = ["LOG-001-02"]
    state = create_test_state()
    generate_final_rca(state)
    assert verify.call_count == validate.call_count == 2
    presentations = [call.kwargs["presentation"] for call in verify.call_args_list]
    assert presentations[0] is not presentations[1]
    for index, presentation in enumerate(presentations):
        assert validate.call_args_list[index].kwargs["presentation"] is presentation
        prompt = verifier.return_value.responses.parse.call_args_list[index].kwargs[
            "input"
        ]
        assert evidence_block(prompt) == presentation.rendered
    assert builder.call_count == 4  # Initial, first verifier, repair, second verifier.
    assert builder.call_args_list[1].kwargs["prioritized_evidence_ids"] == set(
        candidates[0].evidence_ids
    )
    assert builder.call_args_list[3].kwargs["prioritized_evidence_ids"] == set(
        candidates[1].evidence_ids
    )
    assert state.final_result.root_cause == candidates[1].root_cause


@patch("traceroot.agent.grounding.get_llm_client")
@patch("traceroot.agent.rca.get_llm_client")
def test_unpresentable_cited_evidence_triggers_repair_or_fallback(generator, verifier):
    setup_pipeline(generator, verifier, ["supported", "supported"])
    state = create_test_state()
    state.tool_history[0].observations[0] = "Oversized evidence " + "x" * 40_000
    before = state.model_dump()
    generate_final_rca(state)
    assert generator.return_value.responses.parse.call_count == 2
    assert verifier.return_value.responses.parse.call_count == 2
    repair = generator.return_value.responses.parse.call_args_list[1].kwargs["input"]
    assert "supporting_evidence_not_presented" in repair
    assert "contradicted_major_claim" not in repair
    for call in verifier.return_value.responses.parse.call_args_list:
        block = evidence_block(call.kwargs["input"])
        assert len(block) <= AgentContextConfig().max_evidence_chars
        assert json.loads(block)["observations"] == []
        assert "Oversized evidence" not in call.kwargs["input"]
    assert_cautious(state.final_result)
    assert state.model_dump(exclude={"final_result"}) == {
        key: value for key, value in before.items() if key != "final_result"
    }
