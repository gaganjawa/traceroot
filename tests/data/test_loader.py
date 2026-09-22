import json
from datetime import datetime

from traceroot.data.loader import load_incident, load_incident_dataset


def test_load_incident(tmp_path):
    incident_data = {
        "id": "INC-001",
        "title": "Database Connection Pool Exhaustion",
        "description": (
            "The checkout service is experiencing timeouts due to "
            "database connection pool exhaustion."
        ),
        "start_time": "2026-09-20T14:30:00",
        "suspected_services": [
            "checkout-service",
            "database-service",
        ],
    }

    incident_file = tmp_path / "incident.json"

    incident_file.write_text(json.dumps(incident_data))

    loaded_incident = load_incident(incident_file)

    assert loaded_incident.id == "INC-001"
    assert loaded_incident.title == incident_data["title"]
    assert loaded_incident.suspected_services == [
        "checkout-service",
        "database-service",
    ]

    assert isinstance(loaded_incident.start_time, datetime)
    assert loaded_incident.start_time.isoformat() == "2026-09-20T14:30:00"


def test_load_incident_dataset(tmp_path):
    incident_data = {
        "id": "INC-002",
        "title": "API Gateway Latency Spike",
        "description": "The API gateway is experiencing increased latency.",
        "start_time": "2026-09-21T10:15:00",
    }

    logs = [
        {
            "id": "LOG-001",
            "timestamp": "2026-09-21T10:16:00",
            "service": "api-gateway",
            "level": "ERROR",
            "message": "Upstream request timed out",
        }
    ]

    metrics = [
        {
            "id": "METRIC-001",
            "timestamp": "2026-09-21T10:16:00",
            "service": "api-gateway",
            "metric": "http_request_duration_p95",
            "value": 1800.0,
            "unit": "ms",
        }
    ]

    deployments = [
        {
            "id": "DEPLOY-001",
            "timestamp": "2026-09-21T10:00:00",
            "service": "api-gateway",
            "version": "v2.1.0",
            "description": "Production deployment",
        }
    ]

    changes = [
        {
            "id": "CHANGE-001",
            "timestamp": "2026-09-21T09:45:00",
            "service": "api-gateway",
            "commit_sha": "abc123",
            "files": ["config/application.yaml"],
            "description": "Configuration update",
        }
    ]

    incident_file = tmp_path / "incident.json"
    incident_file.write_text(json.dumps(incident_data))

    # Write logs to a JSONL file
    logs_file = tmp_path / "logs.jsonl"
    with open(logs_file, "w") as f:
        f.writelines(json.dumps(log) + "\n" for log in logs)

    # Write metrics to a JSON file
    metrics_file = tmp_path / "metrics.json"
    with open(metrics_file, "w") as f:
        json.dump(metrics, f)

    # Write deployments to a JSON file
    deployments_file = tmp_path / "deployments.json"
    with open(deployments_file, "w") as f:
        json.dump(deployments, f)

    # Write changes to a JSON file
    changes_file = tmp_path / "changes.json"
    with open(changes_file, "w") as f:
        json.dump(changes, f)

    dataset = load_incident_dataset(tmp_path)

    assert dataset.incident.id == "INC-002"

    assert len(dataset.logs) == 1
    assert len(dataset.metrics) == 1
    assert len(dataset.deployments) == 1
    assert len(dataset.changes) == 1

    assert dataset.logs[0].id == "LOG-001"
    assert dataset.metrics[0].id == "METRIC-001"
    assert dataset.deployments[0].id == "DEPLOY-001"
    assert dataset.changes[0].id == "CHANGE-001"

    assert not hasattr(dataset, "ground_truth")
