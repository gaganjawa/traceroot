from traceroot.data.models import CodeChangeEntry
from traceroot.tools.changes import query_code_changes


def test_query_code_changes_returns_all_incident_changes():
    changes = query_code_changes(incident_id="INC-001")
    assert len(changes) > 0  # Ensure that some code changes are returned
    for change in changes:
        assert isinstance(change, CodeChangeEntry)


def test_query_code_changes_filters_by_service():
    changes = query_code_changes(incident_id="INC-001", service="checkout-service")
    assert len(changes) > 0  # Ensure that some code changes are returned
    assert all(change.service == "checkout-service" for change in changes)


def test_query_code_changes_returns_empty_list_when_no_changes_match():
    changes = query_code_changes(incident_id="INC-001", service="non-existent-service")
    assert (
        len(changes) == 0
    )  # Ensure an empty list is returned when no code changes match


def test_query_code_changes_returns_typed_change_entries():
    changes = query_code_changes(incident_id="INC-001")
    for change in changes:
        assert isinstance(change, CodeChangeEntry)


def test_query_code_changes_preserves_evidence_ids():
    changes = query_code_changes(incident_id="INC-001")
    change_ids = {change.id for change in changes}
    assert "CHANGE-001-01" in change_ids


def test_query_code_changes_preserves_change_data():
    changes = query_code_changes(incident_id="INC-001")
    change = changes[0]
    assert change.service == "checkout-service"
    assert change.id == "CHANGE-001-01"


def test_query_code_changes_does_not_return_changes_from_other_incidents():
    inc_001 = query_code_changes(incident_id="INC-001")
    inc_002 = query_code_changes(incident_id="INC-002")

    ids_001 = {change.id for change in inc_001}
    ids_002 = {change.id for change in inc_002}

    assert ids_001
    assert ids_002
    assert ids_001.isdisjoint(ids_002)
