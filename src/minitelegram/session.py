"""HTTP session management with automatic retries."""

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

_STATUS_FORCELIST = (429, 500, 502, 503, 504)
_ALLOWED_METHODS = ("GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS")


@contextmanager
def telegram_session(
    *,
    total: int = 6,
    connect: int = 6,
    read: int = 6,
    status: int = 6,
    backoff_factor: float = 2.0,
) -> Generator[requests.Session, Any, None]:
    """Create an HTTP session pre-configured for the Telegram Bot API.

    Retries transient failures (429 rate limits and 5xx server errors) with
    exponential backoff and honours Telegram's ``Retry-After`` header.

    Args:
        total: Maximum number of retries overall.
        connect: Maximum retries for connection errors.
        read: Maximum retries for read errors.
        status: Maximum retries on ``status_forcelist`` responses.
        backoff_factor: Backoff multiplier between retries.

    Yields:
        A requests Session. Closing the context closes the session.
    """
    retry = Retry(
        total=total,
        connect=connect,
        read=read,
        status=status,
        backoff_factor=backoff_factor,
        status_forcelist=_STATUS_FORCELIST,
        allowed_methods=_ALLOWED_METHODS,
        raise_on_status=False,
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry)

    session = requests.Session()
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    try:
        yield session
    finally:
        session.close()
