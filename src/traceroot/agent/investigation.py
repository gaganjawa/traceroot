from pydantic import BaseModel

from traceroot.agent.state import InvestigationState, ToolCallRecord
from traceroot.llm.client import LLM_MODEL_GPT_5_4_MINI, get_llm_client
from traceroot.llm.usage import LLMUsage, record_response_usage
from traceroot.tools.interface import ToolName, execute_tool


class ToolSelection(BaseModel):
    tool_name: ToolName | None = None
    service: str | None = None
    reasoning: str
    stop: bool = False


def build_prompt(state: InvestigationState) -> str:
    return f"""
    You are investigating a production software incident.
    
    Incident:
    {state.incident}
    
    Current hypotheses:
    {state.hypotheses}
    
    Evidence IDs gathered:
    {state.evidence_ids}
    
    Previous tool calls and observations:
    {state.tool_history}
    
    Choose the next operational tool that would provide the most useful evidence
    for investigating the current hypotheses.
    
    Do not invent evidence.
    Select only from the available operational tools.
    
    Available tools:
    - logs: application logs, optionally filtered by service
    - metrics: operational metrics, optionally filtered by service
    - deployments: recent deployments, optionally filtered by service
    - code_changes: recent code changes, optionally filtered by service
    
    Use service=None to query across all services.
    
    Do not repeat a tool/service combination already present in tool history.
    
    Set stop=true only when further tool calls are unlikely to add useful evidence.
    When stop=true, do not select a tool or service.
    """


def investigate(
    state: InvestigationState,
    max_tool_calls: int = 6,
    llm_usage: LLMUsage | None = None,
) -> InvestigationState:
    if max_tool_calls <= 0:
        raise ValueError("max_tool_calls must be a positive integer.")

    consecutive_empty_calls = 0

    attempted_tool_keys = {
        (ToolName(record.tool_name), record.service) for record in state.tool_history
    }

    remaining_calls = max_tool_calls - len(state.tool_history)

    if remaining_calls <= 0:
        state.stop_reason = "tool_budget_exhausted"
        state.stop_reasoning = "Maximum number of tool calls reached."
        return state

    client = get_llm_client()

    for _ in range(remaining_calls):
        prompt = build_prompt(state)

        response = client.responses.parse(
            model=LLM_MODEL_GPT_5_4_MINI,
            input=prompt,
            text_format=ToolSelection,
        )

        record_response_usage(
            llm_usage=llm_usage,
            response=response,
        )

        selection = response.output_parsed

        if selection is None:
            raise RuntimeError("LLM did not return a valid tool selection.")

        if selection.stop:
            state.stop_reason = "model_stop"
            state.stop_reasoning = selection.reasoning
            break

        if selection.tool_name is None:
            raise RuntimeError("LLM must select a tool when stop is false.")

        current_tool_key = (
            selection.tool_name,
            selection.service,
        )

        if current_tool_key in attempted_tool_keys:
            state.stop_reason = "duplicate_selection"
            state.stop_reasoning = selection.reasoning
            break

        tool_results = execute_tool(
            tool_name=selection.tool_name,
            incident_id=state.incident.id,
            service=selection.service,
        )

        new_evidence_ids = [
            entry.id for entry in tool_results if entry.id not in state.evidence_ids
        ]

        state.evidence_ids.extend(new_evidence_ids)

        state.tool_history.append(
            ToolCallRecord(
                tool_name=selection.tool_name.value,
                service=selection.service,
                evidence_ids=[entry.id for entry in tool_results],
                observations=[str(entry) for entry in tool_results],
                reasoning=selection.reasoning,
            )
        )

        attempted_tool_keys.add(current_tool_key)

        if not tool_results:
            consecutive_empty_calls += 1
        else:
            consecutive_empty_calls = 0

        if consecutive_empty_calls >= 2:
            state.stop_reason = "consecutive_empty_results"
            state.stop_reasoning = (
                "Investigation has yielded no useful evidence "
                "after multiple tool calls."
            )
            break

    if state.stop_reason is None and len(state.tool_history) >= max_tool_calls:
        state.stop_reason = "tool_budget_exhausted"
        state.stop_reasoning = "Maximum number of tool calls reached."

    return state
