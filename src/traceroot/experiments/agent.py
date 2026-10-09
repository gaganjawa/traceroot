import logging
from collections.abc import Callable
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
from traceroot.experiments.models import (
    AgentExperimentRecord,
    FailedAgentExperimentRecord,
    FailureStage,
)
from traceroot.experiments.persistence import (
    PARTIAL_TRACE_NOTE_PREFIX,
    save_agent_experiment_record,
    save_failed_agent_experiment_record,
)
from traceroot.llm.client import LLM_MODEL_GPT_5_4_MINI, LLM_PRICING
from traceroot.llm.usage import LLMUsage
from traceroot.tools.backend import EvidenceEntry

logger = logging.getLogger(__name__)

# Only fixed, payload-free diagnostics are persisted verbatim. Arbitrary exception
# text can contain credentials, request/response bodies, URLs, or validation input.
_SAFE_FAILURE_MESSAGES = frozenset(
    {
        "LLM did not return structured hypotheses",
        "max_hypotheses must be > 0",
        "max_tool_calls must be a positive integer.",
        "LLM did not return a valid tool selection.",
        "LLM must select a tool when stop is false.",
        "LLM did not return hypothesis assessments",
        "No evidence gathered for RCA generation.",
        "LLM did not return a valid final RCA.",
        "LLM did not return RCA claim assessments",
        "Agent investigation did not produce a final RCA.",
        "Loki query failed",
        "Prometheus query failed",
    }
)


def _failure_message(exc: Exception, stage: FailureStage) -> str:
    # Do not stringify provider/validation exceptions or invoke custom __str__.
    message = exc.args[0] if len(exc.args) == 1 else None
    if type(message) is str and message in _SAFE_FAILURE_MESSAGES:
        return message[:240]
    return f"Failure during {stage.value}; exception details omitted for safety."[:240]


def run_agent_experiment(
    incident: Incident,
    output_path: Path,
    max_tool_calls: int = 6,
    *,
    tool_executor: Callable[..., list[EvidenceEntry]] | None = None,
) -> AgentExperimentRecord:

    start = perf_counter()

    llm_usage = LLMUsage()

    investigation_state = InvestigationState(incident=incident)
    stage = FailureStage.HYPOTHESIS_GENERATION
    try:
        investigation_state.hypotheses = generate_hypotheses(
            incident=incident,
            llm_usage=llm_usage,
        )

        executor_kwargs = (
            {"tool_executor": tool_executor} if tool_executor is not None else {}
        )
        stage = FailureStage.INVESTIGATION
        investigation_state = investigate(
            state=investigation_state,
            max_tool_calls=max_tool_calls,
            llm_usage=llm_usage,
            **executor_kwargs,
        )

        stage = FailureStage.HYPOTHESIS_VERIFICATION
        investigation_state = verify_hypotheses(
            state=investigation_state, llm_usage=llm_usage
        )

        stage = FailureStage.FINAL_RCA
        investigation_state = generate_final_rca(
            state=investigation_state, llm_usage=llm_usage
        )

        if investigation_state.final_result is None:
            raise RuntimeError("Agent investigation did not produce a final RCA.")

        stage = FailureStage.RECORD_CONSTRUCTION
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
            hypotheses=investigation_state.hypotheses,
            evidence_ids=investigation_state.evidence_ids,
            tool_history=investigation_state.tool_history,
            stop_reason=investigation_state.stop_reason,
            stop_reasoning=investigation_state.stop_reasoning,
            result=investigation_state.final_result,
            model=LLM_MODEL_GPT_5_4_MINI,
            latency_ms=(perf_counter() - start) * 1000,
            timestamp=datetime.now(UTC),
            input_tokens=llm_usage.input_tokens,
            output_tokens=llm_usage.output_tokens,
            llm_calls=llm_usage.llm_calls,
            estimated_cost_usd=estimated_cost_usd,
        )

        stage = FailureStage.PERSISTENCE
        save_agent_experiment_record(agent_experiment_record, output_path)

        return agent_experiment_record
    except Exception as exc:
        try:
            failed_record = FailedAgentExperimentRecord(
                model=LLM_MODEL_GPT_5_4_MINI,
                state=investigation_state.model_copy(deep=True),
                failure_stage=stage,
                failure_type=type(exc).__name__,
                failure_message=_failure_message(exc, stage),
                latency_ms=(perf_counter() - start) * 1000,
                timestamp=datetime.now(UTC),
                input_tokens=llm_usage.input_tokens,
                output_tokens=llm_usage.output_tokens,
                llm_calls=llm_usage.llm_calls,
            )
            failure_path = save_failed_agent_experiment_record(
                failed_record, output_path
            )
            exc.add_note(f"{PARTIAL_TRACE_NOTE_PREFIX}{failure_path}")
        except Exception as persistence_error:  # noqa: BLE001 — preserve pipeline error
            # No traceback or raw exception text: either can expose provider data.
            logger.error(
                "Could not save partial investigation trace for %s (%s), target %s: %s",
                stage.value,
                type(exc).__name__,
                output_path,
                type(persistence_error).__name__,
            )
        raise
