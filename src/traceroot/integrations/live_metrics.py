from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from hashlib import sha256

import httpx

from traceroot.data.models import MetricEntry
from traceroot.domain.incident import Incident


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
        if payload.get("status") != "success":
            raise RuntimeError("Prometheus query failed")

        metrics: list[MetricEntry] = []
        for series in payload.get("data", {}).get("result", []):
            labels = series.get("metric", {})
            source_service = (
                labels.get("service")
                or labels.get("service_name")
                or service
                or "unknown"
            )
            metric_name = labels.get("__name__", self.metric_name)
            for source_timestamp, source_value in series.get("values", []):
                timestamp = datetime.fromtimestamp(float(source_timestamp), tz=UTC)
                value = float(source_value)
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
                    )
                )
        return metrics
