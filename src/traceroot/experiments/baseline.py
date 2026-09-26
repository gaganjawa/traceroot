import time
from datetime import UTC, datetime

from qdrant_client import QdrantClient

from traceroot.baseline.rag import run_rag_baseline
from traceroot.domain.incident import Incident
from traceroot.evaluation.efficiency import calculate_llm_cost
from traceroot.experiments.models import (
    BaselineExperimentRecord,
    RetrievedKnowledge,
)
from traceroot.llm.client import LLM_MODEL_GPT_5_4_MINI, LLM_PRICING
from traceroot.llm.usage import LLMUsage


def run_baseline_experiment(
    qdrant_client: QdrantClient,
    incident: Incident,
    top_k: int = 5,
) -> BaselineExperimentRecord:
    start_time = time.perf_counter()
    llm_usage = LLMUsage()

    baseline_result = run_rag_baseline(
        qdrant_client=qdrant_client,
        incident=incident,
        top_k=top_k,
        llm_usage=llm_usage,
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

    estimated_cost_usd = None
    pricing = LLM_PRICING.get(LLM_MODEL_GPT_5_4_MINI)
    if (
        llm_usage.input_tokens is not None
        and llm_usage.output_tokens is not None
        and pricing is not None
    ):
        estimated_cost_usd = calculate_llm_cost(
            input_tokens=llm_usage.input_tokens,
            output_tokens=llm_usage.output_tokens,
            **pricing,
        )

    return BaselineExperimentRecord(
        incident_id=incident.id,
        model=LLM_MODEL_GPT_5_4_MINI,
        top_k=top_k,
        retrieved_knowledge=retrieved_knowledge,
        result=baseline_result.result,
        latency_ms=latency_ms,
        input_tokens=llm_usage.input_tokens,
        output_tokens=llm_usage.output_tokens,
        llm_calls=llm_usage.llm_calls,
        estimated_cost_usd=estimated_cost_usd,
        timestamp=datetime.now(UTC),
    )
