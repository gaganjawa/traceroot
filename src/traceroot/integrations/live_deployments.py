from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from hashlib import sha256

import httpx

from traceroot.data.models import DeploymentEntry
from traceroot.domain.incident import Incident


class GitHubDeploymentsProvider:
    def __init__(
        self,
        repo: str,
        service: str,
        token: str | None = None,
        window_minutes: int = 60,
        timeout_seconds: float = 10.0,
    ):
        self.repo = repo
        self.service = service
        self.token = token
        self.window_minutes = window_minutes
        self.timeout_seconds = timeout_seconds

    def query(
        self,
        incident: Incident,
        service: str | None = None,
    ) -> list[DeploymentEntry]:
        if service is not None and service != self.service:
            return []

        start_time = incident.start_time - timedelta(minutes=self.window_minutes)
        end_time = incident.start_time + timedelta(minutes=self.window_minutes)
        headers = {"Accept": "application/vnd.github+json"}
        if self.token is not None:
            headers["Authorization"] = f"Bearer {self.token}"

        deployments: list[DeploymentEntry] = []
        page = 1
        while True:
            response = httpx.get(
                f"https://api.github.com/repos/{self.repo}/releases",
                headers=headers,
                params={"per_page": 100, "page": page},
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, list):
                raise TypeError("Malformed GitHub releases payload: expected a list")

            for release in payload:
                deployment = self._map_release(release)
                if start_time <= deployment.timestamp <= end_time:
                    deployments.append(deployment)

            # Release ordering need not match published_at; inspect every page.
            if len(payload) < 100:
                break
            page += 1

        return sorted(deployments, key=lambda deployment: deployment.timestamp)

    def _map_release(self, release: object) -> DeploymentEntry:
        if not isinstance(release, dict):
            raise TypeError("Malformed GitHub release: expected an object")
        version = release.get("tag_name")
        if not isinstance(version, str) or not version.strip():
            raise ValueError("Malformed GitHub release: missing or invalid tag_name")
        source_timestamp = release.get("published_at")
        if source_timestamp is None:
            source_timestamp = release.get("created_at")
        if not isinstance(source_timestamp, str):
            raise TypeError("Malformed GitHub release: missing or invalid timestamp")
        try:
            timestamp = datetime.fromisoformat(source_timestamp)
        except ValueError as exc:
            raise ValueError("Malformed GitHub release: invalid timestamp") from exc
        if timestamp.tzinfo is None:
            raise ValueError("Malformed GitHub release: timestamp must have a timezone")
        timestamp = timestamp.astimezone(UTC)

        for field in ("name", "body"):
            if release.get(field) is not None and not isinstance(release[field], str):
                raise ValueError(f"Malformed GitHub release: invalid {field}")

        # Exclude editable descriptions so metadata edits preserve evidence identity.
        raw = json.dumps(
            [self.repo.casefold(), self.service, version, timestamp.isoformat()],
            separators=(",", ":"),
        )
        digest = sha256(raw.encode()).hexdigest()[:12].upper()
        return DeploymentEntry(
            id=f"DEPLOY-LIVE-{digest}",
            timestamp=timestamp,
            service=self.service,
            version=version,
            description=release.get("name") or release.get("body") or None,
        )
