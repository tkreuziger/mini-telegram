"""Exception types for Telegram API interactions."""

from typing import Any


class TelegramError(Exception):
    """Base class for all errors raised by this package."""


class TelegramRequestError(TelegramError):
    """A network-level failure: connection refused, timeout, bad response."""


class TelegramAPIError(TelegramError):
    """The Telegram Bot API answered with ``ok: false``.

    Attributes:
        method: The API method that failed (e.g. ``sendMessage``).
        error_code: Telegram error code (e.g. 400, 403, 429), if provided.
        description: Human-readable description from Telegram, if provided.
        http_status: HTTP status of the response.
        payload: The raw JSON payload of the failed response.
    """

    def __init__(
        self,
        method: str,
        *,
        error_code: int | None = None,
        description: str | None = None,
        http_status: int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        self.method = method
        self.error_code = error_code
        self.description = description
        self.http_status = http_status
        self.payload = payload

        detail = description or "<no description>"
        code = error_code or http_status
        prefix = f" [{code}]" if code is not None else ""
        super().__init__(f"{method} failed{prefix}: {detail}")
