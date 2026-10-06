"""Deterministic, whole-observation views of full investigation evidence.

These are presentation models only; the persisted state is never modified.
Character limits measure the JSON text (Python characters), not tokens or bytes.
"""

import json
from collections import deque
from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from pydantic import BaseModel

from traceroot.agent.state import InvestigationState


@dataclass(frozen=True)
class AgentContextConfig:
    max_evidence_chars: int = 32_000
    max_observations: int = 100

    def __post_init__(self) -> None:
        for name in ("max_evidence_chars", "max_observations"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")


class PresentedObservation(BaseModel):
    history_index: int
    observation_index: int
    tool_name: str
    service: str | None
    evidence_id: str
    observation: str


class ContextSummary(BaseModel):
    tool_name: str
    queried: bool
    total_observations: int
    included_observations: int
    omitted_observations: int


class EvidencePresentation(BaseModel):
    observations: list[PresentedObservation]
    summaries: list[ContextSummary]
    partial: bool
    rendered: str
    budget_limited: bool = False


_OMISSION_WARNING = "Omitted evidence may contain support or contradiction; omission does not prove absence."
_BUDGET_WARNING = "Evidence context omitted due to budget."


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"))


def _round_robin[T](groups: Iterable[Iterable[T]]) -> Iterator[T]:
    pending = deque(iter(group) for group in groups)
    while pending:
        group = pending.popleft()
        try:
            yield next(group)
        except StopIteration:
            continue
        pending.append(group)


def _positional(items: list[PresentedObservation]) -> Iterator[PresentedObservation]:
    """First, last, then breadth-first interval midpoints with earlier ties."""
    yield items[0]
    if len(items) == 1:
        return
    yield items[-1]
    intervals = deque([(1, len(items) - 2)])
    while intervals:
        left, right = intervals.popleft()
        if left > right:
            continue
        middle = (left + right) // 2
        yield items[middle]
        intervals.extend(((left, middle - 1), (middle + 1, right)))


def build_evidence_presentation(
    state: InvestigationState,
    *,
    config: AgentContextConfig | None = None,
    prioritized_evidence_ids: set[str] | None = None,
) -> EvidencePresentation:
    """Select evidence fairly across tools, services, calls, then positions.

    Exact duplicates retain their earliest provenance; duplicate occurrences and
    misaligned observations count as omitted returned observations. Summaries are
    in first-query order. Selected observations render in original history order.
    Unknown priority IDs have no effect. budget_limited indicates that character
    or observation limits prevented the complete deduplicated view from fitting;
    ambiguous associations and duplicates alone do not set it.

    If normal metadata cannot fit, return no observations and retain all summary
    counts in the model. rendered falls back to a JSON warning string, then the
    empty JSON object {} if at least two characters fit, then the empty string
    for budgets of zero or one (no JSON document). The character bound always
    holds. budget_limited remains internal, so consumers must inspect the model
    rather than assume rendered always contains the normal JSON object schema.
    partial reports omitted observations, including in this fallback; an empty
    history or only empty queries therefore remains partial=False.
    """
    config = config if config is not None else AgentContextConfig()
    totals: dict[str, int] = {}
    scopes: dict[str, dict[str | None, list[list[PresentedObservation]]]] = {}
    seen: set[tuple[str, str | None, str, str]] = set()
    candidates: list[PresentedObservation] = []
    for history_index, record in enumerate(state.tool_history):
        totals[record.tool_name] = totals.get(record.tool_name, 0) + len(
            record.observations
        )
        if len(record.evidence_ids) != len(record.observations):
            continue
        call = []
        for observation_index, (evidence_id, observation) in enumerate(
            zip(record.evidence_ids, record.observations, strict=True)
        ):
            key = (record.tool_name, record.service, evidence_id, observation)
            if key in seen:
                continue
            seen.add(key)
            item = PresentedObservation(
                history_index=history_index,
                observation_index=observation_index,
                tool_name=record.tool_name,
                service=record.service,
                evidence_id=evidence_id,
                observation=observation,
            )
            call.append(item)
            candidates.append(item)
        if call:
            scopes.setdefault(record.tool_name, {}).setdefault(
                record.service, []
            ).append(call)

    encoded = {
        (item.history_index, item.observation_index): _json(item.model_dump())
        for item in candidates
    }
    included = dict.fromkeys(totals, 0)
    total = sum(totals.values())
    budget_limited = False

    def metadata(count: int) -> tuple[list[ContextSummary], bool, str]:
        summaries = [
            ContextSummary(
                tool_name=tool,
                queried=True,
                total_observations=value,
                included_observations=included[tool],
                omitted_observations=value - included[tool],
            )
            for tool, value in totals.items()
        ]
        partial = count < total
        # Leave the observations array empty to measure the complete envelope.
        envelope = _json(
            {
                "observations": [],
                "summaries": [summary.model_dump() for summary in summaries],
                "partial": partial,
                "omission_warning": _OMISSION_WARNING if partial else None,
            }
        )
        return summaries, partial, envelope

    def size(count: int, observation_chars: int) -> int:
        return len(metadata(count)[2]) + observation_chars + max(0, count - 1)

    # Try the complete view first: removing the warning can make it fit even
    # when the partial envelope would not. Never concatenate an oversized view.
    for item in candidates:
        included[item.tool_name] += 1
    all_chars = sum(len(value) for value in encoded.values())
    if (
        len(candidates) <= config.max_observations
        and size(len(candidates), all_chars) <= config.max_evidence_chars
    ):
        selected = candidates
    else:
        budget_limited = True
        included = dict.fromkeys(totals, 0)
        if size(0, 0) > config.max_evidence_chars:
            summaries, partial, _ = metadata(0)
            warning = _json(_BUDGET_WARNING)
            rendered = next(
                marker
                for marker in (warning, "{}", "")
                if len(marker) <= config.max_evidence_chars
            )
            return EvidencePresentation(
                observations=[],
                summaries=summaries,
                partial=partial,
                rendered=rendered,
                budget_limited=True,
            )
        selected = []
        observation_chars = 0
        priorities = prioritized_evidence_ids or set()
        priority_items = [item for item in candidates if item.evidence_id in priorities]
        general = _round_robin(
            _round_robin(
                _round_robin(_positional(call) for call in calls)
                for calls in services.values()
            )
            for services in scopes.values()
        )
        for group in (priority_items, general):
            for item in group:
                if group is general and item.evidence_id in priorities:
                    continue
                if len(selected) >= config.max_observations:
                    break
                chars = len(encoded[item.history_index, item.observation_index])
                included[item.tool_name] += 1
                if (
                    size(len(selected) + 1, observation_chars + chars)
                    <= config.max_evidence_chars
                ):
                    selected.append(item)
                    observation_chars += chars
                else:
                    included[item.tool_name] -= 1

    selected = sorted(
        selected, key=lambda item: (item.history_index, item.observation_index)
    )
    summaries, partial, envelope = metadata(len(selected))
    # Replace only the known empty leading array, after exact size accounting.
    rendered = (
        '{"observations":['
        + ",".join(
            encoded[item.history_index, item.observation_index] for item in selected
        )
        + envelope[len('{"observations":[') :]
    )
    return EvidencePresentation(
        observations=selected,
        summaries=summaries,
        partial=partial,
        rendered=rendered,
        budget_limited=budget_limited,
    )
