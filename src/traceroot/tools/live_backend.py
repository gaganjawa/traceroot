from traceroot.intake.registry import RuntimeIncidentRegistry
from traceroot.integrations.live_logs import LokiLogsProvider
from traceroot.integrations.live_metrics import PrometheusMetricsProvider
from traceroot.tools.backend import EvidenceEntry
from traceroot.tools.models import ToolName


class LiveEvidenceBackend:
    def __init__(
        self,
        incident_registry: RuntimeIncidentRegistry,
        logs_provider: LokiLogsProvider,
        metrics_provider: PrometheusMetricsProvider,
    ):
        self.incident_registry = incident_registry
        self.logs_provider = logs_provider
        self.metrics_provider = metrics_provider

    def query(
        self,
        tool_name: ToolName,
        incident_id: str,
        service: str | None = None,
    ) -> list[EvidenceEntry]:
        if tool_name not in ToolName:
            raise ValueError(f"Unknown tool name: {tool_name}")

        incident = self.incident_registry.get(incident_id)

        if tool_name == ToolName.LOGS:
            return self.logs_provider.query(
                incident=incident,
                service=service,
            )

        if tool_name == ToolName.METRICS:
            return self.metrics_provider.query(
                incident=incident,
                service=service,
            )

        raise NotImplementedError(
            f"Live evidence provider is not configured for "
            f"tool={tool_name.value}, "
            f"incident={incident.id}, "
            f"service={service}"
        )
