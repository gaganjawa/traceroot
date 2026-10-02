import asyncio

from pydantic import BaseModel

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


def execute_mcp_tool(
    tool_name: ToolName,
    incident_id: str,
    service: str | None = None,
) -> list[BaseModel]:
    result = asyncio.run(
        mcp.call_tool(
            MCP_TOOL_NAMES[tool_name],
            {
                "incident_id": incident_id,
                "service": service,
            },
        )
    )

    if result.is_error:
        raise RuntimeError(f"MCP tool {MCP_TOOL_NAMES[tool_name]} failed")

    structured_content = result.structured_content or {}
    entries = structured_content.get("result", [])
    model = MCP_RESULT_MODELS[tool_name]

    return [model.model_validate(entry) for entry in entries]
