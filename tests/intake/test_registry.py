from datetime import UTC, datetime

import pytest

from traceroot.domain.incident import Incident
from traceroot.intake.registry import RuntimeIncidentRegistry


def make_incident(
    incident_id: str = "INC-RUNTIME-001",
    title: str = "Checkout failures",
) -> Incident:
    return Incident(
        id=incident_id,
        title=title,
        description="Checkout requests are failing.",
        start_time=datetime(2026, 9, 29, 12, 0, tzinfo=UTC),
        suspected_services=["checkout-service"],
    )


def test_registry_registers_incident():
    registry = RuntimeIncidentRegistry()
    incident = make_incident()

    registry.register(incident)

    assert registry.get(incident.id) == incident


def test_registry_returns_registered_incident():
    registry = RuntimeIncidentRegistry()
    incident = make_incident()

    registry.register(incident)

    result = registry.get("INC-RUNTIME-001")

    assert result is incident


def test_registry_rejects_unknown_incident():
    registry = RuntimeIncidentRegistry()

    with pytest.raises(
        ValueError,
        match="Runtime incident not found: INC-RUNTIME-404",
    ):
        registry.get("INC-RUNTIME-404")


def test_registry_replaces_existing_incident():
    registry = RuntimeIncidentRegistry()

    first = make_incident(title="Original title")
    replacement = make_incident(title="Updated title")

    registry.register(first)
    registry.register(replacement)

    result = registry.get("INC-RUNTIME-001")

    assert result is replacement
    assert result.title == "Updated title"
