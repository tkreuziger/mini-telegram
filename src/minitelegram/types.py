"""Typed models for incoming Telegram updates.

The model mirrors what the reference service in ``telegram-ai-bots`` needs
(``core/telegram/types.py`` + ``core/telegram/parsing.py``) while keeping the
types plain and self-contained. Messages are classified into simple variants
(``TextMessage``, ``ImageMessage``, ...) by ``minitelegram.parsing.classify_message``.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TextMessage:
    """A pure text message."""

    text: str


@dataclass(frozen=True)
class ImageMessage:
    """An image without a caption."""

    photo_file_id: str


@dataclass(frozen=True)
class TextAndImageMessage:
    """An image with a text caption."""

    text: str
    photo_file_id: str


@dataclass(frozen=True)
class AudioMessage:
    """An audio file without a caption."""

    audio_file_id: str


@dataclass(frozen=True)
class TextAndAudioMessage:
    """An audio file with a text caption."""

    text: str
    audio_file_id: str


@dataclass(frozen=True)
class VideoMessage:
    """A video without a caption."""

    video_file_id: str


@dataclass(frozen=True)
class TextAndVideoMessage:
    """A video with a text caption."""

    text: str
    video_file_id: str


@dataclass(frozen=True)
class DocumentMessage:
    """A generic file attachment without a caption."""

    document_file_id: str


@dataclass(frozen=True)
class TextAndDocumentMessage:
    """A generic file attachment with a text caption."""

    text: str
    document_file_id: str


# Union of every supported user message shape.
IncomingMessage = (
    TextMessage
    | ImageMessage
    | TextAndImageMessage
    | AudioMessage
    | TextAndAudioMessage
    | VideoMessage
    | TextAndVideoMessage
    | DocumentMessage
    | TextAndDocumentMessage
)


@dataclass(frozen=True)
class TelegramFile:
    """A file reference returned by ``getFile``.

    Attributes:
        file_id: Unique identifier for the file.
        file_unique_id: Persistent identifier that stays the same across
            bot restarts and API calls.
        file_size: File size in bytes, if provided.
        file_path: Server-relative path used to download the file, if
            Telegram made it downloadable.
    """

    file_id: str
    file_unique_id: str
    file_size: int | None = None
    file_path: str | None = None


@dataclass(frozen=True)
class TelegramMessage:
    """A parsed incoming message.

    Attributes:
        message_id: Unique message identifier inside the chat.
        chat_id: Chat the message was sent in (user, group or channel id).
        from_user_id: User id of the sender, if known.
        is_bot: Whether the sender is a bot.
        text: Message text, or the caption when the message carries media.
        photo_file_id: File id of the largest photo size, if present.
        video_file_id: File id of the video, if present.
        audio_file_id: File id of the audio, if present.
        document_file_id: File id of a generic document, if present.
    """

    message_id: int
    chat_id: int
    from_user_id: int | None
    text: str | None
    photo_file_id: str | None = None
    video_file_id: str | None = None
    audio_file_id: str | None = None
    document_file_id: str | None = None
    is_bot: bool = False


@dataclass(frozen=True)
class TelegramCallback:
    """A parsed inline-keyboard callback query.

    Attributes:
        id: Unique callback query identifier, echoed when answering.
        from_user_id: User who pressed the button.
        data: Opaque callback data attached to the button.
        message_chat_id: Chat id of the message the button belongs to,
            if available.
    """

    id: str
    from_user_id: int
    data: str
    message_chat_id: int | None


@dataclass(frozen=True)
class TelegramUpdate:
    """A single update returned by ``getUpdates``.

    Attributes:
        update_id: Monotonic update identifier. Acknowledging updates is done
            by passing ``update_id + 1`` as the next ``offset``.
        message: Parsed message, if the update carries one.
        callback: Parsed callback query, if the update carries one.
    """

    update_id: int
    message: TelegramMessage | None = None
    callback: TelegramCallback | None = None
