from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

from traceroot.agent.hypothesis import generate_hypotheses
from traceroot.agent.investigation import investigate
from traceroot.agent.rca import generate_final_rca
from traceroot.agent.state import InvestigationState
from traceroot.agent.verification import verify_hypotheses
from traceroot.domain.incident import Incident
from traceroot.experiments.models import AgentExperimentRecord
from traceroot.experiments.persistence import save_agent_experiment_record
from traceroot.llm.client import LLM_MODEL_GPT_5_4_MINI


def run_agent_experiment(
    incident: Incident,
    output_path: Path,
    max_tool_calls: int = 6,
) -> AgentExperimentRecord:

    start = perf_counter()

    hypotheses = generate_hypotheses(incident)

    investigation_state = InvestigationState(
        incident=incident,
        hypotheses=hypotheses,
    )

    investigation_state = investigate(
        state=investigation_state, max_tool_calls=max_tool_calls
    )

    investigation_state = verify_hypotheses(state=investigation_state)

    final_state = generate_final_rca(state=investigation_state)

    if final_state.final_result is None:
        raise RuntimeError("Agent investigation did not produce a final RCA.")

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
    )

    save_agent_experiment_record(agent_experiment_record, output_path)

    return agent_experiment_record
