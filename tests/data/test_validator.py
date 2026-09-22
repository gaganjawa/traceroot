from datetime import UTC, datetime

from traceroot.data.models import (
    CodeChangeEntry,
    DeploymentEntry,
    IncidentDataset,
    LogEntry,
    MetricEntry,
)
from traceroot.data.validator import validate_incident_dataset
from traceroot.domain.ground_truth import GroundTruth
from traceroot.domain.incident import Incident


def create_valid_dataset() -> tuple[IncidentDataset, GroundTruth]:
    timestamp = datetime(2026, 9, 20, 10, 0, tzinfo=UTC)

    incident = Incident(
        id="INC-TEST",
        title="Test incident",
        description="Test service is experiencing elevated latency.",
        start_time=timestamp,
        suspected_services=["test-service"],
    )

    log = LogEntry(
        id="LOG-TEST-01",
        timestamp=timestamp,
        service="test-service",
        level="ERROR",
        message="Request timed out.",
    )

    metric = MetricEntry(
        id="METRIC-TEST-01",
        timestamp=timestamp,
        service="test-service",
        metric="request_latency",
        value=2500.0,
        unit="ms",
    )

    deployment = DeploymentEntry(
        id="DEPLOY-TEST-01",
        timestamp=timestamp,
        service="test-service",
        version="v1.0.1",
        description="Test deployment",
    )

    change = CodeChangeEntry(
        id="CHANGE-TEST-01",
        timestamp=timestamp,
        service="test-service",
        commit_sha="abc123",
        files=["config.yaml"],
        description="Test configuration change",
        diff="- timeout: 5000\n+ timeout: 1000",
    )

    dataset = IncidentDataset(
        incident=incident,
        logs=[log],
        metrics=[metric],
        deployments=[deployment],
        changes=[change],
    )

    ground_truth = GroundTruth(
        incident_id="INC-TEST",
        root_cause="A configuration change reduced the request timeout.",
        root_cause_category="configuration_regression",
        affected_service="test-service",
        supporting_evidence_ids=[
            "LOG-TEST-01",
            "CHANGE-TEST-01",
        ],
    )

    return dataset, ground_truth


def test_valid_dataset_returns_no_errors():
    dataset, ground_truth = create_valid_dataset()

    errors = validate_incident_dataset(dataset, ground_truth)
    assert errors == []


def test_incident_id_mismatch_returns_error():
    dataset, ground_truth = create_valid_dataset()
    ground_truth.incident_id = "INC-OTHER"

    errors = validate_incident_dataset(dataset, ground_truth)
    assert "Incident ID mismatch" in errors[0]


def test_missing_supporting_evidence_returns_error():
    dataset, ground_truth = create_valid_dataset()
    ground_truth.supporting_evidence_ids.append(
        "LOG-TEST-02"
    )  # Non-existent evidence ID

    errors = validate_incident_dataset(dataset, ground_truth)
    assert "Supporting evidence ID LOG-TEST-02 not found" in errors[0]


def test_duplicate_evidence_id_returns_error():
    dataset, ground_truth = create_valid_dataset()
    # Add a duplicate log entry with the same ID
    duplicate_log = LogEntry(
        id="LOG-TEST-01",  # Same ID as existing log
        timestamp=datetime(2026, 9, 20, 10, 5, tzinfo=UTC),
        service="test-service",
        level="ERROR",
        message="Another request timed out.",
    )
    dataset.logs.append(duplicate_log)

    errors = validate_incident_dataset(dataset, ground_truth)
    assert "Evidence IDs are not unique." in errors[0]
