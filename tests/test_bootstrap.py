import importlib
from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from traceroot import bootstrap, config
from traceroot.bootstrap import activate_live_runtime, build_live_runtime
from traceroot.config import LiveEvidenceConfig
from traceroot.domain.incident import Incident
from traceroot.intake.registry import RuntimeIncidentRegistry
from traceroot.tools import interface
from traceroot.tools.backend import FixtureEvidenceBackend
from traceroot.tools.models import ToolName


@pytest.fixture
def live_config():
    return LiveEvidenceConfig(
        loki_base_url="https://logs.example.test",
        prometheus_base_url="https://metrics.example.test",
        github_repo="example/checkout",
        github_service="checkout-service",
        github_token="secret-token",
    )


@patch("traceroot.bootstrap.GitHubCodeChangesProvider")
@patch("traceroot.bootstrap.GitHubDeploymentsProvider")
@patch("traceroot.bootstrap.PrometheusMetricsProvider")
@patch("traceroot.bootstrap.LokiLogsProvider")
@pytest.mark.parametrize("overrides", [False, True])
def test_build_live_runtime_constructs_all_four_providers(
    mock_loki,
    mock_prometheus,
    mock_deployments,
    mock_code_changes,
    live_config,
    overrides,
):
    if overrides:
        live_config = LiveEvidenceConfig(
            **(
                live_config.model_dump()
                | {
                    "github_token": "secret-token",
                    "logs_window_minutes": 20,
                    "metrics_window_minutes": 25,
                    "deployments_window_minutes": 90,
                    "code_changes_window_minutes": 120,
                    "metrics_metric_name": "latency",
                    "metrics_unit": "milliseconds",
                    "metrics_step_seconds": 5,
                    "timeout_seconds": 2.5,
                }
            )
        )
    runtime = build_live_runtime(live_config)
    mock_loki.assert_called_once_with(
        base_url=live_config.loki_base_url,
        window_minutes=live_config.logs_window_minutes,
        timeout_seconds=live_config.timeout_seconds,
    )
    mock_prometheus.assert_called_once_with(
        base_url=live_config.prometheus_base_url,
        metric_name=live_config.metrics_metric_name,
        unit=live_config.metrics_unit,
        window_minutes=live_config.metrics_window_minutes,
        step_seconds=live_config.metrics_step_seconds,
        timeout_seconds=live_config.timeout_seconds,
    )
    for constructor, window in (
        (mock_deployments, live_config.deployments_window_minutes),
        (mock_code_changes, live_config.code_changes_window_minutes),
    ):
        constructor.assert_called_once_with(
            repo=live_config.github_repo,
            service=live_config.github_service,
            token="secret-token",
            window_minutes=window,
            timeout_seconds=live_config.timeout_seconds,
        )
    assert runtime.live_backend.logs_provider is mock_loki.return_value
    assert runtime.live_backend.metrics_provider is mock_prometheus.return_value
    assert runtime.live_backend.deployments_provider is mock_deployments.return_value
    assert runtime.live_backend.code_changes_provider is mock_code_changes.return_value


def test_build_live_runtime_shares_one_registry(live_config):
    runtime = build_live_runtime(live_config)
    assert runtime.live_backend.incident_registry is runtime.incident_registry
    assert runtime.router._incident_registry is runtime.incident_registry
    assert runtime.router._live_backend is runtime.live_backend
    assert isinstance(runtime.router._fixture_backend, FixtureEvidenceBackend)


def make_incident():
    return Incident(
        id="INC-001",
        title="Runtime failure",
        description="Checkout fails",
        start_time=datetime(2026, 10, 3, tzinfo=UTC),
    )


def test_build_live_runtime_preserves_supplied_registry_and_incidents(live_config):
    registry = RuntimeIncidentRegistry()
    incident = make_incident()
    registry.register(incident)
    runtime = build_live_runtime(live_config, incident_registry=registry)
    assert runtime.incident_registry is registry
    assert runtime.live_backend.incident_registry is registry
    assert runtime.router._incident_registry is registry
    assert runtime.incident_registry.get(incident.id) is incident


def test_build_live_runtime_creates_independent_runtimes(live_config):
    first, second = build_live_runtime(live_config), build_live_runtime(live_config)
    first.incident_registry.register(make_incident())
    assert not second.incident_registry.contains("INC-001")
    assert first.router is not second.router
    assert first.live_backend.logs_provider is not second.live_backend.logs_provider


@patch("traceroot.bootstrap.configure_backend")
@patch("httpx.get")
def test_build_live_runtime_does_not_make_http_requests_or_activate(
    mock_get, mock_configure, live_config
):
    previous = interface._default_backend
    build_live_runtime(live_config)
    assert interface._default_backend is previous
    mock_get.assert_not_called()
    mock_configure.assert_not_called()


@patch(
    "traceroot.bootstrap.LokiLogsProvider",
    side_effect=RuntimeError("construction failed"),
)
def test_build_live_runtime_failure_preserves_active_backend(
    mock_provider, live_config
):
    previous = interface._default_backend
    with pytest.raises(RuntimeError, match="construction failed"):
        build_live_runtime(live_config)
    assert interface._default_backend is previous


@patch("traceroot.bootstrap.configure_backend")
def test_activate_live_runtime_configures_existing_router(mock_configure, live_config):
    runtime = build_live_runtime(live_config)
    activate_live_runtime(runtime)
    mock_configure.assert_called_once_with(runtime.router)


@pytest.mark.parametrize(
    "tool_name, provider_name",
    [
        (ToolName.LOGS, "logs_provider"),
        (ToolName.METRICS, "metrics_provider"),
        (ToolName.DEPLOYMENTS, "deployments_provider"),
        (ToolName.CODE_CHANGES, "code_changes_provider"),
    ],
)
@patch("traceroot.tools.interface._default_backend")
def test_activated_runtime_routes_registered_incident_to_live_provider(
    mock_previous_backend,
    live_config,
    tool_name,
    provider_name,
):
    runtime = build_live_runtime(live_config)
    incident = make_incident()
    runtime.incident_registry.register(incident)
    expected = ["LIVE-EVIDENCE"]
    with patch.object(
        getattr(runtime.live_backend, provider_name), "query", return_value=expected
    ) as query:
        activate_live_runtime(runtime)
        activate_live_runtime(runtime)
        assert (
            interface.execute_tool(tool_name, incident.id, "checkout-service")
            is expected
        )
        query.assert_called_once_with(incident=incident, service="checkout-service")
    mock_previous_backend.query.assert_not_called()


@patch("traceroot.tools.interface._default_backend")
def test_activated_runtime_preserves_fixture_queries_for_unregistered_incident(
    mock_previous, live_config
):
    runtime = build_live_runtime(live_config)
    with patch.object(runtime.live_backend, "query") as live_query:
        activate_live_runtime(runtime)
        result = interface.execute_tool(ToolName.LOGS, "INC-001", "checkout-service")
    assert [entry.id for entry in result] == [
        "LOG-001-01",
        "LOG-001-02",
        "LOG-001-03",
        "LOG-001-07",
    ]
    live_query.assert_not_called()


@patch("traceroot.tools.interface._default_backend")
def test_unactivated_runtime_preserves_fixture_default(mock_previous, live_config):
    with patch.object(interface, "_default_backend", FixtureEvidenceBackend()):
        build_live_runtime(live_config)
        result = interface.execute_tool(ToolName.LOGS, "INC-001", "checkout-service")
        assert len(result) == 4
        assert isinstance(interface._default_backend, FixtureEvidenceBackend)


def test_build_live_runtime_passes_no_token_when_missing(live_config):
    data = live_config.model_dump()
    runtime = build_live_runtime(LiveEvidenceConfig(**data))
    assert runtime.live_backend.deployments_provider.token is None
    assert runtime.live_backend.code_changes_provider.token is None


@patch("traceroot.tools.interface._default_backend")
def test_bootstrap_import_does_not_read_environment_or_activate_backend(mock_backend):
    # Reload modules while trapping environment access and unrelated client creation.
    with (
        patch("os.environ", {}),
        patch("dotenv.load_dotenv") as dotenv,
        patch("httpx.get") as get,
    ):
        importlib.reload(config)
        importlib.reload(bootstrap)
        assert interface._default_backend is mock_backend
        dotenv.assert_not_called()
        get.assert_not_called()
