import argparse
from pathlib import Path

from traceroot.data.loader import load_incident
from traceroot.experiments.agent import run_agent_experiment
from traceroot.experiments.models import AgentExperimentRecord


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a TraceRoot incident investigation."
    )

    parser.add_argument(
        "--incident-id",
        required=True,
        help="Incident ID to investigate, e.g. INC-001",
    )

    parser.add_argument(
        "--max-tool-calls",
        type=int,
        default=6,
        help="Maximum number of tools to investigate, e.g. 6",
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
