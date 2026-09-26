import argparse
from pathlib import Path

from traceroot.data.loader import load_incident
from traceroot.experiments.agent import run_agent_experiment
from traceroot.experiments.models import AgentExperimentRecord

GETTING_STARTED = """TraceRoot: Getting Started

1. From the repository root, run uv sync and set OPENAI_API_KEY in .env
   or your environment. Live investigations make model API calls.
2. Choose an incident folder from data/incidents/, such as INC-001.
3. Set --max-tool-calls (default 6): the maximum number of evidence queries,
   not the total number of LLM requests. The agent may stop earlier.
4. Run an investigation using one of the examples below.
5. Review hypotheses: possible causes marked OPEN (unresolved), SUPPORTED
   (backed by evidence), or REJECTED (not supported after verification).
6. Inspect tool calls: queries of local logs, metrics, deployments, or code
   changes. Evidence IDs identify returned records so you can trace RCA claims.
7. Inspect the stop reason and its reasoning: model_stop means the model chose
   to stop; tool_budget_exhausted means the query limit was reached;
   duplicate_selection means a repeated query was blocked;
   consecutive_empty_results means two successive queries returned no evidence.
   Stopping does not by itself establish a root cause.
8. Review the final RCA (root-cause analysis): proposed cause, affected service,
   explanation, confidence, and evidence IDs. No evidence means an ungrounded RCA.

Results and full tool observations are saved to
experiments/results/<incident-id>-agent.json. Repeating an incident overwrites
that CLI result file. The terminal prints a compact summary.

Examples:
  uv run python scripts/investigate.py --incident-id INC-001
  uv run python scripts/investigate.py --incident-id INC-002 --max-tool-calls 4

For a guided UI, run: uv run streamlit run app.py
The UI also accepts new incidents (currently without operational evidence) and
can optionally evaluate completed frozen incidents. Ground truth is loaded only
by the evaluator, never by the investigation agent.
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Investigate a local TraceRoot incident and save an evidence-linked "
            "root-cause analysis. Run from the repository root with OPENAI_API_KEY set."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  uv run python scripts/investigate.py --incident-id INC-001
  uv run python scripts/investigate.py --incident-id INC-002 --max-tool-calls 4

Results: experiments/results/<incident-id>-agent.json (overwritten on rerun).
Use --getting-started for the workflow and explanations of the output.
""",
    )

    parser.add_argument(
        "--incident-id",
        required=True,
        help="Folder name under data/incidents/, such as INC-001 (required for an investigation).",
    )

    parser.add_argument(
        "--max-tool-calls",
        type=int,
        default=6,
        help="Maximum evidence queries, as a positive integer (default: 6). The agent may stop earlier; this is not an LLM-call limit.",
    )

    parser.add_argument(
        "--getting-started",
        action="version",
        version=GETTING_STARTED,
        help="Print a guided walkthrough and exit; no incident or API key needed.",
    )

    return parser


def print_agent_result(
    record: AgentExperimentRecord,
    output_path: Path,
) -> None:
    print("\nTraceRoot Investigation")
    print("=" * 23)

    print(f"\nIncident: {record.incident_id}")
    print(f"Model: {record.model}")

    print("\nHypotheses")
    print("-" * 10)

    for index, hypothesis in enumerate(record.hypotheses, start=1):
        print(f"{index}. {hypothesis.description}")
        print(f"   Status: {hypothesis.status.value}")

    print("\nInvestigation Trace")
    print("-" * 19)

    for index, tool_call in enumerate(record.tool_history, start=1):
        service = tool_call.service or "all services"
        evidence = ", ".join(tool_call.evidence_ids) or "none"

        print(f"{index}. {tool_call.tool_name} / {service}")
        print(f"   Evidence: {evidence}")

    print("\nStop Reason")
    print("-" * 11)
    print(record.stop_reason or "none")

    if record.stop_reasoning:
        print(f"Reasoning: {record.stop_reasoning}")

    print("\nFinal RCA")
    print("-" * 9)
    print(f"Root Cause: {record.result.root_cause}")
    print(f"Affected Service: {record.result.affected_service or 'unknown'}")
    print(f"Explanation: {record.result.explanation}")
    print(f"Confidence: {record.result.confidence}")

    print("\nEvidence")
    print("-" * 8)

    if record.result.evidence_ids:
        for evidence_id in record.result.evidence_ids:
            print(f"- {evidence_id}")
    else:
        print("none")

    print(f"\nTrace saved to: {output_path}")


def build_paths(incident_id: str) -> tuple[Path, Path]:
    incident_path = Path("data/incidents") / incident_id / "incident.json"
    output_path = Path("experiments/results") / f"{incident_id}-agent.json"
    return incident_path, output_path


def run_investigation(
    incident_id: str,
    max_tool_calls: int,
) -> AgentExperimentRecord:
    incident_path, output_path = build_paths(incident_id)

    if not incident_path.exists():
        raise FileNotFoundError(f"Incident not found: {incident_id}")

    incident = load_incident(incident_path)

    return run_agent_experiment(
        incident=incident,
        output_path=output_path,
        max_tool_calls=max_tool_calls,
    )


def main() -> None:

    parser = build_parser()
    args = parser.parse_args()

    try:
        record = run_investigation(
            incident_id=args.incident_id,
            max_tool_calls=args.max_tool_calls,
        )
    except FileNotFoundError as ex:
        parser.error(str(ex))
        return

    _, output_path = build_paths(incident_id=args.incident_id)
    print_agent_result(record=record, output_path=output_path)


if __name__ == "__main__":
    main()
