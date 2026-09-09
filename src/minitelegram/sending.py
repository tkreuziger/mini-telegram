"""Sending messages and media through the Telegram Bot API."""

import logging
import re
from pathlib import Path
from typing import Any

import requests

from ._http import api_call
from .constants import MAX_MESSAGE_LENGTH
from .errors import TelegramAPIError, TelegramError
from .formatting import markdown_to_telegram_html, strip_html
from .markup import option_keyboard

logger = logging.getLogger(__name__)

# How long to wait (seconds) before retrying a failed text send.
_DEFAULT_RETRY_DELAY_SECONDS = 120.0


def _split_text(text: str, max_length: int) -> list[str]:
    """Split *text* into chunks of at most *max_length* characters.

    Tries to break at paragraph (blank-line) boundaries first, then at
    individual newlines, and falls back to a hard character cut for lines
    that exceed the limit on their own.
    """
    if len(text) <= max_length:
        return [text]

    paragraphs = re.split(r"(\n\n+)", text)
    merged: list[str] = []
    i = 0
    while i < len(paragraphs):
        chunk = paragraphs[i]
        if i + 1 < len(paragraphs) and re.fullmatch(r"\n\n+", paragraphs[i + 1]):
            chunk += paragraphs[i + 1]
            i += 2
        else:
            i += 1
        merged.append(chunk)

    chunks: list[str] = []
    current = ""

    for para in merged:
        if len(para) > max_length:
            if current:
                chunks.append(current)
                current = ""
            current = _split_at_newlines(para, max_length, chunks)
            continue

        if len(current) + len(para) > max_length:
            chunks.append(current)
            current = para
            continue

        current += para

    if current:
        chunks.append(current)

    return chunks


def _split_at_newlines(text: str, max_length: int, dest: list[str]) -> str:
    """Split *text* at ``\\n`` boundaries, appending complete chunks to *dest*.

    Returns the trailing (possibly empty) partial chunk.
    """
    has_trailing_newline = text.endswith("\n")
    stripped = text[:-1] if has_trailing_newline else text
    lines = stripped.split("\n")

    current = ""
    for j, line in enumerate(lines):
        candidate = line if j == 0 else current + "\n" + line

        if len(candidate) <= max_length:
            current = candidate
        else:
            if current:
                dest.append(current)

            if len(line) <= max_length:
                current = "\n" + line
            else:
                current = ""
                for k in range(0, len(line), max_length):
                    segment = line[k : k + max_length]
                    if k + max_length < len(line):
                        dest.append(segment)
                    else:
                        current = segment

    if has_trailing_newline:
        if len(current) + 1 <= max_length:
            current += "\n"
        else:
            if current:
                dest.append(current)
            current = "\n"

    return current


def send_text(
    session: requests.Session,
    bot_token: str,
    *,
    chat_id: int | str,
    text: str,
    parse_mode: str = "HTML",
    **more_payload_fields: Any,
) -> bool:
    """Send a text message, auto-splitting messages over 4096 characters.

    Text is first converted from the limited Markdown subset to Telegram
    HTML (see :func:`minitelegram.formatting.markdown_to_telegram_html`) and
    sent with ``parse_mode="HTML"``. If Telegram rejects the entities, the
    chunk is retried once as plain text. Long messages are split at paragraph
    boundaries first, then newlines, then hard character cuts.

    Args:
        session: HTTP session for making requests.
        bot_token: Telegram bot token.
        chat_id: Target chat id (user, group or channel).
        text: Message text (Markdown subset).
        parse_mode: Telegram parse mode. ``"HTML"`` converts the Markdown
            subset first; any other value (or empty string) sends the text
            verbatim with that parse mode.
        more_payload_fields: Extra fields for the API payload, e.g.
            ``reply_markup`` or ``disable_notification``.

    Returns:
        True if every chunk was delivered successfully.
    """
    converted = markdown_to_telegram_html(text) if parse_mode == "HTML" else text

    chunks = _split_text(converted, MAX_MESSAGE_LENGTH)
    if len(chunks) > 1:
        logger.info(
            "Splitting message for chat %s into %d parts.", chat_id, len(chunks)
        )

    all_ok = True
    for chunk in chunks:
        if not _send_single(
            session,
            bot_token,
            chat_id=chat_id,
            text=chunk,
            parse_mode=parse_mode,
            extra_fields=more_payload_fields,
        ):
            all_ok = False
    return all_ok


def _send_single(
    session: requests.Session,
    bot_token: str,
    *,
    chat_id: int | str,
    text: str,
    parse_mode: str,
    extra_fields: dict[str, Any],
) -> bool:
    """Send one message chunk, falling back to plain text on HTML errors."""
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "text": text,
        **({"parse_mode": parse_mode} if parse_mode else {}),
        **extra_fields,
    }

    try:
        api_call(session, bot_token, "sendMessage", json_payload=payload)
        return True
    except TelegramAPIError as exc:
        description = (exc.description or "").lower()
        if "parse entities" in description or "parse mode" in description:
            logger.info("Retrying chat %s with plain text (HTML parse error).", chat_id)
            plain_payload = {**payload, "text": strip_html(text)}
            plain_payload.pop("parse_mode", None)
            try:
                api_call(session, bot_token, "sendMessage", json_payload=plain_payload)
                return True
            except TelegramError as retry_exc:
                logger.error("sendMessage retry failed: %s", retry_exc)
                return False
        logger.error("sendMessage failed: %s", exc)
        return False
    except TelegramError as exc:
        logger.error("sendMessage failed: %s", exc)
        return False


def send_text_with_retry(
    session: requests.Session,
    bot_token: str,
    *,
    chat_id: int | str,
    text: str,
    retry_delay: float = _DEFAULT_RETRY_DELAY_SECONDS,
    **more_payload_fields: Any,
) -> bool:
    """Send a text message, scheduling one deferred retry on failure.

    If the first attempt fails (timeout, network blip, 5xx, ...) the send is
    rescheduled on a background timer after ``retry_delay`` seconds and the
    caller immediately gets ``False``. A ``True`` return means the message
    was delivered on the first try.

    Args:
        session: HTTP session for making requests.
        bot_token: Telegram bot token.
        chat_id: Target chat id.
        text: Message text (Markdown subset).
        retry_delay: Seconds to wait before the deferred retry.
        more_payload_fields: Extra fields forwarded to :func:`send_text`.

    Returns:
        True if sent immediately, False if a retry was scheduled.
    """
    ok = send_text(
        session,
        bot_token,
        chat_id=chat_id,
        text=text,
        **more_payload_fields,
    )
    if ok:
        return True

    logger.warning(
        "send_text failed for chat %s, scheduling retry in %.0fs.", chat_id, retry_delay
    )
    from ._defer import defer_after

    defer_after(
        retry_delay,
        send_text,
        session,
        bot_token,
        chat_id=chat_id,
        text=text,
        **more_payload_fields,
    )
    return False


def send_question(
    session: requests.Session,
    bot_token: str,
    *,
    chat_id: int | str,
    text: str,
    options: list[str],
    callback_data: list[str],
) -> bool:
    """Send a text message with an inline keyboard of option buttons.

    Args:
        session: HTTP session for making requests.
        bot_token: Telegram bot token.
        chat_id: Target chat id.
        text: Question text (Markdown subset).
        options: Button labels.
        callback_data: Callback data per option; must match ``options``.

    Returns:
        True if the message was delivered successfully.
    """
    reply_markup = option_keyboard(options, callback_data)
    return send_text(
        session,
        bot_token,
        chat_id=chat_id,
        text=text,
        reply_markup=reply_markup,
    )


def answer_callback_query(
    session: requests.Session,
    bot_token: str,
    *,
    callback_query_id: str,
    text: str | None = None,
    show_alert: bool = False,
) -> bool:
    """Acknowledge a callback query, dismissing the button's loading spinner.

    Args:
        session: HTTP session for making requests.
        bot_token: Telegram bot token.
        callback_query_id: The callback query id to answer.
        text: Optional notification text. Without it Telegram shows no
            feedback unless ``show_alert`` is set.
        show_alert: Show the text as an alert dialog instead of a toast.

    Returns:
        True if the API returned ``ok``.
    """
    payload: dict[str, Any] = {"callback_query_id": callback_query_id}
    if text is not None:
        payload["text"] = text
    if show_alert:
        payload["show_alert"] = True

    try:
        api_call(session, bot_token, "answerCallbackQuery", json_payload=payload)
        return True
    except TelegramError as exc:
        logger.error("answerCallbackQuery failed: %s", exc)
        return False


def _send_file(
    session: requests.Session,
    bot_token: str,
    *,
    method: str,
    file_field: str,
    chat_id: int | str,
    file_path: Path | str,
    caption: str | None,
    extra_fields: dict[str, Any] | None = None,
) -> bool:
    """Upload a local file as a Telegram attachment."""
    path = Path(file_path)
    if not path.is_file():
        logger.error("File does not exist: %s", path)
        return False

    data: dict[str, Any] = {"chat_id": chat_id}
    if caption:
        data["caption"] = caption
    if extra_fields:
        data.update(extra_fields)

    try:
        with path.open("rb") as handle:
            api_call(
                session,
                bot_token,
                method,
                json_payload=data,
                files={file_field: handle},
                timeout=(10.0, 60.0),
            )
        return True
    except TelegramError as exc:
        logger.error("%s upload failed: %s", method, exc)
        return False


def send_photo(
    session: requests.Session,
    bot_token: str,
    *,
    chat_id: int | str,
    photo_path: Path | str,
    caption: str | None = None,
    **extra_fields: Any,
) -> bool:
    """Send a photo from a local file.

    Args:
        session: HTTP session for making requests.
        bot_token: Telegram bot token.
        chat_id: Target chat id.
        photo_path: Local path of the image file.
        caption: Optional caption (0-1024 characters).
        extra_fields: Extra API fields (e.g. ``reply_markup``).

    Returns:
        True if the API returned ``ok``.
    """
    return _send_file(
        session,
        bot_token,
        method="sendPhoto",
        file_field="photo",
        chat_id=chat_id,
        file_path=photo_path,
        caption=caption,
        extra_fields=extra_fields,
    )


def send_video(
    session: requests.Session,
    bot_token: str,
    *,
    chat_id: int | str,
    video_path: Path | str,
    caption: str | None = None,
    **extra_fields: Any,
) -> bool:
    """Send a video from a local file."""
    return _send_file(
        session,
        bot_token,
        method="sendVideo",
        file_field="video",
        chat_id=chat_id,
        file_path=video_path,
        caption=caption,
        extra_fields=extra_fields,
    )


def send_audio(
    session: requests.Session,
    bot_token: str,
    *,
    chat_id: int | str,
    audio_path: Path | str,
    caption: str | None = None,
    **extra_fields: Any,
) -> bool:
    """Send an audio file (music) from a local file."""
    return _send_file(
        session,
        bot_token,
        method="sendAudio",
        file_field="audio",
        chat_id=chat_id,
        file_path=audio_path,
        caption=caption,
        extra_fields=extra_fields,
    )


def send_document(
    session: requests.Session,
    bot_token: str,
    *,
    chat_id: int | str,
    document_path: Path | str,
    caption: str | None = None,
    **extra_fields: Any,
) -> bool:
    """Send a generic file (document) from a local file."""
    return _send_file(
        session,
        bot_token,
        method="sendDocument",
        file_field="document",
        chat_id=chat_id,
        file_path=document_path,
        caption=caption,
        extra_fields=extra_fields,
    )


def send_chat_action(
    session: requests.Session,
    bot_token: str,
    *,
    chat_id: int | str,
    action: str,
) -> bool:
    """Tell the user the bot is doing something (``typing``, ``upload_photo``, ...).

    Args:
        session: HTTP session for making requests.
        bot_token: Telegram bot token.
        chat_id: Target chat id.
        action: One of the action types Telegram accepts, e.g. ``typing``.

    Returns:
        True if the API returned ``ok``.
    """
    try:
        api_call(
            session,
            bot_token,
            "sendChatAction",
            json_payload={"chat_id": chat_id, "action": action},
        )
        return True
    except TelegramError as exc:
        logger.error("sendChatAction failed: %s", exc)
        return False
