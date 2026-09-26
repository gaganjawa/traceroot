import datetime
from unittest.mock import MagicMock, patch

import pytest

from traceroot.domain.incident import Incident
from traceroot.domain.rca import RCAResult
from traceroot.experiments.baseline import run_baseline_experiment
from traceroot.experiments.models import BaselineExperimentRecord
from traceroot.llm.client import LLM_MODEL_GPT_5_4_MINI


@patch("traceroot.experiments.baseline.run_rag_baseline")
def test_run_baseline_experiment_records_incident_metadata(mock_run_rag):

    mock_qdrant_client = MagicMock()
    mock_incident = Incident(
        id="INC-123",
        title="Test Incident",
        description="This is a test incident.",
        start_time=datetime.datetime(2024, 1, 1, 12, 0, tzinfo=datetime.UTC),
    )

    rca_result = RCAResult(
        incident_id="INC-123",
        root_cause="Test root cause",
        affected_service="test-service",
        evidence_ids=[],
        explanation="Test explanation",
        confidence=0.5,
    )

    mock_run_rag.return_value = MagicMock(
        retrieval_results=[],
        result=rca_result,
    )

    record = run_baseline_experiment(
        qdrant_client=mock_qdrant_client,
        incident=mock_incident,
        top_k=5,
    )

    assert isinstance(record, BaselineExperimentRecord)
    assert record.incident_id == "INC-123"
    assert record.approach == "rag_baseline"
    assert record.model == LLM_MODEL_GPT_5_4_MINI
    assert record.top_k == 5


@patch("traceroot.experiments.baseline.run_rag_baseline")
def test_run_baseline_experiment_records_retrieval_provenance(mock_run_rag):
    mock_qdrant_client = MagicMock()
    mock_incident = Incident(
        id="INC-456",
        title="Another Test Incident",
        description="This is another test incident.",
        start_time=datetime.datetime(2024, 1, 2, 12, 0, tzinfo=datetime.UTC),
    )

    retrieval_results = [
        MagicMock(chunk=MagicMock(id="chunk-1", source="source-1"), score=0.9),
        MagicMock(chunk=MagicMock(id="chunk-2", source="source-2"), score=0.8),
    ]

    rca_result = RCAResult(
        incident_id="INC-456",
        root_cause="Another test root cause",
        affected_service="another-test-service",
        evidence_ids=[],
        explanation="Another test explanation",
        confidence=0.7,
    )

    mock_run_rag.return_value = MagicMock(
        retrieval_results=retrieval_results,
        result=rca_result,
    )

    record = run_baseline_experiment(
        qdrant_client=mock_qdrant_client,
        incident=mock_incident,
        top_k=5,
    )

    assert len(record.retrieved_knowledge) == 2
    assert record.retrieved_knowledge[0].chunk_id == "chunk-1"
    assert record.retrieved_knowledge[0].source == "source-1"
    assert record.retrieved_knowledge[0].score == 0.9
    assert record.retrieved_knowledge[1].chunk_id == "chunk-2"
    assert record.retrieved_knowledge[1].source == "source-2"
    assert record.retrieved_knowledge[1].score == 0.8


@patch("traceroot.experiments.baseline.run_rag_baseline")
def test_run_baseline_experiment_preserves_rca_result(mock_run_rag):
    mock_qdrant_client = MagicMock()
    mock_incident = Incident(
        id="INC-789",
        title="Yet Another Test Incident",
        description="This is yet another test incident.",
        start_time=datetime.datetime(2024, 1, 3, 12, 0, tzinfo=datetime.UTC),
    )

    rca_result = RCAResult(
        incident_id="INC-789",
        root_cause="Yet another test root cause",
        affected_service="yet-another-test-service",
        evidence_ids=[],
        explanation="Yet another test explanation",
        confidence=0.9,
    )

    mock_run_rag.return_value = MagicMock(
        retrieval_results=[],
        result=rca_result,
    )

    record = run_baseline_experiment(
        qdrant_client=mock_qdrant_client,
        incident=mock_incident,
        top_k=5,
    )

    assert record.result.incident_id == "INC-789"
    assert record.result.root_cause == "Yet another test root cause"
    assert record.result.affected_service == "yet-another-test-service"
    assert record.result.explanation == "Yet another test explanation"
    assert record.result.confidence == 0.9


@patch("traceroot.experiments.baseline.run_rag_baseline")
def test_run_baseline_experiment_records_execution_latency(mock_run_rag):
    mock_qdrant_client = MagicMock()
    mock_incident = Incident(
        id="INC-101",
        title="Latency Test Incident",
        description="This is a latency test incident.",
        start_time=datetime.datetime(2024, 1, 4, 12, 0, tzinfo=datetime.UTC),
    )

    rca_result = RCAResult(
        incident_id="INC-101",
        root_cause="Latency test root cause",
        affected_service="latency-test-service",
        evidence_ids=[],
        explanation="Latency test explanation",
        confidence=0.95,
    )

    mock_run_rag.return_value = MagicMock(
        retrieval_results=[],
        result=rca_result,
    )

    record = run_baseline_experiment(
        qdrant_client=mock_qdrant_client,
        incident=mock_incident,
        top_k=5,
    )

    assert record.latency_ms >= 0


@patch("traceroot.experiments.baseline.run_rag_baseline")
def test_run_baseline_experiment_uses_timezone_aware_timestamp(mock_run_rag):
    mock_qdrant_client = MagicMock()
    mock_incident = Incident(
        id="INC-101",
        title="Timezone Test Incident",
        description="This is a timezone test incident.",
        start_time=datetime.datetime(2024, 1, 4, 12, 0, tzinfo=datetime.UTC),
    )

    rca_result = RCAResult(
        incident_id="INC-101",
        root_cause="Timezone test root cause",
        affected_service="timezone-test-service",
        evidence_ids=[],
        explanation="Timezone test explanation",
        confidence=0.95,
    )

    mock_run_rag.return_value = MagicMock(
        retrieval_results=[],
        result=rca_result,
    )

    record = run_baseline_experiment(
        qdrant_client=mock_qdrant_client,
        incident=mock_incident,
        top_k=5,
    )

    assert record.timestamp.tzinfo is not None


@patch("traceroot.experiments.baseline.run_rag_baseline")
def test_run_baseline_experiment_calls_rag_baseline_once(mock_run_rag):
    mock_qdrant_client = MagicMock()
    mock_incident = Incident(
        id="INC-101",
        title="Test Incident",
        description="This is a test incident.",
        start_time=datetime.datetime(2024, 1, 4, 12, 0, tzinfo=datetime.UTC),
    )

    rca_result = RCAResult(
        incident_id="INC-101",
        root_cause="Test root cause",
        affected_service="test-service",
        evidence_ids=[],
        explanation="Test explanation",
        confidence=0.95,
    )

    mock_run_rag.return_value = MagicMock(
        retrieval_results=[],
        result=rca_result,
    )

    run_baseline_experiment(
        qdrant_client=mock_qdrant_client,
        incident=mock_incident,
        top_k=5,
    )

    mock_run_rag.assert_called_once()


@patch("traceroot.experiments.baseline.run_rag_baseline")
def test_baseline_experiment_record_serializes_to_json(mock_run_rag):
    mock_qdrant_client = MagicMock()
    mock_incident = Incident(
        id="INC-101",
        title="Test Incident",
        description="This is a test incident.",
        start_time=datetime.datetime(2024, 1, 4, 12, 0, tzinfo=datetime.UTC),
    )

    rca_result = RCAResult(
        incident_id="INC-101",
        root_cause="Test root cause",
        affected_service="test-service",
        evidence_ids=[],
        explanation="Test explanation",
        confidence=0.95,
    )

    mock_run_rag.return_value = MagicMock(
        retrieval_results=[],
        result=rca_result,
    )

    record = run_baseline_experiment(
        qdrant_client=mock_qdrant_client,
        incident=mock_incident,
        top_k=5,
    )

    json_record = record.model_dump_json()
    assert isinstance(json_record, str)


@patch("traceroot.experiments.baseline.run_rag_baseline")
@patch("traceroot.experiments.baseline.LLM_MODEL_GPT_5_4_MINI", "gpt-5.4-mini")
def test_run_baseline_experiment_persists_llm_usage(mock_run_rag):
    mock_qdrant_client = MagicMock()
    incident = Incident(
        id="INC-123",
        title="Test Incident",
        description="This is a test incident.",
        start_time=datetime.datetime(2024, 1, 1, 12, 0, tzinfo=datetime.UTC),
    )
    rca_result = RCAResult(
        incident_id=incident.id,
        root_cause="Test root cause",
        affected_service="test-service",
        evidence_ids=[],
        explanation="Test explanation",
        confidence=0.5,
    )

    def run_rag_side_effect(qdrant_client, incident, top_k, llm_usage):
        llm_usage.add(input_tokens=100, output_tokens=20)
        llm_usage.add(input_tokens=50, output_tokens=10)
        return MagicMock(retrieval_results=[], result=rca_result)

    mock_run_rag.side_effect = run_rag_side_effect

    record = run_baseline_experiment(
        qdrant_client=mock_qdrant_client,
        incident=incident,
        top_k=5,
    )

    assert record.input_tokens == 150
    assert record.output_tokens == 30
    assert record.llm_calls == 2
    assert record.estimated_cost_usd == pytest.approx(0.0002475)
    persisted_record = BaselineExperimentRecord.model_validate_json(
        record.model_dump_json()
    )
    assert persisted_record == record
    assert "total_tokens" not in record.model_dump()


@patch("traceroot.experiments.baseline.run_rag_baseline")
@pytest.mark.parametrize(
    "input_tokens, output_tokens",
    [(None, None), (None, 20), (100, None)],
)
def test_run_baseline_experiment_preserves_unavailable_llm_usage(
    mock_run_rag,
    input_tokens,
    output_tokens,
):
    mock_qdrant_client = MagicMock()
    incident = Incident(
        id="INC-123",
        title="Test Incident",
        description="This is a test incident.",
        start_time=datetime.datetime(2024, 1, 1, 12, 0, tzinfo=datetime.UTC),
    )
    rca_result = RCAResult(
        incident_id=incident.id,
        root_cause="Test root cause",
        affected_service="test-service",
        evidence_ids=[],
        explanation="Test explanation",
        confidence=0.5,
    )

    def run_rag_side_effect(qdrant_client, incident, top_k, llm_usage):
        llm_usage.add(input_tokens=input_tokens, output_tokens=output_tokens)
        return MagicMock(retrieval_results=[], result=rca_result)

    mock_run_rag.side_effect = run_rag_side_effect

    record = run_baseline_experiment(
        qdrant_client=mock_qdrant_client,
        incident=incident,
        top_k=5,
    )

    assert record.input_tokens == input_tokens
    assert record.output_tokens == output_tokens
    assert record.llm_calls == 1
    assert record.estimated_cost_usd is None
    persisted_record = BaselineExperimentRecord.model_validate_json(
        record.model_dump_json()
    )
    assert persisted_record == record
