import json
from datetime import UTC, datetime

import pytest

from traceroot.data.models import (
    CodeChangeEntry,
    DeploymentEntry,
    LogEntry,
    MetricEntry,
)


def test_create_log_entry():
    log_entry = LogEntry(
        id="LOG-001",
        timestamp=datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC),
        service="checkout-service",
        level="INFO",
        message="User logged in successfully.",
    )

    assert log_entry.id == "LOG-001"
    assert log_entry.timestamp.isoformat() == "2023-01-01T12:00:00+00:00"
    assert log_entry.service == "checkout-service"
    assert log_entry.level == "INFO"
    assert log_entry.message == "User logged in successfully."


def test_create_metric_entry():
    metric = MetricEntry(
        id="METRIC-001",
        timestamp=datetime(2026, 9, 20, 12, 0, 0, tzinfo=UTC),
        service="checkout-service",
        metric="http_request_duration_p95",
        value=1840.0,
        unit="ms",
    )

    assert metric.id == "METRIC-001"
    assert metric.service == "checkout-service"
    assert metric.metric == "http_request_duration_p95"
    assert metric.value == 1840.0
    assert metric.unit == "ms"
    assert isinstance(metric.timestamp, datetime)


def test_create_deployment_entry():
    deployment_entry = DeploymentEntry(
        id="DEPLOY-001",
        timestamp=datetime(2026, 9, 20, 14, 20, 0, tzinfo=UTC),
        service="checkout-service",
        version="v2.4.1",
        description="Checkout service production deployment",
    )

    assert deployment_entry.id == "DEPLOY-001"
    assert deployment_entry.timestamp.isoformat() == "2026-09-20T14:20:00+00:00"
    assert deployment_entry.service == "checkout-service"
    assert deployment_entry.version == "v2.4.1"
    assert deployment_entry.description == "Checkout service production deployment"


def test_create_code_change_entry():
    code_change_entry = CodeChangeEntry(
        id="CHANGE-001",
        timestamp=datetime(2026, 9, 20, 13, 45, 0, tzinfo=UTC),
        service="checkout-service",
        commit_sha="a1b2c3d",
        files=[
            "src/database.py",
            "config/application.yaml",
        ],
        description="Updated database connection pool configuration",
        diff="- maximumPoolSize: 100\n+ maximumPoolSize: 20",
    )

    assert code_change_entry.id == "CHANGE-001"
    assert code_change_entry.timestamp.isoformat() == "2026-09-20T13:45:00+00:00"
    assert code_change_entry.service == "checkout-service"
    assert code_change_entry.commit_sha == "a1b2c3d"
    assert code_change_entry.files == ["src/database.py", "config/application.yaml"]
    assert (
        code_change_entry.description
        == "Updated database connection pool configuration"
    )
    assert code_change_entry.diff == "- maximumPoolSize: 100\n+ maximumPoolSize: 20"


@pytest.fixture(params=[LogEntry, MetricEntry], ids=["log", "metric"])
def historical_evidence(request):
    fields = {
        "id": "LOG-001" if request.param is LogEntry else "METRIC-001",
        "timestamp": "2026-09-20T12:00:00Z",
        "service": "checkout-service",
    }
    if request.param is LogEntry:
        fields.update(level="INFO", message="Request complete")
    else:
        fields.update(metric="request_duration", value=0.125, unit="seconds")
    return request.param, fields


def test_evidence_labels_default_to_independent_empty_dicts(historical_evidence):
    model, fields = historical_evidence
    first, second = model(**fields), model(**fields)
    assert first.labels == second.labels == {}
    assert first.labels is not second.labels
    first.labels["instance"] = "a"
    assert second.labels == {}


def test_historical_evidence_json_loads_without_provenance_fields(historical_evidence):
    model, fields = historical_evidence
    entry = model.model_validate_json(json.dumps(fields))
    assert entry.labels == {}
    assert entry.model_dump(mode="json", exclude={"labels"}) == fields
    assert set(model.model_fields) == set(fields) | {"labels"}


def test_evidence_labels_round_trip_through_json(historical_evidence):
    model, fields = historical_evidence
    labels = {"instance": "a", "route": "/café", "empty": ""}
    entry = model(**fields, labels=labels)
    encoded = entry.model_dump_json()
    assert json.loads(encoded)["labels"] == labels
    assert model.model_validate_json(encoded) == entry
    assert "labels=" in str(entry)
    assert "/café" in str(entry)
