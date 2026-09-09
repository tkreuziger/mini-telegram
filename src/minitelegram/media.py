"""Downloading media that arrives in messages.

Telegram does not hand out raw download URLs; instead every attachment has a
``file_id`` which must first be resolved through ``getFile`` to a
server-relative ``file_path`` that can then be downloaded from the file
endpoint.
"""

import logging
from pathlib import Path
from typing import Any

import requests

from ._http import api_call, file_url
from .errors import TelegramError, TelegramRequestError
from .types import TelegramFile

logger = logging.getLogger(__name__)


def get_file(
    session: requests.Session,
    bot_token: str,
    *,
    file_id: str,
) -> TelegramFile | None:
    """Resolve a Telegram ``file_id`` into a :class:`TelegramFile`.

    Args:
        session: HTTP session for making requests.
        bot_token: Telegram bot token.
        file_id: The file identifier from an incoming message.

    Returns:
        A :class:`TelegramFile`, or ``None`` on failure.
    """
    try:
        payload = api_call(
            session,
            bot_token,
            "getFile",
            params={"file_id": file_id},
        )
    except TelegramError as exc:
        logger.error("getFile failed for file_id %s: %s", file_id, exc)
        return None

    result: dict[str, Any] = payload.get("result") or {}
    try:
        return TelegramFile(
            file_id=result["file_id"],
            file_unique_id=result.get("file_unique_id", ""),
            file_size=result.get("file_size"),
            file_path=result.get("file_path"),
        )
    except KeyError:
        logger.error("getFile result missing file_id: %s", result)
        return None


def get_file_path(
    session: requests.Session,
    bot_token: str,
    *,
    file_id: str,
) -> str | None:
    """Resolve a Telegram ``file_id`` to its downloadable server path.

    Args:
        session: HTTP session for making requests.
        bot_token: Telegram bot token.
        file_id: The file identifier from an incoming message.

    Returns:
        The server-relative file path, or ``None`` on failure or when the
        file is not downloadable via the API (e.g. too large).
    """
    file_info = get_file(session, bot_token, file_id=file_id)
    return file_info.file_path if file_info else None


def download_file(
    session: requests.Session,
    bot_token: str,
    *,
    file_path: str,
    target_path: Path | str,
) -> bool:
    """Download a file from Telegram's file server to ``target_path``.

    Args:
        session: HTTP session for making requests.
        bot_token: Telegram bot token.
        file_path: The server path returned by :func:`get_file_path`.
        target_path: Local path to write the downloaded file into.

    Returns:
        True if the download succeeded, False otherwise.
    """
    url = file_url(bot_token, file_path)
    target = Path(target_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    try:
        with session.get(url, stream=True, timeout=120) as response:
            response.raise_for_status()
            with target.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        handle.write(chunk)
    except (requests.RequestException, TelegramRequestError, OSError) as exc:
        logger.error("Download of %s failed: %s", url, exc)
        return False
    return True


def download_by_file_id(
    session: requests.Session,
    bot_token: str,
    *,
    file_id: str,
    target_path: Path | str,
) -> bool:
    """Convenience: resolve a ``file_id`` and download it in one step.

    Args:
        session: HTTP session for making requests.
        bot_token: Telegram bot token.
        file_id: The file identifier from an incoming message.
        target_path: Local path to write the downloaded file into.

    Returns:
        True if the file was downloaded successfully.
    """
    server_path = get_file_path(session, bot_token, file_id=file_id)
    if not server_path:
        return False
    return download_file(
        session, bot_token, file_path=server_path, target_path=target_path
    )
