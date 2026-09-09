# mini-telegram

A small, dependency-light toolkit for building Telegram bots: **polling,
sending, receiving, media, inline callbacks and access control** — without
any AI-specific layers (no personas, memory, or LLM integration).

It is an extraction of the generic plumbing that powers the
[`telegram-ai-bots`](https://github.com/tkreuziger/telegram-ai-bots) service
(its `core/telegram/*` package and the two supporting utilities
`retrying_requests_session` / `defer`), cleaned up into a reusable library.

## Install

```bash
pip install -e .
# or, for development:
pip install -e ".[dev]"
```

Requires Python ≥ 3.10 and `requests`.

## Quick start

Every API function takes the `session` and `bot_token` explicitly, so a
single session can be shared between the polling loop and out-of-band jobs,
and everything is easy to test with a fake session.

```python
import time

from minitelegram import get_updates, send_text, telegram_session

TOKEN = "123456:ABC-DEF..."

with telegram_session() as session:
    offset = None
    while True:
        updates = get_updates(session, TOKEN, offset=offset, allowed_updates=["message"])
        for update in updates:
            offset = update.update_id + 1  # acknowledge
            msg = update.message
            if msg is None or msg.text is None:
                continue
            send_text(session, TOKEN, chat_id=msg.chat_id, text=f"You said: {msg.text}")
        time.sleep(0.5)
```

Messages longer than 4096 characters are split automatically (preferring
paragraph, then newline, then hard boundaries). Text is sent as Telegram HTML
after conversion from a small, safe Markdown subset (`**bold**`, `*italic*`,
`[links](url)`, `` `code` ``, `# headings`, `> quotes`); if Telegram rejects
the entities the chunk is retried once as plain text.

## Inline keyboards and callbacks

Send a question with buttons, then match button presses back to the pending
question via `CallbackManager` (persisted to disk when a `persist_dir` is
given, so presses survive restarts; entries expire after a TTL):

```python
from pathlib import Path

from minitelegram import (
    CallbackManager, answer_callback_query, send_question,
    telegram_session, get_updates,
)

manager = CallbackManager(persist_dir=Path("/tmp/mybot-callbacks"))

with telegram_session() as session:
    # Ask a question with two options.
    cb_id = manager.create(chat_id=123, question="Continue?", options=["Yes", "No"])
    send_question(
        session, TOKEN, chat_id=123,
        text="Continue?",
        options=["Yes", "No"],
        callback_data=[manager.make_callback_data(cb_id, i) for i in range(2)],
    )

    # In the polling loop:
    for update in get_updates(session, TOKEN, offset=offset):
        offset = update.update_id + 1
        callback = update.callback
        if callback is None:
            continue
        parsed = CallbackManager.parse_callback_data(callback.data)  # (cb_id, idx)
        if parsed is not None:
            pending, chosen = manager.resolve(*parsed)  # consumes the entry
            answer_callback_query(session, TOKEN, callback_query_id=callback.id)
            if chosen is not None:
                send_text(session, TOKEN, chat_id=pending.chat_id, text=f"You chose: {chosen}")
```

## Receiving media

```python
from minitelegram import ImageMessage, TextAndImageMessage, download_by_file_id
from minitelegram.parsing import classify_message

incoming = classify_message(update.message)  # typed variant
if isinstance(incoming, (ImageMessage, TextAndImageMessage)):
    download_by_file_id(
        session, TOKEN,
        file_id=incoming.photo_file_id,
        target_path=f"/tmp/downloads/{update.message.message_id}.jpg",
    )
```

## Restricting access

```python
from minitelegram import UserWhitelist, whitelist_filter_update

allowlist = UserWhitelist(allowed={123, 456})  # empty set = allow everyone
for update in get_updates(session, TOKEN, offset=offset):
    if not whitelist_filter_update(allowlist, update):
        continue  # skip disallowed senders / button presses
```

## Low-level escape hatch

Methods that have no dedicated wrapper (e.g. `editMessageText`,
`deleteMessage`, `setMyCommands`) can be called directly:

```python
from minitelegram import api_call
from minitelegram.errors import TelegramAPIError

try:
    api_call(session, TOKEN, "editMessageText",
             json_payload={"chat_id": ..., "message_id": ..., "text": "edited"})
except TelegramAPIError as exc:
    print("Telegram said no:", exc)
```

## Module map

| Module | Purpose |
| --- | --- |
| `polling.py` | `get_updates` long polling with offset |
| `sending.py` | text (splitting + HTML fallback), question keyboards, media uploads, chat actions |
| `parsing.py` | raw update JSON → typed models |
| `types.py` | `TelegramUpdate`, `TelegramMessage`, `TelegramCallback`, content variants |
| `media.py` | resolve `file_id` → download to disk |
| `callbacks.py` | pending inline-keyboard question store (TTL + optional persistence) |
| `whitelist.py` | thread-safe user allowlist |
| `markup.py` | inline keyboard / option keyboard builders |
| `formatting.py` | Markdown-subset → Telegram HTML, tag stripping |
| `session.py` | retrying `telegram_session()` context manager |
| `errors.py` | `TelegramError`, `TelegramRequestError`, `TelegramAPIError` |

## Tests

```bash
pytest
```

The tests run against a fake HTTP session — no network or bot token needed.
