import pytest
from pydantic import ValidationError

from traceroot.domain.rca import RCAResult


def test_create_rca_result_with_evidence_ids():
    rca_result = RCAResult(
        incident_id="INC-001",
        root_cause="Database Connection Pool Exhaustion",
        affected_service="checkout-service",
        evidence_ids=["EV-001", "EV-002"],
        explanation="API Gateway Latency Spike",
        confidence=0.95,
    )
    assert rca_result.incident_id == "INC-001"
    assert rca_result.root_cause == "Database Connection Pool Exhaustion"
    assert rca_result.affected_service == "checkout-service"
    assert rca_result.evidence_ids == ["EV-001", "EV-002"]


def test_create_rca_result_with_empty_evidence_ids():
    rca_result = RCAResult(
        incident_id="INC-002",
        root_cause="API Gateway Latency Spike",
        affected_service="api-gateway-service",
        evidence_ids=[],
        explanation="API Gateway Latency Spike",
        confidence=0.95,
    )
    assert rca_result.incident_id == "INC-002"
    assert rca_result.root_cause == "API Gateway Latency Spike"
    assert rca_result.affected_service == "api-gateway-service"
    assert rca_result.evidence_ids == []


def test_create_rca_result_without_confidence_and_affected_service():
    rca_result = RCAResult(
        incident_id="INC-003",
        root_cause="Service Mesh Misconfiguration",
        explanation="The service mesh was misconfigured, leading to routing issues.",
    )
    assert rca_result.incident_id == "INC-003"
    assert rca_result.root_cause == "Service Mesh Misconfiguration"
    assert rca_result.affected_service is None
    assert rca_result.evidence_ids == []
    assert rca_result.confidence is None


def test_rca_rejects_invalid_confidence():
    with pytest.raises(ValidationError):
        RCAResult(
            incident_id="INC-001",
            root_cause="Database connection pool exhausted",
            explanation="Connection pool usage reached its configured maximum.",
            confidence=1.5,
        )
