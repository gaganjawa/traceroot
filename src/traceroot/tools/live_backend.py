from traceroot.intake.registry import RuntimeIncidentRegistry
from traceroot.tools.backend import EvidenceEntry
from traceroot.tools.models import ToolName


class LiveEvidenceBackend:
    def __init__(
        self,
        incident_registry: RuntimeIncidentRegistry,
    ):
        self.incident_registry = incident_registry

    def query(
        self,
        tool_name: ToolName,
        incident_id: str,
        service: str | None = None,
    ) -> list[EvidenceEntry]:
        if tool_name not in ToolName:
            raise ValueError(f"Unknown tool name: {tool_name}")

        incident = self.incident_registry.get(incident_id)

        raise NotImplementedError(
            f"Live evidence provider is not configured for "
            f"tool={tool_name.value}, "
            f"incident={incident.id}, "
            f"service={service}"
        )
