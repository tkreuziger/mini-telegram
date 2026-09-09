"""Shared test fixtures.

All tests talk to a :class:`FakeSession` that records requests and returns
scripted JSON payloads, so no network access or bot token is required.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest


@dataclass
class RecordedRequest:
    method: str
    url: str
    params: dict | None = None
    json: dict | None = None
    data: dict | None = None
    files: dict | None = None
    timeout: object = None


class FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self) -> dict:
        return self._payload

    @property
    def ok(self) -> bool:  # pragma: no cover - convenience
        return 200 <= self.status_code < 300

    def raise_for_status(self) -> None:
        if not self.ok:  # pragma: no cover
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    """A requests-like session that returns scripted JSON responses."""

    def __init__(self, responses: list[dict] | None = None) -> None:
        self.responses: list[dict] = list(responses or [])
        self.requests: list[RecordedRequest] = []

    def _next_payload(self) -> dict:
        if self.responses:
            return self.responses.pop(0)
        return {"ok": True, "result": True}

    def _record(
        self,
        method: str,
        url: str,
        params: dict | None = None,
        json: dict | None = None,
        data: dict | None = None,
        files: dict | None = None,
        timeout: object = None,
    ) -> FakeResponse:
        self.requests.append(
            RecordedRequest(
                method=method,
                url=url,
                params=params,
                json=json,
                data=data,
                files=files,
                timeout=timeout,
            )
        )
        payload = self._next_payload()
        return FakeResponse(payload, status_code=200 if payload.get("ok") else 400)

    def post(self, url, *, params=None, json=None, data=None, files=None, timeout=None):
        return self._record(
            "POST",
            url,
            params=params,
            json=json,
            data=data,
            files=files,
            timeout=timeout,
        )

    def get(self, url, *, params=None, timeout=None):
        return self._record("GET", url, params=params, timeout=timeout)


@pytest.fixture
def fake_session() -> FakeSession:
    """A session that answers ``ok: True`` to every request by default."""
    return FakeSession()
