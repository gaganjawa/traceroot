from enum import StrEnum

from traceroot.tools.changes import query_code_changes
from traceroot.tools.deployments import query_deployments
from traceroot.tools.logs import query_logs
from traceroot.tools.metrics import query_metrics


class ToolName(StrEnum):
    LOGS = "logs"
    METRICS = "metrics"
    DEPLOYMENTS = "deployments"
    CODE_CHANGES = "code_changes"


def execute_tool(
    tool_name: ToolName,
    incident_id: str,
    service: str | None = None,
) -> list:
    if tool_name is None:
        raise ValueError(f"Unknown tool name: {tool_name}")
    if tool_name == ToolName.LOGS:
        return query_logs(incident_id=incident_id, service=service)
    elif tool_name == ToolName.METRICS:
        return query_metrics(incident_id=incident_id, service=service)
    elif tool_name == ToolName.DEPLOYMENTS:
        return query_deployments(incident_id=incident_id, service=service)
    elif tool_name == ToolName.CODE_CHANGES:
        return query_code_changes(incident_id=incident_id, service=service)
    else:
        raise ValueError(f"Unknown tool name: {tool_name}")
