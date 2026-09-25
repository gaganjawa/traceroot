from pydantic import BaseModel

from traceroot.agent.state import InvestigationState
from traceroot.domain.rca import RCAResult
from traceroot.llm.client import GPT_5_4_MINI_MODEL, get_llm_client


class GeneratedFinalRCA(BaseModel):
    root_cause: str
    affected_service: str | None = None
    evidence_ids: list[str]
    explanation: str
    confidence: float | None = None


def build_context_from_state(
    state: InvestigationState,
) -> str:
    hypotheses = "\n".join(f"- {hypothesis}" for hypothesis in state.hypotheses)

    tool_history = "\n".join(f"- {record}" for record in state.tool_history)

    evidence_ids = ", ".join(state.evidence_ids)

    return f"""
You are producing the final root-cause analysis for a production incident.

Generate the final RCA using only the investigation information provided below.

Rules:
- Use only evidence that was actually gathered during the investigation.
- Every evidence ID in the final answer must come from the provided gathered evidence IDs.
- Do not invent evidence IDs.
- Prefer supported hypotheses when determining the root cause.
- Do not present rejected hypotheses as established causes.
- Open hypotheses may be discussed only when uncertainty remains.

Incident:
{state.incident}

Hypotheses:
{hypotheses}

Gathered evidence IDs:
{evidence_ids}

Tool calls and observations:
{tool_history}
"""


def generate_final_rca(
    state: InvestigationState,
) -> InvestigationState:
    if not state.evidence_ids:
        raise ValueError("No evidence gathered for RCA generation.")

    context = build_context_from_state(state)

    client = get_llm_client()

    response = client.responses.parse(
        model=GPT_5_4_MINI_MODEL,
        input=context,
        text_format=GeneratedFinalRCA,
    )

    generated = response.output_parsed

    if generated is None:
        raise RuntimeError("LLM did not return a valid final RCA.")

    unknown_evidence_ids = set(generated.evidence_ids) - set(state.evidence_ids)

    if unknown_evidence_ids:
        raise RuntimeError(
            "Final RCA referenced evidence that was not gathered: "
            f"{sorted(unknown_evidence_ids)}"
        )

    final_result = RCAResult(
        incident_id=state.incident.id,
        root_cause=generated.root_cause,
        affected_service=generated.affected_service,
        evidence_ids=generated.evidence_ids,
        explanation=generated.explanation,
        confidence=generated.confidence,
    )

    state.final_result = final_result

    return state
