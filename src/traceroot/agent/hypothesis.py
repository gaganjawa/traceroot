from pydantic import BaseModel

from traceroot.agent.state import Hypothesis
from traceroot.domain.incident import Incident
from traceroot.llm.client import LLM_MODEL_GPT_5_4_MINI, get_llm_client
from traceroot.llm.usage import LLMUsage, record_response_usage


class GeneratedHypotheses(BaseModel):
    hypotheses: list[str]


def build_prompt(
    incident: Incident,
) -> str:
    prompt = f"{incident.title}: {incident.description}: {incident.suspected_services}"
    return prompt


def generate_hypothesis_from_llm(
    incident: Incident,
    max_hypotheses: int,
    llm_usage: LLMUsage | None = None,
) -> list[Hypothesis]:
    prompt = f"""
    You are investigating a production software incident.

    Use only the incident information provided below.
    Do not assume access to logs, metrics, deployments, code changes, or ground truth.
    Do not invent evidence.
    Generate up to {max_hypotheses} distinct and testable root-cause hypotheses.

    Each hypothesis should:
    - describe a plausible technical cause
    - be concise
    - be specific enough to investigate using operational tools
    - remain a hypothesis, not a conclusion
    - avoid claiming certainty without evidence

    Incident ID: {incident.id}
    Title: {incident.title}
    Description: {incident.description}
    Suspected services: {incident.suspected_services}

    Return only the structured hypothesis output.
    """

    response = get_llm_client().responses.parse(
        model=LLM_MODEL_GPT_5_4_MINI,
        input=prompt,
        text_format=GeneratedHypotheses,
    )

    record_response_usage(
        llm_usage=llm_usage,
        response=response,
    )

    generated = response.output_parsed

    if generated is None:
        raise RuntimeError("LLM did not return structured hypotheses")

    return [
        Hypothesis(description=text) for text in generated.hypotheses[:max_hypotheses]
    ]


def generate_hypotheses(
    incident: Incident,
    max_hypotheses: int = 3,
    llm_usage: LLMUsage | None = None,
) -> list[Hypothesis]:

    if max_hypotheses <= 0:
        raise ValueError("max_hypotheses must be > 0")

    hypotheses = generate_hypothesis_from_llm(
        incident,
        max_hypotheses,
        llm_usage=llm_usage,
    )

    return hypotheses
