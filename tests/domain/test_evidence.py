from datetime import datetime

from traceroot.domain.evidence import Evidence, EvidenceType


def test_evidence_type_values():
    assert EvidenceType.LOG == "log"
    assert EvidenceType.GIT_CHANGE == "git_change"


def test_create_log_evidence():
    evidence = Evidence(
        id="EV-001",
        type=EvidenceType.LOG,
        source="checkout-service.log",
        content="Database connection acquisition timed out",
        service="checkout-service",
        timestamp=datetime(2026, 9, 20, 14, 23),
    )

    assert evidence.id == "EV-001"
    assert evidence.type == EvidenceType.LOG
    assert evidence.service == "checkout-service"


def test_evidence_allows_optional_fields():
    evidence = Evidence(
        id="EV-002",
        type=EvidenceType.KNOWLEDGE,
        source="runbooks/database-pool.md",
        content="Connection pool exhaustion can cause request timeouts.",
    )

    assert evidence.service is None
    assert evidence.timestamp is None