"""Shared LLM evidence section; query metadata never contains evidence payloads."""

import json

from traceroot.agent.context import EvidencePresentation, build_evidence_presentation
from traceroot.agent.state import InvestigationState
from traceroot.tools.models import ToolName


def prepare_evidence_presentation(
    state: InvestigationState,
    *,
    prioritized_evidence_ids: set[str] | None = None,
) -> EvidencePresentation:
    """Central default-config entry point for prompt evidence selection."""
    return build_evidence_presentation(
        state, prioritized_evidence_ids=prioritized_evidence_ids
    )


def build_evidence_prompt(
    state: InvestigationState,
    *,
    prioritized_evidence_ids: set[str] | None = None,
    presentation: EvidencePresentation | None = None,
) -> str:
    """Use builder defaults centrally, retaining a payload-free query ledger.

    Only the OBSERVED EVIDENCE block is character-bounded. The query ledger is
    per-call control metadata, not another evidence view or a global ID list.
    This pass intentionally does not impose a limit on the entire prompt.
    A supplied presentation is used unchanged; selection (including priorities)
    has already happened and must not be repeated before validation.
    """
    if presentation is None:
        presentation = prepare_evidence_presentation(
            state, prioritized_evidence_ids=prioritized_evidence_ids
        )
    tool_summaries = {}
    for tool in ToolName:
        calls = [
            (index, call)
            for index, call in enumerate(state.tool_history)
            if call.tool_name == tool
        ]
        tool_summaries[tool.value] = {
            "queried": bool(calls),
            "unique_evidence_count": len(
                {evidence_id for _, call in calls for evidence_id in call.evidence_ids}
            ),
            "calls": [
                {
                    "history_index": index,
                    "service": call.service,
                    "returned_count": len(call.evidence_ids),
                    "returned_observations": len(call.observations),
                }
                for index, call in calls
            ],
        }
    limitations = json.dumps(
        {
            "tool_summaries": tool_summaries,
            "stop_reason": state.stop_reason,
            "stop_reasoning": state.stop_reasoning,
            "ambiguous_history_indices": [
                index
                for index, call in enumerate(state.tool_history)
                if len(call.evidence_ids) != len(call.observations)
            ],
        },
        separators=(",", ":"),
    )
    status = (
        "Evidence view is partial because of context budget pressure."
        if presentation.budget_limited
        else "Evidence view is partial because some observations are unavailable."
        if presentation.partial
        else "All unambiguous, deduplicated observations are visible."
    )
    return f"""
{status}
Omitted evidence is unknown, not negative evidence. Omission does not imply absence.
Omitted evidence may contain support or contradiction. Do not reject a hypothesis
or claim merely because evidence was omitted. Cite only visible observations.
A missing rendered summary does not mean a tool was unqueried; consult query metadata.
Query counts describe full returned data, not the number of visible observations.
Queried + zero results means "This completed query returned no matching evidence."
It does NOT mean "The event definitely did not happen."
Unqueried tools provide no query result. service=null does not prove universal coverage.

OBSERVED EVIDENCE
{presentation.rendered}
END OBSERVED EVIDENCE

QUERY RESULTS / LIMITATIONS
{limitations}
"""
