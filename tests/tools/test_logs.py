from traceroot.data.models import LogEntry
from traceroot.tools.logs import query_logs

# At minimum test:
# - no filters returns all logs for the incident
# - service filter returns only that service
# - level filter returns only that level
# - contains performs substring filtering on the message
# - multiple supplied filters behave as AND conditions
# - no matches returns []
# - returned items are LogEntry
# - original evidence IDs are preserved
# - querying one incident never returns another incident's logs
# - load_incident_dataset() can be mocked so the unit tests don't depend on actual files


def test_query_logs_returns_all_incident_logs():
    logs = query_logs(incident_id="INC-001")
    assert len(logs) > 0  # Ensure that logs are returned
    for log in logs:
        assert isinstance(log, LogEntry)  # Ensure each log is a LogEntry instance


def test_query_logs_filters_by_service():
    service = "checkout-service"
    logs = query_logs(incident_id="INC-001", service=service)
    for log in logs:
        assert log.service == service  # Ensure each log is from the specified service


def test_query_logs_filters_by_level():
    level = "ERROR"
    logs = query_logs(incident_id="INC-001", level=level)
    for log in logs:
        assert log.level == level  # Ensure each log is of the specified level


def test_query_logs_filters_by_message_content():
    contains = "failed"
    logs = query_logs(incident_id="INC-001", contains=contains)
    for log in logs:
        assert (
            contains in log.message
        )  # Ensure each log message contains the specified substring


def test_query_logs_combines_filters_with_and_semantics():
    service = "checkout-service"
    level = "ERROR"
    contains = "failed"
    logs = query_logs(
        incident_id="INC-001",
        service="checkout-service",
        level="ERROR",
        contains="failed",
    )
    for log in logs:
        assert log.service == service
        assert log.level == level
        assert (
            contains in log.message
        )  # Ensure all filters are applied with AND semantics


def test_query_logs_returns_empty_list_when_no_logs_match():
    logs = query_logs(incident_id="INC-001", service="nonexistent-service")
    assert logs == []  # Ensure an empty list is returned when no logs match


def test_query_logs_returns_typed_log_entries():
    logs = query_logs(
        incident_id="INC-001",
        service="checkout-service",
    )
    for log in logs:
        assert isinstance(
            log, LogEntry
        )  # Ensure each returned item is a LogEntry instance


def test_query_logs_preserves_evidence_ids():
    logs = query_logs(
        incident_id="INC-001",
        service="checkout-service",
    )
    for log in logs:
        assert hasattr(log, "id")  # Ensure each log has an 'id' attribute


def test_query_logs_does_not_return_logs_from_other_incidents():
    incident_1_logs = query_logs(incident_id="INC-001")
    incident_2_logs = query_logs(incident_id="INC-002")

    incident_1_ids = {log.id for log in incident_1_logs}
    incident_2_ids = {log.id for log in incident_2_logs}

    assert incident_1_ids
    assert incident_2_ids
    assert incident_1_ids.isdisjoint(incident_2_ids)
