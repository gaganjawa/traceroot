import math
import os
import re
from collections.abc import Mapping
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


class LiveEvidenceConfig(BaseModel):
    """Explicit live source settings; constructing these never activates routing."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        hide_input_in_errors=True,
    )

    loki_base_url: str
    prometheus_base_url: str

    github_repo: str
    github_service: str
    github_token: SecretStr | None = Field(default=None, repr=False, exclude=True)

    logs_window_minutes: int = Field(default=15, gt=0)
    metrics_window_minutes: int = Field(default=15, gt=0)
    deployments_window_minutes: int = Field(default=60, gt=0)
    code_changes_window_minutes: int = Field(default=60, gt=0)

    metrics_metric_name: str = "http_server_request_duration_seconds"
    metrics_unit: str = "seconds"
    metrics_step_seconds: int = Field(default=30, gt=0)

    timeout_seconds: float = Field(default=10.0, gt=0)

    @field_validator("loki_base_url", "prometheus_base_url")
    @classmethod
    def validate_http_url(cls, value: str) -> str:
        value = value.strip()

        parsed = urlparse(value)

        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("must be a valid HTTP or HTTPS URL")

        try:
            _ = parsed.port
        except ValueError as exc:
            raise ValueError("must have a valid port") from exc
        if any(char.isspace() for char in value) or parsed.query or parsed.fragment:
            raise ValueError(
                "base URL must not contain whitespace, a query, or a fragment"
            )
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("base URL must not contain credentials")

        return value

    @field_validator("github_repo")
    @classmethod
    def validate_github_repo(cls, value: str) -> str:
        value = value.strip()

        if not re.fullmatch(
            r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?/[A-Za-z0-9_.-]+", value
        ) or value.split("/")[-1] in {".", ".."}:
            raise ValueError("github_repo must be in owner/repo format")

        return value

    @field_validator(
        "github_service",
        "metrics_metric_name",
        "metrics_unit",
    )
    @classmethod
    def validate_non_blank(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("must not be blank")

        return value

    @field_validator("github_token", mode="before")
    @classmethod
    def normalize_blank_token(cls, value):
        if isinstance(value, SecretStr):
            value = value.get_secret_value()
        if isinstance(value, str) and not value.strip():
            return None

        return value

    @field_validator("timeout_seconds")
    @classmethod
    def validate_finite_timeout(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("timeout_seconds must be finite")

        return value


_ENV_TO_FIELD = {
    "TRACEROOT_LOKI_BASE_URL": "loki_base_url",
    "TRACEROOT_PROMETHEUS_BASE_URL": "prometheus_base_url",
    "TRACEROOT_GITHUB_REPO": "github_repo",
    "TRACEROOT_GITHUB_SERVICE": "github_service",
    "TRACEROOT_GITHUB_TOKEN": "github_token",
    "TRACEROOT_LOGS_WINDOW_MINUTES": "logs_window_minutes",
    "TRACEROOT_METRICS_WINDOW_MINUTES": "metrics_window_minutes",
    "TRACEROOT_DEPLOYMENTS_WINDOW_MINUTES": "deployments_window_minutes",
    "TRACEROOT_CODE_CHANGES_WINDOW_MINUTES": "code_changes_window_minutes",
    "TRACEROOT_METRICS_METRIC_NAME": "metrics_metric_name",
    "TRACEROOT_METRICS_UNIT": "metrics_unit",
    "TRACEROOT_METRICS_STEP_SECONDS": "metrics_step_seconds",
    "TRACEROOT_LIVE_TIMEOUT_SECONDS": "timeout_seconds",
}


def load_live_evidence_config(
    environ: Mapping[str, str] | None = None,
) -> LiveEvidenceConfig:
    """Read only the supplied mapping or current environment, without dotenv loading."""
    source = os.environ if environ is None else environ

    values = {
        field_name: source[env_name]
        for env_name, field_name in _ENV_TO_FIELD.items()
        if env_name in source
    }

    return LiveEvidenceConfig(**values)
