"""Internal low-level HTTP helpers for the Telegram Bot API.

Everything is a thin wrapper around ``requests``; the public modules
(``sending``, ``polling``, ``media``) build on top of these helpers.
"""

import logging
from typing import Any

import requests

from .constants import DEFAULT_API_TIMEOUT, TELEGRAM_API_BASE
from .errors import TelegramAPIError, TelegramRequestError

logger = logging.getLogger(__name__)


def api_url(bot_token: str, method: str) -> str:
    """Build the API URL for a bot token and method name."""
    return f"{TELEGRAM_API_BASE}/bot{bot_token}/{method}"


def file_url(bot_token: str, file_path: str) -> str:
    """Build the download URL for a file previously resolved via ``getFile``."""
    return f"{TELEGRAM_API_BASE}/file/bot{bot_token}/{file_path}"


def api_call(
    session: requests.Session,
    bot_token: str,
    method: str,
    *,
    params: dict[str, Any] | None = None,
    json_payload: dict[str, Any] | None = None,
    files: dict[str, Any] | None = None,
    timeout: tuple[float, float] = DEFAULT_API_TIMEOUT,
) -> dict[str, Any]:
    """Call a Telegram Bot API method and return its full JSON payload.

    Network failures raise :class:`TelegramRequestError`; an ``ok: false``
    response raises :class:`TelegramAPIError`. On success the returned dict
    has ``ok: True`` and the method-specific ``result``.

    Args:
        session: Requests session to use.
        bot_token: Telegram bot token.
        method: API method name, e.g. ``sendMessage``.
        params: Optional query-string parameters (GET-style calls).
        json_payload: Optional JSON body (POST calls).
        files: Optional multipart file fields; when present the payload is
            sent as form data instead of JSON.
        timeout: (connect, read) timeout in seconds.

    Returns:
        The decoded JSON payload dict.

    Raises:
        TelegramRequestError: On transport-level failures.
        TelegramAPIError: When Telegram answers with ``ok: false``.
    """
    url = api_url(bot_token, method)

    try:
        if files is not None:
            response = session.post(
                url, data=json_payload or {}, files=files, timeout=timeout
            )
        elif json_payload is not None:
            response = session.post(
                url, params=params, json=json_payload, timeout=timeout
            )
        else:
            response = session.get(url, params=params, timeout=timeout)
    except requests.RequestException as exc:
        logger.debug("%s transport failure: %s", method, exc)
        raise TelegramRequestError(f"{method} transport failure: {exc}") from exc

    try:
        payload = response.json()
    except ValueError as exc:
        logger.debug("%s returned a non-JSON response", method)
        raise TelegramRequestError(
            f"{method} returned a non-JSON response (HTTP {response.status_code})"
        ) from exc

    if not payload.get("ok"):
        raise TelegramAPIError(
            method,
            error_code=payload.get("error_code"),
            description=payload.get("description"),
            http_status=response.status_code,
            payload=payload,
        )
    return payload
