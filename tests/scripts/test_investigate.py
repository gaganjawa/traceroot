from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.investigate import (
    build_parser,
    build_paths,
    print_agent_result,
    run_investigation,
)
from traceroot.agent.state import Hypothesis, HypothesisStatus, ToolCallRecord
from traceroot.domain.incident import Incident
from traceroot.domain.rca import RCAResult
from traceroot.experiments.models import AgentExperimentRecord


def create_record() -> AgentExperimentRecord:
    return AgentExperimentRecord(
        incident_id="INC-001",
        approach="agent",
        model="gpt-5.4-mini",
        hypotheses=[
            Hypothesis(
                description="Database connection pool exhaustion",
                status=HypothesisStatus.SUPPORTED,
            )
        ],
        evidence_ids=["LOG-001-02", "METRIC-001-02"],
        tool_history=[
            ToolCallRecord(
                tool_name="logs",
                service="checkout-service",
                evidence_ids=["LOG-001-02"],
                observations=["Database connection timeout"],
                reasoning="Check checkout logs",
            )
        ],
        stop_reason="model_stop",
        stop_reasoning="Enough evidence gathered",
        result=RCAResult(
            incident_id="INC-001",
            root_cause="Database connection pool exhaustion",
            affected_service="checkout-service",
            evidence_ids=["LOG-001-02", "METRIC-001-02"],
            explanation="Database connections were exhausted.",
            confidence=0.95,
        ),
        latency_ms=1000,
        timestamp=datetime.now(UTC),
    )


def test_parser_requires_incident_id():
    parser = build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args([])


def test_parser_uses_default_max_tool_calls():
    parser = build_parser()

    args = parser.parse_args(["--incident-id", "INC-001"])

    assert args.incident_id == "INC-001"
    assert args.max_tool_calls == 6


def test_parser_accepts_custom_max_tool_calls():
    parser = build_parser()

    args = parser.parse_args(
        [
            "--incident-id",
            "INC-001",
            "--max-tool-calls",
            "4",
        ]
    )

    assert args.max_tool_calls == 4


def test_build_paths_returns_correct_paths():
    incident_path, output_path = build_paths("INC-001")

    assert incident_path == Path("data/incidents/INC-001/incident.json")
    assert output_path == Path("experiments/results/INC-001-agent.json")


def test_run_investigation_fails_for_missing_incident(tmp_path):
    incident_path = tmp_path / "missing.json"
    output_path = tmp_path / "result.json"

    with (
        patch(
            "scripts.investigate.build_paths",
            return_value=(incident_path, output_path),
        ),
        pytest.raises(
            FileNotFoundError,
            match="Incident not found: INC-999",
        ),
    ):
        run_investigation("INC-999", 6)


def test_run_investigation_loads_incident(tmp_path):
    incident_path = tmp_path / "incident.json"
    incident_path.write_text("{}", encoding="utf-8")
    output_path = tmp_path / "result.json"

    incident = Incident(
        id="INC-001",
        title="Checkout failure",
        description="Checkout requests are timing out.",
        start_time=datetime(2026, 9, 25, tzinfo=UTC),
        suspected_services=["checkout-service"],
    )

    record = create_record()

    with (
        patch(
            "scripts.investigate.build_paths",
            return_value=(incident_path, output_path),
        ),
        patch(
            "scripts.investigate.load_incident",
            return_value=incident,
        ) as mock_load,
        patch(
            "scripts.investigate.run_agent_experiment",
            return_value=record,
        ),
    ):
        run_investigation("INC-001", 6)

    mock_load.assert_called_once_with(incident_path)


def test_run_investigation_calls_agent_experiment(tmp_path):
    incident_path = tmp_path / "incident.json"
    incident_path.write_text("{}", encoding="utf-8")
    output_path = tmp_path / "result.json"

    incident = Incident(
        id="INC-001",
        title="Checkout failure",
        description="Checkout requests are timing out.",
        start_time=datetime(2026, 9, 25, tzinfo=UTC),
        suspected_services=["checkout-service"],
    )

    record = create_record()

    with (
        patch(
            "scripts.investigate.build_paths",
            return_value=(incident_path, output_path),
        ),
        patch(
            "scripts.investigate.load_incident",
            return_value=incident,
        ),
        patch(
            "scripts.investigate.run_agent_experiment",
            return_value=record,
        ) as mock_run,
    ):
        result = run_investigation("INC-001", 4)

    mock_run.assert_called_once_with(
        incident=incident,
        output_path=output_path,
        max_tool_calls=4,
    )

    assert result == record


def test_print_agent_result_prints_expected_output(capsys):
    record = create_record()
    output_path = Path("experiments/results/INC-001-agent.json")

    print_agent_result(record, output_path)

    output = capsys.readouterr().out

    assert "INC-001" in output
    assert "gpt-5.4-mini" in output
    assert "Database connection pool exhaustion" in output
    assert "supported" in output
    assert "logs / checkout-service" in output
    assert "LOG-001-02" in output
    assert "model_stop" in output
    assert "Enough evidence gathered" in output
    assert "checkout-service" in output
    assert "0.95" in output
    assert str(output_path) in output


def test_help_includes_examples_and_arguments(capsys):
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["--help"])
    assert exc.value.code == 0
    output = capsys.readouterr().out
    assert "--incident-id INC-001" in output
    assert "--incident-id INC-002 --max-tool-calls 4" in output
    assert "default: 6" in output
    assert "--getting-started" in output
    assert "experiments/results/<incident-id>-agent.json" in output


def test_getting_started_exits_without_incident_or_investigation(monkeypatch, capsys):
    from scripts.investigate import main

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("sys.argv", ["investigate.py", "--getting-started"])
    with (
        patch("scripts.investigate.run_investigation") as run,
        pytest.raises(SystemExit) as exc,
    ):
        main()
    assert exc.value.code == 0
    run.assert_not_called()
    output = capsys.readouterr().out
    for term in (
        "hypotheses",
        "tool calls",
        "Evidence IDs",
        "stop reason",
        "final RCA",
        "--max-tool-calls",
        "experiments/results/",
    ):
        assert term in output


@pytest.fixture(autouse=True)
def no_external_http():
    with (
        patch("httpx.get", side_effect=AssertionError("Unexpected provider HTTP call")),
        patch(
            "httpx.Client.send",
            side_effect=AssertionError("Unexpected model HTTP call"),
        ),
    ):
        yield


@pytest.fixture
def live_config():
    from traceroot.config import LiveEvidenceConfig

    return LiveEvidenceConfig(
        loki_base_url="https://logs.example.test",
        prometheus_base_url="https://metrics.example.test",
        github_repo="example/checkout",
        github_service="checkout-service",
    )


def live_args():
    return [
        "--live",
        "--title",
        "Checkout failures",
        "--description",
        "Requests time out",
        "--start-time",
        "2026-10-03T12:00:00+05:30",
    ]


def test_live_cli_parser_accepts_required_arguments_and_service_leads():
    args = build_parser().parse_args(
        live_args()
        + [
            "--suspected-service",
            "checkout-service",
            "--suspected-service",
            "payment-service",
        ]
    )
    assert args.live
    assert args.incident_id is None
    assert args.suspected_service == ["checkout-service", "payment-service"]
    assert args.start_time.utcoffset().total_seconds() == 19800
    assert args.max_tool_calls == 6


@pytest.mark.parametrize(
    "timestamp", ["2026-10-03T12:00:00Z", "2026-10-03T12:00:00+05:30"]
)
def test_live_cli_accepts_utc_and_offset_start_times(timestamp):
    args = live_args()
    args[-1] = timestamp
    assert build_parser().parse_args(args).start_time.utcoffset() is not None


@pytest.mark.parametrize("timestamp", ["invalid", "2026-10-03", "2026-10-03T12:00:00"])
def test_live_cli_rejects_invalid_or_naive_start_time(timestamp):
    args = live_args()
    args[-1] = timestamp
    with pytest.raises(SystemExit) as error:
        build_parser().parse_args(args)
    assert error.value.code == 2


def test_cli_rejects_conflicting_fixture_and_live_modes():
    with pytest.raises(SystemExit) as error:
        build_parser().parse_args(live_args() + ["--incident-id", "INC-001"])
    assert error.value.code == 2


@pytest.mark.parametrize("flag", ["--title", "--description", "--start-time"])
def test_live_cli_rejects_missing_required_inputs(monkeypatch, flag):
    from scripts.investigate import main

    args = live_args()
    index = args.index(flag)
    del args[index : index + 2]
    monkeypatch.setattr("sys.argv", ["investigate.py", *args])
    with (
        patch("scripts.investigate.run_live_investigation") as run,
        pytest.raises(SystemExit) as error,
    ):
        main()
    assert error.value.code == 2
    run.assert_not_called()


@pytest.mark.parametrize(
    "flag, value",
    [
        ("--title", " "),
        ("--description", " "),
        ("--suspected-service", " "),
        ("--max-tool-calls", "0"),
        ("--max-tool-calls", "-1"),
    ],
)
def test_live_cli_rejects_invalid_inputs_before_configuration(monkeypatch, flag, value):
    from scripts.investigate import main

    monkeypatch.setattr("sys.argv", ["investigate.py", *live_args(), flag, value])
    with (
        patch("scripts.investigate.load_live_evidence_config") as config,
        pytest.raises(SystemExit) as error,
    ):
        main()
    assert error.value.code == 2
    config.assert_not_called()


@pytest.mark.parametrize(
    "flag, value",
    [
        ("--title", "title"),
        ("--description", "description"),
        ("--start-time", "2026-10-03T12:00:00Z"),
        ("--suspected-service", "checkout-service"),
    ],
)
def test_cli_rejects_live_arguments_in_fixture_mode(monkeypatch, flag, value):
    from scripts.investigate import main

    monkeypatch.setattr(
        "sys.argv", ["investigate.py", "--incident-id", "INC-001", flag, value]
    )
    with (
        patch("scripts.investigate.run_investigation") as run,
        pytest.raises(SystemExit) as error,
    ):
        main()
    assert error.value.code == 2
    run.assert_not_called()


def test_fixture_cli_does_not_load_live_configuration(monkeypatch, capsys):
    from scripts.investigate import main

    monkeypatch.setattr("sys.argv", ["investigate.py", "--incident-id", "INC-001"])
    with (
        patch(
            "scripts.investigate.run_investigation", return_value=create_record()
        ) as run,
        patch("scripts.investigate.load_live_evidence_config") as config,
        patch("scripts.investigate.build_live_runtime") as build,
    ):
        main()
    run.assert_called_once_with(incident_id="INC-001", max_tool_calls=6)
    config.assert_not_called()
    build.assert_not_called()
    assert "experiments/results/INC-001-agent.json" in capsys.readouterr().out


def test_fixture_cli_missing_incident_exits_with_code_two(monkeypatch, capsys):
    from scripts.investigate import main

    monkeypatch.setattr("sys.argv", ["investigate.py", "--incident-id", "INC-999"])
    with (
        patch(
            "scripts.investigate.run_investigation",
            side_effect=FileNotFoundError("Incident not found: INC-999"),
        ),
        pytest.raises(SystemExit) as error,
    ):
        main()
    assert error.value.code == 2
    assert "Incident not found: INC-999" in capsys.readouterr().err


@pytest.mark.parametrize(
    "services",
    [
        [],
        [
            "--suspected-service",
            " checkout-service ",
            "--suspected-service",
            "payment-service",
        ],
    ],
)
def test_live_cli_creates_incident_and_renders_runtime_record(
    monkeypatch, capsys, live_config, services
):
    from scripts.investigate import main

    record = create_record()
    record.incident_id = "INC-RUNTIME-123"
    output_path = Path("experiments/results/live/INC-RUNTIME-123-agent.json")
    monkeypatch.setattr("sys.argv", ["investigate.py", *live_args(), *services])
    with (
        patch("scripts.investigate.load_dotenv") as dotenv,
        patch(
            "scripts.investigate.load_live_evidence_config", return_value=live_config
        ) as config,
        patch(
            "scripts.investigate.run_live_investigation",
            return_value=(record, output_path),
        ) as run,
        patch("scripts.investigate.load_incident") as load,
    ):
        main()
    incident, passed_config, budget = run.call_args.args
    assert incident.id.startswith("INC-RUNTIME-")
    assert incident.title == "Checkout failures"
    assert incident.description == "Requests time out"
    assert incident.start_time.utcoffset().total_seconds() == 19800
    assert incident.suspected_services == (
        ["checkout-service", "payment-service"] if services else []
    )
    assert passed_config is live_config
    assert budget == 6
    dotenv.assert_called_once_with()
    config.assert_called_once_with()
    load.assert_not_called()
    output = capsys.readouterr().out
    assert record.incident_id in output
    assert str(output_path) in output
    assert "Final RCA" in output


def test_live_cli_missing_config_exits_before_activation(monkeypatch, capsys):
    from scripts.investigate import main

    monkeypatch.setattr("sys.argv", ["investigate.py", *live_args()])
    with (
        patch("scripts.investigate.load_dotenv"),
        patch("os.environ", {}),
        patch("scripts.investigate.activate_live_runtime") as activate,
        patch("scripts.investigate.run_agent_experiment") as run,
        pytest.raises(SystemExit) as error,
    ):
        main()
    assert error.value.code == 2
    activate.assert_not_called()
    run.assert_not_called()
    assert "Invalid live input or configuration" in capsys.readouterr().err


def test_live_cli_execution_failure_exits_with_code_one(
    monkeypatch, capsys, live_config
):
    from scripts.investigate import main

    monkeypatch.setattr("sys.argv", ["investigate.py", *live_args()])
    with (
        patch("scripts.investigate.load_dotenv"),
        patch(
            "scripts.investigate.load_live_evidence_config", return_value=live_config
        ),
        patch(
            "scripts.investigate.run_live_investigation",
            side_effect=RuntimeError("Provider unavailable"),
        ),
        pytest.raises(SystemExit) as error,
    ):
        main()
    assert error.value.code == 1
    output = capsys.readouterr()
    assert "Live investigation failed: Provider unavailable" in output.err
    assert not output.out


def test_live_cli_registers_shared_registry_and_activates_before_agent(live_config):
    from scripts.investigate import run_live_investigation
    from traceroot.bootstrap import build_live_runtime
    from traceroot.intake.service import create_incident
    from traceroot.tools import interface
    from traceroot.tools.models import ToolName

    incident = create_incident(
        "Failure", "Requests time out", datetime(2026, 10, 3, tzinfo=UTC)
    )
    runtime = build_live_runtime(live_config)
    previous = interface._default_backend
    record = create_record()

    def run(incident, output_path, max_tool_calls):
        assert runtime.incident_registry.get(incident.id) is incident
        assert runtime.router._incident_registry is runtime.incident_registry
        assert runtime.live_backend.incident_registry is runtime.incident_registry
        assert interface._default_backend is runtime.router
        assert interface.execute_tool(ToolName.LOGS, incident.id) == ["LIVE-EVIDENCE"]
        assert (
            output_path
            == Path("experiments/results/live") / f"{incident.id}-agent.json"
        )
        assert max_tool_calls == 4
        return record

    with (
        patch.object(interface, "_default_backend", previous),
        patch("scripts.investigate.build_live_runtime", return_value=runtime) as build,
        patch.object(
            runtime.live_backend.logs_provider, "query", return_value=["LIVE-EVIDENCE"]
        ),
        patch("scripts.investigate.run_agent_experiment", side_effect=run),
    ):
        result, path = run_live_investigation(incident, live_config, 4)
    assert interface._default_backend is previous
    assert result is record
    assert path.parent == Path("experiments/results/live")
    build.assert_called_once_with(live_config)


def test_live_cli_runner_constructs_runtime_incident_state(live_config):
    from scripts.investigate import run_live_investigation
    from traceroot.intake.service import create_incident
    from traceroot.tools import interface

    incident = create_incident(
        "Failure", "Requests time out", datetime(2026, 10, 3, tzinfo=UTC)
    )
    record = create_record()

    def final_rca(state, llm_usage):
        state.final_result = record.result.model_copy(
            update={"incident_id": incident.id}
        )
        return state

    with (
        patch.object(interface, "_default_backend", interface._default_backend),
        patch("traceroot.experiments.agent.generate_hypotheses", return_value=[]),
        patch(
            "traceroot.experiments.agent.investigate",
            side_effect=lambda state, **kwargs: state,
        ) as investigate,
        patch(
            "traceroot.experiments.agent.verify_hypotheses",
            side_effect=lambda state, **kwargs: state,
        ),
        patch("traceroot.experiments.agent.generate_final_rca", side_effect=final_rca),
        patch("traceroot.experiments.agent.save_agent_experiment_record") as save,
    ):
        result, path = run_live_investigation(incident, live_config, 4)
    state = investigate.call_args.kwargs["state"]
    assert state.incident is incident
    assert investigate.call_args.kwargs["max_tool_calls"] == 4
    assert "tool_executor" not in investigate.call_args.kwargs
    assert result.incident_id == incident.id
    save.assert_called_once_with(result, path)


@pytest.mark.parametrize("flag", ["--help", "--getting-started"])
def test_cli_help_requires_no_live_configuration(flag, monkeypatch, capsys):
    from scripts.investigate import main

    monkeypatch.setattr("sys.argv", ["investigate.py", flag])
    with (
        patch("scripts.investigate.load_live_evidence_config") as config,
        pytest.raises(SystemExit) as error,
    ):
        main()
    assert error.value.code == 0
    config.assert_not_called()
    output = capsys.readouterr().out
    assert "--live" in output
    assert "--start-time" in output


def test_fixture_cli_reports_saved_failure_path_and_reraises(monkeypatch, capsys):
    import traceback

    from scripts.investigate import main

    monkeypatch.setattr("sys.argv", ["investigate.py", "--incident-id", "INC-001"])
    error = RuntimeError("pipeline failed")
    note = "Partial investigation trace saved to: failures/agent-failed-test.json"
    error.add_note(note)
    with (
        patch("scripts.investigate.run_investigation", side_effect=error),
        pytest.raises(RuntimeError) as caught,
    ):
        main()
    assert caught.value is error
    # Fixture mode leaves ordinary exceptions unhandled; Python renders the note.
    assert note in "".join(traceback.format_exception(caught.value))
    assert not capsys.readouterr().out


def test_fixture_cli_file_not_found_reports_saved_failure_path(monkeypatch, capsys):
    from scripts.investigate import main

    monkeypatch.setattr("sys.argv", ["investigate.py", "--incident-id", "INC-001"])
    error = FileNotFoundError("evidence missing")
    note = "Partial investigation trace saved to: failures/agent-failed-test.json"
    error.add_note(note)
    with (
        patch("scripts.investigate.run_investigation", side_effect=error),
        pytest.raises(SystemExit) as caught,
    ):
        main()
    assert caught.value.code == 2
    assert note in capsys.readouterr().err


def test_live_cli_reports_saved_failure_path_and_exits_one(
    monkeypatch, capsys, live_config
):
    from scripts.investigate import main

    monkeypatch.setattr("sys.argv", ["investigate.py", *live_args()])
    error = RuntimeError("Provider unavailable")
    note = "Partial investigation trace saved to: results/live/failures/agent-failed-test.json"
    error.add_note(note)
    with (
        patch("scripts.investigate.load_dotenv"),
        patch(
            "scripts.investigate.load_live_evidence_config", return_value=live_config
        ),
        patch("scripts.investigate.run_live_investigation", side_effect=error),
        pytest.raises(SystemExit) as caught,
    ):
        main()
    assert caught.value.code == 1
    assert caught.value.__cause__ is error
    output = capsys.readouterr()
    assert "Live investigation failed: Provider unavailable" in output.err
    assert note in output.err
    assert not output.out


def test_cli_does_not_report_trace_saved_when_failure_persistence_fails(
    monkeypatch, capsys, live_config
):
    from scripts.investigate import main
    from traceroot.experiments.agent import run_agent_experiment

    monkeypatch.setattr("sys.argv", ["investigate.py", *live_args()])
    original = RuntimeError("Provider unavailable")

    def fail_run(incident, config, budget):
        return run_agent_experiment(incident, Path("results/live/agent.json"), budget)

    with (
        patch("scripts.investigate.load_dotenv"),
        patch(
            "scripts.investigate.load_live_evidence_config", return_value=live_config
        ),
        patch("scripts.investigate.run_live_investigation", side_effect=fail_run),
        patch("traceroot.experiments.agent.generate_hypotheses", side_effect=original),
        patch(
            "traceroot.experiments.agent.save_failed_agent_experiment_record",
            side_effect=OSError("disk full"),
        ),
        pytest.raises(SystemExit) as caught,
    ):
        main()
    assert caught.value.code == 1
    assert caught.value.__cause__ is original
    output = capsys.readouterr()
    assert "trace saved" not in (output.out + output.err).lower()


def test_successful_cli_output_remains_unchanged(monkeypatch, capsys):
    from scripts.investigate import main

    record = create_record()
    target = Path("experiments/results/INC-001-agent.json")
    print_agent_result(record, target)
    expected = capsys.readouterr().out
    monkeypatch.setattr("sys.argv", ["investigate.py", "--incident-id", "INC-001"])
    with patch("scripts.investigate.run_investigation", return_value=record):
        main()
    output = capsys.readouterr()
    assert output.out == expected
    assert output.err == ""


def test_investigate_help_without_credentials():
    import subprocess
    import sys

    code = """
import os
import runpy
import sys
from unittest.mock import patch
os.environ.pop('OPENAI_API_KEY', None)
sys.argv = ['investigate.py', '--help']
with patch('dotenv.load_dotenv'), patch('openai.OpenAI') as client:
    try:
        runpy.run_module('scripts.investigate', run_name='__main__')
    except SystemExit as exc:
        assert exc.code == 0
    else:
        raise AssertionError('help did not exit')
    client.assert_not_called()
"""
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
    assert "usage:" in result.stdout
