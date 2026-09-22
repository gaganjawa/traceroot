from traceroot.data.models import IncidentDataset
from traceroot.domain.ground_truth import GroundTruth


def validate_incident_dataset(
    dataset: IncidentDataset,
    ground_truth: GroundTruth,
) -> list[str]:
    """
    Validate the incident dataset against the ground truth.

    Args:
        dataset (IncidentDataset): The incident dataset to validate.
        ground_truth (GroundTruth): The ground truth data to validate against.

    Returns:
        list[str]: A list of validation error messages, if any.
    """
    errors = []

    # Validate that all incidents in the dataset are present in the ground truth
    if dataset.incident.id != ground_truth.incident_id:
        errors.append(
            f"Incident ID mismatch: dataset has {dataset.incident.id}, "
            f"ground truth has {ground_truth.incident_id}"
        )
    # Validate every evidence ID is unique
    evidence_ids = [
        evidence.id
        for evidence in dataset.logs
        + dataset.metrics
        + dataset.deployments
        + dataset.changes
    ]
    if len(evidence_ids) != len(set(evidence_ids)):
        errors.append("Evidence IDs are not unique.")

    # Validate every ground_truth.supporting_evidence_id exists in the incident's operational evidence
    for evidence_id in ground_truth.supporting_evidence_ids:
        if evidence_id not in evidence_ids:
            errors.append(
                f"Supporting evidence ID {evidence_id} not found in the incident dataset."
            )

    # Validate ground_truth.affected_service is non-empty
    if not ground_truth.affected_service.strip():
        errors.append("Ground truth affected service is empty.")

    # Validate dataset contains:
    #     >= 1 log
    #     >= 1 metric
    #     >= 1 deployment
    #     >= 1 code change
    if len(dataset.logs) < 1:
        errors.append("Incident dataset must contain at least one log entry.")
    if len(dataset.metrics) < 1:
        errors.append("Incident dataset must contain at least one metric entry.")
    if len(dataset.deployments) < 1:
        errors.append("Incident dataset must contain at least one deployment entry.")
    if len(dataset.changes) < 1:
        errors.append("Incident dataset must contain at least one code change entry.")

    return errors
