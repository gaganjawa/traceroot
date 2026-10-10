import argparse
import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4

from traceroot.evaluation.comparison import run_incident_comparison

DEFAULT_INCIDENT_IDS = [
    "INC-001",
    "INC-002",
    "INC-003",
    "INC-004",
    "INC-005",
    "INC-006",
]


def positive_int(value: str) -> int:
    parsed = int(value)

    if parsed <= 0:
        raise argparse.ArgumentTypeError("Value must be greater than zero")

    return parsed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=("Run the TraceRoot RAG vs Agent comparative evaluation.")
    )

    parser.add_argument(
        "--incident-id",
        action="append",
        dest="incident_ids",
        help=(
            "Incident to evaluate. May be supplied multiple times. "
            "Defaults to INC-001 through INC-006."
        ),
    )

    parser.add_argument(
        "--top-k",
        type=positive_int,
        default=3,
        help="Number of knowledge chunks retrieved by the RAG baseline.",
    )

    parser.add_argument(
        "--max-tool-calls",
        type=positive_int,
        default=6,
        help="Maximum operational tool calls available to the Agent.",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("experiments/comparison"),
        help="Parent directory for a new unique run directory per invocation.",
    )

    args = parser.parse_args()
    if args.incident_ids and len(set(args.incident_ids)) != len(args.incident_ids):
        parser.error("duplicate --incident-id values are not allowed")
    return args


def main() -> int:
    args = parse_args()

    incident_ids = args.incident_ids if args.incident_ids else DEFAULT_INCIDENT_IDS

    args.output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    run_dir = args.output_dir / f"run-{uuid4().hex}"
    run_dir.mkdir()  # Exclusive creation: collisions must never reuse a run.
    (run_dir / "raw" / "failures").mkdir(parents=True)
    (run_dir / "evaluations").mkdir()

    successful_results = []
    failures = []

    print("TraceRoot Comparative Evaluation")
    print(f"Incidents: {', '.join(incident_ids)}")
    print(f"RAG top_k: {args.top_k}")
    print(f"Agent max_tool_calls: {args.max_tool_calls}")
    print(f"Output: {run_dir}")
    print()

    for incident_id in incident_ids:
        print(f"Running {incident_id}...")

        try:
            result = run_incident_comparison(
                incident_id=incident_id,
                top_k=args.top_k,
                max_tool_calls=args.max_tool_calls,
                output_dir=run_dir,
            )

            successful_results.append(result.model_dump(mode="json"))

            print(f"{incident_id}: completed")

            print("  RAG:")
            for metric in result.rag.metrics:
                print(f"    {metric.name}: {metric.score} (passed={metric.passed})")

            print("  Agent:")
            for metric in result.agent.metrics:
                print(f"    {metric.name}: {metric.score} (passed={metric.passed})")

        # One failed incident must not abort the remaining comparison runs.
        except Exception as exc:  # noqa: BLE001
            failures.append(
                {
                    "incident_id": incident_id,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )

            print(f"{incident_id}: FAILED — {type(exc).__name__}: {exc}")

        print()

    summary = {
        "configuration": {
            "incident_ids": incident_ids,
            "top_k": args.top_k,
            "max_tool_calls": args.max_tool_calls,
        },
        "results": successful_results,
        "failures": failures,
    }

    summary_path = run_dir / "summary.json"
    summary_json = json.dumps(summary, indent=2)
    temporary_path = None
    try:
        with NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=run_dir, suffix=".tmp", delete=False
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(summary_json)
        temporary_path.replace(summary_path)
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass  # Cleanup must not mask the original publication failure.

    print(f"Completed: {len(successful_results)}/{len(incident_ids)}")
    print(f"Failures: {len(failures)}")
    print(f"Summary: {summary_path}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
