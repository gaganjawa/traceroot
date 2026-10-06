import asyncio
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from mcp.server import MCPServer

from traceroot.data.models import (
    CodeChangeEntry,
    DeploymentEntry,
    LogEntry,
    MetricEntry,
)
from traceroot.mcp.server import (
    get_code_changes,
    get_deployments,
    get_logs,
    get_metrics,
    mcp,
)
from traceroot.tools.interface import ToolName

TIMESTAMP = datetime(2026, 9, 27, 12, 0, tzinfo=UTC)


def test_mcp_server_exposes_all_evidence_operations():
    assert all(
        callable(operation)
        for operation in (get_logs, get_metrics, get_deployments, get_code_changes)
    )


@patch("traceroot.mcp.server.execute_tool")
def test_get_logs_dispatches_to_existing_logs_tool(mock_execute_tool):
    mock_execute_tool.return_value = []

    assert get_logs("INC-001", "checkout-service") == []
    mock_execute_tool.assert_called_once_with(
        ToolName.LOGS,
        incident_id="INC-001",
        service="checkout-service",
    )


@patch("traceroot.mcp.server.execute_tool")
def test_get_logs_forwards_optional_service(mock_execute_tool):
    mock_execute_tool.return_value = []

    get_logs("INC-001", service=None)

    mock_execute_tool.assert_called_once_with(
        ToolName.LOGS,
        incident_id="INC-001",
        service=None,
    )


@patch("traceroot.mcp.server.execute_tool")
def test_get_logs_serializes_evidence(mock_execute_tool):
    mock_execute_tool.return_value = [
        LogEntry(
            id="log-1",
            timestamp=TIMESTAMP,
            service="checkout-service",
            level="ERROR",
            message="request failed",
        ),
        LogEntry(
            id="log-2",
            timestamp=TIMESTAMP,
            service="checkout-service",
            level="INFO",
            message="retry succeeded",
        ),
    ]

    result = get_logs("INC-001")

    assert result == [
        {
            "id": "log-1",
            "timestamp": "2026-09-27T12:00:00Z",
            "service": "checkout-service",
            "level": "ERROR",
            "message": "request failed",
            "labels": {},
        },
        {
            "id": "log-2",
            "timestamp": "2026-09-27T12:00:00Z",
            "service": "checkout-service",
            "level": "INFO",
            "message": "retry succeeded",
            "labels": {},
        },
    ]


@patch("traceroot.mcp.server.execute_tool")
def test_get_logs_returns_empty_list_when_no_evidence(mock_execute_tool):
    mock_execute_tool.return_value = []

    assert get_logs("INC-001") == []


@patch("traceroot.mcp.server.execute_tool")
def test_get_metrics_dispatches_to_existing_metrics_tool(mock_execute_tool):
    mock_execute_tool.return_value = []

    get_metrics("INC-001", "checkout-service")

    mock_execute_tool.assert_called_once_with(
        ToolName.METRICS,
        incident_id="INC-001",
        service="checkout-service",
    )


@patch("traceroot.mcp.server.execute_tool")
def test_get_metrics_serializes_evidence(mock_execute_tool):
    mock_execute_tool.return_value = [
        MetricEntry(
            id="metric-1",
            timestamp=TIMESTAMP,
            service="checkout-service",
            metric="latency",
            value=125.5,
            unit="ms",
        )
    ]

    assert get_metrics("INC-001") == [
        {
            "id": "metric-1",
            "timestamp": "2026-09-27T12:00:00Z",
            "service": "checkout-service",
            "metric": "latency",
            "value": 125.5,
            "unit": "ms",
            "labels": {},
        }
    ]


@patch("traceroot.mcp.server.execute_tool")
def test_get_deployments_dispatches_to_existing_deployments_tool(mock_execute_tool):
    mock_execute_tool.return_value = []

    get_deployments("INC-001", "checkout-service")

    mock_execute_tool.assert_called_once_with(
        ToolName.DEPLOYMENTS,
        incident_id="INC-001",
        service="checkout-service",
    )


@patch("traceroot.mcp.server.execute_tool")
def test_get_deployments_serializes_evidence(mock_execute_tool):
    mock_execute_tool.return_value = [
        DeploymentEntry(
            id="deployment-1",
            timestamp=TIMESTAMP,
            service="checkout-service",
            version="v1.2.3",
            description="Increase timeout",
        )
    ]

    assert get_deployments("INC-001") == [
        {
            "id": "deployment-1",
            "timestamp": "2026-09-27T12:00:00Z",
            "service": "checkout-service",
            "version": "v1.2.3",
            "description": "Increase timeout",
        }
    ]


@patch("traceroot.mcp.server.execute_tool")
def test_get_code_changes_dispatches_to_existing_code_changes_tool(mock_execute_tool):
    mock_execute_tool.return_value = []

    get_code_changes("INC-001", "checkout-service")

    mock_execute_tool.assert_called_once_with(
        ToolName.CODE_CHANGES,
        incident_id="INC-001",
        service="checkout-service",
    )


@patch("traceroot.mcp.server.execute_tool")
def test_get_code_changes_serializes_evidence(mock_execute_tool):
    mock_execute_tool.return_value = [
        CodeChangeEntry(
            id="change-1",
            timestamp=TIMESTAMP,
            service="checkout-service",
            commit_sha="abc123",
            files=["src/checkout.py"],
            description="Handle timeout",
            diff=None,
        )
    ]

    assert get_code_changes("INC-001") == [
        {
            "id": "change-1",
            "timestamp": "2026-09-27T12:00:00Z",
            "service": "checkout-service",
            "commit_sha": "abc123",
            "files": ["src/checkout.py"],
            "description": "Handle timeout",
            "diff": None,
        }
    ]


@patch("traceroot.mcp.server.execute_tool")
def test_mcp_tool_preserves_evidence_ids(mock_execute_tool):
    mock_execute_tool.return_value = [
        LogEntry(
            id="original-id",
            timestamp=TIMESTAMP,
            service="checkout-service",
            level="INFO",
            message="unchanged",
        )
    ]

    assert get_logs("INC-001")[0]["id"] == "original-id"


@patch("traceroot.mcp.server.execute_tool")
def test_mcp_tool_propagates_underlying_tool_failure(mock_execute_tool):
    error = FileNotFoundError("incident data is missing")
    mock_execute_tool.side_effect = error

    with pytest.raises(FileNotFoundError) as raised:
        get_logs("INC-001")

    assert raised.value is error


def test_mcp_server_is_created():
    assert isinstance(mcp, MCPServer)


def test_mcp_server_registers_all_evidence_tools():
    registered_tools = asyncio.run(mcp.list_tools())

    assert {tool.name for tool in registered_tools} == {
        "get_logs",
        "get_metrics",
        "get_deployments",
        "get_code_changes",
    }
