from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

from traceroot.evaluation.comparison import run_incident_comparison


def make_incident():
    return SimpleNamespace(id="INC-001")


def make_chunks():
    return [
        SimpleNamespace(
            id="architecture.md::0",
            content="Checkout architecture knowledge",
        ),
        SimpleNamespace(
            id="runbook.md::0",
            content="Checkout investigation runbook",
        ),
    ]


def make_rag_record():
    return SimpleNamespace(
        retrieved_knowledge=[
            SimpleNamespace(
                chunk_id="architecture.md::0",
                source="architecture.md",
                score=0.9,
            ),
            SimpleNamespace(
                chunk_id="runbook.md::0",
                source="runbook.md",
                score=0.8,
            ),
        ]
    )


@patch("traceroot.evaluation.comparison.IncidentComparisonResult")
@patch("traceroot.evaluation.comparison.persist")
@patch("traceroot.evaluation.comparison.evaluate_agent_record")
@patch("traceroot.evaluation.comparison.evaluate_rag_record")
@patch("traceroot.evaluation.comparison.GroundTruth")
@patch("traceroot.evaluation.comparison.run_agent_experiment")
@patch("traceroot.evaluation.comparison.run_baseline_experiment")
@patch("traceroot.evaluation.comparison.index_chunks")
@patch("traceroot.evaluation.comparison.create_knowledge_collection")
@patch("traceroot.evaluation.comparison.QdrantClient")
@patch("traceroot.evaluation.comparison.chunk_document")
@patch("traceroot.evaluation.comparison.load_knowledge_corpus")
@patch("traceroot.evaluation.comparison.load_incident")
def test_run_incident_comparison_runs_rag_and_agent(
    mock_load_incident,
    mock_load_knowledge_corpus,
    mock_chunk_document,
    mock_qdrant_client,
    mock_create_collection,
    mock_index_chunks,
    mock_run_baseline,
    mock_run_agent,
    mock_ground_truth,
    mock_evaluate_rag,
    mock_evaluate_agent,
    mock_persist,
    mock_comparison_result,
    tmp_path,
):
    incident = make_incident()
    rag_record = make_rag_record()
    agent_record = MagicMock()

    mock_load_incident.return_value = incident
    mock_load_knowledge_corpus.return_value = [MagicMock()]
    mock_chunk_document.return_value = make_chunks()
    mock_run_baseline.return_value = rag_record
    mock_run_agent.return_value = agent_record

    run_incident_comparison(
        incident_id="INC-001",
        top_k=3,
        max_tool_calls=6,
        output_dir=tmp_path,
    )

    mock_run_baseline.assert_called_once()
    mock_run_agent.assert_called_once()


@patch("traceroot.evaluation.comparison.IncidentComparisonResult")
@patch("traceroot.evaluation.comparison.persist")
@patch("traceroot.evaluation.comparison.evaluate_agent_record")
@patch("traceroot.evaluation.comparison.evaluate_rag_record")
@patch("traceroot.evaluation.comparison.GroundTruth")
@patch("traceroot.evaluation.comparison.run_agent_experiment")
@patch("traceroot.evaluation.comparison.run_baseline_experiment")
@patch("traceroot.evaluation.comparison.index_chunks")
@patch("traceroot.evaluation.comparison.create_knowledge_collection")
@patch("traceroot.evaluation.comparison.QdrantClient")
@patch("traceroot.evaluation.comparison.chunk_document")
@patch("traceroot.evaluation.comparison.load_knowledge_corpus")
@patch("traceroot.evaluation.comparison.load_incident")
def test_run_incident_comparison_uses_same_incident(
    mock_load_incident,
    mock_load_knowledge_corpus,
    mock_chunk_document,
    mock_qdrant_client,
    mock_create_collection,
    mock_index_chunks,
    mock_run_baseline,
    mock_run_agent,
    mock_ground_truth,
    mock_evaluate_rag,
    mock_evaluate_agent,
    mock_persist,
    mock_comparison_result,
    tmp_path,
):
    incident = make_incident()

    mock_load_incident.return_value = incident
    mock_load_knowledge_corpus.return_value = [MagicMock()]
    mock_chunk_document.return_value = make_chunks()
    mock_run_baseline.return_value = make_rag_record()

    run_incident_comparison(
        "INC-001",
        3,
        6,
        tmp_path,
    )

    assert mock_run_baseline.call_args.kwargs["incident"] is incident
    assert mock_run_agent.call_args.kwargs["incident"] is incident


@patch("traceroot.evaluation.comparison.IncidentComparisonResult")
@patch("traceroot.evaluation.comparison.persist")
@patch("traceroot.evaluation.comparison.evaluate_agent_record")
@patch("traceroot.evaluation.comparison.evaluate_rag_record")
@patch("traceroot.evaluation.comparison.GroundTruth")
@patch("traceroot.evaluation.comparison.run_agent_experiment")
@patch("traceroot.evaluation.comparison.run_baseline_experiment")
@patch("traceroot.evaluation.comparison.index_chunks")
@patch("traceroot.evaluation.comparison.create_knowledge_collection")
@patch("traceroot.evaluation.comparison.QdrantClient")
@patch("traceroot.evaluation.comparison.chunk_document")
@patch("traceroot.evaluation.comparison.load_knowledge_corpus")
@patch("traceroot.evaluation.comparison.load_incident")
def test_run_incident_comparison_passes_top_k(
    mock_load_incident,
    mock_load_knowledge_corpus,
    mock_chunk_document,
    mock_qdrant_client,
    mock_create_collection,
    mock_index_chunks,
    mock_run_baseline,
    mock_run_agent,
    mock_ground_truth,
    mock_evaluate_rag,
    mock_evaluate_agent,
    mock_persist,
    mock_comparison_result,
    tmp_path,
):
    mock_load_incident.return_value = make_incident()
    mock_load_knowledge_corpus.return_value = [MagicMock()]
    mock_chunk_document.return_value = make_chunks()
    mock_run_baseline.return_value = make_rag_record()

    run_incident_comparison(
        "INC-001",
        top_k=3,
        max_tool_calls=6,
        output_dir=tmp_path,
    )

    assert mock_run_baseline.call_args.kwargs["top_k"] == 3


@patch("traceroot.evaluation.comparison.IncidentComparisonResult")
@patch("traceroot.evaluation.comparison.persist")
@patch("traceroot.evaluation.comparison.evaluate_agent_record")
@patch("traceroot.evaluation.comparison.evaluate_rag_record")
@patch("traceroot.evaluation.comparison.GroundTruth")
@patch("traceroot.evaluation.comparison.run_agent_experiment")
@patch("traceroot.evaluation.comparison.run_baseline_experiment")
@patch("traceroot.evaluation.comparison.index_chunks")
@patch("traceroot.evaluation.comparison.create_knowledge_collection")
@patch("traceroot.evaluation.comparison.QdrantClient")
@patch("traceroot.evaluation.comparison.chunk_document")
@patch("traceroot.evaluation.comparison.load_knowledge_corpus")
@patch("traceroot.evaluation.comparison.load_incident")
def test_run_incident_comparison_passes_max_tool_calls(
    mock_load_incident,
    mock_load_knowledge_corpus,
    mock_chunk_document,
    mock_qdrant_client,
    mock_create_collection,
    mock_index_chunks,
    mock_run_baseline,
    mock_run_agent,
    mock_ground_truth,
    mock_evaluate_rag,
    mock_evaluate_agent,
    mock_persist,
    mock_comparison_result,
    tmp_path,
):
    mock_load_incident.return_value = make_incident()
    mock_load_knowledge_corpus.return_value = [MagicMock()]
    mock_chunk_document.return_value = make_chunks()
    mock_run_baseline.return_value = make_rag_record()

    run_incident_comparison(
        "INC-001",
        top_k=3,
        max_tool_calls=6,
        output_dir=tmp_path,
    )

    assert mock_run_agent.call_args.kwargs["max_tool_calls"] == 6


@patch("traceroot.evaluation.comparison.IncidentComparisonResult")
@patch("traceroot.evaluation.comparison.persist")
@patch("traceroot.evaluation.comparison.evaluate_agent_record")
@patch("traceroot.evaluation.comparison.evaluate_rag_record")
@patch("traceroot.evaluation.comparison.GroundTruth")
@patch("traceroot.evaluation.comparison.run_agent_experiment")
@patch("traceroot.evaluation.comparison.run_baseline_experiment")
@patch("traceroot.evaluation.comparison.index_chunks")
@patch("traceroot.evaluation.comparison.create_knowledge_collection")
@patch("traceroot.evaluation.comparison.QdrantClient")
@patch("traceroot.evaluation.comparison.chunk_document")
@patch("traceroot.evaluation.comparison.load_knowledge_corpus")
@patch("traceroot.evaluation.comparison.load_incident")
def test_run_incident_comparison_persists_raw_rag_before_evaluation(
    mock_load_incident,
    mock_load_knowledge_corpus,
    mock_chunk_document,
    mock_qdrant_client,
    mock_create_collection,
    mock_index_chunks,
    mock_run_baseline,
    mock_run_agent,
    mock_ground_truth,
    mock_evaluate_rag,
    mock_evaluate_agent,
    mock_persist,
    mock_comparison_result,
    tmp_path,
):
    events = []

    mock_load_incident.return_value = make_incident()
    mock_load_knowledge_corpus.return_value = [MagicMock()]
    mock_chunk_document.return_value = make_chunks()
    mock_run_baseline.return_value = make_rag_record()

    mock_persist.side_effect = lambda *args, **kwargs: events.append("persist")
    mock_evaluate_rag.side_effect = lambda *args, **kwargs: events.append(
        "evaluate_rag"
    )

    run_incident_comparison(
        "INC-001",
        3,
        6,
        tmp_path,
    )

    assert events.index("persist") < events.index("evaluate_rag")

    assert mock_persist.call_args_list[0] == call(
        mock_run_baseline.return_value,
        tmp_path / "raw" / "INC-001-rag.json",
    )


@patch("traceroot.evaluation.comparison.IncidentComparisonResult")
@patch("traceroot.evaluation.comparison.persist")
@patch("traceroot.evaluation.comparison.evaluate_agent_record")
@patch("traceroot.evaluation.comparison.evaluate_rag_record")
@patch("traceroot.evaluation.comparison.GroundTruth")
@patch("traceroot.evaluation.comparison.run_agent_experiment")
@patch("traceroot.evaluation.comparison.run_baseline_experiment")
@patch("traceroot.evaluation.comparison.index_chunks")
@patch("traceroot.evaluation.comparison.create_knowledge_collection")
@patch("traceroot.evaluation.comparison.QdrantClient")
@patch("traceroot.evaluation.comparison.chunk_document")
@patch("traceroot.evaluation.comparison.load_knowledge_corpus")
@patch("traceroot.evaluation.comparison.load_incident")
def test_run_incident_comparison_passes_retrieval_context(
    mock_load_incident,
    mock_load_knowledge_corpus,
    mock_chunk_document,
    mock_qdrant_client,
    mock_create_collection,
    mock_index_chunks,
    mock_run_baseline,
    mock_run_agent,
    mock_ground_truth,
    mock_evaluate_rag,
    mock_evaluate_agent,
    mock_persist,
    mock_comparison_result,
    tmp_path,
):
    mock_load_incident.return_value = make_incident()
    mock_load_knowledge_corpus.return_value = [MagicMock()]
    mock_chunk_document.return_value = make_chunks()
    mock_run_baseline.return_value = make_rag_record()

    run_incident_comparison(
        "INC-001",
        3,
        6,
        tmp_path,
    )

    assert mock_evaluate_rag.call_args.kwargs["retrieval_context"] == [
        "Checkout architecture knowledge",
        "Checkout investigation runbook",
    ]


@patch("traceroot.evaluation.comparison.IncidentComparisonResult")
@patch("traceroot.evaluation.comparison.persist")
@patch("traceroot.evaluation.comparison.evaluate_agent_record")
@patch("traceroot.evaluation.comparison.evaluate_rag_record")
@patch("traceroot.evaluation.comparison.GroundTruth")
@patch("traceroot.evaluation.comparison.run_agent_experiment")
@patch("traceroot.evaluation.comparison.run_baseline_experiment")
@patch("traceroot.evaluation.comparison.index_chunks")
@patch("traceroot.evaluation.comparison.create_knowledge_collection")
@patch("traceroot.evaluation.comparison.QdrantClient")
@patch("traceroot.evaluation.comparison.chunk_document")
@patch("traceroot.evaluation.comparison.load_knowledge_corpus")
@patch("traceroot.evaluation.comparison.load_incident")
def test_run_incident_comparison_evaluates_both_approaches(
    mock_load_incident,
    mock_load_knowledge_corpus,
    mock_chunk_document,
    mock_qdrant_client,
    mock_create_collection,
    mock_index_chunks,
    mock_run_baseline,
    mock_run_agent,
    mock_ground_truth,
    mock_evaluate_rag,
    mock_evaluate_agent,
    mock_persist,
    mock_comparison_result,
    tmp_path,
):
    rag_record = make_rag_record()
    agent_record = MagicMock()
    ground_truth = MagicMock()

    mock_load_incident.return_value = make_incident()
    mock_load_knowledge_corpus.return_value = [MagicMock()]
    mock_chunk_document.return_value = make_chunks()
    mock_run_baseline.return_value = rag_record
    mock_run_agent.return_value = agent_record
    mock_ground_truth.model_validate_json.return_value = ground_truth

    run_incident_comparison(
        "INC-001",
        3,
        6,
        tmp_path,
    )

    mock_evaluate_rag.assert_called_once_with(
        record=rag_record,
        ground_truth=ground_truth,
        retrieval_context=[
            "Checkout architecture knowledge",
            "Checkout investigation runbook",
        ],
    )

    mock_evaluate_agent.assert_called_once_with(
        record=agent_record,
        ground_truth=ground_truth,
    )


@patch("traceroot.evaluation.comparison.IncidentComparisonResult")
@patch("traceroot.evaluation.comparison.persist")
@patch("traceroot.evaluation.comparison.evaluate_agent_record")
@patch("traceroot.evaluation.comparison.evaluate_rag_record")
@patch("traceroot.evaluation.comparison.GroundTruth")
@patch("traceroot.evaluation.comparison.run_agent_experiment")
@patch("traceroot.evaluation.comparison.run_baseline_experiment")
@patch("traceroot.evaluation.comparison.index_chunks")
@patch("traceroot.evaluation.comparison.create_knowledge_collection")
@patch("traceroot.evaluation.comparison.QdrantClient")
@patch("traceroot.evaluation.comparison.chunk_document")
@patch("traceroot.evaluation.comparison.load_knowledge_corpus")
@patch("traceroot.evaluation.comparison.load_incident")
def test_run_incident_comparison_returns_both_results(
    mock_load_incident,
    mock_load_knowledge_corpus,
    mock_chunk_document,
    mock_qdrant_client,
    mock_create_collection,
    mock_index_chunks,
    mock_run_baseline,
    mock_run_agent,
    mock_ground_truth,
    mock_evaluate_rag,
    mock_evaluate_agent,
    mock_persist,
    mock_comparison_result,
    tmp_path,
):
    rag_evaluation = MagicMock()
    agent_evaluation = MagicMock()
    expected = MagicMock()

    mock_load_incident.return_value = make_incident()
    mock_load_knowledge_corpus.return_value = [MagicMock()]
    mock_chunk_document.return_value = make_chunks()
    mock_run_baseline.return_value = make_rag_record()

    mock_evaluate_rag.return_value = rag_evaluation
    mock_evaluate_agent.return_value = agent_evaluation
    mock_comparison_result.return_value = expected

    result = run_incident_comparison(
        "INC-001",
        3,
        6,
        tmp_path,
    )

    mock_comparison_result.assert_called_once_with(
        incident_id="INC-001",
        rag=rag_evaluation,
        agent=agent_evaluation,
    )

    assert result is expected
