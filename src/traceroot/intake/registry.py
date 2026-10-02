from traceroot.domain.incident import Incident


class RuntimeIncidentRegistry:
    def __init__(self):
        self._incidents: dict[str, Incident] = {}

    def register(self, incident: Incident) -> None:
        self._incidents[incident.id] = incident

    def get(self, incident_id: str) -> Incident:
        try:
            return self._incidents[incident_id]
        except KeyError as exc:
            raise ValueError(f"Runtime incident not found: {incident_id}") from exc

    def contains(self, incident_id: str) -> bool:
        return incident_id in self._incidents
