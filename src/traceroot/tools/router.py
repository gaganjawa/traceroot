from traceroot.intake.registry import RuntimeIncidentRegistry
from traceroot.tools.backend import EvidenceBackend, EvidenceEntry
from traceroot.tools.models import ToolName


class EvidenceBackendRouter:
    def __init__(
        self,
        fixture_backend: EvidenceBackend,
        live_backend: EvidenceBackend,
        incident_registry: RuntimeIncidentRegistry,
    ):
        self._fixture_backend = fixture_backend
        self._live_backend = live_backend
        self._incident_registry = incident_registry

    def query(
        self,
        tool_name: ToolName,
        incident_id: str,
        service: str | None = None,
    ) -> list[EvidenceEntry]:
        backend = (
            self._live_backend
            if self._incident_registry.contains(incident_id)
            else self._fixture_backend
        )

        return backend.query(
            tool_name=tool_name,
            incident_id=incident_id,
            service=service,
        )
