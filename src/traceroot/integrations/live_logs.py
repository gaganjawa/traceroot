from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta
from hashlib import sha256

import httpx

from traceroot.data.models import LogEntry
from traceroot.domain.incident import Incident


def _validate_response(payload: object) -> list[dict]:
    """Malformed external data consistently raises ValueError, including type errors."""
    prefix = "Invalid Loki response"
    if not isinstance(payload, dict):
        raise ValueError(f"{prefix}: expected an object")  # noqa: TRY004
    if payload.get("status") == "error":
        raise RuntimeError("Loki query failed")
    if payload.get("status") != "success":
        raise ValueError(f"{prefix}: status must be success or error")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise ValueError(f"{prefix}: data must be an object")  # noqa: TRY004
    if data.get("resultType") != "streams":
        raise ValueError(f"{prefix}: data.resultType must be streams")
    results = data.get("result")
    if not isinstance(results, list):
        raise ValueError(f"{prefix}: data.result must be a list")  # noqa: TRY004
    for index, stream in enumerate(results):
        location = f"{prefix}: data.result[{index}]"
        if not isinstance(stream, dict):
            raise ValueError(f"{location} must be an object")  # noqa: TRY004
        labels = stream.get("stream")
        if not isinstance(labels, dict) or any(
            not isinstance(key, str) or not isinstance(value, str)
            for key, value in labels.items()
        ):
            raise ValueError(f"{location}.stream must be a string label mapping")
        if not isinstance(stream.get("values"), list):
            raise ValueError(f"{location}.values must be a list")  # noqa: TRY004
    return results


def _parse_sample(sample: object, location: str) -> tuple[str, str, datetime]:
    prefix = f"Invalid Loki response: {location}"
    if not isinstance(sample, (list, tuple)) or len(sample) != 2:
        raise ValueError(f"{prefix} must be a timestamp/message pair")
    timestamp_ns, message = sample
    if not isinstance(timestamp_ns, str) or not re.fullmatch(
        r"[+-]?[0-9]+", timestamp_ns
    ):
        raise ValueError(f"{prefix}[0] must be an integer nanosecond string")
    if not isinstance(message, str):
        raise ValueError(f"{prefix}[1] must be a string")  # noqa: TRY004
    try:
        timestamp = datetime.fromtimestamp(int(timestamp_ns) / 1_000_000_000, tz=UTC)
    except (ValueError, OverflowError, OSError):
        raise ValueError(
            f"{prefix}[0] is outside the supported timestamp range"
        ) from None
    return timestamp_ns, message, timestamp


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

        results = _validate_response(payload)

        logs: list[LogEntry] = []

        for stream_index, stream in enumerate(results):
            labels = dict(sorted(stream["stream"].items()))
            stream_service = (
                labels.get("service_name")
                or labels.get("service")
                or service
                or "unknown"
            )
            level = labels.get("level", "unknown")

            for sample_index, sample in enumerate(stream["values"]):
                timestamp_ns, message, timestamp = _parse_sample(
                    sample, f"data.result[{stream_index}].values[{sample_index}]"
                )

                logs.append(
                    LogEntry(
                        id=self._build_evidence_id(
                            labels,
                            timestamp_ns,
                            message,
                        ),
                        timestamp=timestamp,
                        service=stream_service,
                        level=level,
                        message=message,
                        labels=labels,
                    )
                )

        return logs

    def _build_query(
        self,
        service: str | None,
    ) -> str:
        if service is None:
            return '{service_name=~".+"}'

        return f"{{service_name={json.dumps(service, ensure_ascii=False)}}}"

    def _build_evidence_id(
        self,
        labels: dict[str, str],
        timestamp_ns: str,
        message: str,
    ) -> str:
        raw = json.dumps(
            [labels, timestamp_ns, message],
            sort_keys=True,
            separators=(",", ":"),
        )

        digest = sha256(raw.encode()).hexdigest()[:12].upper()

        return f"LOG-LIVE-{digest}"
