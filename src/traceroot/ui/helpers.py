"""Small adapters for the existing experiment and evaluation workflows."""

from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from traceroot.bootstrap import build_live_runtime
from traceroot.config import LiveEvidenceConfig
from traceroot.domain.incident import Incident
from traceroot.experiments.agent import run_agent_experiment
from traceroot.experiments.models import AgentExperimentRecord
from traceroot.intake.service import create_incident


def discover_incidents(directory: Path) -> list[Path]:
    return sorted(
        path
        for path in directory.glob("*/incident.json")
        if not path.parent.name.startswith("NEW-")
    )


def new_incident(
    title: str, description: str, start_time: str, services: str
) -> Incident:
    if not title.strip() or not description.strip():
        raise ValueError("Title and description are required.")
    return Incident(
        id=f"NEW-{uuid4().hex}",
        title=title.strip(),
        description=description.strip(),
        start_time=datetime.fromisoformat(start_time.strip()),
        suspected_services=[
            service.strip() for service in services.split(",") if service.strip()
        ],
    )


def new_live_incident(
    title: str, description: str, start_time: str, services: str
) -> Incident:
    """Validate live form input through the runtime incident intake service."""
    return create_incident(
        title=title,
        description=description,
        start_time=datetime.fromisoformat(start_time.strip()),
        suspected_services=[
            service.strip() for service in services.split(",") if service.strip()
        ],
    )


def run_investigation(
    incident: Incident, max_tool_calls: int, *, is_new: bool = False
) -> AgentExperimentRecord:
    output_path = Path("experiments/results/ui") / f"{uuid4().hex}-agent.json"
    if not is_new:
        return run_agent_experiment(
            incident, output_path, max_tool_calls=max_tool_calls
        )

    # Existing tools require a local dataset. Supply empty evidence, never fixture
    # evidence from a different incident. Remove this temporary dataset afterward.
    directory = Path("data/incidents")
    directory.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="NEW-", dir=directory) as temporary:
        dataset = Path(temporary)
        incident = incident.model_copy(update={"id": dataset.name})
        (dataset / "incident.json").write_text(
            incident.model_dump_json(), encoding="utf-8"
        )
        (dataset / "logs.jsonl").write_text("", encoding="utf-8")
        for name in ("metrics", "deployments", "changes"):
            (dataset / f"{name}.json").write_text("[]", encoding="utf-8")
        return run_agent_experiment(
            incident, output_path, max_tool_calls=max_tool_calls
        )


def run_live_investigation(
    incident: Incident,
    config: LiveEvidenceConfig,
    max_tool_calls: int,
) -> tuple[AgentExperimentRecord, Path]:
    """Run with an incident-local router without changing process-wide routing."""
    if max_tool_calls <= 0:
        raise ValueError("max_tool_calls must be a positive integer.")

    runtime = build_live_runtime(config)
    runtime.incident_registry.register(incident)
    output_path = Path("experiments/results/live") / f"{incident.id}-agent.json"
    record = run_agent_experiment(
        incident=incident,
        output_path=output_path,
        max_tool_calls=max_tool_calls,
        tool_executor=runtime.router.query,
    )
    return record, output_path


def evaluate_result(record: AgentExperimentRecord, incident_path: Path):
    """Load evaluator-only labels only on an explicit completed-result action."""
    from traceroot.domain.ground_truth import GroundTruth
    from traceroot.evaluation.runner import evaluate_agent_record

    if incident_path not in discover_incidents(Path("data/incidents")):
        raise ValueError("Evaluation requires an existing frozen incident.")
    if record.incident_id != incident_path.parent.name:
        raise ValueError("Result does not match the selected incident.")
    truth_path = Path("data/ground_truth") / f"{record.incident_id}.json"
    truth = GroundTruth.model_validate_json(truth_path.read_text(encoding="utf-8"))
    return evaluate_agent_record(record, truth)
