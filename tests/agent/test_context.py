import json
from datetime import UTC, datetime

import pytest

from traceroot.agent.context import AgentContextConfig, build_evidence_presentation
from traceroot.agent.state import InvestigationState, ToolCallRecord
from traceroot.domain.incident import Incident


def state_with(*calls):
    return InvestigationState(
        incident=Incident(
            id="INC-TEST",
            title="Test",
            description="Test incident",
            start_time=datetime(2026, 1, 1, tzinfo=UTC),
            suspected_services=["checkout"],
        ),
        tool_history=list(calls),
        evidence_ids=[
            evidence_id for call in calls for evidence_id in call.evidence_ids
        ],
    )


def call(tool="logs", service="checkout", count=10, prefix="log", text=None):
    return ToolCallRecord(
        tool_name=tool,
        service=service,
        evidence_ids=[f"{prefix}-{i}" for i in range(count)],
        observations=[
            text if text is not None else f"Observation {i}" for i in range(count)
        ],
    )


def assert_bounded(presentation, config):
    assert len(presentation.rendered) <= config.max_evidence_chars
    assert len(presentation.observations) <= config.max_observations
    payload = json.loads(presentation.rendered)
    assert payload["observations"] == [
        item.model_dump() for item in presentation.observations
    ]
    assert payload["summaries"] == [
        item.model_dump() for item in presentation.summaries
    ]
    assert payload["partial"] == presentation.partial
    if presentation.partial:
        assert "support or contradiction" in payload["omission_warning"]
        assert "omission does not prove absence" in payload["omission_warning"]


def test_large_history_produces_bounded_serialized_context():
    state = state_with(
        *(call(service=f"svc-{i}", count=200, prefix=str(i)) for i in range(20))
    )
    config = AgentContextConfig()
    result = build_evidence_presentation(state, config=config)
    assert_bounded(result, config)
    assert result.partial
    assert len(result.observations) == 100
    assert len({item.service for item in result.observations}) == 20


def test_context_building_does_not_mutate_investigation_state():
    state = state_with(call(count=200), call(count=0))
    before = state.model_dump()
    priorities = {"log-199"}
    build_evidence_presentation(state, prioritized_evidence_ids=priorities)
    assert state.model_dump() == before
    assert priorities == {"log-199"}


def test_context_budget_counts_json_escaping_and_metadata():
    state = state_with(
        call(tool='lo"gs', service="svc\\\n", count=4, text='"\\\n☃' * 12)
    )
    full = build_evidence_presentation(state)
    exact = AgentContextConfig(max_evidence_chars=len(full.rendered))
    assert build_evidence_presentation(state, config=exact) == full
    config = AgentContextConfig(max_evidence_chars=len(full.rendered) - 1)
    bounded = build_evidence_presentation(state, config=config)
    assert_bounded(bounded, config)
    assert bounded.partial
    assert len(bounded.observations) < 4


def test_omission_counts_partition_all_returned_observations():
    mismatch = ToolCallRecord(
        tool_name="metrics", evidence_ids=["m"], observations=["a", "b"]
    )
    state = state_with(call(count=10), mismatch, call(count=0))
    result = build_evidence_presentation(
        state, config=AgentContextConfig(max_observations=3)
    )
    for summary in result.summaries:
        assert (
            summary.total_observations
            == summary.included_observations + summary.omitted_observations
        )
        assert summary.included_observations == sum(
            item.tool_name == summary.tool_name for item in result.observations
        )
    assert result.summaries[1].total_observations == 2
    assert result.summaries[1].included_observations == 0
    assert result.partial


def test_empty_queries_remain_distinct_from_unqueried_tools():
    result = build_evidence_presentation(state_with(call(count=0)))
    assert [summary.model_dump() for summary in result.summaries] == [
        {
            "tool_name": "logs",
            "queried": True,
            "total_observations": 0,
            "included_observations": 0,
            "omitted_observations": 0,
        }
    ]
    assert not result.partial
    assert build_evidence_presentation(state_with()).summaries == []


def test_selection_is_deterministic_with_stable_tie_breakers():
    state = state_with(
        call(count=9), call(count=9, prefix="other"), call(tool="metrics", count=9)
    )
    config = AgentContextConfig(max_observations=9)
    result = build_evidence_presentation(state, config=config)
    assert (
        result.model_dump()
        == build_evidence_presentation(state, config=config).model_dump()
    )
    assert [
        (item.history_index, item.observation_index) for item in result.observations
    ] == [
        (0, 0),
        (0, 4),
        (0, 8),
        (1, 0),
        (1, 8),
        (2, 0),
        (2, 2),
        (2, 4),
        (2, 8),
    ]


def test_duplicate_content_is_collapsed_without_losing_query_counts():
    state = state_with(call(count=2), call(count=2))
    result = build_evidence_presentation(state)
    assert len(result.observations) == 2
    assert all(item.history_index == 0 for item in result.observations)
    assert result.summaries[0].model_dump() == {
        "tool_name": "logs",
        "queried": True,
        "total_observations": 4,
        "included_observations": 2,
        "omitted_observations": 2,
    }
    assert result.partial


def test_distinct_loki_streams_are_not_deduplicated_by_message():
    state = state_with(
        call(count=1, text='stream={pod="a"} timeout'),
        call(count=1, text='stream={pod="b"} timeout'),
        call(count=1, prefix="other", text='stream={pod="a"} timeout'),
        call(count=1, service="payments", text='stream={pod="a"} timeout'),
        call(tool="traces", count=1, text='stream={pod="a"} timeout'),
    )
    assert len(build_evidence_presentation(state).observations) == 5


def test_small_context_preserves_all_observations():
    state = state_with(call(count=3), call(tool="metrics", service=None, count=2))
    result = build_evidence_presentation(state)
    assert len(result.observations) == 5
    assert not result.partial
    assert_bounded(result, AgentContextConfig())
    assert [item.observation for item in result.observations] == [
        text for record in state.tool_history for text in record.observations
    ]


def test_presented_observations_match_original_associations():
    state = state_with(
        call(count=200),
        ToolCallRecord(
            tool_name="bad", evidence_ids=["x", "y"], observations=["ambiguous"]
        ),
    )
    result = build_evidence_presentation(state)
    for item in result.observations:
        original = state.tool_history[item.history_index]
        assert item.evidence_id == original.evidence_ids[item.observation_index]
        assert item.observation == original.observations[item.observation_index]
        assert (item.tool_name, item.service) == (original.tool_name, original.service)
    assert all(item.tool_name != "bad" for item in result.observations)


def test_prioritized_evidence_is_included_when_it_fits():
    state = state_with(call(count=30))
    result = build_evidence_presentation(
        state,
        config=AgentContextConfig(max_observations=2),
        prioritized_evidence_ids={"log-17", "unknown"},
    )
    assert [item.evidence_id for item in result.observations] == ["log-0", "log-17"]


def test_prioritized_evidence_does_not_bypass_budget():
    state = state_with(call(count=10))
    state.tool_history[0].observations[0] = "x" * 5000
    config = AgentContextConfig(max_observations=2, max_evidence_chars=750)
    result = build_evidence_presentation(
        state, config=config, prioritized_evidence_ids=set(state.evidence_ids)
    )
    assert_bounded(result, config)
    assert [item.evidence_id for item in result.observations] == ["log-1", "log-2"]
    assert result.partial


def test_oversized_single_observation_is_omitted_without_truncation():
    state = state_with(call(count=1, text="x" * 40_000))
    before = state.model_dump()
    result = build_evidence_presentation(state)
    assert result.observations == []
    assert result.summaries[0].omitted_observations == 1
    assert result.partial
    assert_bounded(result, AgentContextConfig())
    assert state.model_dump() == before


def test_oversized_observation_does_not_block_smaller_observations():
    state = state_with(call(count=3))
    state.tool_history[0].observations[0] = "x" * 40_000
    result = build_evidence_presentation(state)
    assert [item.observation_index for item in result.observations] == [1, 2]


def test_selection_covers_services_and_calls():
    state = state_with(
        call(count=30),
        call(count=30, prefix="second"),
        call(service="payments", count=30),
    )
    result = build_evidence_presentation(
        state, config=AgentContextConfig(max_observations=3)
    )
    assert {item.history_index for item in result.observations} == {0, 1, 2}


def test_zero_observation_budget_and_impossible_metadata_budget():
    state = state_with(call(count=2))
    result = build_evidence_presentation(
        state, config=AgentContextConfig(max_observations=0)
    )
    assert result.observations == []
    assert result.summaries[0].omitted_observations == 2
    assert result.partial
    tiny = build_evidence_presentation(
        state, config=AgentContextConfig(max_evidence_chars=1)
    )
    assert tiny.rendered == ""
    assert tiny.budget_limited
    assert tiny.partial
    assert tiny.summaries == result.summaries


@pytest.mark.parametrize("budget", [0, 1, 2, 39, 40, 41, 100])
def test_tiny_context_budget_returns_budget_limited_presentation(budget):
    state = state_with(call(count=2))
    config = AgentContextConfig(max_evidence_chars=budget)
    result = build_evidence_presentation(state, config=config)
    warning = '"Evidence context omitted due to budget."'
    expected = warning if budget >= len(warning) else "{}" if budget >= 2 else ""
    assert result.rendered == expected
    assert len(result.rendered) <= budget
    assert result.observations == []
    assert result.partial
    assert result.budget_limited
    if result.rendered:
        assert json.loads(result.rendered) in (
            {},
            "Evidence context omitted due to budget.",
        )
    assert (
        result.model_dump()
        == build_evidence_presentation(state, config=config).model_dump()
    )


def test_budget_limited_presentation_does_not_mutate_state():
    state = state_with(call(count=3), call(count=0))
    before = state.model_dump()
    priorities = {"log-1"}
    result = build_evidence_presentation(
        state,
        config=AgentContextConfig(max_evidence_chars=2),
        prioritized_evidence_ids=priorities,
    )
    assert result.budget_limited
    assert state.model_dump() == before
    assert priorities == {"log-1"}


def test_budget_limited_presentation_accounts_for_all_omissions():
    state = state_with(
        call(count=3),
        call(count=3),
        call(tool="empty", count=0),
        ToolCallRecord(
            tool_name="metrics", evidence_ids=["m"], observations=["a", "b"]
        ),
    )
    result = build_evidence_presentation(
        state, config=AgentContextConfig(max_evidence_chars=2)
    )
    assert result.budget_limited
    assert result.partial
    assert result.observations == []
    assert [
        (
            s.tool_name,
            s.total_observations,
            s.included_observations,
            s.omitted_observations,
        )
        for s in result.summaries
    ] == [
        ("logs", 6, 0, 6),
        ("empty", 0, 0, 0),
        ("metrics", 2, 0, 2),
    ]
    assert all(s.queried for s in result.summaries)


def test_zero_observations_fit_without_raising():
    state = state_with(call(count=1, text="x" * 40_000))
    config = AgentContextConfig(max_evidence_chars=500)
    result = build_evidence_presentation(state, config=config)
    assert_bounded(result, config)
    assert result.observations == []
    assert result.partial
    assert result.budget_limited
    assert result.summaries[0].omitted_observations == 1


@pytest.mark.parametrize("empty_query", [False, True])
def test_tiny_budget_preserves_empty_query_metadata(empty_query):
    state = state_with(call(count=0)) if empty_query else state_with()
    result = build_evidence_presentation(
        state, config=AgentContextConfig(max_evidence_chars=0)
    )
    assert result.rendered == ""
    assert result.budget_limited
    assert not result.partial
    assert result.observations == []
    assert len(result.summaries) == int(empty_query)
    assert all(
        s.queried and s.total_observations == s.omitted_observations == 0
        for s in result.summaries
    )


def test_budget_limited_distinguishes_budget_pressure_from_deduplication():
    state = state_with(call(count=2), call(count=2))
    complete = build_evidence_presentation(state)
    assert complete.partial
    assert not complete.budget_limited
    limited = build_evidence_presentation(
        state, config=AgentContextConfig(max_observations=1)
    )
    assert limited.budget_limited
    assert len(limited.observations) == 1


@pytest.mark.parametrize("value", [-1, 1.5, True])
@pytest.mark.parametrize("field", ["max_evidence_chars", "max_observations"])
def test_invalid_budgets_are_rejected(field, value):
    with pytest.raises(ValueError, match=field):
        AgentContextConfig(**{field: value})
