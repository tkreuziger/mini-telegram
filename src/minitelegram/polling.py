"""Long-polling for updates via the Telegram Bot API."""

import json
import logging
from typing import Any

import requests

from ._http import api_call
from .constants import DEFAULT_LONG_POLL_SECONDS, LONG_POLL_READ_SLACK
from .errors import TelegramError
from .parsing import parse_update
from .types import TelegramUpdate

logger = logging.getLogger(__name__)


def get_updates(
    session: requests.Session,
    bot_token: str,
    *,
    offset: int | None = None,
    timeout: tuple[int, int] | None = None,
    allowed_updates: list[str] | None = None,
    limit: int | None = None,
) -> list[TelegramUpdate]:
    """Fetch pending updates from the Telegram Bot API.

    This is a long-poll: Telegram holds the request open until at least one
    update is available or the poll timeout expires.

    Args:
        session: HTTP session for making requests.
        bot_token: Telegram bot token.
        offset: Only return updates with an id greater than this. Passing the
            last seen ``update_id + 1`` acknowledges all earlier updates.
        timeout: Optional ``(connect, long_poll)`` seconds. The HTTP read
            timeout is derived from the long-poll value with a little slack.
        allowed_updates: Optional whitelist of update types to receive, e.g.
            ``["message", "callback_query"]``. Defaults to all types.
        limit: Optional cap on how many updates to return (1-100).

    Returns:
        List of parsed :class:`TelegramUpdate` objects. Empty on failure or
        when there are no pending updates.
    """
    long_poll = timeout[1] if timeout else DEFAULT_LONG_POLL_SECONDS
    connect = timeout[0] if timeout else 5

    params: dict[str, Any] = {"timeout": long_poll}
    if offset is not None:
        params["offset"] = offset
    if limit is not None:
        params["limit"] = limit
    if allowed_updates is not None:
        params["allowed_updates"] = json.dumps(allowed_updates)

    try:
        payload = api_call(
            session,
            bot_token,
            "getUpdates",
            params=params,
            timeout=(connect, long_poll + LONG_POLL_READ_SLACK),
        )
    except TelegramError as exc:
        logger.error("getUpdates failed: %s", exc)
        return []

    updates: list[TelegramUpdate] = []
    for raw in payload.get("result", []):
        update = parse_update(raw)
        if update is not None:
            updates.append(update)
    return updates
