"""Shared HTTP session with timeouts, retries and exponential backoff."""

from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DEFAULT_TIMEOUT = 30  # seconds
RETRY_STATUSES = (429, 500, 502, 503, 504)


def build_session(user_agent: str | None = None, retries: int = 5, backoff: float = 1.0) -> requests.Session:
    """Return a session that retries rate-limited (429) and transient 5xx responses.

    Backoff grows exponentially (1s, 2s, 4s, ...) and honours any Retry-After header.
    """
    retry = Retry(
        total=retries,
        backoff_factor=backoff,
        status_forcelist=RETRY_STATUSES,
        allowed_methods=frozenset({"GET", "POST"}),
        respect_retry_after_header=True,
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    if user_agent:
        session.headers["User-Agent"] = user_agent
    return session
