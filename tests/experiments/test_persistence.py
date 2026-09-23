import json
from datetime import UTC, datetime

import pytest

from traceroot.domain.rca import RCAResult
from traceroot.experiments.models import (
    BaselineExperimentRecord,
    RetrievedKnowledge,
)
from traceroot.experiments.persistence import save_baseline_record


@pytest.fixture
def baseline_record() -> BaselineExperimentRecord:
    return BaselineExperimentRecord(
        incident_id="INC-001",
        model="gpt-5.4-mini",
        top_k=5,
        retrieved_knowledge=[
            RetrievedKnowledge(
                chunk_id="checkout-runbook.md::0",
                source="checkout-runbook.md",
                score=0.573,
            )
        ],
        result=RCAResult(
            incident_id="INC-001",
            root_cause="Insufficient evidence to confirm root cause",
            affected_service="checkout-service",
            evidence_ids=[],
            explanation="Knowledge-only baseline explanation.",
            confidence=0.22,
        ),
        latency_ms=125.5,
        timestamp=datetime(
            2026,
            9,
            23,
            12,
            0,
            tzinfo=UTC,
        ),
    )


def test_save_baseline_record_creates_json_file(
    tmp_path,
    baseline_record,
):
    file_path = tmp_path / "baseline.json"

    save_baseline_record(
        record=baseline_record,
        file_path=str(file_path),
    )

    assert file_path.exists()
    assert file_path.is_file()
    assert file_path.stat().st_size > 0


def test_save_baseline_record_creates_missing_parent_directory(
    tmp_path,
    baseline_record,
):
    file_path = tmp_path / "results" / "baseline" / "INC-001-rag_baseline.json"

    assert not file_path.parent.exists()

    save_baseline_record(
        record=baseline_record,
        file_path=str(file_path),
    )

    assert file_path.parent.exists()
    assert file_path.exists()


def test_save_baseline_record_persists_complete_record(
    tmp_path,
    baseline_record,
):
    file_path = tmp_path / "baseline.json"

    save_baseline_record(
        record=baseline_record,
        file_path=str(file_path),
    )

    with file_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    assert data["incident_id"] == "INC-001"
    assert data["approach"] == "rag_baseline"
    assert data["model"] == "gpt-5.4-mini"
    assert data["top_k"] == 5
    assert data["latency_ms"] == 125.5

    assert len(data["retrieved_knowledge"]) == 1
    assert data["retrieved_knowledge"][0]["chunk_id"] == "checkout-runbook.md::0"
    assert data["retrieved_knowledge"][0]["source"] == "checkout-runbook.md"
    assert data["retrieved_knowledge"][0]["score"] == 0.573

    assert data["result"]["incident_id"] == "INC-001"
    assert data["result"]["root_cause"] == "Insufficient evidence to confirm root cause"
    assert data["result"]["affected_service"] == "checkout-service"
    assert data["result"]["evidence_ids"] == []
    assert data["result"]["confidence"] == 0.22

    assert data["timestamp"] == "2026-09-23T12:00:00Z"


def test_save_baseline_record_returns_output_path(
    tmp_path,
    baseline_record,
):
    file_path = tmp_path / "INC-001-rag_baseline.json"

    returned_path = save_baseline_record(
        record=baseline_record,
        file_path=str(file_path),
    )

    assert returned_path == file_path
    assert returned_path.exists()
