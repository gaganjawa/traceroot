from pathlib import Path

from pydantic import BaseModel
from qdrant_client import QdrantClient

from traceroot.data.loader import load_incident
from traceroot.domain.ground_truth import GroundTruth
from traceroot.evaluation.runner import (
    evaluate_agent_record,
    evaluate_rag_record,
)
from traceroot.evaluation.schemas import EvaluationResult
from traceroot.experiments.agent import run_agent_experiment
from traceroot.experiments.baseline import run_baseline_experiment
from traceroot.experiments.persistence import persist
from traceroot.rag.chunker import chunk_document
from traceroot.rag.index import (
    create_knowledge_collection,
    index_chunks,
)
from traceroot.rag.loader import load_knowledge_corpus


class IncidentComparisonResult(BaseModel):
    incident_id: str
    rag: EvaluationResult
    agent: EvaluationResult


def run_incident_comparison(
    incident_id: str,
    top_k: int,
    max_tool_calls: int,
    output_dir: Path,
) -> IncidentComparisonResult:
    incident_path = Path("data/incidents") / incident_id / "incident.json"

    incident = load_incident(incident_path)

    raw_dir = output_dir / "raw"
    evaluation_dir = output_dir / "evaluations"

    raw_dir.mkdir(parents=True, exist_ok=True)
    evaluation_dir.mkdir(parents=True, exist_ok=True)

    # -------------------------
    # RAG
    # -------------------------

    knowledge_documents = load_knowledge_corpus(Path("data/knowledge"))

    chunks = [
        chunk for document in knowledge_documents for chunk in chunk_document(document)
    ]

    qdrant_client = QdrantClient(":memory:")

    create_knowledge_collection(qdrant_client)
    index_chunks(qdrant_client, chunks)

    rag_record = run_baseline_experiment(
        qdrant_client=qdrant_client,
        incident=incident,
        top_k=top_k,
    )

    # Persist raw output BEFORE loading ground truth/evaluation.
    persist(
        rag_record,
        raw_dir / f"{incident_id}-rag.json",
    )

    # BaselineExperimentRecord only stores provenance,
    # so recover actual retrieved text using the retrieved chunk IDs.
    chunk_by_id = {chunk.id: chunk for chunk in chunks}

    retrieval_context = [
        chunk_by_id[item.chunk_id].content for item in rag_record.retrieved_knowledge
    ]

    # -------------------------
    # AGENT
    # -------------------------

    agent_record = run_agent_experiment(
        incident=incident,
        max_tool_calls=max_tool_calls,
        output_path=raw_dir / f"{incident_id}-agent.json",
    )

    # If run_agent_experiment already persists internally,
    # DO NOT persist it again here.

    # -------------------------
    # EVALUATION-ONLY BOUNDARY
    # -------------------------

    ground_truth = GroundTruth.model_validate_json(
        (Path("data/ground_truth") / f"{incident_id}.json").read_text()
    )

    rag_evaluation = evaluate_rag_record(
        record=rag_record,
        ground_truth=ground_truth,
        retrieval_context=retrieval_context,
    )

    agent_evaluation = evaluate_agent_record(
        record=agent_record,
        ground_truth=ground_truth,
    )

    persist(
        rag_evaluation,
        evaluation_dir / f"{incident_id}-rag-eval.json",
    )

    persist(
        agent_evaluation,
        evaluation_dir / f"{incident_id}-agent-eval.json",
    )

    return IncidentComparisonResult(
        incident_id=incident_id,
        rag=rag_evaluation,
        agent=agent_evaluation,
    )
