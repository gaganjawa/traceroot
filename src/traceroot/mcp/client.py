import asyncio
import math
import os
from urllib.parse import urlsplit

from mcp.client import Client
from mcp.types import CallToolResult
from pydantic import BaseModel, HttpUrl, TypeAdapter

from traceroot.data.models import (
    CodeChangeEntry,
    DeploymentEntry,
    LogEntry,
    MetricEntry,
)
from traceroot.mcp.server import mcp
from traceroot.tools.interface import ToolName

MCPToolResult = LogEntry | MetricEntry | DeploymentEntry | CodeChangeEntry

MCP_TOOL_NAMES = {
    ToolName.LOGS: "get_logs",
    ToolName.METRICS: "get_metrics",
    ToolName.DEPLOYMENTS: "get_deployments",
    ToolName.CODE_CHANGES: "get_code_changes",
}

MCP_RESULT_MODELS: dict[ToolName, type[BaseModel]] = {
    ToolName.LOGS: LogEntry,
    ToolName.METRICS: MetricEntry,
    ToolName.DEPLOYMENTS: DeploymentEntry,
    ToolName.CODE_CHANGES: CodeChangeEntry,
}


def _transport_config() -> tuple[str, str | None, float]:
    transport = os.getenv("TRACEROOT_MCP_TRANSPORT", "in-process")
    if transport not in {"in-process", "streamable-http"}:
        raise ValueError("Invalid TRACEROOT_MCP_TRANSPORT")
    try:
        timeout = float(os.getenv("TRACEROOT_MCP_TIMEOUT_SECONDS", "30"))
    except ValueError as exc:
        raise ValueError(
            "TRACEROOT_MCP_TIMEOUT_SECONDS must be positive and finite"
        ) from exc
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("TRACEROOT_MCP_TIMEOUT_SECONDS must be positive and finite")
    url = os.getenv("TRACEROOT_MCP_SERVER_URL")
    if transport == "streamable-http":
        if not url:
            raise ValueError("TRACEROOT_MCP_SERVER_URL is required")
        try:
            TypeAdapter(HttpUrl).validate_python(url, strict=True)
            parsed = urlsplit(url)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or any(character.isspace() for character in url)
            ):
                raise ValueError("Invalid URL")
        except ValueError as exc:
            raise ValueError(
                "TRACEROOT_MCP_SERVER_URL must be a valid http/https URL"
            ) from exc
    return transport, url, timeout


def _parse_result(
    tool_name: ToolName, result: CallToolResult, *, strict: bool = False
) -> list[BaseModel]:
    if result.is_error:
        if strict:
            detail = "; ".join(
                item.text for item in result.content if item.type == "text"
            )
            raise RuntimeError(
                f"MCP tool {MCP_TOOL_NAMES[tool_name]} failed: {detail or 'remote tool error'}"
            )
        raise RuntimeError(f"MCP tool {MCP_TOOL_NAMES[tool_name]} failed")

    if strict and (
        result.structured_content is None
        or not isinstance(result.structured_content.get("result"), list)
    ):
        raise ValueError(
            f"MCP tool {MCP_TOOL_NAMES[tool_name]} returned invalid structured content: "
            "expected a result list"
        )
    structured_content = result.structured_content or {}
    entries = structured_content.get("result", [])
    model = MCP_RESULT_MODELS[tool_name]

    return [model.model_validate(entry) for entry in entries]


async def _execute_remote(
    url: str, timeout: float, tool_name: ToolName, arguments: dict
) -> list[BaseModel]:
    # Live registry/configuration belongs to the server process; it is not transferred.
    async with Client(url, read_timeout_seconds=timeout) as client:
        result = await client.call_tool(MCP_TOOL_NAMES[tool_name], arguments)
        return _parse_result(tool_name, result, strict=True)


def execute_mcp_tool(
    tool_name: ToolName,
    incident_id: str,
    service: str | None = None,
) -> list[BaseModel]:
    transport, url, timeout = _transport_config()
    arguments = {"incident_id": incident_id, "service": service}
    if transport == "streamable-http":
        assert url is not None
        return asyncio.run(_execute_remote(url, timeout, tool_name, arguments))
    result = asyncio.run(mcp.call_tool(MCP_TOOL_NAMES[tool_name], arguments))
    return _parse_result(tool_name, result)
