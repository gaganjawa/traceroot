from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

from traceroot.agent.hypothesis import generate_hypotheses
from traceroot.agent.investigation import investigate
from traceroot.agent.rca import generate_final_rca
from traceroot.agent.state import InvestigationState
from traceroot.agent.verification import verify_hypotheses
from traceroot.domain.incident import Incident
from traceroot.evaluation.efficiency import calculate_llm_cost
from traceroot.experiments.models import AgentExperimentRecord
from traceroot.experiments.persistence import save_agent_experiment_record
from traceroot.llm.client import LLM_MODEL_GPT_5_4_MINI, LLM_PRICING
from traceroot.llm.usage import LLMUsage


def run_agent_experiment(
    incident: Incident,
    output_path: Path,
    max_tool_calls: int = 6,
) -> AgentExperimentRecord:

    start = perf_counter()

    llm_usage = LLMUsage()

    hypotheses = generate_hypotheses(
        incident=incident,
        llm_usage=llm_usage,
    )

    investigation_state = InvestigationState(
        incident=incident,
        hypotheses=hypotheses,
    )

    investigation_state = investigate(
        state=investigation_state,
        max_tool_calls=max_tool_calls,
        llm_usage=llm_usage,
    )

    investigation_state = verify_hypotheses(
        state=investigation_state, llm_usage=llm_usage
    )

    final_state = generate_final_rca(state=investigation_state, llm_usage=llm_usage)

    if final_state.final_result is None:
        raise RuntimeError("Agent investigation did not produce a final RCA.")

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

    agent_experiment_record = AgentExperimentRecord(
        incident_id=incident.id,
        hypotheses=final_state.hypotheses,
        evidence_ids=final_state.evidence_ids,
        tool_history=final_state.tool_history,
        stop_reason=final_state.stop_reason,
        stop_reasoning=final_state.stop_reasoning,
        result=final_state.final_result,
        model=LLM_MODEL_GPT_5_4_MINI,
        latency_ms=(perf_counter() - start) * 1000,
        timestamp=datetime.now(UTC),
        input_tokens=llm_usage.input_tokens,
        output_tokens=llm_usage.output_tokens,
        llm_calls=llm_usage.llm_calls,
        estimated_cost_usd=estimated_cost_usd,
    )

    save_agent_experiment_record(agent_experiment_record, output_path)

    return agent_experiment_record
