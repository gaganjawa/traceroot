from datetime import UTC, datetime
from unittest.mock import Mock

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

    logs_provider = Mock()
    logs_provider.query.return_value = []

    backend = LiveEvidenceBackend(
        incident_registry=registry,
        logs_provider=logs_provider,
    )

    result = backend.query(
        tool_name=ToolName.LOGS,
        incident_id="INC-RUNTIME-001",
        service="checkout-service",
    )

    logs_provider.query.assert_called_once_with(
        incident=incident,
        service="checkout-service",
    )

    assert result == []


def test_live_backend_rejects_unknown_incident():
    registry = RuntimeIncidentRegistry()
    backend = LiveEvidenceBackend(
        incident_registry=registry,
        logs_provider=Mock(),
    )

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

    backend = LiveEvidenceBackend(
        incident_registry=registry,
        logs_provider=Mock(),
    )

    with pytest.raises(
        ValueError,
        match="Unknown tool name: unknown_tool",
    ):
        backend.query(
            tool_name="unknown_tool",  # type: ignore[arg-type]
            incident_id="INC-RUNTIME-001",
        )


def test_live_backend_delegates_logs_to_provider():
    registry = RuntimeIncidentRegistry()
    incident = make_incident()
    registry.register(incident)

    logs_provider = Mock()
    logs_provider.query.return_value = []

    backend = LiveEvidenceBackend(
        incident_registry=registry,
        logs_provider=logs_provider,
    )

    result = backend.query(
        tool_name=ToolName.LOGS,
        incident_id=incident.id,
        service="checkout-service",
    )

    logs_provider.query.assert_called_once_with(
        incident=incident,
        service="checkout-service",
    )

    assert result == []


def test_live_backend_rejects_unconfigured_metrics_provider():
    registry = RuntimeIncidentRegistry()
    incident = make_incident()
    registry.register(incident)

    backend = LiveEvidenceBackend(
        incident_registry=registry,
        logs_provider=Mock(),
    )

    with pytest.raises(
        NotImplementedError,
        match="tool=metrics",
    ):
        backend.query(
            tool_name=ToolName.METRICS,
            incident_id=incident.id,
        )
