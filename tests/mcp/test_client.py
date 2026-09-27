from unittest.mock import AsyncMock, patch

import pytest
from mcp.types import CallToolResult

from traceroot.data.models import (
    CodeChangeEntry,
    DeploymentEntry,
    LogEntry,
    MetricEntry,
)
from traceroot.mcp.client import execute_mcp_tool, mcp
from traceroot.tools.interface import ToolName

TIMESTAMP = "2026-09-27T12:00:00Z"


def create_mcp_result(entries: list[dict]) -> CallToolResult:
    return CallToolResult(content=[], structuredContent={"result": entries})


def _assert_tool_mapping(
    call_tool: AsyncMock,
    tool_name: ToolName,
    expected_name: str,
) -> None:
    call_tool.return_value = create_mcp_result([])
    execute_mcp_tool(tool_name, "INC-001")

    assert call_tool.await_args.args[0] == expected_name


@patch.object(mcp, "call_tool", new_callable=AsyncMock)
def test_execute_mcp_tool_maps_logs(mock_call_tool):
    _assert_tool_mapping(mock_call_tool, ToolName.LOGS, "get_logs")


@patch.object(mcp, "call_tool", new_callable=AsyncMock)
def test_execute_mcp_tool_maps_metrics(mock_call_tool):
    _assert_tool_mapping(mock_call_tool, ToolName.METRICS, "get_metrics")


@patch.object(mcp, "call_tool", new_callable=AsyncMock)
def test_execute_mcp_tool_maps_deployments(mock_call_tool):
    _assert_tool_mapping(mock_call_tool, ToolName.DEPLOYMENTS, "get_deployments")


@patch.object(mcp, "call_tool", new_callable=AsyncMock)
def test_execute_mcp_tool_maps_code_changes(mock_call_tool):
    _assert_tool_mapping(mock_call_tool, ToolName.CODE_CHANGES, "get_code_changes")


@patch.object(mcp, "call_tool", new_callable=AsyncMock)
def test_execute_mcp_tool_forwards_incident_id_and_service(mock_call_tool):
    mock_call_tool.return_value = create_mcp_result([])
    execute_mcp_tool(ToolName.LOGS, "INC-123", "checkout-service")

    mock_call_tool.assert_awaited_once_with(
        "get_logs",
        {"incident_id": "INC-123", "service": "checkout-service"},
    )


@pytest.mark.parametrize(
    ("tool_name", "entry", "model"),
    [
        (
            ToolName.LOGS,
            {
                "id": "LOG-1",
                "timestamp": TIMESTAMP,
                "service": "checkout-service",
                "level": "ERROR",
                "message": "request failed",
            },
            LogEntry,
        ),
        (
            ToolName.METRICS,
            {
                "id": "METRIC-1",
                "timestamp": TIMESTAMP,
                "service": "checkout-service",
                "metric": "latency",
                "value": 125.0,
                "unit": "ms",
            },
            MetricEntry,
        ),
        (
            ToolName.DEPLOYMENTS,
            {
                "id": "DEPLOY-1",
                "timestamp": TIMESTAMP,
                "service": "checkout-service",
                "version": "v1.2.3",
                "description": "release",
            },
            DeploymentEntry,
        ),
        (
            ToolName.CODE_CHANGES,
            {
                "id": "CHANGE-1",
                "timestamp": TIMESTAMP,
                "service": "checkout-service",
                "commit_sha": "abc123",
                "files": ["checkout.py"],
                "description": "fix timeout",
                "diff": None,
            },
            CodeChangeEntry,
        ),
    ],
)
@patch.object(mcp, "call_tool", new_callable=AsyncMock)
def test_execute_mcp_tool_returns_typed_evidence(
    mock_call_tool,
    tool_name,
    entry,
    model,
):
    mock_call_tool.return_value = create_mcp_result([entry])
    result = execute_mcp_tool(tool_name, "INC-001")

    assert len(result) == 1
    assert isinstance(result[0], model)
    assert result[0].id == entry["id"]


@patch.object(mcp, "call_tool", new_callable=AsyncMock)
def test_execute_mcp_tool_returns_empty_list(mock_call_tool):
    mock_call_tool.return_value = create_mcp_result([])

    assert execute_mcp_tool(ToolName.LOGS, "INC-001") == []


@patch.object(mcp, "call_tool", new_callable=AsyncMock)
def test_execute_mcp_tool_propagates_failure(mock_call_tool):
    error = RuntimeError("MCP transport failed")
    mock_call_tool.side_effect = error

    with pytest.raises(RuntimeError) as raised:
        execute_mcp_tool(ToolName.LOGS, "INC-001")

    assert raised.value is error
