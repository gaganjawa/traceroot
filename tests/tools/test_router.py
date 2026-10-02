from unittest.mock import Mock

import pytest

from traceroot.intake.registry import RuntimeIncidentRegistry
from traceroot.tools.backend import EvidenceBackend
from traceroot.tools.models import ToolName
from traceroot.tools.router import EvidenceBackendRouter


@pytest.fixture
def fixture_backend():
    return Mock(spec=EvidenceBackend)


@pytest.fixture
def live_backend():
    return Mock(spec=EvidenceBackend)


@pytest.fixture
def incident_registry():
    return RuntimeIncidentRegistry()


def test_router_uses_fixture_backend_for_unregistered_incident(
    fixture_backend,
    live_backend,
    incident_registry,
):
    fixture_backend.query.return_value = ["log1"]

    router = EvidenceBackendRouter(
        fixture_backend=fixture_backend,
        live_backend=live_backend,
        incident_registry=incident_registry,
    )

    incident_id = "INC-001"
    tool_name = ToolName.LOGS
    service = "checkout-service"

    result = router.query(tool_name=tool_name, incident_id=incident_id, service=service)

    fixture_backend.query.assert_called_once_with(
        tool_name=tool_name,
        incident_id=incident_id,
        service=service,
    )
    live_backend.query.assert_not_called()

    assert result == ["log1"]


def test_router_uses_live_backend_for_registered_incident(
    fixture_backend,
    live_backend,
    incident_registry,
):

    live_backend.query.return_value = ["log2"]

    router = EvidenceBackendRouter(
        fixture_backend=fixture_backend,
        live_backend=live_backend,
        incident_registry=incident_registry,
    )

    incident_id = "INC-002"
    tool_name = ToolName.LOGS
    service = "checkout-service"

    incident = Mock()
    incident.id = incident_id
    incident_registry.register(incident)

    result = router.query(tool_name=tool_name, incident_id=incident_id, service=service)

    live_backend.query.assert_called_once_with(
        tool_name=tool_name,
        incident_id=incident_id,
        service=service,
    )
    fixture_backend.query.assert_not_called()

    assert result == ["log2"]


def test_router_passes_tool_name(
    fixture_backend,
    live_backend,
    incident_registry,
):
    fixture_backend.query.return_value = []

    router = EvidenceBackendRouter(
        fixture_backend=fixture_backend,
        live_backend=live_backend,
        incident_registry=incident_registry,
    )

    router.query(
        tool_name=ToolName.METRICS,
        incident_id="INC-001",
        service="checkout-service",
    )

    fixture_backend.query.assert_called_once_with(
        tool_name=ToolName.METRICS,
        incident_id="INC-001",
        service="checkout-service",
    )


def test_router_passes_incident_id(
    fixture_backend,
    live_backend,
    incident_registry,
):
    fixture_backend.query.return_value = []

    router = EvidenceBackendRouter(
        fixture_backend=fixture_backend,
        live_backend=live_backend,
        incident_registry=incident_registry,
    )

    router.query(
        tool_name=ToolName.LOGS,
        incident_id="INC-123",
        service="checkout-service",
    )

    fixture_backend.query.assert_called_once_with(
        tool_name=ToolName.LOGS,
        incident_id="INC-123",
        service="checkout-service",
    )


def test_router_passes_service(
    fixture_backend,
    live_backend,
    incident_registry,
):
    fixture_backend.query.return_value = []

    router = EvidenceBackendRouter(
        fixture_backend=fixture_backend,
        live_backend=live_backend,
        incident_registry=incident_registry,
    )

    router.query(
        tool_name=ToolName.LOGS,
        incident_id="INC-001",
        service="payment-service",
    )

    fixture_backend.query.assert_called_once_with(
        tool_name=ToolName.LOGS,
        incident_id="INC-001",
        service="payment-service",
    )


def test_router_returns_fixture_results_unchanged(
    fixture_backend,
    live_backend,
    incident_registry,
):
    expected = ["evidence-1", "evidence-2"]
    fixture_backend.query.return_value = expected

    router = EvidenceBackendRouter(
        fixture_backend=fixture_backend,
        live_backend=live_backend,
        incident_registry=incident_registry,
    )

    result = router.query(
        tool_name=ToolName.LOGS,
        incident_id="INC-001",
        service="checkout-service",
    )

    assert result is expected


def test_router_returns_live_results_unchanged(
    fixture_backend,
    live_backend,
    incident_registry,
):
    expected = ["live-1", "live-2"]
    live_backend.query.return_value = expected

    incident = Mock()
    incident.id = "INC-002"
    incident_registry.register(incident)

    router = EvidenceBackendRouter(
        fixture_backend=fixture_backend,
        live_backend=live_backend,
        incident_registry=incident_registry,
    )

    result = router.query(
        tool_name=ToolName.LOGS,
        incident_id="INC-002",
        service="checkout-service",
    )

    assert result is expected


def test_router_preserves_fixture_backend_error(
    fixture_backend,
    live_backend,
    incident_registry,
):
    fixture_backend.query.side_effect = RuntimeError("fixture failed")

    router = EvidenceBackendRouter(
        fixture_backend=fixture_backend,
        live_backend=live_backend,
        incident_registry=incident_registry,
    )

    with pytest.raises(RuntimeError, match="fixture failed"):
        router.query(
            tool_name=ToolName.LOGS,
            incident_id="INC-001",
            service="checkout-service",
        )


def test_router_preserves_live_backend_error(
    fixture_backend,
    live_backend,
    incident_registry,
):
    live_backend.query.side_effect = RuntimeError("live failed")

    incident = Mock()
    incident.id = "INC-002"
    incident_registry.register(incident)

    router = EvidenceBackendRouter(
        fixture_backend=fixture_backend,
        live_backend=live_backend,
        incident_registry=incident_registry,
    )

    with pytest.raises(RuntimeError, match="live failed"):
        router.query(
            tool_name=ToolName.LOGS,
            incident_id="INC-002",
            service="checkout-service",
        )


def test_router_does_not_route_by_incident_id_prefix(
    fixture_backend,
    live_backend,
    incident_registry,
):
    fixture_backend.query.return_value = ["fixture"]
    live_backend.query.return_value = ["live"]

    registered_incident = Mock()
    registered_incident.id = "INC-123"
    incident_registry.register(registered_incident)

    router = EvidenceBackendRouter(
        fixture_backend=fixture_backend,
        live_backend=live_backend,
        incident_registry=incident_registry,
    )

    registered_result = router.query(
        tool_name=ToolName.LOGS,
        incident_id="INC-123",
        service="checkout-service",
    )

    unregistered_result = router.query(
        tool_name=ToolName.LOGS,
        incident_id="INC-RUNTIME-999",
        service="checkout-service",
    )

    assert registered_result == ["live"]
    assert unregistered_result == ["fixture"]
