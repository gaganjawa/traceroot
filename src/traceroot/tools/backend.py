from typing import Protocol

from traceroot.data.models import (
    CodeChangeEntry,
    DeploymentEntry,
    LogEntry,
    MetricEntry,
)
from traceroot.tools.changes import query_code_changes
from traceroot.tools.deployments import query_deployments
from traceroot.tools.logs import query_logs
from traceroot.tools.metrics import query_metrics
from traceroot.tools.models import ToolName

EvidenceEntry = LogEntry | MetricEntry | DeploymentEntry | CodeChangeEntry


class EvidenceBackend(Protocol):
    def query(
        self,
        tool_name: ToolName,
        incident_id: str,
        service: str | None = None,
    ) -> list[EvidenceEntry]: ...


class FixtureEvidenceBackend:
    def query(
        self,
        tool_name: ToolName,
        incident_id: str,
        service: str | None = None,
    ) -> list[EvidenceEntry]:
        if tool_name == ToolName.LOGS:
            return query_logs(
                incident_id=incident_id,
                service=service,
            )

        if tool_name == ToolName.METRICS:
            return query_metrics(
                incident_id=incident_id,
                service=service,
            )

        if tool_name == ToolName.DEPLOYMENTS:
            return query_deployments(
                incident_id=incident_id,
                service=service,
            )

        if tool_name == ToolName.CODE_CHANGES:
            return query_code_changes(
                incident_id=incident_id,
                service=service,
            )

        raise ValueError(f"Unknown tool name: {tool_name}")
