import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

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
        output_dir=next(tmp_path.glob("run-*")),
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

    summary_path = next(tmp_path.glob("run-*/summary.json"))

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


@pytest.fixture
def cli(monkeypatch, tmp_path):
    def configure(*ids):
        monkeypatch.setattr(
            "sys.argv",
            [
                "run_comparison.py",
                "--output-dir",
                str(tmp_path),
                *[arg for incident in ids for arg in ("--incident-id", incident)],
            ],
        )

    configure("INC-001")
    with patch("scripts.run_comparison.run_incident_comparison") as compare:
        compare.side_effect = lambda **kwargs: make_result(kwargs["incident_id"])
        yield configure, compare


def test_reruns_create_distinct_run_directories(cli, tmp_path, capsys):
    _, compare = cli
    assert run_comparison.main() == 0
    assert run_comparison.main() == 0
    paths = [call.kwargs["output_dir"] for call in compare.call_args_list]
    assert paths[0] != paths[1]
    output = capsys.readouterr().out
    for path in paths:
        assert path.parent == tmp_path
        assert path.name.startswith("run-")
        assert (path / "raw" / "failures").is_dir()
        assert (path / "evaluations").is_dir()
        assert (path / "summary.json").is_file()
        assert f"Output: {path}" in output
        assert f"Summary: {path / 'summary.json'}" in output


def test_all_incidents_share_current_run_directory(cli):
    configure, compare = cli
    configure("INC-001", "INC-002")
    run_comparison.main()
    assert len({call.kwargs["output_dir"] for call in compare.call_args_list}) == 1


def test_partial_failure_does_not_mix_with_previous_run(cli):
    _, compare = cli

    def success(**kwargs):
        path = kwargs["output_dir"]
        (path / "raw" / "INC-001-agent.json").write_text("old agent")
        (path / "evaluations" / "INC-001-agent-eval.json").write_text("old evaluation")
        return make_result("INC-001")

    compare.side_effect = success
    run_comparison.main()
    previous = compare.call_args.kwargs["output_dir"]
    before = {
        p.relative_to(previous): p.read_bytes()
        for p in previous.rglob("*")
        if p.is_file()
    }

    def failure(**kwargs):
        (kwargs["output_dir"] / "raw" / "INC-001-rag.json").write_text("new partial")
        raise RuntimeError("failed after raw write")

    compare.side_effect = failure
    assert run_comparison.main() == 1
    current = compare.call_args.kwargs["output_dir"]
    assert not (current / "raw" / "INC-001-agent.json").exists()
    assert list((current / "evaluations").iterdir()) == []
    assert before == {
        p.relative_to(previous): p.read_bytes()
        for p in previous.rglob("*")
        if p.is_file()
    }


def test_subset_run_preserves_historical_artifacts(cli, tmp_path):
    historical = tmp_path / "raw" / "INC-006-agent.json"
    historical.parent.mkdir()
    historical.write_text("historical artifact")
    summary = tmp_path / "summary.json"
    summary.write_text("historical summary")
    run_comparison.main()
    assert historical.read_text() == "historical artifact"
    assert summary.read_text() == "historical summary"


def test_duplicate_incident_ids_are_rejected_before_execution(cli, tmp_path):
    configure, compare = cli
    configure("INC-001", "INC-002", "INC-001")
    with pytest.raises(SystemExit) as caught:
        run_comparison.main()
    assert caught.value.code == 2
    compare.assert_not_called()
    assert list(tmp_path.iterdir()) == []


def test_summary_contains_only_current_run_results(cli):
    configure, compare = cli
    configure("INC-006")
    run_comparison.main()
    configure("INC-001", "INC-002")
    compare.side_effect = [make_result("INC-001"), RuntimeError("current failure")]
    assert run_comparison.main() == 1
    summary = json.loads(
        (compare.call_args.kwargs["output_dir"] / "summary.json").read_text()
    )
    assert [r["incident_id"] for r in summary["results"]] == ["INC-001"]
    assert summary["failures"] == [
        {
            "incident_id": "INC-002",
            "error_type": "RuntimeError",
            "error": "current failure",
        }
    ]
    assert summary["configuration"]["incident_ids"] == ["INC-001", "INC-002"]
    assert set(summary) == {"configuration", "results", "failures"}


def test_summary_publication_is_atomic(cli):
    _, compare = cli
    replace = Path.replace
    publications = []

    def inspect(source, target):
        assert source.parent == target.parent
        assert not target.exists()
        assert json.loads(source.read_text())["results"][0]["incident_id"] == "INC-001"
        publications.append(target)
        return replace(source, target)

    with patch.object(Path, "replace", inspect):
        run_comparison.main()
    run_dir = compare.call_args.kwargs["output_dir"]
    assert publications == [run_dir / "summary.json"]
    assert list(run_dir.glob("*.tmp")) == []


def test_run_directory_collision_does_not_reuse_existing_directory(cli, tmp_path):
    _, compare = cli
    existing = tmp_path / "run-collision"
    existing.mkdir()
    sentinel = existing / "summary.json"
    sentinel.write_text("keep")
    with (
        patch(
            "scripts.run_comparison.uuid4",
            return_value=SimpleNamespace(hex="collision"),
        ),
        pytest.raises(FileExistsError),
    ):
        run_comparison.main()
    compare.assert_not_called()
    assert sentinel.read_text() == "keep"


def test_failed_summary_publication_leaves_run_incomplete(cli):
    _, compare = cli
    with (
        patch.object(Path, "replace", side_effect=OSError("disk error")),
        pytest.raises(OSError),
    ):
        run_comparison.main()
    run_dir = compare.call_args.kwargs["output_dir"]
    assert not (run_dir / "summary.json").exists()
    assert list(run_dir.glob("*.tmp")) == []


def test_interrupted_run_has_no_summary(cli):
    _, compare = cli
    compare.side_effect = KeyboardInterrupt
    with pytest.raises(KeyboardInterrupt):
        run_comparison.main()
    assert not (compare.call_args.kwargs["output_dir"] / "summary.json").exists()
