from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4

from pydantic import BaseModel

from traceroot.experiments.models import (
    AgentExperimentRecord,
    BaselineExperimentRecord,
    FailedAgentExperimentRecord,
)


def persist(
    record: BaseModel,
    file_path: str | Path,
) -> Path:
    output_path = Path(file_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    record_json = record.model_dump_json(
        indent=4,
        ensure_ascii=False,
    )

    output_path.write_text(
        record_json,
        encoding="utf-8",
    )

    return output_path


def save_baseline_record(
    record: BaselineExperimentRecord,
    file_path: str | Path,
) -> Path:
    return persist(record, file_path)


def save_agent_experiment_record(
    record: AgentExperimentRecord,
    file_path: str | Path,
) -> Path:
    return persist(record, file_path)


PARTIAL_TRACE_NOTE_PREFIX = "Partial investigation trace saved to: "


def save_failed_agent_experiment_record(
    record: FailedAgentExperimentRecord,
    output_path: str | Path,
) -> Path:
    """Publish a unique failure snapshot beside the intended successful trace."""
    record_json = record.model_dump_json(indent=4, ensure_ascii=False)
    target = Path(output_path)
    directory = target.parent / "failures"
    directory.mkdir(parents=True, exist_ok=True)
    failure_path = directory / f"{target.stem}-failed-{uuid4().hex}.json"
    temporary_path = None
    try:
        with NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=directory, suffix=".tmp", delete=False
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(record_json)
        temporary_path.replace(failure_path)
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass  # Cleanup must not replace the original write/publication error.
    return failure_path
