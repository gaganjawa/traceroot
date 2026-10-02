from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock

import httpx
import pytest
from pydantic import ValidationError
from streamlit.testing.v1 import AppTest

from traceroot.agent.state import Hypothesis, HypothesisStatus, ToolCallRecord
from traceroot.config import LiveEvidenceConfig
from traceroot.domain.incident import Incident
from traceroot.domain.rca import RCAResult
from traceroot.experiments.models import AgentExperimentRecord

APP_PATH = Path(__file__).resolve().parents[2] / "app.py"
LIVE_START_TIME = "2026-10-03T12:00:00+05:30"


def make_record(incident_id: str) -> AgentExperimentRecord:
    return AgentExperimentRecord(
        incident_id=incident_id,
        model="test-model",
        hypotheses=[
            Hypothesis(
                description="Connection pool exhaustion",
                status=HypothesisStatus.SUPPORTED,
            )
        ],
        evidence_ids=["LOG-LIVE-TEST"],
        tool_history=[
            ToolCallRecord(
                tool_name="logs",
                service="checkout-service",
                evidence_ids=["LOG-LIVE-TEST"],
                observations=["Database connection acquisition timed out"],
                reasoning="Inspect checkout errors",
            )
        ],
        stop_reason="model_stop",
        stop_reasoning="Sufficient evidence gathered",
        result=RCAResult(
            incident_id=incident_id,
            root_cause="Database connection pool was exhausted",
            affected_service="checkout-service",
            evidence_ids=["LOG-LIVE-TEST"],
            explanation="Connection acquisition timed out in checkout requests",
            confidence=0.85,
        ),
        latency_ms=123.0,
        timestamp=datetime(2026, 10, 3, tzinfo=UTC),
    )


@pytest.fixture
def app_dependencies(monkeypatch):
    import dotenv

    from traceroot import config
    from traceroot.data import loader
    from traceroot.llm import client
    from traceroot.ui import helpers

    def forbid_external_call(*args, **kwargs):
        raise AssertionError("UI tests must not make external requests")

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(httpx.Client, "send", forbid_external_call)
    monkeypatch.setattr(httpx.AsyncClient, "send", forbid_external_call)
    monkeypatch.setattr(client, "get_llm_client", forbid_external_call)
    dotenv_loader = Mock()
    monkeypatch.setattr(dotenv, "load_dotenv", dotenv_loader)

    live_config = LiveEvidenceConfig(
        loki_base_url="http://loki.test",
        prometheus_base_url="http://prometheus.test",
        github_repo="example/checkout",
        github_service="checkout-service",
    )
    config_loader = Mock(return_value=live_config)
    monkeypatch.setattr(config, "load_live_evidence_config", config_loader)

    frozen_incident = Incident(
        id="INC-001",
        title="Fixture checkout latency",
        description="Frozen incident description",
        start_time=datetime(2026, 9, 25, tzinfo=UTC),
        suspected_services=["checkout-service"],
    )
    fixture_path = Path("data/incidents/INC-001/incident.json")
    monkeypatch.setattr(
        helpers, "discover_incidents", Mock(return_value=[fixture_path])
    )
    monkeypatch.setattr(loader, "load_incident", Mock(return_value=frozen_incident))
    fixture_runner = Mock(
        side_effect=lambda incident, max_tool_calls, **kwargs: make_record(incident.id)
    )
    monkeypatch.setattr(helpers, "run_investigation", fixture_runner)

    def finish_live_investigation(incident, config, max_tool_calls):
        return (
            make_record(incident.id),
            Path("experiments/results/live") / f"{incident.id}-agent.json",
        )

    live_runner = Mock(side_effect=finish_live_investigation)
    monkeypatch.setattr(helpers, "run_live_investigation", live_runner)
    evaluator = Mock()
    monkeypatch.setattr(helpers, "evaluate_result", evaluator)
    return {
        "config": live_config,
        "config_loader": config_loader,
        "dotenv_loader": dotenv_loader,
        "fixture_runner": fixture_runner,
        "live_runner": live_runner,
        "evaluator": evaluator,
    }


def live_app() -> AppTest:
    app = AppTest.from_file(APP_PATH).run()
    app.sidebar.selectbox[0].set_value("Live Incident").run()
    assert not app.exception
    return app


def submit_live(
    app: AppTest,
    *,
    title: str = "Checkout timeout",
    description: str = "Checkout requests are timing out",
    start_time: str = LIVE_START_TIME,
    services: str = "checkout-service, payment-service",
) -> AppTest:
    app.text_input(key="live_title").set_value(title)
    app.text_area(key="live_description").set_value(description)
    app.text_input(key="live_start_time").set_value(start_time)
    app.text_input(key="live_services").set_value(services)
    next(
        button for button in app.button if button.label == "Start Investigation"
    ).click()
    app.run()
    assert not app.exception
    return app


def rendered_text(app: AppTest) -> str:
    return "\n".join(
        str(element.value)
        for kind in ("markdown", "caption", "text", "subheader", "error", "warning")
        for element in getattr(app, kind)
    )


def test_app_preserves_fixture_and_new_demo_modes(app_dependencies):
    app = AppTest.from_file(APP_PATH).run()
    assert app.sidebar.selectbox[0].options == [
        "Existing Evaluation Incident",
        "New Incident",
        "Live Incident",
    ]
    next(
        button for button in app.button if button.label == "Start Investigation"
    ).click()
    app.run()
    assert not app.exception
    app_dependencies["fixture_runner"].assert_called_once()
    assert app.session_state["completed"][0].id == "INC-001"
    app_dependencies["config_loader"].assert_not_called()
    app_dependencies["live_runner"].assert_not_called()

    app.sidebar.selectbox[0].set_value("New Incident").run()
    assert not app.exception
    assert any("no operational evidence" in item.value.lower() for item in app.info)
    assert [item.label for item in app.text_input] == [
        "Title",
        "Start time (ISO 8601, include timezone)",
        "Suspected services (optional, comma-separated)",
    ]
    assert "completed" not in app.session_state


def test_app_live_mode_shows_basic_incident_form(app_dependencies):
    app = live_app()
    assert app.text_input(key="live_title").value == ""
    assert app.text_area(key="live_description").value == ""
    default_start_time = app.text_input(key="live_start_time").value
    assert datetime.fromisoformat(default_start_time).utcoffset() is not None
    assert app.text_input(key="live_services").value == ""
    app.run()
    assert app.text_input(key="live_start_time").value == default_start_time
    app_dependencies["live_runner"].assert_not_called()
    app_dependencies["config_loader"].assert_not_called()


@pytest.mark.parametrize(
    "invalid_input",
    [
        {"title": " "},
        {"description": " "},
        {"start_time": "invalid"},
        {"start_time": "2026-10-03T12:00:00"},
    ],
)
def test_app_live_form_validation_prevents_execution(app_dependencies, invalid_input):
    app = submit_live(live_app(), **invalid_input)
    assert app.error
    assert "completed" not in app.session_state
    app_dependencies["config_loader"].assert_not_called()
    app_dependencies["live_runner"].assert_not_called()


@pytest.mark.parametrize("invalid_config", [{}, {"loki_base_url": "invalid"}])
def test_app_live_mode_reports_missing_or_invalid_configuration(
    app_dependencies, invalid_config
):
    values = {"github_token": "private-token", **invalid_config}
    with pytest.raises(ValidationError) as exc:
        LiveEvidenceConfig.model_validate(values)
    app_dependencies["config_loader"].side_effect = exc.value
    app = submit_live(live_app())
    assert "configuration" in rendered_text(app).lower()
    assert "private-token" not in rendered_text(app)
    assert app.error
    assert "completed" not in app.session_state
    app_dependencies["live_runner"].assert_not_called()


def test_app_live_mode_reports_missing_openai_key(app_dependencies, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY")
    app = submit_live(live_app())
    assert "OPENAI_API_KEY" in rendered_text(app)
    assert "completed" not in app.session_state
    app_dependencies["live_runner"].assert_not_called()


def test_app_live_mode_renders_completed_investigation_and_trace_path(app_dependencies):
    app = submit_live(live_app())
    app_dependencies["live_runner"].assert_called_once()
    incident, record, frozen_path = app.session_state["completed"]
    assert incident.id.startswith("INC-RUNTIME-")
    assert incident.title == "Checkout timeout"
    assert incident.start_time == datetime.fromisoformat(LIVE_START_TIME)
    assert incident.suspected_services == ["checkout-service", "payment-service"]
    assert frozen_path is None
    assert record.incident_id == incident.id
    assert app.session_state["completed_trace_path"].name == f"{incident.id}-agent.json"
    output = rendered_text(app)
    for expected in (
        incident.id,
        "SUPPORTED: Connection pool exhaustion",
        "Inspect checkout errors",
        "Database connection acquisition timed out",
        "LOG-LIVE-TEST",
        "model_stop",
        "Database connection pool was exhausted",
        "0.85",
        str(app.session_state["completed_trace_path"]),
    ):
        assert expected in output
    app_dependencies["dotenv_loader"].assert_called()
    app_dependencies["config_loader"].assert_called_once()
    app_dependencies["fixture_runner"].assert_not_called()


def test_app_live_mode_reports_provider_failure(app_dependencies):
    request = httpx.Request("GET", "https://provider.test/query")
    app_dependencies["live_runner"].side_effect = httpx.HTTPStatusError(
        "Private provider response", request=request, response=httpx.Response(503)
    )
    app = submit_live(live_app())
    assert app.error
    assert "evidence request failed" in rendered_text(app).lower()
    assert "Private provider response" not in rendered_text(app)
    assert "completed" not in app.session_state
    assert "completed_trace_path" not in app.session_state


def test_app_live_mode_reports_no_evidence(app_dependencies):
    app_dependencies["live_runner"].side_effect = ValueError(
        "No evidence gathered for RCA generation."
    )
    app = submit_live(live_app())
    assert "No evidence was gathered for this incident" in rendered_text(app)
    assert "completed" not in app.session_state
    assert "completed_trace_path" not in app.session_state


def test_app_live_results_persist_across_reruns(app_dependencies):
    app = submit_live(live_app())
    incident_id = app.session_state["completed"][0].id
    trace_path = app.session_state["completed_trace_path"]
    app.run()
    assert not app.exception
    assert app.session_state["completed"][0].id == incident_id
    assert app.session_state["completed_trace_path"] == trace_path
    app_dependencies["live_runner"].assert_called_once()


def test_app_mode_change_clears_result_evaluation_and_trace_path(app_dependencies):
    app = submit_live(live_app())
    app.session_state["evaluation"] = object()
    app.sidebar.selectbox[0].set_value("Existing Evaluation Incident").run()
    assert not app.exception
    for key in ("completed", "evaluation", "completed_trace_path"):
        assert key not in app.session_state


def test_app_live_retry_clears_previous_result(app_dependencies):
    app = submit_live(live_app())
    app_dependencies["live_runner"].side_effect = RuntimeError("Investigation failure")
    submit_live(app, title="Retry checkout timeout")
    assert app.error
    for key in ("completed", "evaluation", "completed_trace_path"):
        assert key not in app.session_state
    assert app_dependencies["live_runner"].call_count == 2


def test_app_live_mode_does_not_offer_frozen_evaluation(app_dependencies):
    app = submit_live(live_app())
    assert all(button.label != "Evaluate Result" for button in app.button)
    app_dependencies["evaluator"].assert_not_called()


def test_app_sessions_keep_completed_results_separate(app_dependencies):
    first = submit_live(live_app(), title="First incident")
    first_incident_id = first.session_state["completed"][0].id
    second = submit_live(live_app(), title="Second incident")
    second_incident_id = second.session_state["completed"][0].id
    assert first_incident_id != second_incident_id
    first.run()
    second.run()
    assert not first.exception
    assert not second.exception
    assert first.session_state["completed"][0].id == first_incident_id
    assert second.session_state["completed"][0].id == second_incident_id
    assert first.session_state["completed"][0].title == "First incident"
    assert second.session_state["completed"][0].title == "Second incident"
    assert app_dependencies["live_runner"].call_count == 2
