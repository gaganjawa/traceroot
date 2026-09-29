from datetime import UTC, datetime

import pytest

from traceroot.domain.incident import Incident
from traceroot.intake.registry import RuntimeIncidentRegistry
from traceroot.tools.live_backend import LiveEvidenceBackend
from traceroot.tools.models import ToolName


def make_incident() -> Incident:
    return Incident(
        id="INC-RUNTIME-001",
        title="Checkout failures",
        description="Checkout requests are failing.",
        start_time=datetime(2026, 9, 29, 12, 0, tzinfo=UTC),
        suspected_services=["checkout-service"],
    )


def test_live_backend_resolves_runtime_incident():
    registry = RuntimeIncidentRegistry()
    incident = make_incident()
    registry.register(incident)

    backend = LiveEvidenceBackend(registry)

    with pytest.raises(
        NotImplementedError,
        match="incident=INC-RUNTIME-001",
    ):
        backend.query(
            tool_name=ToolName.LOGS,
            incident_id="INC-RUNTIME-001",
            service="checkout-service",
        )


def test_live_backend_rejects_unknown_incident():
    registry = RuntimeIncidentRegistry()
    backend = LiveEvidenceBackend(registry)

    with pytest.raises(
        ValueError,
        match="Runtime incident not found: INC-RUNTIME-404",
    ):
        backend.query(
            tool_name=ToolName.LOGS,
            incident_id="INC-RUNTIME-404",
            service="checkout-service",
        )


def test_live_backend_rejects_unknown_tool():
    registry = RuntimeIncidentRegistry()
    incident = make_incident()
    registry.register(incident)

    backend = LiveEvidenceBackend(registry)

    with pytest.raises(
        ValueError,
        match="Unknown tool name: unknown_tool",
    ):
        backend.query(
            tool_name="unknown_tool",  # type: ignore[arg-type]
            incident_id="INC-RUNTIME-001",
        )
