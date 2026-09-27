from mcp.server import MCPServer
from pydantic import BaseModel

from traceroot.tools.interface import ToolName, execute_tool

mcp = MCPServer("TraceRoot Evidence Server")


def _validate_incident_id(incident_id: str) -> None:
    if not isinstance(incident_id, str) or not incident_id.strip():
        raise ValueError("incident_id is required")
    if incident_id != incident_id.strip() or "/" in incident_id or "\\" in incident_id:
        raise ValueError("incident_id is invalid")


def _serialize_entries(entries: list[BaseModel]) -> list[dict]:
    return [entry.model_dump(mode="json") for entry in entries]


def _get_evidence(
    tool_name: ToolName,
    incident_id: str,
    service: str | None,
) -> list[dict]:
    _validate_incident_id(incident_id)
    return _serialize_entries(
        execute_tool(tool_name, incident_id=incident_id, service=service)
    )


@mcp.tool()
def get_logs(
    incident_id: str,
    service: str | None = None,
) -> list[dict]:
    return _get_evidence(ToolName.LOGS, incident_id, service)


@mcp.tool()
def get_metrics(
    incident_id: str,
    service: str | None = None,
) -> list[dict]:
    return _get_evidence(ToolName.METRICS, incident_id, service)


@mcp.tool()
def get_deployments(
    incident_id: str,
    service: str | None = None,
) -> list[dict]:
    return _get_evidence(ToolName.DEPLOYMENTS, incident_id, service)


@mcp.tool()
def get_code_changes(
    incident_id: str,
    service: str | None = None,
) -> list[dict]:
    return _get_evidence(ToolName.CODE_CHANGES, incident_id, service)


if __name__ == "__main__":
    mcp.run()
