import json
from types import SimpleNamespace
from unittest.mock import patch

from scripts import run_comparison


def make_result(incident_id: str):
    return SimpleNamespace(
        incident_id=incident_id,
        rag=SimpleNamespace(
            metrics=[],
        ),
        agent=SimpleNamespace(
            metrics=[],
        ),
        model_dump=lambda mode="json": {
            "incident_id": incident_id,
            "rag": {"metrics": []},
            "agent": {"metrics": []},
        },
    )


@patch("scripts.run_comparison.run_incident_comparison")
@patch("scripts.run_comparison.parse_args")
def test_main_runs_all_default_incidents(
    mock_parse_args,
    mock_run_incident_comparison,
    tmp_path,
):
    mock_parse_args.return_value = SimpleNamespace(
        incident_ids=None,
        top_k=3,
        max_tool_calls=6,
        output_dir=tmp_path,
    )

    mock_run_incident_comparison.side_effect = [
        make_result(incident_id) for incident_id in run_comparison.DEFAULT_INCIDENT_IDS
    ]

    exit_code = run_comparison.main()

    assert exit_code == 0

    assert mock_run_incident_comparison.call_count == 6

    called_incident_ids = [
        item.kwargs["incident_id"]
        for item in mock_run_incident_comparison.call_args_list
    ]

    assert called_incident_ids == run_comparison.DEFAULT_INCIDENT_IDS


@patch("scripts.run_comparison.run_incident_comparison")
@patch("scripts.run_comparison.parse_args")
def test_main_passes_top_k_and_max_tool_calls(
    mock_parse_args,
    mock_run_incident_comparison,
    tmp_path,
):
    mock_parse_args.return_value = SimpleNamespace(
        incident_ids=["INC-001"],
        top_k=4,
        max_tool_calls=7,
        output_dir=tmp_path,
    )

    mock_run_incident_comparison.return_value = make_result("INC-001")

    exit_code = run_comparison.main()

    assert exit_code == 0

    mock_run_incident_comparison.assert_called_once_with(
        incident_id="INC-001",
        top_k=4,
        max_tool_calls=7,
        output_dir=tmp_path,
    )


@patch("scripts.run_comparison.run_incident_comparison")
@patch("scripts.run_comparison.parse_args")
def test_main_continues_after_incident_failure(
    mock_parse_args,
    mock_run_incident_comparison,
    tmp_path,
):
    mock_parse_args.return_value = SimpleNamespace(
        incident_ids=[
            "INC-001",
            "INC-002",
            "INC-003",
        ],
        top_k=3,
        max_tool_calls=6,
        output_dir=tmp_path,
    )

    mock_run_incident_comparison.side_effect = [
        make_result("INC-001"),
        RuntimeError("evaluation failed"),
        make_result("INC-003"),
    ]

    exit_code = run_comparison.main()

    assert exit_code == 1

    assert mock_run_incident_comparison.call_count == 3

    called_incident_ids = [
        item.kwargs["incident_id"]
        for item in mock_run_incident_comparison.call_args_list
    ]

    assert called_incident_ids == [
        "INC-001",
        "INC-002",
        "INC-003",
    ]


@patch("scripts.run_comparison.run_incident_comparison")
@patch("scripts.run_comparison.parse_args")
def test_main_writes_summary_file(
    mock_parse_args,
    mock_run_incident_comparison,
    tmp_path,
):
    mock_parse_args.return_value = SimpleNamespace(
        incident_ids=[
            "INC-001",
            "INC-002",
        ],
        top_k=3,
        max_tool_calls=6,
        output_dir=tmp_path,
    )

    mock_run_incident_comparison.side_effect = [
        make_result("INC-001"),
        RuntimeError("boom"),
    ]

    exit_code = run_comparison.main()

    assert exit_code == 1

    summary_path = tmp_path / "summary.json"

    assert summary_path.exists()

    summary = json.loads(summary_path.read_text())

    assert summary["configuration"] == {
        "incident_ids": [
            "INC-001",
            "INC-002",
        ],
        "top_k": 3,
        "max_tool_calls": 6,
    }

    assert len(summary["results"]) == 1
    assert summary["results"][0]["incident_id"] == "INC-001"

    assert summary["failures"] == [
        {
            "incident_id": "INC-002",
            "error_type": "RuntimeError",
            "error": "boom",
        }
    ]


@patch("scripts.run_comparison.run_incident_comparison")
@patch("scripts.run_comparison.parse_args")
def test_main_returns_zero_when_all_succeed(
    mock_parse_args,
    mock_run_incident_comparison,
    tmp_path,
):
    mock_parse_args.return_value = SimpleNamespace(
        incident_ids=[
            "INC-001",
            "INC-002",
        ],
        top_k=3,
        max_tool_calls=6,
        output_dir=tmp_path,
    )

    mock_run_incident_comparison.side_effect = [
        make_result("INC-001"),
        make_result("INC-002"),
    ]

    assert run_comparison.main() == 0


@patch("scripts.run_comparison.run_incident_comparison")
@patch("scripts.run_comparison.parse_args")
def test_main_returns_one_when_any_incident_fails(
    mock_parse_args,
    mock_run_incident_comparison,
    tmp_path,
):
    mock_parse_args.return_value = SimpleNamespace(
        incident_ids=[
            "INC-001",
            "INC-002",
        ],
        top_k=3,
        max_tool_calls=6,
        output_dir=tmp_path,
    )

    mock_run_incident_comparison.side_effect = [
        make_result("INC-001"),
        ValueError("bad incident"),
    ]

    assert run_comparison.main() == 1
