from pydantic import BaseModel

from traceroot.agent.state import InvestigationState, ToolCallRecord
from traceroot.llm.client import GPT_5_4_MINI_MODEL, get_llm_client
from traceroot.tools.interface import ToolName, execute_tool


class ToolSelection(BaseModel):
    tool_name: ToolName
    service: str | None = None
    reasoning: str


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
    """


def investigate(
    state: InvestigationState,
    max_tool_calls: int = 6,
) -> InvestigationState:

    if max_tool_calls <= 0:
        raise ValueError("max_tool_calls must be a positive integer.")

    for _ in range(max_tool_calls):
        prompt = build_prompt(state)

        response = get_llm_client().responses.parse(
            model=GPT_5_4_MINI_MODEL,
            input=prompt,
            text_format=ToolSelection,
        )

        selection = response.output_parsed

        if selection is None:
            raise RuntimeError("LLM did not return a valid tool selection.")

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
                evidence_ids=[entry.id for entry in tool_results],
                observations=[str(entry) for entry in tool_results],
                reasoning=selection.reasoning,
            )
        )
    return state
