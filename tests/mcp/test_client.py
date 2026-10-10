from unittest.mock import AsyncMock, patch

import pytest
from mcp.shared.exceptions import MCPError
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


@pytest.fixture(autouse=True)
def isolate_mcp_config(monkeypatch):
    for name in (
        "TRACEROOT_MCP_TRANSPORT",
        "TRACEROOT_MCP_SERVER_URL",
        "TRACEROOT_MCP_TIMEOUT_SECONDS",
    ):
        monkeypatch.delenv(name, raising=False)
    # Every test must explicitly mock the remote client before it can connect.
    with patch("traceroot.mcp.client.Client") as factory:
        factory.side_effect = AssertionError("Unexpected remote connection")
        yield


@pytest.fixture
def remote_client(monkeypatch):
    monkeypatch.setenv("TRACEROOT_MCP_TRANSPORT", "streamable-http")
    monkeypatch.setenv("TRACEROOT_MCP_SERVER_URL", "http://127.0.0.1:8000/mcp")
    with patch("traceroot.mcp.client.Client") as factory:
        client = AsyncMock()
        factory.return_value.__aenter__.return_value = client
        client.call_tool.return_value = create_mcp_result([])
        yield factory, client


@pytest.mark.parametrize(
    "settings",
    [
        {"TRACEROOT_MCP_TRANSPORT": "sse"},
        {"TRACEROOT_MCP_TRANSPORT": "streamable-http"},
        *[
            {
                "TRACEROOT_MCP_TRANSPORT": "streamable-http",
                "TRACEROOT_MCP_SERVER_URL": url,
            }
            for url in (
                "",
                "localhost:8000/mcp",
                "ftp://host/mcp",
                "http://",
                "http://bad host/mcp",
            )
        ],
        *[
            {"TRACEROOT_MCP_TIMEOUT_SECONDS": timeout}
            for timeout in ("0", "-1", "nan", "inf", "-inf", "bad", "")
        ],
    ],
)
def test_invalid_config_rejected_before_connection(monkeypatch, settings):
    for name, value in settings.items():
        monkeypatch.setenv(name, value)
    with patch.object(mcp, "call_tool", new_callable=AsyncMock) as direct:
        with pytest.raises(ValueError):
            execute_mcp_tool(ToolName.LOGS, "INC-001")
        direct.assert_not_awaited()


@pytest.mark.parametrize(
    ("tool_name", "entry", "model", "wire_name"),
    [
        (
            ToolName.LOGS,
            {
                "id": "L1",
                "timestamp": TIMESTAMP,
                "service": "svc",
                "level": "ERROR",
                "message": "failed",
            },
            LogEntry,
            "get_logs",
        ),
        (
            ToolName.METRICS,
            {
                "id": "M1",
                "timestamp": TIMESTAMP,
                "service": "svc",
                "metric": "latency",
                "value": 1,
                "unit": "ms",
            },
            MetricEntry,
            "get_metrics",
        ),
        (
            ToolName.DEPLOYMENTS,
            {
                "id": "D1",
                "timestamp": TIMESTAMP,
                "service": "svc",
                "version": "v1",
                "description": "release",
            },
            DeploymentEntry,
            "get_deployments",
        ),
        (
            ToolName.CODE_CHANGES,
            {
                "id": "C1",
                "timestamp": TIMESTAMP,
                "service": "svc",
                "commit_sha": "abc",
                "files": ["a.py"],
                "description": "fix",
                "diff": None,
            },
            CodeChangeEntry,
            "get_code_changes",
        ),
    ],
)
def test_remote_mapping_and_typed_evidence(
    remote_client, tool_name, entry, model, wire_name
):
    factory, client = remote_client
    client.call_tool.return_value = create_mcp_result([entry])
    result = execute_mcp_tool(tool_name, "INC-123", "svc")
    assert result == [model.model_validate(entry)]
    client.call_tool.assert_awaited_once_with(
        wire_name, {"incident_id": "INC-123", "service": "svc"}
    )
    factory.assert_called_once_with(
        "http://127.0.0.1:8000/mcp", read_timeout_seconds=30.0
    )
    factory.return_value.__aexit__.assert_awaited_once_with(None, None, None)


def test_remote_empty_and_timeout_and_fresh_sessions(remote_client, monkeypatch):
    factory, client = remote_client
    monkeypatch.setenv("TRACEROOT_MCP_TIMEOUT_SECONDS", "2.5")
    for _ in range(2):
        assert execute_mcp_tool(ToolName.LOGS, "INC-001") == []
    assert factory.call_count == 2
    assert factory.return_value.__aenter__.await_count == 2
    assert factory.return_value.__aexit__.await_count == 2
    factory.assert_called_with("http://127.0.0.1:8000/mcp", read_timeout_seconds=2.5)
    client.call_tool.assert_awaited_with(
        "get_logs", {"incident_id": "INC-001", "service": None}
    )


@pytest.mark.parametrize(
    "content",
    [None, {}, {"result": None}, {"result": {}}, {"result": "bad"}, {"result": [{}]}],
)
def test_remote_invalid_response_closes_context(remote_client, content):
    factory, client = remote_client
    client.call_tool.return_value = CallToolResult(
        content=[], structuredContent=content
    )
    with pytest.raises(ValueError):
        execute_mcp_tool(ToolName.LOGS, "INC-001")
    factory.return_value.__aexit__.assert_awaited_once()
    assert issubclass(factory.return_value.__aexit__.await_args.args[0], ValueError)


def test_remote_tool_error_has_detail_and_closes(remote_client):
    factory, client = remote_client
    client.call_tool.return_value = CallToolResult(
        isError=True, content=[{"type": "text", "text": "incident unavailable"}]
    )
    with pytest.raises(RuntimeError, match="get_logs failed: incident unavailable"):
        execute_mcp_tool(ToolName.LOGS, "INC-001")
    factory.return_value.__aexit__.assert_awaited_once()


@pytest.mark.parametrize(
    "error",
    [
        ConnectionError("connection failed"),
        TimeoutError("timed out"),
        MCPError(-32600, "protocol failure"),
    ],
)
def test_remote_failure_preserves_exception_and_cause(remote_client, error):
    factory, client = remote_client
    cause = OSError("underlying failure")
    error.__cause__ = cause
    client.call_tool.side_effect = error
    with pytest.raises(type(error)) as raised:
        execute_mcp_tool(ToolName.LOGS, "INC-001")
    assert raised.value is error
    assert raised.value.__cause__ is cause
    factory.return_value.__aexit__.assert_awaited_once()


def test_remote_connection_entry_failure_propagates(remote_client):
    factory, client = remote_client
    error = ConnectionError("cannot connect")
    factory.return_value.__aenter__.side_effect = error
    with pytest.raises(ConnectionError) as raised:
        execute_mcp_tool(ToolName.LOGS, "INC-001")
    assert raised.value is error
    client.call_tool.assert_not_awaited()
    # SDK __aenter__ owns cleanup when entering fails; Python does not call __aexit__.
    factory.return_value.__aexit__.assert_not_awaited()


@patch.object(mcp, "call_tool", new_callable=AsyncMock)
def test_in_process_retains_missing_content_behavior(mock_call_tool):
    mock_call_tool.return_value = CallToolResult(content=[])
    assert execute_mcp_tool(ToolName.LOGS, "INC-001") == []
