from unittest.mock import patch

from traceroot.tools.interface import ToolName, execute_tool


@patch("traceroot.tools.interface.query_logs")
def test_execute_tool_dispatches_to_logs(mock_query_logs):
    mock_query_logs.return_value = ["log1", "log2"]

    result = execute_tool(
        ToolName.LOGS,
        incident_id="INC-001",
        service="checkout-service",
    )

    mock_query_logs.assert_called_once_with(
        incident_id="INC-001",
        service="checkout-service",
    )

    assert result == ["log1", "log2"]


@patch("traceroot.tools.interface.query_metrics")
def test_execute_tool_dispatches_to_metrics(mock_query_metrics):
    mock_query_metrics.return_value = ["metric1", "metric2"]

    result = execute_tool(
        ToolName.METRICS,
        incident_id="INC-001",
        service="checkout-service",
    )

    mock_query_metrics.assert_called_once_with(
        incident_id="INC-001",
        service="checkout-service",
    )

    assert result == ["metric1", "metric2"]


@patch("traceroot.tools.interface.query_deployments")
def test_execute_tool_dispatches_to_deployments(mock_query_deployments):
    mock_query_deployments.return_value = ["deployment1", "deployment2"]

    result = execute_tool(
        ToolName.DEPLOYMENTS,
        incident_id="INC-001",
        service="checkout-service",
    )

    mock_query_deployments.assert_called_once_with(
        incident_id="INC-001",
        service="checkout-service",
    )

    assert result == ["deployment1", "deployment2"]


@patch("traceroot.tools.interface.query_code_changes")
def test_execute_tool_dispatches_to_code_changes(mock_query_code_changes):
    mock_query_code_changes.return_value = ["change1", "change2"]

    result = execute_tool(
        ToolName.CODE_CHANGES,
        incident_id="INC-001",
        service="checkout-service",
    )

    mock_query_code_changes.assert_called_once_with(
        incident_id="INC-001",
        service="checkout-service",
    )

    assert result == ["change1", "change2"]


@patch("traceroot.tools.interface.query_logs")
def test_execute_tool_passes_incident_id(mock_query_logs):
    mock_query_logs.return_value = ["log1", "log2"]

    result = execute_tool(
        ToolName.LOGS,
        incident_id="INC-001",
        service="checkout-service",
    )

    mock_query_logs.assert_called_once_with(
        incident_id="INC-001",
        service="checkout-service",
    )

    assert result == ["log1", "log2"]


@patch("traceroot.tools.interface.query_logs")
def test_execute_tool_passes_service(mock_query_logs):
    mock_query_logs.return_value = ["log1", "log2"]

    result = execute_tool(
        ToolName.LOGS,
        incident_id="INC-001",
        service="checkout-service",
    )

    mock_query_logs.assert_called_once_with(
        incident_id="INC-001",
        service="checkout-service",
    )

    assert result == ["log1", "log2"]


@patch("traceroot.tools.interface.query_logs")
def test_execute_tool_returns_underlying_results_unchanged(mock_query_logs):
    mock_query_logs.return_value = ["log1", "log2"]

    result = execute_tool(
        ToolName.LOGS,
        incident_id="INC-001",
        service="checkout-service",
    )

    assert result == ["log1", "log2"]


@patch("traceroot.tools.interface.query_logs")
def test_execute_tool_rejects_unknown_tool(mock_query_logs):
    try:
        execute_tool(
            "unknown_tool",  # type: ignore
            incident_id="INC-001",
            service="checkout-service",
        )
    except ValueError as e:
        assert str(e) == "Unknown tool name: unknown_tool"
    else:
        assert False, "Expected ValueError for unknown tool name"
