"""Convert raw Telegram update JSON into the typed models in :mod:`types`."""

from typing import Any

from .types import (
    AudioMessage,
    DocumentMessage,
    ImageMessage,
    IncomingMessage,
    TelegramCallback,
    TelegramMessage,
    TelegramUpdate,
    TextAndAudioMessage,
    TextAndDocumentMessage,
    TextAndImageMessage,
    TextAndVideoMessage,
    TextMessage,
    VideoMessage,
)

_MEDIA_KEYS = ("photo", "video", "audio", "document")

_TEXT_SOURCE_FIELDS = ("caption", "text")


def parse_message(raw: dict[str, Any] | None) -> TelegramMessage | None:
    """Parse a raw Telegram message dict into a :class:`TelegramMessage`.

    Returns ``None`` for empty input or malformed messages (missing ids).

    Args:
        raw: The raw ``message`` / ``channel_post`` object from an update.

    Returns:
        A :class:`TelegramMessage`, or ``None`` when parsing fails.
    """
    if raw is None:
        return None

    try:
        chat_id = int(raw["chat"]["id"])
        message_id = int(raw["message_id"])
    except (KeyError, TypeError, ValueError):
        return None

    from_user = raw.get("from") or raw.get("sender_chat")
    try:
        from_user_id = int(from_user["id"]) if from_user else None
    except (KeyError, TypeError, ValueError):
        from_user_id = None
    is_bot = bool(from_user.get("is_bot", False)) if from_user else False

    # Telegram puts media text in ``caption``, plain text in ``text``.
    text = next((raw.get(key) for key in _TEXT_SOURCE_FIELDS if raw.get(key)), None)

    photo = raw.get("photo")
    photo_file_id: str | None = None
    if isinstance(photo, list) and photo:
        # Photo sizes are ordered smallest to largest; keep the biggest.
        photo_file_id = photo[-1].get("file_id")

    def _file_id(media_key: str) -> str | None:
        media = raw.get(media_key)
        if isinstance(media, dict):
            return media.get("file_id")
        return None

    return TelegramMessage(
        message_id=message_id,
        chat_id=chat_id,
        from_user_id=from_user_id,
        is_bot=is_bot,
        text=text,
        photo_file_id=photo_file_id,
        video_file_id=_file_id("video"),
        audio_file_id=_file_id("audio"),
        document_file_id=_file_id("document"),
    )


def parse_callback(raw: dict[str, Any] | None) -> TelegramCallback | None:
    """Parse a raw ``callback_query`` dict into a :class:`TelegramCallback`.

    Returns ``None`` for empty or malformed input.

    Args:
        raw: The raw ``callback_query`` object from an update.

    Returns:
        A :class:`TelegramCallback`, or ``None`` when parsing fails.
    """
    if raw is None:
        return None

    try:
        from_user_id = int(raw["from"]["id"])
    except (KeyError, TypeError, ValueError):
        return None

    callback_id = raw.get("id")
    data = raw.get("data")
    if not isinstance(callback_id, str) or data is None:
        return None

    message_chat_id: int | None = None
    message = raw.get("message")
    if isinstance(message, dict):
        chat = message.get("chat")
        if isinstance(chat, dict):
            try:
                message_chat_id = int(chat["id"])
            except (KeyError, TypeError, ValueError):
                message_chat_id = None

    return TelegramCallback(
        id=callback_id,
        from_user_id=from_user_id,
        data=data,
        message_chat_id=message_chat_id,
    )


def parse_update(raw: dict[str, Any]) -> TelegramUpdate | None:
    """Parse a raw update dict into a :class:`TelegramUpdate`.

    Args:
        raw: A single item from the ``result`` array of ``getUpdates``.

    Returns:
        A :class:`TelegramUpdate`, or ``None`` when the update id is missing.
    """
    try:
        update_id = int(raw["update_id"])
    except (KeyError, TypeError, ValueError):
        return None

    return TelegramUpdate(
        update_id=update_id,
        message=parse_message(raw.get("message") or raw.get("channel_post")),
        callback=parse_callback(raw.get("callback_query")),
    )


def classify_message(msg: TelegramMessage) -> IncomingMessage | None:
    """Classify a :class:`TelegramMessage` into a typed content variant.

    Media with a caption become the ``TextAnd*`` variants; media without a
    caption become the plain variants. Returns ``None`` for messages with no
    supported content (stickers, locations, service messages, ...).

    Args:
        msg: A parsed :class:`TelegramMessage`.

    Returns:
        A typed content variant, or ``None`` if the message has no
        text/photo/video/audio/document content.
    """
    text = msg.text
    photo = msg.photo_file_id
    audio = msg.audio_file_id
    video = msg.video_file_id
    document = msg.document_file_id

    if photo:
        return (
            TextAndImageMessage(text=text, photo_file_id=photo)
            if text
            else ImageMessage(photo_file_id=photo)
        )
    if video:
        return (
            TextAndVideoMessage(text=text, video_file_id=video)
            if text
            else VideoMessage(video_file_id=video)
        )
    if audio:
        return (
            TextAndAudioMessage(text=text, audio_file_id=audio)
            if text
            else AudioMessage(audio_file_id=audio)
        )
    if document:
        return (
            TextAndDocumentMessage(text=text, document_file_id=document)
            if text
            else DocumentMessage(document_file_id=document)
        )
    if text:
        return TextMessage(text=text)
    return None
