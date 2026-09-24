import time
from datetime import UTC, datetime

from qdrant_client import QdrantClient

from traceroot.baseline.rag import run_rag_baseline
from traceroot.domain.incident import Incident
from traceroot.experiments.models import (
    BaselineExperimentRecord,
    RetrievedKnowledge,
)
from traceroot.llm.client import GPT_5_4_MINI_MODEL


def run_baseline_experiment(
    qdrant_client: QdrantClient,
    incident: Incident,
    top_k: int = 5,
) -> BaselineExperimentRecord:
    start_time = time.perf_counter()

    baseline_result = run_rag_baseline(
        qdrant_client=qdrant_client,
        incident=incident,
        top_k=top_k,
    )

    latency_ms = (time.perf_counter() - start_time) * 1000

    retrieved_knowledge = [
        RetrievedKnowledge(
            chunk_id=retrieval.chunk.id,
            source=retrieval.chunk.source,
            score=retrieval.score,
        )
        for retrieval in baseline_result.retrieval_results
    ]

    return BaselineExperimentRecord(
        incident_id=incident.id,
        model=GPT_5_4_MINI_MODEL,
        top_k=top_k,
        retrieved_knowledge=retrieved_knowledge,
        result=baseline_result.result,
        latency_ms=latency_ms,
        timestamp=datetime.now(UTC),
    )
