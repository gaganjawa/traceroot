from traceroot.domain.ground_truth import GroundTruth

def test_create_ground_truth_with_evidence_ids():
    ground_truth = GroundTruth(
        incident_id="INC-001",
        root_cause="Database Connection Pool Exhaustion",
        root_cause_category="Database",
        affected_service="checkout-service",
        supporting_evidence_ids=["EV-001", "EV-002"],
    )
    assert ground_truth.incident_id == "INC-001"
    assert ground_truth.root_cause == "Database Connection Pool Exhaustion"
    assert ground_truth.root_cause_category == "Database"
    assert ground_truth.affected_service == "checkout-service"
    assert ground_truth.supporting_evidence_ids == ["EV-001", "EV-002"]

def test_create_ground_truth_without_evidence_ids():
    ground_truth = GroundTruth(
        incident_id="INC-002",
        root_cause="API Gateway Latency Spike",
        root_cause_category="API",
        affected_service="api-gateway-service",
    )
    assert ground_truth.incident_id == "INC-002"
    assert ground_truth.root_cause == "API Gateway Latency Spike"
    assert ground_truth.root_cause_category == "API"
    assert ground_truth.affected_service == "api-gateway-service"
    assert ground_truth.supporting_evidence_ids == []