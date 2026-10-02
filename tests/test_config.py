import pytest
from pydantic import ValidationError

from traceroot.config import LiveEvidenceConfig, load_live_evidence_config


@pytest.fixture
def valid_config_data():
    return {
        "loki_base_url": "http://localhost:3100",
        "prometheus_base_url": "http://localhost:9090",
        "github_repo": "gaganjawa/traceroot",
        "github_service": "traceroot",
    }


@pytest.fixture
def valid_environ():
    return {
        "TRACEROOT_LOKI_BASE_URL": "http://localhost:3100",
        "TRACEROOT_PROMETHEUS_BASE_URL": "http://localhost:9090",
        "TRACEROOT_GITHUB_REPO": "gaganjawa/traceroot",
        "TRACEROOT_GITHUB_SERVICE": "traceroot",
    }


@pytest.mark.parametrize(
    "required_field",
    [
        "loki_base_url",
        "prometheus_base_url",
        "github_repo",
        "github_service",
    ],
)
def test_live_config_requires_source_urls_repo_and_service(
    valid_config_data,
    required_field,
):
    data = valid_config_data.copy()
    data.pop(required_field)

    with pytest.raises(ValidationError):
        LiveEvidenceConfig(**data)


def test_live_config_uses_current_provider_defaults(valid_config_data):
    config = LiveEvidenceConfig(**valid_config_data)

    assert config.logs_window_minutes == 15
    assert config.metrics_window_minutes == 15
    assert config.deployments_window_minutes == 60
    assert config.code_changes_window_minutes == 60
    assert config.metrics_metric_name == "http_server_request_duration_seconds"
    assert config.metrics_unit == "seconds"
    assert config.metrics_step_seconds == 30
    assert config.timeout_seconds == 10.0
    assert config.github_token is None


def test_live_config_accepts_explicit_overrides(valid_config_data):
    config = LiveEvidenceConfig(
        **valid_config_data,
        logs_window_minutes=30,
        metrics_window_minutes=45,
        deployments_window_minutes=120,
        code_changes_window_minutes=90,
        metrics_metric_name="request_latency_seconds",
        metrics_unit="milliseconds",
        metrics_step_seconds=10,
        timeout_seconds=5.0,
    )

    assert config.logs_window_minutes == 30
    assert config.metrics_window_minutes == 45
    assert config.deployments_window_minutes == 120
    assert config.code_changes_window_minutes == 90
    assert config.metrics_metric_name == "request_latency_seconds"
    assert config.metrics_unit == "milliseconds"
    assert config.metrics_step_seconds == 10
    assert config.timeout_seconds == 5.0


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("loki_base_url", "not-a-url"),
        ("prometheus_base_url", "not-a-url"),
        ("loki_base_url", "ftp://logs.example.test"),
        ("loki_base_url", "https://"),
        ("loki_base_url", "https://logs.example.test:invalid"),
        ("loki_base_url", "https://logs.example.test:70000"),
        ("loki_base_url", "https://logs.example.test?query=1"),
        ("loki_base_url", "https://logs.example.test/#fragment"),
        ("loki_base_url", "https://user:password@logs.example.test"),
        ("loki_base_url", "https://bad host.test"),
        ("github_repo", "owner/repo/extra"),
        ("github_repo", "owner /repo"),
        ("github_repo", "owner/repo?query=1"),
        ("github_repo", "owner/.."),
        ("github_repo", "invalid-repo"),
        ("github_service", ""),
        ("metrics_metric_name", ""),
        ("metrics_unit", ""),
    ],
)
def test_live_config_rejects_invalid_urls_repo_and_blank_fields(
    valid_config_data,
    field,
    value,
):
    data = valid_config_data | {field: value}

    with pytest.raises(ValidationError):
        LiveEvidenceConfig(**data)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("logs_window_minutes", 0),
        ("metrics_window_minutes", 0),
        ("deployments_window_minutes", 0),
        ("code_changes_window_minutes", 0),
        ("metrics_step_seconds", 0),
        ("timeout_seconds", 0),
        ("timeout_seconds", float("inf")),
        ("timeout_seconds", float("nan")),
        ("timeout_seconds", -1),
        ("logs_window_minutes", -1),
        ("metrics_step_seconds", 1.5),
    ],
)
def test_live_config_rejects_invalid_windows_step_and_timeout(
    valid_config_data,
    field,
    value,
):
    data = valid_config_data | {field: value}

    with pytest.raises(ValidationError):
        LiveEvidenceConfig(**data)


def test_live_config_rejects_unknown_fields(valid_config_data):
    with pytest.raises(ValidationError):
        LiveEvidenceConfig(
            **valid_config_data,
            unknown_setting="value",
        )


def test_live_config_normalizes_blank_token_to_none(valid_config_data):
    config = LiveEvidenceConfig(
        **valid_config_data,
        github_token="   ",
    )

    assert config.github_token is None


def test_load_live_config_reads_supplied_mapping(valid_environ):
    config = load_live_evidence_config(valid_environ)

    assert config.loki_base_url == "http://localhost:3100"
    assert config.prometheus_base_url == "http://localhost:9090"
    assert config.github_repo == "gaganjawa/traceroot"
    assert config.github_service == "traceroot"


def test_load_live_config_does_not_replace_empty_mapping_with_environment(
    monkeypatch,
):
    monkeypatch.setenv(
        "TRACEROOT_LOKI_BASE_URL",
        "http://localhost:3100",
    )
    monkeypatch.setenv(
        "TRACEROOT_PROMETHEUS_BASE_URL",
        "http://localhost:9090",
    )
    monkeypatch.setenv(
        "TRACEROOT_GITHUB_REPO",
        "gaganjawa/traceroot",
    )
    monkeypatch.setenv(
        "TRACEROOT_GITHUB_SERVICE",
        "traceroot",
    )

    with pytest.raises(ValidationError):
        load_live_evidence_config({})


def test_load_live_config_reads_environment_when_mapping_is_none(
    monkeypatch,
):
    monkeypatch.setenv(
        "TRACEROOT_LOKI_BASE_URL",
        "http://localhost:3100",
    )
    monkeypatch.setenv(
        "TRACEROOT_PROMETHEUS_BASE_URL",
        "http://localhost:9090",
    )
    monkeypatch.setenv(
        "TRACEROOT_GITHUB_REPO",
        "gaganjawa/traceroot",
    )
    monkeypatch.setenv(
        "TRACEROOT_GITHUB_SERVICE",
        "traceroot",
    )

    config = load_live_evidence_config()

    assert config.loki_base_url == "http://localhost:3100"
    assert config.prometheus_base_url == "http://localhost:9090"
    assert config.github_repo == "gaganjawa/traceroot"
    assert config.github_service == "traceroot"


def test_load_live_config_parses_numeric_overrides(valid_environ):
    environ = valid_environ | {
        "TRACEROOT_LOGS_WINDOW_MINUTES": "30",
        "TRACEROOT_METRICS_WINDOW_MINUTES": "45",
        "TRACEROOT_DEPLOYMENTS_WINDOW_MINUTES": "120",
        "TRACEROOT_CODE_CHANGES_WINDOW_MINUTES": "90",
        "TRACEROOT_METRICS_STEP_SECONDS": "10",
        "TRACEROOT_LIVE_TIMEOUT_SECONDS": "5.5",
    }

    config = load_live_evidence_config(environ)

    assert config.logs_window_minutes == 30
    assert config.metrics_window_minutes == 45
    assert config.deployments_window_minutes == 120
    assert config.code_changes_window_minutes == 90
    assert config.metrics_step_seconds == 10
    assert config.timeout_seconds == 5.5


def test_live_config_redacts_token(valid_config_data):
    config = LiveEvidenceConfig(**valid_config_data, github_token="secret-token")
    assert config.github_token.get_secret_value() == "secret-token"
    assert "secret-token" not in repr(config)
    assert "github_token" not in config.model_dump()
    assert "secret-token" not in config.model_dump_json()


def test_live_config_validation_errors_hide_secret_inputs(valid_config_data):
    with pytest.raises(ValidationError) as error:
        LiveEvidenceConfig(
            **(valid_config_data | {"github_token": {"secret-token": "invalid"}})
        )
    assert "secret-token" not in str(error.value)


def test_live_config_is_frozen(valid_config_data):
    config = LiveEvidenceConfig(**valid_config_data)
    with pytest.raises(ValidationError, match="frozen"):
        config.github_service = "other"


@pytest.mark.parametrize(
    "field, value",
    [
        ("TRACEROOT_LOGS_WINDOW_MINUTES", ""),
        ("TRACEROOT_METRICS_WINDOW_MINUTES", "invalid"),
        ("TRACEROOT_DEPLOYMENTS_WINDOW_MINUTES", "0"),
        ("TRACEROOT_CODE_CHANGES_WINDOW_MINUTES", "-1"),
        ("TRACEROOT_METRICS_STEP_SECONDS", "1.5"),
        ("TRACEROOT_LIVE_TIMEOUT_SECONDS", "inf"),
        ("TRACEROOT_LIVE_TIMEOUT_SECONDS", "nan"),
    ],
)
def test_load_live_config_rejects_malformed_environment_values(
    valid_environ, field, value
):
    with pytest.raises(ValidationError):
        load_live_evidence_config(valid_environ | {field: value})


def test_load_live_config_reads_token_metric_and_unit_overrides(valid_environ):
    config = load_live_evidence_config(
        valid_environ
        | {
            "TRACEROOT_GITHUB_TOKEN": "secret-token",
            "TRACEROOT_METRICS_METRIC_NAME": "latency",
            "TRACEROOT_METRICS_UNIT": "milliseconds",
        }
    )
    assert config.github_token.get_secret_value() == "secret-token"
    assert config.metrics_metric_name == "latency"
    assert config.metrics_unit == "milliseconds"


def test_load_live_config_does_not_mutate_supplied_mapping(valid_environ):
    before = valid_environ.copy()
    load_live_evidence_config(valid_environ)
    assert valid_environ == before
