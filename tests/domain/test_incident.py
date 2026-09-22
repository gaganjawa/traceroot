from datetime import UTC, datetime

from traceroot.domain.incident import Incident


def test_incident_creation_with_suspected_services():

    incident = Incident(
        id="INC-001",
        title="Database Connection Pool Exhaustion",
        description="The checkout service is experiencing timeouts due to database connection pool exhaustion.",
        start_time=datetime(2026, 9, 20, 14, 30, tzinfo=UTC),
        suspected_services=["checkout-service", "database-service"],
    )

    assert incident.id == "INC-001"
    assert incident.title == "Database Connection Pool Exhaustion"
    assert incident.suspected_services == ["checkout-service", "database-service"]


def test_incident_creation_without_suspected_services():
    incident = Incident(
        id="INC-002",
        title="API Gateway Latency Spike",
        description="The API gateway is experiencing increased latency.",
        start_time=datetime(2026, 9, 21, 10, 15, tzinfo=UTC),
    )

    assert incident.id == "INC-002"
    assert incident.title == "API Gateway Latency Spike"
    assert incident.suspected_services == []
