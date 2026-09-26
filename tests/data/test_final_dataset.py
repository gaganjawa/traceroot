from itertools import pairwise
from pathlib import Path

import pytest

from traceroot.data.loader import load_incident_dataset
from traceroot.domain.ground_truth import GroundTruth

INCIDENTS_DIR = Path("data/incidents")
GROUND_TRUTH_DIR = Path("data/ground_truth")

NEW_INCIDENT_IDS = [
    "INC-004",
    "INC-005",
    "INC-006",
]


def load_ground_truth(incident_id: str) -> GroundTruth:
    path = GROUND_TRUTH_DIR / f"{incident_id}.json"

    return GroundTruth.model_validate_json(path.read_text())


def get_dataset_evidence_ids(dataset) -> set[str]:
    return {
        entry.id
        for collection in [
            dataset.logs,
            dataset.metrics,
            dataset.deployments,
            dataset.changes,
        ]
        for entry in collection
    }


def test_final_dataset_contains_six_incidents():
    incident_ids = {
        path.name
        for path in INCIDENTS_DIR.iterdir()
        if path.is_dir() and path.name.startswith("INC-")
    }

    assert incident_ids == {
        "INC-001",
        "INC-002",
        "INC-003",
        "INC-004",
        "INC-005",
        "INC-006",
    }


@pytest.mark.parametrize("incident_id", NEW_INCIDENT_IDS)
def test_new_incident_dataset_is_valid(incident_id):
    dataset = load_incident_dataset(INCIDENTS_DIR / incident_id)

    assert dataset.incident.id == incident_id
    assert dataset.logs
    assert dataset.metrics
    assert dataset.deployments
    assert dataset.changes


@pytest.mark.parametrize("incident_id", NEW_INCIDENT_IDS)
def test_new_incident_ground_truth_is_valid(incident_id):
    ground_truth = load_ground_truth(incident_id)

    assert ground_truth.incident_id == incident_id
    assert ground_truth.root_cause
    assert ground_truth.root_cause_category
    assert ground_truth.affected_service
    assert ground_truth.supporting_evidence_ids


@pytest.mark.parametrize("incident_id", NEW_INCIDENT_IDS)
def test_new_incidents_supporting_evidence_ids_exist(incident_id):
    dataset = load_incident_dataset(INCIDENTS_DIR / incident_id)
    ground_truth = load_ground_truth(incident_id)

    available_evidence_ids = get_dataset_evidence_ids(dataset)

    assert set(ground_truth.supporting_evidence_ids).issubset(available_evidence_ids)


@pytest.mark.parametrize("incident_id", NEW_INCIDENT_IDS)
def test_new_incident_evidence_ids_are_unique(incident_id):
    dataset = load_incident_dataset(INCIDENTS_DIR / incident_id)

    evidence_ids = [
        entry.id
        for collection in [
            dataset.logs,
            dataset.metrics,
            dataset.deployments,
            dataset.changes,
        ]
        for entry in collection
    ]

    assert len(evidence_ids) == len(set(evidence_ids))


def test_inc_004_contains_success_and_failure():
    dataset = load_incident_dataset(INCIDENTS_DIR / "INC-004")

    ad_logs = [
        log.message.lower()
        for log in dataset.logs
        if log.service == "ad-service" and "getads" in log.message.lower()
    ]

    assert any("success" in message for message in ad_logs)

    assert any("fail" in message for message in ad_logs)


def test_inc_004_error_rate_is_intermittent_not_total_outage():
    dataset = load_incident_dataset(INCIDENTS_DIR / "INC-004")

    error_rates = [
        metric.value
        for metric in dataset.metrics
        if metric.service == "ad-service"
        and metric.metric == "app.ads.request.error_rate"
    ]

    assert error_rates

    peak_error_rate = max(error_rates)

    assert peak_error_rate > 0
    assert peak_error_rate < 1.0


def test_inc_005_memory_usage_progressively_increases():
    dataset = load_incident_dataset(INCIDENTS_DIR / "INC-005")

    memory_metrics = sorted(
        [
            metric
            for metric in dataset.metrics
            if metric.service == "email-service"
            and metric.metric == "process.memory.rss"
        ],
        key=lambda metric: metric.timestamp,
    )

    assert len(memory_metrics) >= 3

    values = [metric.value for metric in memory_metrics]

    assert all(later > earlier for earlier, later in pairwise(values))


def test_inc_005_checkout_and_payment_remain_healthy():
    dataset = load_incident_dataset(INCIDENTS_DIR / "INC-005")

    healthy_messages = [
        log.message.lower()
        for log in dataset.logs
        if log.service
        in {
            "checkout-service",
            "payment-service",
        }
    ]

    assert any("checkout completed" in message for message in healthy_messages)

    assert any(
        "payment" in message and "success" in message for message in healthy_messages
    )


def test_inc_006_failure_is_specific_to_empty_cart():
    dataset = load_incident_dataset(INCIDENTS_DIR / "INC-006")

    cart_messages = [
        log.message.lower() for log in dataset.logs if log.service == "cart-service"
    ]

    assert any(
        "emptycart" in message and "fail" in message for message in cart_messages
    )

    assert any(
        "getcart" in message and "success" in message for message in cart_messages
    )

    assert any(
        "additem" in message and "success" in message for message in cart_messages
    )


def test_inc_006_empty_cart_error_rate_exceeds_other_cart_operations():
    dataset = load_incident_dataset(INCIDENTS_DIR / "INC-006")

    metric_values = {
        metric.metric: metric.value
        for metric in dataset.metrics
        if metric.service == "cart-service"
    }

    assert metric_values["empty_cart.error_rate"] > metric_values["get_cart.error_rate"]

    assert metric_values["empty_cart.error_rate"] > metric_values["add_item.error_rate"]


@pytest.mark.parametrize("incident_id", NEW_INCIDENT_IDS)
def test_ground_truth_is_not_loaded_into_runtime_dataset(
    incident_id,
):
    dataset = load_incident_dataset(INCIDENTS_DIR / incident_id)

    assert not hasattr(dataset, "ground_truth")
