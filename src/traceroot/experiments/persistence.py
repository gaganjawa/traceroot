from pathlib import Path

from traceroot.experiments.models import BaselineExperimentRecord


def save_baseline_record(record: BaselineExperimentRecord, file_path: str) -> Path:

    # Create the output directory if it doesn't exist
    output_path = Path(file_path)
    output_dir = output_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # Serialize the record to JSON
    record_json = record.model_dump_json(indent=4, ensure_ascii=False)

    # Write the JSON to the specified file path
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(record_json)

    return output_path
