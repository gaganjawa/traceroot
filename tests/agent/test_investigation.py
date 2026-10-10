from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from tests.agent.prompt_helpers import (
    add_large_history,
    assert_prompt_evidence,
    query_metadata,
)
from traceroot.agent.investigation import ToolSelection, build_prompt, investigate
from traceroot.agent.state import (
    Hypothesis,
    InvestigationState,
    ToolCallRecord,
)
from traceroot.data.models import LogEntry, MetricEntry
from traceroot.domain.incident import Incident
from traceroot.llm.usage import LLMUsage
from traceroot.tools.interface import ToolName


def create_test_incident() -> Incident:
    return Incident(
        id="INC-TEST",
        title="Checkout latency",
        description="Checkout requests are slow and timing out.",
        start_time=datetime(2020, 9, 25, 0, 0, 0, tzinfo=UTC),
        suspected_services=["checkout-service"],
    )


def create_test_state() -> InvestigationState:
    return InvestigationState(
        incident=create_test_incident(),
        hypotheses=[
            Hypothesis(
                description="Database connection exhaustion",
            )
        ],
    )


def create_mock_llm_response(
    tool_name: ToolName,
    service: str | None = None,
    reasoning: str = "Investigate this evidence source next.",
):
    response = MagicMock()
    response.output_parsed = ToolSelection(
        tool_name=tool_name,
        service=service,
        reasoning=reasoning,
    )
    return response


def test_investigate_rejects_invalid_max_tool_calls():
    state = create_test_state()

    with pytest.raises(ValueError):
        investigate(
            state=state,
            max_tool_calls=0,
        )

    with pytest.raises(ValueError):
        investigate(
            state=state,
            max_tool_calls=-1,
        )


@patch("traceroot.agent.investigation.execute_tool")
@patch("traceroot.agent.investigation.get_llm_client")
def test_investigate_executes_selected_tool(
    mock_get_llm_client,
    mock_execute_tool,
):
    mock_client = MagicMock()
    mock_client.responses.parse.return_value = create_mock_llm_response(
        ToolName.LOGS,
        "checkout-service",
    )
    mock_get_llm_client.return_value = mock_client

    mock_execute_tool.return_value = []

    investigate(
        state=create_test_state(),
        max_tool_calls=1,
    )

    mock_execute_tool.assert_called_once_with(
        tool_name=ToolName.LOGS,
        incident_id="INC-TEST",
        service="checkout-service",
    )


@patch("traceroot.agent.investigation.execute_tool")
@patch("traceroot.agent.investigation.get_llm_client")
def test_investigate_passes_selected_service(
    mock_get_llm_client,
    mock_execute_tool,
):
    mock_client = MagicMock()
    mock_client.responses.parse.return_value = create_mock_llm_response(
        ToolName.METRICS,
        "payment-service",
    )
    mock_get_llm_client.return_value = mock_client

    mock_execute_tool.return_value = []

    investigate(
        state=create_test_state(),
        max_tool_calls=1,
    )

    mock_execute_tool.assert_called_once_with(
        tool_name=ToolName.METRICS,
        incident_id="INC-TEST",
        service="payment-service",
    )


@patch("traceroot.agent.investigation.execute_tool")
@patch("traceroot.agent.investigation.get_llm_client")
def test_investigate_adds_evidence_ids_to_state(
    mock_get_llm_client,
    mock_execute_tool,
):
    mock_client = MagicMock()
    mock_client.responses.parse.return_value = create_mock_llm_response(
        ToolName.LOGS,
        "checkout-service",
    )
    mock_get_llm_client.return_value = mock_client

    mock_execute_tool.return_value = [
        LogEntry(
            id="LOG-TEST-01",
            timestamp="2026-09-25T00:00:00Z",
            service="checkout-service",
            level="ERROR",
            message="Database timeout",
        )
    ]

    state = create_test_state()

    result = investigate(
        state=state,
        max_tool_calls=1,
    )

    assert result.evidence_ids == ["LOG-TEST-01"]


@patch("traceroot.agent.investigation.execute_tool")
@patch("traceroot.agent.investigation.get_llm_client")
def test_investigate_does_not_duplicate_global_evidence_ids(
    mock_get_llm_client,
    mock_execute_tool,
):
    mock_client = MagicMock()
    mock_client.responses.parse.return_value = create_mock_llm_response(
        ToolName.LOGS,
        "checkout-service",
    )
    mock_get_llm_client.return_value = mock_client

    log_entry = LogEntry(
        id="LOG-TEST-01",
        timestamp="2026-09-25T00:00:00Z",
        service="checkout-service",
        level="ERROR",
        message="Database timeout",
    )

    mock_execute_tool.return_value = [log_entry]

    state = create_test_state()

    result = investigate(
        state=state,
        max_tool_calls=2,
    )

    assert result.evidence_ids == ["LOG-TEST-01"]


@patch("traceroot.agent.investigation.execute_tool")
@patch("traceroot.agent.investigation.get_llm_client")
def test_investigate_records_tool_call(
    mock_get_llm_client,
    mock_execute_tool,
):
    mock_client = MagicMock()
    mock_client.responses.parse.return_value = create_mock_llm_response(
        ToolName.LOGS,
        "checkout-service",
    )
    mock_get_llm_client.return_value = mock_client

    mock_execute_tool.return_value = [
        LogEntry(
            id="LOG-TEST-01",
            timestamp="2026-09-25T00:00:00Z",
            service="checkout-service",
            level="ERROR",
            message="Database timeout",
        )
    ]

    result = investigate(
        state=create_test_state(),
        max_tool_calls=1,
    )

    assert len(result.tool_history) == 1
    assert isinstance(result.tool_history[0], ToolCallRecord)
    assert result.tool_history[0].tool_name == "logs"
    assert result.tool_history[0].evidence_ids == ["LOG-TEST-01"]


@patch("traceroot.agent.investigation.execute_tool")
@patch("traceroot.agent.investigation.get_llm_client")
def test_investigate_preserves_tool_reasoning(
    mock_get_llm_client,
    mock_execute_tool,
):
    mock_client = MagicMock()
    mock_client.responses.parse.return_value = create_mock_llm_response(
        ToolName.LOGS,
        "checkout-service",
        reasoning="Logs can confirm whether requests are timing out.",
    )
    mock_get_llm_client.return_value = mock_client

    mock_execute_tool.return_value = []

    result = investigate(
        state=create_test_state(),
        max_tool_calls=1,
    )

    assert (
        result.tool_history[0].reasoning
        == "Logs can confirm whether requests are timing out."
    )


@patch("traceroot.agent.investigation.execute_tool")
@patch("traceroot.agent.investigation.get_llm_client")
def test_investigate_preserves_tool_observations(
    mock_get_llm_client,
    mock_execute_tool,
):
    mock_client = MagicMock()
    mock_client.responses.parse.return_value = create_mock_llm_response(
        ToolName.LOGS,
        "checkout-service",
    )
    mock_get_llm_client.return_value = mock_client

    log_entry = LogEntry(
        id="LOG-TEST-01",
        timestamp="2026-09-25T00:00:00Z",
        service="checkout-service",
        level="ERROR",
        message="Database timeout",
    )

    mock_execute_tool.return_value = [log_entry]

    result = investigate(
        state=create_test_state(),
        max_tool_calls=1,
    )

    assert len(result.tool_history[0].observations) == 1
    assert "LOG-TEST-01" in result.tool_history[0].observations[0]
    assert "Database timeout" in result.tool_history[0].observations[0]


@patch("traceroot.agent.investigation.execute_tool")
@patch("traceroot.agent.investigation.get_llm_client")
def test_investigate_respects_max_tool_calls(
    mock_get_llm_client,
    mock_execute_tool,
):
    mock_client = MagicMock()

    mock_client.responses.parse.side_effect = [
        create_mock_llm_response(
            ToolName.LOGS,
            "checkout-service",
        ),
        create_mock_llm_response(
            ToolName.METRICS,
            "checkout-service",
        ),
        create_mock_llm_response(
            ToolName.DEPLOYMENTS,
            "checkout-service",
        ),
    ]

    mock_get_llm_client.return_value = mock_client

    mock_execute_tool.side_effect = [
        [MagicMock(id="LOG-001")],
        [MagicMock(id="METRIC-001")],
        [MagicMock(id="DEPLOY-001")],
    ]

    result = investigate(
        state=create_test_state(),
        max_tool_calls=3,
    )

    assert mock_client.responses.parse.call_count == 3
    assert mock_execute_tool.call_count == 3

    assert len(result.tool_history) == 3
    assert result.stop_reason == "tool_budget_exhausted"


@patch("traceroot.agent.investigation.execute_tool")
@patch("traceroot.agent.investigation.get_llm_client")
def test_investigate_accumulates_evidence_across_tool_calls(
    mock_get_llm_client,
    mock_execute_tool,
):
    mock_client = MagicMock()

    mock_client.responses.parse.side_effect = [
        create_mock_llm_response(
            ToolName.LOGS,
            "checkout-service",
        ),
        create_mock_llm_response(
            ToolName.METRICS,
            "checkout-service",
        ),
    ]

    mock_get_llm_client.return_value = mock_client

    log_entry = LogEntry(
        id="LOG-TEST-01",
        timestamp="2026-09-25T00:00:00Z",
        service="checkout-service",
        level="ERROR",
        message="Database timeout",
    )

    metric_entry = MetricEntry(
        id="METRIC-TEST-01",
        timestamp="2026-09-25T00:00:00Z",
        service="checkout-service",
        metric="db_connection_waiters",
        value=37.0,
        unit="count",
    )

    mock_execute_tool.side_effect = [
        [log_entry],
        [metric_entry],
    ]

    result = investigate(
        state=create_test_state(),
        max_tool_calls=2,
    )

    assert result.evidence_ids == [
        "LOG-TEST-01",
        "METRIC-TEST-01",
    ]

    assert len(result.tool_history) == 2


@patch("traceroot.agent.investigation.execute_tool")
@patch("traceroot.agent.investigation.get_llm_client")
def test_investigate_preserves_incident(
    mock_get_llm_client,
    mock_execute_tool,
):
    mock_client = MagicMock()
    mock_client.responses.parse.return_value = create_mock_llm_response(
        ToolName.LOGS,
        "checkout-service",
    )
    mock_get_llm_client.return_value = mock_client

    mock_execute_tool.return_value = []

    state = create_test_state()
    original_incident = state.incident

    result = investigate(
        state=state,
        max_tool_calls=1,
    )

    assert result.incident == original_incident


@patch("traceroot.agent.investigation.get_llm_client")
def test_investigate_raises_when_tool_selection_is_missing(
    mock_get_llm_client,
):
    mock_response = MagicMock()
    mock_response.output_parsed = None

    mock_client = MagicMock()
    mock_client.responses.parse.return_value = mock_response
    mock_get_llm_client.return_value = mock_client

    with pytest.raises(RuntimeError):
        investigate(
            state=create_test_state(),
            max_tool_calls=1,
        )


@patch("traceroot.agent.investigation.execute_tool")
@patch("traceroot.agent.investigation.get_llm_client")
def test_investigate_records_llm_usage(
    mock_get_llm_client,
    mock_execute_tool,
):
    usage = LLMUsage()

    mock_response = create_mock_llm_response(
        ToolName.LOGS,
        "checkout-service",
    )
    mock_response.usage.input_tokens = 200
    mock_response.usage.output_tokens = 40

    mock_client = MagicMock()
    mock_client.responses.parse.return_value = mock_response
    mock_get_llm_client.return_value = mock_client

    mock_execute_tool.return_value = [MagicMock(id="LOG-TEST-01")]

    investigate(
        state=create_test_state(),
        max_tool_calls=1,
        llm_usage=usage,
    )

    assert usage.input_tokens == 200
    assert usage.output_tokens == 40
    assert usage.total_tokens == 240
    assert usage.llm_calls == 1


@patch("traceroot.agent.investigation.execute_tool")
@patch("traceroot.agent.investigation.get_llm_client")
def test_investigate_records_call_when_token_usage_unavailable(
    mock_get_llm_client,
    mock_execute_tool,
):
    usage = LLMUsage()

    mock_response = create_mock_llm_response(
        ToolName.LOGS,
        "checkout-service",
    )
    mock_response.usage = None

    mock_client = MagicMock()
    mock_client.responses.parse.return_value = mock_response
    mock_get_llm_client.return_value = mock_client

    mock_execute_tool.return_value = [MagicMock(id="LOG-TEST-01")]

    investigate(
        state=create_test_state(),
        max_tool_calls=1,
        llm_usage=usage,
    )

    assert usage.input_tokens is None
    assert usage.output_tokens is None
    assert usage.total_tokens is None
    assert usage.llm_calls == 1


@patch("traceroot.agent.investigation.execute_tool")
@patch("traceroot.agent.investigation.get_llm_client")
def test_investigate_accumulates_llm_usage_across_selections(
    mock_get_llm_client,
    mock_execute_tool,
):
    usage = LLMUsage()

    first_response = create_mock_llm_response(
        ToolName.LOGS,
        "checkout-service",
    )
    first_response.usage.input_tokens = 200
    first_response.usage.output_tokens = 40

    second_response = create_mock_llm_response(
        ToolName.METRICS,
        "checkout-service",
    )
    second_response.usage.input_tokens = 250
    second_response.usage.output_tokens = 50

    mock_client = MagicMock()
    mock_client.responses.parse.side_effect = [
        first_response,
        second_response,
    ]
    mock_get_llm_client.return_value = mock_client

    mock_execute_tool.side_effect = [
        [MagicMock(id="LOG-TEST-01")],
        [MagicMock(id="METRIC-TEST-01")],
    ]

    investigate(
        state=create_test_state(),
        max_tool_calls=2,
        llm_usage=usage,
    )

    assert usage.input_tokens == 450
    assert usage.output_tokens == 90
    assert usage.total_tokens == 540
    assert usage.llm_calls == 2


def test_build_prompt_treats_suspected_services_as_leads():
    prompt = " ".join(build_prompt(create_test_state()).split())

    assert "checkout-service" in prompt
    assert "Checkout requests are slow and timing out." in prompt
    assert "Database connection exhaustion" in prompt
    assert (
        "Treat suspected_services and current hypotheses as leads, not confirmed causes"
        in prompt
    )
    assert "or restrictions on which services to investigate" in prompt
    assert "distinguish the service reporting an error from its source" in prompt


def test_build_prompt_discourages_redundant_exploration():
    prompt = " ".join(build_prompt(create_test_state()).split())

    assert (
        "Do not repeat a tool/service combination already present in tool history"
        in prompt
    )
    assert "Check the full history, including empty calls" in prompt
    assert "changing between service-filtered and all-service queries" in prompt
    assert "explain what new evidence the wider scope is likely to add" in prompt
    assert "Prefer unexplored evidence sources likely to discriminate" in prompt
    assert "support or contradict a hypothesis" in prompt


@patch("builtins.open")
@patch("pathlib.Path.read_text")
def test_build_prompt_does_not_load_ground_truth(mock_read_text, mock_open):
    state = create_test_state()
    prompt = build_prompt(state)

    mock_read_text.assert_not_called()
    mock_open.assert_not_called()
    assert "ground_truth" not in prompt
    assert "supporting_evidence_ids" not in prompt
    assert "INC-TEST" in prompt


@patch("traceroot.agent.investigation.execute_tool")
@patch("traceroot.agent.investigation.get_llm_client")
def test_investigate_prompts_to_broaden_after_empty_targeted_result(
    mock_get_llm_client,
    mock_execute_tool,
):
    mock_client = mock_get_llm_client.return_value
    mock_client.responses.parse.side_effect = [
        create_mock_llm_response(ToolName.LOGS, "checkout-service"),
        create_mock_llm_response(ToolName.LOGS, None),
    ]
    mock_execute_tool.side_effect = [[], [MagicMock(id="LOG-OTHER")]]

    result = investigate(create_test_state(), max_tool_calls=2)

    second_prompt = " ".join(
        mock_client.responses.parse.call_args_list[1].kwargs["input"].split()
    )
    assert (
        "After a service-targeted call returns no evidence, broaden service scope"
        in second_prompt
    )
    assert (
        "consider service=None or another service supported by the symptoms"
        in second_prompt
    )
    assert "An empty result does not confirm or rule out a cause" in second_prompt
    assert '"service":"checkout-service"' in second_prompt
    assert '"returned_count":0' in second_prompt
    assert '"returned_observations":0' in second_prompt
    mock_execute_tool.assert_called_with(
        tool_name=ToolName.LOGS,
        incident_id="INC-TEST",
        service=None,
    )
    assert result.evidence_ids == ["LOG-OTHER"]
    assert result.stop_reason == "tool_budget_exhausted"


@patch("traceroot.agent.investigation.execute_tool")
@patch("traceroot.agent.investigation.get_llm_client")
def test_investigate_stops_before_executing_duplicate_selection(
    mock_get_llm_client,
    mock_execute_tool,
):
    mock_client = mock_get_llm_client.return_value
    mock_client.responses.parse.return_value = create_mock_llm_response(
        ToolName.LOGS,
        "checkout-service",
    )
    mock_execute_tool.return_value = [MagicMock(id="LOG-TEST-01")]

    result = investigate(create_test_state(), max_tool_calls=6)

    assert result.stop_reason == "duplicate_selection"
    assert mock_client.responses.parse.call_count == 2
    mock_execute_tool.assert_called_once()
    assert len(result.tool_history) == 1


@patch("traceroot.agent.investigation.execute_tool")
@patch("traceroot.agent.investigation.get_llm_client")
def test_investigate_broadens_same_service_after_empty_targeted_result(
    mock_get_llm_client,
    mock_execute_tool,
):
    mock_client = mock_get_llm_client.return_value
    mock_client.responses.parse.side_effect = [
        create_mock_llm_response(ToolName.LOGS, "checkout-service"),
        create_mock_llm_response(ToolName.METRICS, "checkout-service"),
    ]
    mock_execute_tool.side_effect = [[], [MagicMock(id="METRIC-OTHER")]]

    result = investigate(create_test_state(), max_tool_calls=2)

    assert mock_execute_tool.call_args_list[1].kwargs == {
        "tool_name": ToolName.METRICS,
        "incident_id": "INC-TEST",
        "service": None,
    }
    assert result.tool_history[1].tool_name == "metrics"
    assert result.tool_history[1].service is None
    assert result.tool_history[1].evidence_ids == ["METRIC-OTHER"]


@patch("traceroot.agent.investigation.execute_tool")
@patch("traceroot.agent.investigation.get_llm_client")
def test_investigate_keeps_same_service_after_nonempty_targeted_result(
    mock_get_llm_client,
    mock_execute_tool,
):
    mock_client = mock_get_llm_client.return_value
    mock_client.responses.parse.side_effect = [
        create_mock_llm_response(ToolName.LOGS, "checkout-service"),
        create_mock_llm_response(ToolName.METRICS, "checkout-service"),
    ]
    mock_execute_tool.side_effect = [
        [MagicMock(id="LOG-TEST-01")],
        [MagicMock(id="METRIC-TEST-01")],
    ]

    result = investigate(create_test_state(), max_tool_calls=2)

    assert mock_execute_tool.call_args_list[1].kwargs["service"] == "checkout-service"
    assert result.tool_history[1].service == "checkout-service"


@patch("traceroot.agent.investigation.execute_tool")
@patch("traceroot.agent.investigation.get_llm_client")
def test_investigate_preserves_different_service_after_empty_targeted_result(
    mock_get_llm_client,
    mock_execute_tool,
):
    mock_client = mock_get_llm_client.return_value
    mock_client.responses.parse.side_effect = [
        create_mock_llm_response(ToolName.LOGS, "checkout-service"),
        create_mock_llm_response(ToolName.METRICS, "payment-service"),
    ]
    mock_execute_tool.side_effect = [[], [MagicMock(id="METRIC-PAYMENT")]]

    result = investigate(create_test_state(), max_tool_calls=2)

    assert mock_execute_tool.call_args_list[1].kwargs["service"] == "payment-service"
    assert result.tool_history[1].service == "payment-service"


@patch("traceroot.agent.investigation.execute_tool")
@patch("traceroot.agent.investigation.get_llm_client")
def test_investigate_preserves_global_selection_after_empty_targeted_result(
    mock_get_llm_client,
    mock_execute_tool,
):
    mock_client = mock_get_llm_client.return_value
    mock_client.responses.parse.side_effect = [
        create_mock_llm_response(ToolName.LOGS, "checkout-service"),
        create_mock_llm_response(ToolName.METRICS, None),
    ]
    mock_execute_tool.side_effect = [[], [MagicMock(id="METRIC-GLOBAL")]]

    result = investigate(create_test_state(), max_tool_calls=2)

    assert mock_execute_tool.call_args_list[1].kwargs["service"] is None
    assert result.tool_history[1].service is None


@patch("traceroot.agent.investigation.execute_tool")
@patch("traceroot.agent.investigation.get_llm_client")
def test_investigate_keeps_consecutive_empty_result_guardrail(
    mock_get_llm_client,
    mock_execute_tool,
):
    mock_client = mock_get_llm_client.return_value
    mock_client.responses.parse.side_effect = [
        create_mock_llm_response(ToolName.LOGS, "checkout-service"),
        create_mock_llm_response(ToolName.LOGS, None),
    ]
    mock_execute_tool.return_value = []

    result = investigate(create_test_state(), max_tool_calls=6)

    assert result.stop_reason == "consecutive_empty_results"
    assert mock_client.responses.parse.call_count == 2
    assert mock_execute_tool.call_count == 2
    assert len(result.tool_history) == 2


@patch("traceroot.agent.investigation.get_llm_client")
def test_investigate_uses_injected_mcp_executor(mock_get_llm_client):
    mock_get_llm_client.return_value.responses.parse.return_value = (
        create_mock_llm_response(ToolName.LOGS, "checkout-service")
    )
    mcp_executor = MagicMock(return_value=[])

    investigate(create_test_state(), max_tool_calls=1, tool_executor=mcp_executor)

    mcp_executor.assert_called_once_with(
        tool_name=ToolName.LOGS,
        incident_id="INC-TEST",
        service="checkout-service",
    )


@patch("traceroot.agent.investigation.get_llm_client")
def test_investigate_with_mcp_preserves_tool_history(mock_get_llm_client):
    mock_get_llm_client.return_value.responses.parse.return_value = (
        create_mock_llm_response(ToolName.LOGS, "checkout-service")
    )
    entry = LogEntry(
        id="LOG-MCP-1",
        timestamp="2026-09-27T12:00:00Z",
        service="checkout-service",
        level="ERROR",
        message="database timeout",
    )

    result = investigate(
        create_test_state(),
        max_tool_calls=1,
        tool_executor=MagicMock(return_value=[entry]),
    )

    assert result.tool_history[0].tool_name == "logs"
    assert result.tool_history[0].service == "checkout-service"
    assert result.tool_history[0].evidence_ids == ["LOG-MCP-1"]


@patch("traceroot.agent.investigation.get_llm_client")
def test_investigate_with_mcp_preserves_evidence_ids(mock_get_llm_client):
    mock_get_llm_client.return_value.responses.parse.return_value = (
        create_mock_llm_response(ToolName.LOGS, "checkout-service")
    )
    entry = LogEntry(
        id="LOG-MCP-1",
        timestamp="2026-09-27T12:00:00Z",
        service="checkout-service",
        level="ERROR",
        message="database timeout",
    )

    result = investigate(
        create_test_state(),
        max_tool_calls=1,
        tool_executor=MagicMock(return_value=[entry]),
    )

    assert result.evidence_ids == ["LOG-MCP-1"]


@patch("traceroot.agent.investigation.get_llm_client")
def test_investigate_with_mcp_keeps_duplicate_guardrail(mock_get_llm_client):
    mock_get_llm_client.return_value.responses.parse.return_value = (
        create_mock_llm_response(ToolName.LOGS, "checkout-service")
    )
    mcp_executor = MagicMock(
        return_value=[
            LogEntry(
                id="LOG-MCP-1",
                timestamp="2026-09-27T12:00:00Z",
                service="checkout-service",
                level="ERROR",
                message="database timeout",
            )
        ]
    )

    result = investigate(
        create_test_state(),
        max_tool_calls=3,
        tool_executor=mcp_executor,
    )

    assert result.stop_reason == "duplicate_selection"
    mcp_executor.assert_called_once()


@patch("traceroot.agent.investigation.get_llm_client")
def test_investigate_with_mcp_keeps_empty_result_guardrail(mock_get_llm_client):
    mock_get_llm_client.return_value.responses.parse.side_effect = [
        create_mock_llm_response(ToolName.LOGS, "checkout-service"),
        create_mock_llm_response(ToolName.METRICS, "payment-service"),
    ]
    mcp_executor = MagicMock(return_value=[])

    result = investigate(
        create_test_state(),
        max_tool_calls=3,
        tool_executor=mcp_executor,
    )

    assert result.stop_reason == "consecutive_empty_results"
    assert mcp_executor.call_count == 2


@patch("traceroot.agent.investigation.execute_tool")
@patch("traceroot.agent.investigation.get_llm_client")
def test_investigate_defaults_to_direct_tool_execution(
    mock_get_llm_client,
    mock_execute_tool,
):
    mock_get_llm_client.return_value.responses.parse.return_value = (
        create_mock_llm_response(ToolName.LOGS, "checkout-service")
    )
    mock_execute_tool.return_value = []

    investigate(create_test_state(), max_tool_calls=1)

    mock_execute_tool.assert_called_once_with(
        tool_name=ToolName.LOGS,
        incident_id="INC-TEST",
        service="checkout-service",
    )


@patch("traceroot.agent.investigation.execute_tool")
@patch("traceroot.agent.investigation.get_llm_client")
def test_tool_selection_prompt_is_bounded_after_large_tool_result(client, executor):
    state = create_test_state()
    entries = [
        LogEntry(
            id=f"LARGE-{index:04d}",
            timestamp="2026-09-25T00:00:00Z",
            service="checkout-service",
            level="ERROR",
            message=f"Unique log {index:04d} " + "x" * 1500,
        )
        for index in range(240)
    ]
    executor.return_value = entries
    client.return_value.responses.parse.side_effect = [
        create_mock_llm_response(ToolName.LOGS, "checkout-service"),
        MagicMock(output_parsed=ToolSelection(stop=True, reasoning="Enough")),
    ]
    investigate(state)
    prompt = client.return_value.responses.parse.call_args_list[1].kwargs["input"]
    presentation = assert_prompt_evidence(prompt, state)
    visible = {item.evidence_id for item in presentation.observations}
    assert visible and len(visible) < len(entries)
    for entry in entries:
        if entry.id not in visible:
            assert entry.id not in prompt
            assert entry.message not in prompt
    assert state.evidence_ids == [entry.id for entry in entries]
    assert state.tool_history[0].observations == [str(entry) for entry in entries]


@patch("traceroot.agent.investigation.execute_tool")
@patch("traceroot.agent.investigation.get_llm_client")
def test_bounded_context_preserves_empty_call_broadening(client, executor):
    state = add_large_history(create_test_state())
    state.tool_history.append(
        ToolCallRecord(tool_name="metrics", service="checkout-service")
    )
    before = state.model_dump()
    client.return_value.responses.parse.return_value = create_mock_llm_response(
        ToolName.DEPLOYMENTS, "checkout-service"
    )
    executor.return_value = []
    investigate(state, max_tool_calls=3)
    prompt = client.return_value.responses.parse.call_args.kwargs["input"]
    assert_prompt_evidence(prompt, InvestigationState.model_validate(before))
    summary = query_metadata(prompt)["tool_summaries"]["metrics"]
    assert summary["queried"]
    assert summary["calls"][0]["service"] == "checkout-service"
    assert summary["calls"][0]["returned_count"] == 0
    executor.assert_called_once_with(
        tool_name=ToolName.DEPLOYMENTS, incident_id=state.incident.id, service=None
    )
    assert [record.model_dump() for record in state.tool_history[:2]] == before[
        "tool_history"
    ]
    assert state.evidence_ids == before["evidence_ids"]


@patch("traceroot.agent.investigation.get_llm_client")
def test_small_tool_history_remains_fully_visible_to_selection_prompt(client):
    state = create_test_state()
    state.tool_history = [
        ToolCallRecord(
            tool_name="logs",
            evidence_ids=["SMALL-1", "SMALL-2"],
            observations=["First fact", "Second fact"],
        )
    ]
    state.evidence_ids = ["SMALL-1", "SMALL-2"]
    before = state.model_dump()
    client.return_value.responses.parse.return_value = MagicMock(
        output_parsed=ToolSelection(stop=True, reasoning="Enough")
    )
    investigate(state)
    result = assert_prompt_evidence(
        client.return_value.responses.parse.call_args.kwargs["input"], state
    )
    assert len(result.observations) == 2
    assert not result.partial
    assert [r.model_dump() for r in state.tool_history] == before["tool_history"]
    assert state.evidence_ids == before["evidence_ids"]


@patch("traceroot.agent.investigation.get_llm_client")
def test_consecutive_empty_stop_reason_matches_evaluator_contract(mock_get_llm_client):
    from traceroot.domain.ground_truth import GroundTruth
    from traceroot.domain.rca import RCAResult
    from traceroot.evaluation.agent_trace import evaluate_agent_trace
    from traceroot.experiments.models import AgentExperimentRecord

    mock_get_llm_client.return_value.responses.parse.side_effect = [
        create_mock_llm_response(ToolName.LOGS),
        create_mock_llm_response(ToolName.METRICS),
    ]
    state = investigate(create_test_state(), tool_executor=MagicMock(return_value=[]))
    assert state.stop_reason == "consecutive_empty_results"
    # A minimal final result permits evaluating the trace without any RCA API call.
    record = AgentExperimentRecord(
        incident_id=state.incident.id,
        model="test-model",
        hypotheses=state.hypotheses,
        evidence_ids=state.evidence_ids,
        tool_history=state.tool_history,
        stop_reason=state.stop_reason,
        stop_reasoning=state.stop_reasoning,
        result=RCAResult(
            incident_id=state.incident.id,
            root_cause="Unknown",
            evidence_ids=[],
            explanation="Test trace only",
        ),
        latency_ms=0,
        timestamp=datetime.now(UTC),
    )
    truth = GroundTruth(
        incident_id=state.incident.id,
        root_cause="Test cause",
        root_cause_category="configuration_regression",
        affected_service="checkout-service",
        supporting_evidence_ids=[],
    )
    metric = next(
        metric
        for metric in evaluate_agent_trace(record, truth)
        if metric.name == "Stop Quality"
    )
    assert metric.score == 0.5
    assert metric.passed is True
