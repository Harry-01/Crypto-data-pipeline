from __future__ import annotations

from typing import Any

import pytest


class FakeResponse:
    def __init__(self, json_data: Any = None, content: bytes = b"", status: int = 200):
        self._json = json_data
        self.content = content
        self.status_code = status
        self.text = str(json_data)

    def json(self) -> Any:
        return self._json

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            import requests

            raise requests.HTTPError(f"{self.status_code}")


class FakeSession:
    """Returns queued responses in order and records every call."""

    def __init__(self, responses: list[FakeResponse]):
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def _next(self, method: str, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append({"method": method, "url": url, **kwargs})
        return self.responses.pop(0)

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        return self._next("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> FakeResponse:
        return self._next("POST", url, **kwargs)


@pytest.fixture
def fake_session():
    return FakeSession
