from datetime import UTC, datetime

import pytest

from traceroot.domain.incident import Incident
from traceroot.intake.service import create_incident

START_TIME = datetime(2026, 9, 27, 12, 0, tzinfo=UTC)


def test_create_incident_returns_domain_incident():
    incident = create_incident(
        title="Checkout failures",
        description="Checkout requests are failing.",
        start_time=START_TIME,
    )

    assert isinstance(incident, Incident)


def test_create_incident_generates_id_when_missing():
    incident = create_incident(
        title="Checkout failures",
        description="Checkout requests are failing.",
        start_time=START_TIME,
    )

    assert incident.id.startswith("INC-RUNTIME-")
    assert len(incident.id) > len("INC-RUNTIME-")


def test_create_incident_preserves_supplied_id():
    incident = create_incident(
        title="Checkout failures",
        description="Checkout requests are failing.",
        start_time=START_TIME,
        incident_id="INC-LIVE-001",
    )

    assert incident.id == "INC-LIVE-001"


def test_create_incident_preserves_fields():
    incident = create_incident(
        title="Checkout failures",
        description="Checkout requests are failing.",
        start_time=START_TIME,
    )

    assert incident.title == "Checkout failures"
    assert incident.description == "Checkout requests are failing."
    assert incident.start_time == START_TIME


def test_create_incident_preserves_suspected_services():
    incident = create_incident(
        title="Checkout failures",
        description="Checkout requests are failing.",
        start_time=START_TIME,
        suspected_services=[
            "checkout-service",
            "payment-service",
        ],
    )

    assert incident.suspected_services == [
        "checkout-service",
        "payment-service",
    ]


def test_create_incident_handles_missing_suspected_services():
    incident = create_incident(
        title="Checkout failures",
        description="Checkout requests are failing.",
        start_time=START_TIME,
    )

    assert incident.suspected_services == []


def test_create_incident_rejects_blank_title():
    with pytest.raises(ValueError, match="title is required"):
        create_incident(
            title="   ",
            description="Checkout requests are failing.",
            start_time=START_TIME,
        )


def test_create_incident_rejects_blank_description():
    with pytest.raises(ValueError, match="description is required"):
        create_incident(
            title="Checkout failures",
            description="   ",
            start_time=START_TIME,
        )


def test_create_incident_rejects_blank_service():
    with pytest.raises(
        ValueError,
        match="suspected_services cannot contain blank values",
    ):
        create_incident(
            title="Checkout failures",
            description="Checkout requests are failing.",
            start_time=START_TIME,
            suspected_services=["checkout-service", "   "],
        )


def test_create_incident_rejects_blank_incident_id():
    with pytest.raises(
        ValueError,
        match="incident_id cannot be blank",
    ):
        create_incident(
            title="Checkout failures",
            description="Checkout requests are failing.",
            start_time=START_TIME,
            incident_id="   ",
        )


def test_create_incident_strips_supplied_incident_id():
    incident = create_incident(
        title="Checkout failures",
        description="Checkout requests are failing.",
        start_time=START_TIME,
        incident_id="  INC-LIVE-001  ",
    )

    assert incident.id == "INC-LIVE-001"


def test_create_incident_strips_title_and_description():
    incident = create_incident(
        title="  Checkout failures  ",
        description="  Checkout requests are failing.  ",
        start_time=START_TIME,
    )

    assert incident.title == "Checkout failures"
    assert incident.description == "Checkout requests are failing."
