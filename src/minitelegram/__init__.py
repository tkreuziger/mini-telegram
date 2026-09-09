"""mini-telegram: a small toolkit for building Telegram bots.

Extracted from the generic plumbing of the ``telegram-ai-bots`` service
(``core/telegram/*``) so it can be reused without any of the AI-specific
layers (personas, memory, LLM integration).

Features
--------
- **Polling** — long-poll ``getUpdates`` with offset bookkeeping
  (:mod:`minitelegram.polling`).
- **Sending** — text with automatic long-message splitting and an HTML
  fallback, question keyboards, media uploads and chat actions
  (:mod:`minitelegram.sending`).
- **Receiving** — typed models and parsers for messages and callback queries
  (:mod:`minitelegram.types`, :mod:`minitelegram.parsing`).
- **Media** — resolve ``file_id`` to a download URL and stream files to disk
  (:mod:`minitelegram.media`).
- **Callbacks** — persistent store of pending inline-keyboard questions with
  TTL (:mod:`minitelegram.callbacks`).
- **Access control** — thread-safe user whitelist (:mod:`minitelegram.whitelist`).
- **Markup & formatting** — inline keyboards and a safe Markdown-to-HTML
  converter (:mod:`minitelegram.markup`, :mod:`minitelegram.formatting`).

Usage
-----
All API functions take the ``session`` and ``bot_token`` explicitly, which
keeps them easy to test and lets one session be shared across a polling loop
and out-of-band jobs::

    import time

    from minitelegram import get_updates, send_text, telegram_session

    TOKEN = "123456:ABC..."

    with telegram_session() as session:
        offset = None
        while True:
            updates = get_updates(session, TOKEN, offset=offset)
            for update in updates:
                offset = update.update_id + 1
                if update.message and update.message.text:
                    send_text(
                        session, TOKEN,
                        chat_id=update.message.chat_id,
                        text=f"You said: {update.message.text}",
                    )
            time.sleep(0.5)
"""

from . import callbacks, formatting, markup, media, parsing, polling, sending, whitelist
from ._defer import defer, defer_after
from ._http import api_call, api_url, file_url
from .callbacks import CallbackManager, PendingCallback
from .constants import (
    DEFAULT_API_TIMEOUT,
    DEFAULT_LONG_POLL_SECONDS,
    MAX_MESSAGE_LENGTH,
    TELEGRAM_API_BASE,
)
from .errors import TelegramAPIError, TelegramError, TelegramRequestError
from .formatting import markdown_to_telegram_html, strip_html
from .markup import inline_button, inline_keyboard, option_keyboard
from .media import (
    download_by_file_id,
    download_file,
    get_file,
    get_file_path,
)
from .parsing import (
    classify_message,
    parse_callback,
    parse_message,
    parse_update,
)
from .polling import get_updates
from .sending import (
    answer_callback_query,
    send_audio,
    send_chat_action,
    send_document,
    send_photo,
    send_question,
    send_text,
    send_text_with_retry,
    send_video,
)
from .session import telegram_session
from .types import (
    AudioMessage,
    DocumentMessage,
    ImageMessage,
    IncomingMessage,
    TelegramCallback,
    TelegramFile,
    TelegramMessage,
    TelegramUpdate,
    TextAndAudioMessage,
    TextAndDocumentMessage,
    TextAndImageMessage,
    TextAndVideoMessage,
    TextMessage,
    VideoMessage,
)
from .whitelist import (
    UserWhitelist,
)
from .whitelist import (
    add as whitelist_add,
)
from .whitelist import (
    clear as whitelist_clear,
)
from .whitelist import (
    filter_update as whitelist_filter_update,
)
from .whitelist import (
    is_active as whitelist_is_active,
)
from .whitelist import (
    is_allowed as whitelist_is_allowed,
)
from .whitelist import (
    remove as whitelist_remove,
)
from .whitelist import (
    snapshot as whitelist_snapshot,
)

__version__ = "1.0.0"

__all__ = [
    # modules
    "callbacks",
    "formatting",
    "markup",
    "media",
    "parsing",
    "polling",
    "sending",
    "whitelist",
    # constants
    "TELEGRAM_API_BASE",
    "DEFAULT_API_TIMEOUT",
    "DEFAULT_LONG_POLL_SECONDS",
    "MAX_MESSAGE_LENGTH",
    # session / http
    "telegram_session",
    "api_call",
    "api_url",
    "file_url",
    # errors
    "TelegramError",
    "TelegramRequestError",
    "TelegramAPIError",
    # polling
    "get_updates",
    # sending
    "send_text",
    "send_text_with_retry",
    "send_question",
    "answer_callback_query",
    "send_photo",
    "send_video",
    "send_audio",
    "send_document",
    "send_chat_action",
    # media
    "get_file",
    "get_file_path",
    "download_file",
    "download_by_file_id",
    # markup & formatting
    "inline_button",
    "inline_keyboard",
    "option_keyboard",
    "markdown_to_telegram_html",
    "strip_html",
    # types
    "TextMessage",
    "ImageMessage",
    "TextAndImageMessage",
    "AudioMessage",
    "TextAndAudioMessage",
    "VideoMessage",
    "TextAndVideoMessage",
    "DocumentMessage",
    "TextAndDocumentMessage",
    "IncomingMessage",
    "TelegramFile",
    "TelegramMessage",
    "TelegramCallback",
    "TelegramUpdate",
    # parsing
    "parse_update",
    "parse_message",
    "parse_callback",
    "classify_message",
    # callbacks
    "CallbackManager",
    "PendingCallback",
    # whitelist
    "UserWhitelist",
    "whitelist_is_active",
    "whitelist_is_allowed",
    "whitelist_add",
    "whitelist_remove",
    "whitelist_clear",
    "whitelist_snapshot",
    "whitelist_filter_update",
    # deferred execution
    "defer",
    "defer_after",
]
