"""Assertions shared by captured-prompt integration tests."""

import json

from traceroot.agent.context import AgentContextConfig, build_evidence_presentation
from traceroot.agent.state import ToolCallRecord


def add_large_history(state):
    record = ToolCallRecord(
        tool_name="logs",
        service="bulk-service",
        evidence_ids=[f"BULK-{index:04d}" for index in range(240)],
        observations=[
            f"UNIQUE-OBS-{index:04d}: " + ('escaped "value"\\\n☃ ' * 80)
            for index in range(240)
        ],
        reasoning="TOOL-REASONING-MUST-NOT-BECOME-EVIDENCE",
    )
    state.tool_history.append(record)
    state.evidence_ids.extend(record.evidence_ids)
    return state


def evidence_block(prompt):
    assert prompt.count("\nOBSERVED EVIDENCE\n") == 1
    assert prompt.count("\nEND OBSERVED EVIDENCE\n") == 1
    return prompt.split("\nOBSERVED EVIDENCE\n", 1)[1].split(
        "\nEND OBSERVED EVIDENCE\n", 1
    )[0]


def query_metadata(prompt):
    section = prompt.split("\nQUERY RESULTS / LIMITATIONS\n", 1)[1]
    return json.JSONDecoder().raw_decode(section)[0]


def assert_prompt_evidence(prompt, state, *, priorities=None):
    expected = build_evidence_presentation(state, prioritized_evidence_ids=priorities)
    block = evidence_block(prompt)
    assert block == expected.rendered
    assert len(block) <= AgentContextConfig().max_evidence_chars
    assert len(expected.observations) <= AgentContextConfig().max_observations
    visible_positions = {
        (o.history_index, o.observation_index) for o in expected.observations
    }
    for history_index, record in enumerate(state.tool_history):
        for index, observation in enumerate(record.observations):
            escaped = json.dumps(observation)[1:-1]
            if (history_index, index) in visible_positions:
                assert escaped in block
            elif observation.startswith("UNIQUE-OBS-"):
                assert escaped not in prompt
                # Bulk IDs must not leak through query metadata/global ID lists.
                if record.evidence_ids[index] not in (priorities or set()):
                    assert record.evidence_ids[index] not in prompt
    assert "TOOL-REASONING-MUST-NOT-BECOME-EVIDENCE" not in prompt
    if expected.budget_limited:
        assert "Evidence view is partial because of context budget pressure." in prompt
        assert "Omission does not imply absence." in prompt
        assert "unknown, not negative evidence" in prompt
    return expected
