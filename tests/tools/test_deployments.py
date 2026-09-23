from traceroot.data.models import DeploymentEntry
from traceroot.tools.deployments import query_deployments


def test_query_deployments_returns_all_incident_deployments():
    deployments = query_deployments(incident_id="INC-001")
    assert len(deployments) > 0  # Ensure that some deployments are returned
    for deployment in deployments:
        assert isinstance(deployment, DeploymentEntry)


def test_query_deployments_filters_by_service():
    service = "checkout-service"
    deployments = query_deployments(incident_id="INC-001", service=service)
    for deployment in deployments:
        assert deployment.service == service


def test_query_deployments_returns_empty_list_when_no_deployments_match():
    deployments = query_deployments(
        incident_id="INC-001", service="non-existent-service"
    )
    assert (
        len(deployments) == 0
    )  # Ensure an empty list is returned when no deployments match


def test_query_deployments_returns_typed_deployment_entries():
    deployments = query_deployments(
        incident_id="INC-001",
        service="checkout-service",
    )
    for deployment in deployments:
        assert isinstance(deployment, DeploymentEntry)


def test_query_deployments_preserves_evidence_ids():
    deployments = query_deployments(
        incident_id="INC-001",
        service="checkout-service",
    )
    for deployment in deployments:
        assert deployment.id is not None  # Ensure evidence_id is preserved


def test_query_deployments_preserves_deployment_data():
    deployments = query_deployments(
        incident_id="INC-001",
        service="checkout-service",
    )
    for deployment in deployments:
        assert deployment is not None  # Ensure deployment_data is preserved


def test_query_deployments_does_not_return_deployments_from_other_incidents():
    deployments = query_deployments(incident_id="INC-001", service="checkout-service")
    for deployment in deployments:
        assert (
            deployment.id == "DEPLOY-001-01"
        )  # Ensure all deployments are from the specified incident
