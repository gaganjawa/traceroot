from pathlib import Path

import pytest

from traceroot.data.loader import load_incident_dataset
from traceroot.domain.ground_truth import GroundTruth

INCIDENTS_DIR = Path("data/incidents")
GROUND_TRUTH_DIR = Path("data/ground_truth")

FINAL_INCIDENT_IDS = [
    "INC-001",
    "INC-002",
    "INC-003",
    "INC-004",
    "INC-005",
    "INC-006",
]


def load_ground_truth(incident_id: str) -> GroundTruth:
    return GroundTruth.model_validate_json(
        (GROUND_TRUTH_DIR / f"{incident_id}.json").read_text()
    )


@pytest.mark.parametrize("incident_id", FINAL_INCIDENT_IDS)
def test_final_dataset_incident_loads_successfully(incident_id):
    dataset = load_incident_dataset(INCIDENTS_DIR / incident_id)

    assert dataset.incident.id == incident_id


@pytest.mark.parametrize("incident_id", FINAL_INCIDENT_IDS)
def test_final_dataset_ground_truth_loads_successfully(incident_id):
    ground_truth = load_ground_truth(incident_id)

    assert ground_truth.incident_id == incident_id


@pytest.mark.parametrize("incident_id", FINAL_INCIDENT_IDS)
def test_final_dataset_supporting_evidence_ids_exist(incident_id):
    dataset = load_incident_dataset(INCIDENTS_DIR / incident_id)
    ground_truth = load_ground_truth(incident_id)

    evidence_ids = {
        item.id
        for collection in [
            dataset.logs,
            dataset.metrics,
            dataset.deployments,
            dataset.changes,
        ]
        for item in collection
    }

    assert set(ground_truth.supporting_evidence_ids).issubset(evidence_ids)


@pytest.mark.parametrize("incident_id", FINAL_INCIDENT_IDS)
def test_final_dataset_evidence_ids_are_unique(incident_id):
    dataset = load_incident_dataset(INCIDENTS_DIR / incident_id)

    evidence_ids = [
        item.id
        for collection in [
            dataset.logs,
            dataset.metrics,
            dataset.deployments,
            dataset.changes,
        ]
        for item in collection
    ]

    assert len(evidence_ids) == len(set(evidence_ids))


@pytest.mark.parametrize("incident_id", FINAL_INCIDENT_IDS)
def test_final_dataset_has_required_evidence_surfaces(incident_id):
    dataset = load_incident_dataset(INCIDENTS_DIR / incident_id)

    assert dataset.logs
    assert dataset.metrics
    assert dataset.deployments
    assert dataset.changes


@pytest.mark.parametrize("incident_id", FINAL_INCIDENT_IDS)
def test_ground_truth_is_excluded_from_runtime_dataset(incident_id):
    dataset = load_incident_dataset(INCIDENTS_DIR / incident_id)

    assert not hasattr(dataset, "ground_truth")
