from traceroot.tools.backend import EvidenceBackend, FixtureEvidenceBackend
from traceroot.tools.models import ToolName

_default_backend: EvidenceBackend = FixtureEvidenceBackend()


def configure_backend(backend: EvidenceBackend) -> None:
    global _default_backend
    _default_backend = backend


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
