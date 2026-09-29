from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from hashlib import sha256

import httpx

from traceroot.data.models import CodeChangeEntry
from traceroot.domain.incident import Incident


class GitHubCodeChangesProvider:
    """Treat repository commits as service code-change evidence.

    This integration does not imply that a commit was deployed or affected production.
    Queries use GitHub's default branch and require timezone-aware incident times.
    """

    _MAX_COMMIT_PAGES = 100
    _MAX_FILE_PAGES = 30

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
    ) -> list[CodeChangeEntry]:
        if service is not None and service != self.service:
            return []
        if incident.start_time.tzinfo is None:
            raise ValueError("Incident start_time must have a timezone")
        start_time = incident.start_time.astimezone(UTC) - timedelta(
            minutes=self.window_minutes
        )
        end_time = incident.start_time.astimezone(UTC) + timedelta(
            minutes=self.window_minutes
        )
        headers = {"Accept": "application/vnd.github+json"}
        if self.token is not None:
            headers["Authorization"] = f"Bearer {self.token}"

        changes: list[CodeChangeEntry] = []
        seen: set[str] = set()
        for page in range(1, self._MAX_COMMIT_PAGES + 1):
            response = httpx.get(
                f"https://api.github.com/repos/{self.repo}/commits",
                headers=headers,
                params={
                    "since": start_time.isoformat(),
                    "until": end_time.isoformat(),
                    "per_page": 100,
                    "page": page,
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, list):
                raise TypeError("Malformed GitHub commit list: expected a list")
            commits = [self._parse_commit(commit) for commit in payload]
            new_shas = {sha for sha, _, _ in commits} - seen
            for sha, timestamp, description in commits:
                if sha in seen:
                    continue
                seen.add(sha)
                if not start_time <= timestamp <= end_time:
                    continue
                files = self._fetch_files(sha, headers)
                raw = json.dumps(
                    [self.repo.casefold(), self.service, sha], separators=(",", ":")
                )
                digest = sha256(raw.encode()).hexdigest()[:12].upper()
                changes.append(
                    CodeChangeEntry(
                        id=f"CHANGE-LIVE-{digest}",
                        timestamp=timestamp,
                        service=self.service,
                        commit_sha=sha,
                        files=files,
                        description=description,
                    )
                )
            # GitHub lists recent commits first. A whole older page ends the scan;
            # a single older entry must not hide in-window entries on the same page.
            if len(commits) < 100 or all(
                timestamp < start_time for _, timestamp, _ in commits
            ):
                break
            if not new_shas:
                raise RuntimeError("GitHub commit pagination made no progress")
        else:
            raise RuntimeError(
                "GitHub commit pagination limit reached; results may be incomplete"
            )
        return sorted(changes, key=lambda change: change.timestamp)

    def _parse_commit(self, item: object) -> tuple[str, datetime, str]:
        if not isinstance(item, dict):
            raise TypeError("Malformed GitHub commit: expected an object")
        sha = item.get("sha")
        if not isinstance(sha, str) or not sha.strip():
            raise ValueError("Malformed GitHub commit: missing or invalid SHA")
        commit = item.get("commit")
        if not isinstance(commit, dict):
            raise TypeError("Malformed GitHub commit: missing commit metadata")
        source_timestamp = None
        for field in ("committer", "author"):
            person = commit.get(field)
            if person is None:
                continue
            if not isinstance(person, dict):
                raise TypeError(f"Malformed GitHub commit: invalid {field}")
            source_timestamp = person.get("date")
            if source_timestamp is not None:
                break
        if not isinstance(source_timestamp, str):
            raise TypeError("Malformed GitHub commit: missing or invalid timestamp")
        try:
            timestamp = datetime.fromisoformat(source_timestamp)
        except ValueError as exc:
            raise ValueError("Malformed GitHub commit: invalid timestamp") from exc
        if timestamp.tzinfo is None:
            raise ValueError("Malformed GitHub commit: timestamp must have a timezone")
        description = commit.get("message", "")
        if not isinstance(description, str):
            raise TypeError("Malformed GitHub commit: invalid message")
        return sha, timestamp.astimezone(UTC), description

    def _fetch_files(self, sha: str, headers: dict[str, str]) -> list[str]:
        filenames: list[str] = []
        for page in range(1, self._MAX_FILE_PAGES + 1):
            response = httpx.get(
                f"https://api.github.com/repos/{self.repo}/commits/{sha}",
                headers=headers,
                params={"per_page": 100, "page": page},
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise TypeError("Malformed GitHub commit detail: expected an object")
            files = payload.get("files")
            if not isinstance(files, list):
                raise TypeError(
                    "Malformed GitHub commit detail: missing or invalid files"
                )
            for file in files:
                if not isinstance(file, dict):
                    raise TypeError("Malformed GitHub commit detail: invalid file")
                filename = file.get("filename")
                if not isinstance(filename, str) or not filename.strip():
                    raise ValueError(
                        "Malformed GitHub commit detail: missing or invalid filename"
                    )
                filenames.append(filename)
            if len(files) < 100:
                return filenames
        # GitHub exposes at most 3,000 files. Do not silently return a truncated list.
        raise RuntimeError(
            "GitHub commit file pagination limit reached; files may be incomplete"
        )
