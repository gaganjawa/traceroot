from pathlib import Path

from pydantic import BaseModel

from traceroot.experiments.models import (
    AgentExperimentRecord,
    BaselineExperimentRecord,
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
