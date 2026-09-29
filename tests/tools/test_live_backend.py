from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

from traceroot.data.models import MetricEntry
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
        metrics_provider=Mock(),
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
        metrics_provider=Mock(),
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
        metrics_provider=Mock(),
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
        metrics_provider=Mock(),
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


@pytest.mark.parametrize("tool_name", [ToolName.DEPLOYMENTS, ToolName.CODE_CHANGES])
def test_live_backend_rejects_unconfigured_provider(tool_name):
    registry = RuntimeIncidentRegistry()
    incident = make_incident()
    registry.register(incident)

    backend = LiveEvidenceBackend(
        incident_registry=registry,
        logs_provider=Mock(),
        metrics_provider=Mock(),
    )

    with pytest.raises(
        NotImplementedError,
        match=f"tool={tool_name.value}",
    ):
        backend.query(
            tool_name=tool_name,
            incident_id=incident.id,
        )


@pytest.fixture
def metrics_backend():
    registry = RuntimeIncidentRegistry()
    incident = make_incident()
    registry.register(incident)
    metrics_provider = Mock()
    metrics_provider.query.return_value = []
    backend = LiveEvidenceBackend(registry, Mock(), metrics_provider)
    return backend, incident, metrics_provider


def test_live_backend_delegates_metrics_to_provider(metrics_backend):
    backend, incident, provider = metrics_backend
    backend.query(ToolName.METRICS, incident.id)
    provider.query.assert_called_once_with(incident=incident, service=None)
    backend.logs_provider.query.assert_not_called()


def test_live_backend_passes_resolved_incident_to_metrics_provider(metrics_backend):
    backend, incident, provider = metrics_backend
    backend.query(ToolName.METRICS, incident.id)
    assert provider.query.call_args.kwargs["incident"] is incident


def test_live_backend_passes_service_to_metrics_provider(metrics_backend):
    backend, incident, provider = metrics_backend
    backend.query(ToolName.METRICS, incident.id, service="payment-service")
    provider.query.assert_called_once_with(incident=incident, service="payment-service")


def test_live_backend_returns_metrics_provider_results(metrics_backend):
    backend, incident, provider = metrics_backend
    provider.query.return_value = [
        MetricEntry(
            id="METRIC-LIVE-123",
            timestamp=incident.start_time,
            service="checkout-service",
            metric="latency",
            value=0.5,
            unit="seconds",
        )
    ]
    assert backend.query(ToolName.METRICS, incident.id) is provider.query.return_value


def test_live_backend_resolves_incident_before_metrics_delegation(metrics_backend):
    backend, _, provider = metrics_backend
    with pytest.raises(ValueError, match="Runtime incident not found"):
        backend.query(ToolName.METRICS, "missing")
    provider.query.assert_not_called()
