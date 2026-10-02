from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256

import httpx

from traceroot.data.models import LogEntry
from traceroot.domain.incident import Incident


class LokiLogsProvider:
    def __init__(
        self,
        base_url: str,
        window_minutes: int = 15,
        timeout_seconds: float = 10.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.window_minutes = window_minutes
        self.timeout_seconds = timeout_seconds

    def query(
        self,
        incident: Incident,
        service: str | None = None,
    ) -> list[LogEntry]:
        start_time = incident.start_time - timedelta(minutes=self.window_minutes)
        end_time = incident.start_time + timedelta(minutes=self.window_minutes)

        query = self._build_query(service)

        response = httpx.get(
            f"{self.base_url}/loki/api/v1/query_range",
            params={
                "query": query,
                "start": str(int(start_time.timestamp() * 1_000_000_000)),
                "end": str(int(end_time.timestamp() * 1_000_000_000)),
            },
            timeout=self.timeout_seconds,
        )

        response.raise_for_status()

        payload = response.json()

        if payload.get("status") != "success":
            raise RuntimeError("Loki query failed")

        results = payload.get("data", {}).get("result", [])

        logs: list[LogEntry] = []

        for stream in results:
            labels = stream.get("stream", {})
            stream_service = (
                labels.get("service_name")
                or labels.get("service")
                or service
                or "unknown"
            )
            level = labels.get("level", "unknown")

            for timestamp_ns, message in stream.get("values", []):
                timestamp = datetime.fromtimestamp(
                    int(timestamp_ns) / 1_000_000_000,
                    tz=UTC,
                )

                logs.append(
                    LogEntry(
                        id=self._build_evidence_id(
                            stream_service,
                            timestamp_ns,
                            message,
                        ),
                        timestamp=timestamp,
                        service=stream_service,
                        level=level,
                        message=message,
                    )
                )

        return logs

    def _build_query(
        self,
        service: str | None,
    ) -> str:
        if service is None:
            return '{service_name=~".+"}'

        return f'{{service_name="{service}"}}'

    def _build_evidence_id(
        self,
        service: str,
        timestamp_ns: str,
        message: str,
    ) -> str:
        raw = f"{service}|{timestamp_ns}|{message}"

        digest = sha256(raw.encode()).hexdigest()[:12].upper()

        return f"LOG-LIVE-{digest}"
