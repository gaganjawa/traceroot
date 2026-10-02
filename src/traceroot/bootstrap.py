"""Construct live evidence dependencies and explicitly activate process-local routing."""

from dataclasses import dataclass

from traceroot.config import LiveEvidenceConfig
from traceroot.intake.registry import RuntimeIncidentRegistry
from traceroot.integrations.live_code_changes import GitHubCodeChangesProvider
from traceroot.integrations.live_deployments import GitHubDeploymentsProvider
from traceroot.integrations.live_logs import LokiLogsProvider
from traceroot.integrations.live_metrics import PrometheusMetricsProvider
from traceroot.tools.backend import FixtureEvidenceBackend
from traceroot.tools.interface import configure_backend
from traceroot.tools.live_backend import LiveEvidenceBackend
from traceroot.tools.router import EvidenceBackendRouter


@dataclass(frozen=True)
class LiveEvidenceRuntime:
    """Keep the registry callers register into alongside the backend and router."""

    incident_registry: RuntimeIncidentRegistry
    live_backend: LiveEvidenceBackend
    router: EvidenceBackendRouter


def build_live_runtime(
    config: LiveEvidenceConfig,
    *,
    incident_registry: RuntimeIncidentRegistry | None = None,
) -> LiveEvidenceRuntime:
    """Build an independent runtime without activating routing or querying providers."""
    if incident_registry is None:
        incident_registry = RuntimeIncidentRegistry()

    logs_provider = LokiLogsProvider(
        base_url=config.loki_base_url,
        window_minutes=config.logs_window_minutes,
        timeout_seconds=config.timeout_seconds,
    )

    metrics_provider = PrometheusMetricsProvider(
        base_url=config.prometheus_base_url,
        metric_name=config.metrics_metric_name,
        unit=config.metrics_unit,
        window_minutes=config.metrics_window_minutes,
        step_seconds=config.metrics_step_seconds,
        timeout_seconds=config.timeout_seconds,
    )

    github_token = (
        config.github_token.get_secret_value()
        if config.github_token is not None
        else None
    )

    deployments_provider = GitHubDeploymentsProvider(
        repo=config.github_repo,
        service=config.github_service,
        token=github_token,
        window_minutes=config.deployments_window_minutes,
        timeout_seconds=config.timeout_seconds,
    )

    code_changes_provider = GitHubCodeChangesProvider(
        repo=config.github_repo,
        service=config.github_service,
        token=github_token,
        window_minutes=config.code_changes_window_minutes,
        timeout_seconds=config.timeout_seconds,
    )

    live_backend = LiveEvidenceBackend(
        incident_registry=incident_registry,
        logs_provider=logs_provider,
        metrics_provider=metrics_provider,
        deployments_provider=deployments_provider,
        code_changes_provider=code_changes_provider,
    )

    fixture_backend = FixtureEvidenceBackend()

    router = EvidenceBackendRouter(
        fixture_backend=fixture_backend,
        live_backend=live_backend,
        incident_registry=incident_registry,
    )

    return LiveEvidenceRuntime(
        incident_registry=incident_registry,
        live_backend=live_backend,
        router=router,
    )


def activate_live_runtime(
    runtime: LiveEvidenceRuntime,
) -> None:
    """Select this runtime for execute_tool calls in the current process."""
    configure_backend(runtime.router)
