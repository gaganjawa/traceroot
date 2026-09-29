from unittest.mock import patch

from traceroot.tools.backend import FixtureEvidenceBackend
from traceroot.tools.models import ToolName


@patch("traceroot.tools.backend.query_logs")
def test_fixture_backend_queries_logs(mock_query_logs):
    mock_query_logs.return_value = []

    backend = FixtureEvidenceBackend()

    result = backend.query(
        tool_name=ToolName.LOGS,
        incident_id="INC-001",
        service="checkout-service",
    )

    mock_query_logs.assert_called_once_with(
        incident_id="INC-001",
        service="checkout-service",
    )
    assert result == []


@patch("traceroot.tools.backend.query_code_changes")
def test_fixture_backend_queries_code_changes(mock_query_code_changes):
    mock_query_code_changes.return_value = []

    backend = FixtureEvidenceBackend()

    result = backend.query(
        tool_name=ToolName.CODE_CHANGES,
        incident_id="INC-001",
        service="checkout-service",
    )

    mock_query_code_changes.assert_called_once_with(
        incident_id="INC-001",
        service="checkout-service",
    )
    assert result == []


@patch("traceroot.tools.backend.query_metrics")
def test_fixture_backend_queries_metrics(mock_query_metrics):
    mock_query_metrics.return_value = []

    backend = FixtureEvidenceBackend()

    result = backend.query(
        tool_name=ToolName.METRICS,
        incident_id="INC-001",
        service="checkout-service",
    )

    mock_query_metrics.assert_called_once_with(
        incident_id="INC-001",
        service="checkout-service",
    )
    assert result == []


@patch("traceroot.tools.backend.query_deployments")
def test_fixture_backend_queries_deployments(mock_query_deployments):
    mock_query_deployments.return_value = []

    backend = FixtureEvidenceBackend()

    result = backend.query(
        tool_name=ToolName.DEPLOYMENTS,
        incident_id="INC-001",
        service="checkout-service",
    )

    mock_query_deployments.assert_called_once_with(
        incident_id="INC-001",
        service="checkout-service",
    )
    assert result == []
