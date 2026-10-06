from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from math import isfinite

import httpx

from traceroot.data.models import MetricEntry
from traceroot.domain.incident import Incident


def _validate_response(payload: object) -> list[dict]:
    """Malformed external data consistently raises ValueError, including type errors."""
    prefix = "Invalid Prometheus response"
    if not isinstance(payload, dict):
        raise ValueError(f"{prefix}: expected an object")  # noqa: TRY004
    if payload.get("status") == "error":
        raise RuntimeError("Prometheus query failed")
    if payload.get("status") != "success":
        raise ValueError(f"{prefix}: status must be success or error")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise ValueError(f"{prefix}: data must be an object")  # noqa: TRY004
    if data.get("resultType") != "matrix":
        raise ValueError(f"{prefix}: data.resultType must be matrix")
    results = data.get("result")
    if not isinstance(results, list):
        raise ValueError(f"{prefix}: data.result must be a list")  # noqa: TRY004
    for index, series in enumerate(results):
        location = f"{prefix}: data.result[{index}]"
        if not isinstance(series, dict):
            raise ValueError(f"{location} must be an object")  # noqa: TRY004
        labels = series.get("metric")
        if not isinstance(labels, dict) or any(
            not isinstance(key, str) or not isinstance(value, str)
            for key, value in labels.items()
        ):
            raise ValueError(f"{location}.metric must be a string label mapping")
        if not isinstance(series.get("values"), list):
            raise ValueError(f"{location}.values must be a list")  # noqa: TRY004
        if "histograms" in series:
            raise ValueError(f"{location}.histograms is not supported")
    return results


def _finite_number(
    value: object, location: str, *, allow_string: bool = False
) -> float:
    types = (int, float, str) if allow_string else (int, float)
    error = f"Invalid Prometheus response: {location} must be numeric and finite"
    if isinstance(value, bool) or not isinstance(value, types):
        raise ValueError(error)  # noqa: TRY004
    try:
        number = float(value)
    except (ValueError, OverflowError):
        raise ValueError(error) from None
    if not isfinite(number):
        raise ValueError(error)
    return number


def _parse_sample(sample: object, location: str) -> tuple[datetime, float]:
    prefix = f"Invalid Prometheus response: {location}"
    if not isinstance(sample, (list, tuple)) or len(sample) != 2:
        raise ValueError(f"{prefix} must be a timestamp/value pair")
    source_timestamp = _finite_number(sample[0], f"{location}[0]")
    value = _finite_number(sample[1], f"{location}[1]", allow_string=True)
    try:
        timestamp = datetime.fromtimestamp(source_timestamp, tz=UTC)
    except (ValueError, OverflowError, OSError):
        raise ValueError(
            f"{prefix}[0] is outside the supported timestamp range"
        ) from None
    return timestamp, value


class PrometheusMetricsProvider:
    def __init__(
        self,
        base_url: str,
        metric_name: str = "http_server_request_duration_seconds",
        unit: str = "seconds",
        window_minutes: int = 15,
        step_seconds: int = 30,
        timeout_seconds: float = 10.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.metric_name = metric_name
        self.unit = unit
        self.window_minutes = window_minutes
        self.step_seconds = step_seconds
        self.timeout_seconds = timeout_seconds

    def query(
        self,
        incident: Incident,
        service: str | None = None,
    ) -> list[MetricEntry]:
        start_time = incident.start_time - timedelta(minutes=self.window_minutes)
        end_time = incident.start_time + timedelta(minutes=self.window_minutes)
        query = self.metric_name
        if service is not None:
            query += f"{{service={json.dumps(service, ensure_ascii=False)}}}"

        response = httpx.get(
            f"{self.base_url}/api/v1/query_range",
            params={
                "query": query,
                "start": start_time.timestamp(),
                "end": end_time.timestamp(),
                "step": self.step_seconds,
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        results = _validate_response(payload)

        metrics: list[MetricEntry] = []
        for series_index, series in enumerate(results):
            labels = dict(sorted(series["metric"].items()))
            source_service = (
                labels.get("service")
                or labels.get("service_name")
                or service
                or "unknown"
            )
            metric_name = labels.get("__name__", self.metric_name)
            for sample_index, sample in enumerate(series["values"]):
                timestamp, value = _parse_sample(
                    sample, f"data.result[{series_index}].values[{sample_index}]"
                )
                # Canonical labels distinguish series and ignore label ordering.
                raw = json.dumps(
                    [labels, source_service, metric_name, timestamp.isoformat(), value],
                    sort_keys=True,
                    separators=(",", ":"),
                )
                digest = sha256(raw.encode()).hexdigest()[:12].upper()
                metrics.append(
                    MetricEntry(
                        id=f"METRIC-LIVE-{digest}",
                        timestamp=timestamp,
                        service=source_service,
                        metric=metric_name,
                        value=value,
                        unit=self.unit,
                        labels=labels,
                    )
                )
        return metrics
