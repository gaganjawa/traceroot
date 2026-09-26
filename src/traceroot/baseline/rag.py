from pydantic import BaseModel, Field
from qdrant_client import QdrantClient

from traceroot.domain.incident import Incident
from traceroot.domain.rca import RCAResult
from traceroot.llm.client import LLM_MODEL_GPT_5_4_MINI, get_llm_client
from traceroot.llm.usage import LLMUsage, record_response_usage
from traceroot.rag.models import RetrievalResult
from traceroot.rag.retriever import retrieve


class RAGBaselineResult(BaseModel):
    result: RCAResult
    retrieval_results: list[RetrievalResult]


class GeneratedRCA(BaseModel):
    root_cause: str
    affected_service: str | None = None
    explanation: str
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


def generate_rca(
    incident: Incident,
    context: str,
    llm_usage: LLMUsage | None = None,
) -> GeneratedRCA:
    """Generate a knowledge-only RCA using semantically retrieved engineering documentation."""

    system_prompt = """
    You are a production incident investigator.

    Analyze the incident using only the supplied engineering knowledge.

    Do not claim that a possible cause is confirmed unless the supplied
    information supports that conclusion. If the available information is
    insufficient to establish the root cause, clearly state the uncertainty.

    Return a root cause, affected service, explanation, and confidence.
    """

    user_prompt = f"""
    INCIDENT

    Title:
    {incident.title}

    Description:
    {incident.description}

    RETRIEVED ENGINEERING KNOWLEDGE

    {context}
    """

    response = get_llm_client().responses.parse(
        model=LLM_MODEL_GPT_5_4_MINI,
        input=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        text_format=GeneratedRCA,
    )

    record_response_usage(
        llm_usage=llm_usage,
        response=response,
    )

    generated = response.output_parsed

    if generated is None:
        raise RuntimeError("LLM did not return a valid structured RCA response.")

    return generated


def build_context(
    retrieval_results: list[RetrievalResult],
) -> str:
    context_parts = []

    for result in retrieval_results:
        context_parts.append(
            f"[CHUNK_ID: {result.chunk.id}]\n"
            f"[SOURCE: {result.chunk.source}]\n"
            f"{result.chunk.content}"
        )

    return "\n\n".join(context_parts)


def run_rag_baseline(
    qdrant_client: QdrantClient,
    incident: Incident,
    top_k: int = 5,
    llm_usage: LLMUsage | None = None,
) -> RAGBaselineResult:
    """
    Generate a Root Cause Analysis (RCA) result for a given incident using Retrieval-Augmented Generation (RAG).

    Args:
        qdrant_client (QdrantClient): The Qdrant client for querying the knowledge base.
        incident (Incident): The incident for which to generate the RCA.
        top_k (int): The number of top retrieved sources to consider.
        llm_usage (LLMUsage | None): Optional accumulator for generation usage.

    Returns:
        RAGBaselineResult: The generated RCA result containing the incident, retrieved sources, and the generated RCA text.
    """

    query = f"{incident.title}\n{incident.description}"

    # Retrieve relevant knowledge chunks based on the incident description
    retrieval_results = retrieve(qdrant_client, query, top_k=top_k)

    context = build_context(retrieval_results)

    # Generate RCA text using the retrieved sources and the incident description
    generated = generate_rca(incident, context, llm_usage=llm_usage)

    rca_result = RCAResult(
        incident_id=incident.id,
        root_cause=generated.root_cause,
        affected_service=generated.affected_service,
        evidence_ids=[],
        explanation=generated.explanation,
        confidence=generated.confidence,
    )

    return RAGBaselineResult(
        result=rca_result,
        retrieval_results=retrieval_results,
    )


def generate_rag_rca(
    qdrant_client: QdrantClient,
    incident: Incident,
    top_k: int = 5,
) -> RCAResult:
    baseline_result = run_rag_baseline(
        qdrant_client=qdrant_client,
        incident=incident,
        top_k=top_k,
    )

    return baseline_result.result
