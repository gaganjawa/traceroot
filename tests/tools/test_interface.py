from unittest.mock import patch

import pytest

from traceroot.tools.interface import execute_tool
from traceroot.tools.models import ToolName


@patch("traceroot.tools.interface._default_backend")
def test_execute_tool_dispatches_to_logs(mock_default_backend):
    mock_default_backend.query.return_value = ["log1", "log2"]

    result = execute_tool(
        ToolName.LOGS,
        incident_id="INC-001",
        service="checkout-service",
    )

    mock_default_backend.query.assert_called_once_with(
        tool_name=ToolName.LOGS,
        incident_id="INC-001",
        service="checkout-service",
    )
    assert result == ["log1", "log2"]


@patch("traceroot.tools.interface._default_backend")
def test_execute_tool_dispatches_to_metrics(mock_default_backend):
    mock_default_backend.query.return_value = ["metric1"]

    result = execute_tool(
        ToolName.METRICS,
        incident_id="INC-001",
        service="checkout-service",
    )

    mock_default_backend.query.assert_called_once_with(
        tool_name=ToolName.METRICS,
        incident_id="INC-001",
        service="checkout-service",
    )
    assert result == ["metric1"]


@patch("traceroot.tools.interface._default_backend")
def test_execute_tool_dispatches_to_deployments(mock_default_backend):
    mock_default_backend.query.return_value = ["deployment1"]

    result = execute_tool(
        ToolName.DEPLOYMENTS,
        incident_id="INC-001",
        service="checkout-service",
    )

    mock_default_backend.query.assert_called_once_with(
        tool_name=ToolName.DEPLOYMENTS,
        incident_id="INC-001",
        service="checkout-service",
    )
    assert result == ["deployment1"]


@patch("traceroot.tools.interface._default_backend")
def test_execute_tool_dispatches_to_code_changes(mock_default_backend):
    mock_default_backend.query.return_value = ["change1"]

    result = execute_tool(
        ToolName.CODE_CHANGES,
        incident_id="INC-001",
        service="checkout-service",
    )

    mock_default_backend.query.assert_called_once_with(
        tool_name=ToolName.CODE_CHANGES,
        incident_id="INC-001",
        service="checkout-service",
    )
    assert result == ["change1"]


@patch("traceroot.tools.interface._default_backend")
def test_execute_tool_passes_incident_id(mock_default_backend):
    mock_default_backend.query.return_value = []

    execute_tool(
        ToolName.LOGS,
        incident_id="INC-123",
    )

    mock_default_backend.query.assert_called_once_with(
        tool_name=ToolName.LOGS,
        incident_id="INC-123",
        service=None,
    )


@patch("traceroot.tools.interface._default_backend")
def test_execute_tool_passes_service(mock_default_backend):
    mock_default_backend.query.return_value = []

    execute_tool(
        ToolName.LOGS,
        incident_id="INC-001",
        service="payment-service",
    )

    mock_default_backend.query.assert_called_once_with(
        tool_name=ToolName.LOGS,
        incident_id="INC-001",
        service="payment-service",
    )


@patch("traceroot.tools.interface._default_backend")
def test_execute_tool_returns_underlying_results_unchanged(mock_default_backend):
    expected = ["log1", "log2"]
    mock_default_backend.query.return_value = expected

    result = execute_tool(
        ToolName.LOGS,
        incident_id="INC-001",
        service="checkout-service",
    )

    assert result is expected


def test_execute_tool_rejects_unknown_tool():
    with pytest.raises(ValueError, match="Unknown tool name: unknown_tool"):
        execute_tool(
            "unknown_tool",  # type: ignore[arg-type]
            incident_id="INC-001",
            service="checkout-service",
        )
