from pydantic import BaseModel

from traceroot.agent.state import Hypothesis, HypothesisStatus, InvestigationState
from traceroot.llm.client import LLM_MODEL_GPT_5_4_MINI, get_llm_client
from traceroot.llm.usage import LLMUsage, record_response_usage


class HypothesisAssessment(BaseModel):
    description: str
    status: HypothesisStatus
    reasoning: str


class HypothesisAssessments(BaseModel):
    assessments: list[HypothesisAssessment]


def build_prompt_for_verification(
    incident,
    hypotheses: list[Hypothesis],
    tool_history,
) -> str:
    return f"""
    You are evaluating hypotheses for a production incident.

    Incident:
    {incident}

    Current hypotheses:
    {hypotheses}
    
    Observed evidence from operational tools:
    {tool_history}

    For each existing hypothesis, classify it as:
    - open: evidence is insufficient
    - supported: available evidence supports the hypothesis
    - rejected: available evidence contradicts the hypothesis
    
    Do not invent evidence.
    Do not create new hypotheses.
    Evaluate only the hypotheses supplied.
    """


def verify_hypotheses(
    state: InvestigationState,
    llm_usage: LLMUsage | None = None,
) -> InvestigationState:

    prompt = build_prompt_for_verification(
        incident=state.incident,
        hypotheses=state.hypotheses,
        tool_history=state.tool_history,
    )

    response = get_llm_client().responses.parse(
        model=LLM_MODEL_GPT_5_4_MINI,
        input=prompt,
        text_format=HypothesisAssessments,
    )

    record_response_usage(
        llm_usage=llm_usage,
        response=response,
    )

    generated = response.output_parsed

    if generated is None:
        raise RuntimeError("LLM did not return hypothesis assessments")

    assessment_by_description = {
        assessment.description: assessment for assessment in generated.assessments
    }

    for hypothesis in state.hypotheses:
        assessment = assessment_by_description.get(hypothesis.description)

        if assessment is not None:
            hypothesis.status = assessment.status

    return state
