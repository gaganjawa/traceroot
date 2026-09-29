from traceroot.tools.backend import FixtureEvidenceBackend
from traceroot.tools.models import ToolName

_default_backend = FixtureEvidenceBackend()


def execute_tool(
    tool_name: ToolName,
    incident_id: str,
    service: str | None = None,
) -> list:
    if tool_name is None:
        raise ValueError(f"Unknown tool name: {tool_name}")

    return _default_backend.query(
        tool_name=tool_name,
        incident_id=incident_id,
        service=service,
    )
