"""Callbacks module: manage pending inline-keyboard questions.

A common pattern is to send a question with inline buttons and then match a
``callback_query`` back to the question.  Callback data is space-limited, so
the manager stores the pending question (chat id, question text, options)
locally under a short generated id and encodes ``id:option_index`` into the
button's ``callback_data``.

Pending entries expire after a configurable TTL.  When ``persist_dir`` is
given the pending map is saved to disk (``pending_callbacks.json``) after
every mutation so callbacks survive a service restart.
"""

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from threading import Lock
from uuid import uuid4

logger = logging.getLogger(__name__)

_DEFAULT_TTL_SECONDS = 3600
_DEFAULT_ID_CHARS = 8


@dataclass(frozen=True)
class PendingCallback:
    """A stored question that is waiting for a button press.

    Attributes:
        chat_id: Chat the question was asked in.
        question: The question text.
        options: Option labels in order.
        bot_identifier: Optional name of the bot that asked (useful when one
            callback store is shared by several bots).
        created_at: Unix timestamp of creation.
    """

    chat_id: int | str
    question: str
    options: list[str]
    bot_identifier: str | None = None
    created_at: float = field(default_factory=time.time)


@dataclass
class CallbackManager:
    """Thread-safe store of pending inline-keyboard questions.

    Attributes:
        persist_dir: Optional directory for persisting pending callbacks
            across restarts. Created if it does not exist.
        ttl_seconds: Seconds a pending callback stays valid.
        id_chars: Number of hex characters in generated callback ids.
    """

    persist_dir: Path | None = None
    ttl_seconds: float = _DEFAULT_TTL_SECONDS
    id_chars: int = _DEFAULT_ID_CHARS
    _pending: dict[str, PendingCallback] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock)

    def __post_init__(self) -> None:
        if self.persist_dir is not None:
            self.persist_dir.mkdir(parents=True, exist_ok=True)
            self._load()

    def create(
        self,
        chat_id: int | str,
        question: str,
        options: list[str],
        *,
        bot_identifier: str | None = None,
    ) -> str:
        """Store a pending question and return its callback id."""
        if not options:
            raise ValueError("options must not be empty")
        with self._lock:
            self._cleanup_expired()
            callback_id = uuid4().hex[: self.id_chars]
            self._pending[callback_id] = PendingCallback(
                chat_id=chat_id,
                question=question,
                options=list(options),
                bot_identifier=bot_identifier,
                created_at=time.time(),
            )
            self._save()
        logger.debug(
            "Created callback %s in chat %s with %d options",
            callback_id,
            chat_id,
            len(options),
        )
        return callback_id

    def resolve(
        self, callback_id: str, option_index: int
    ) -> tuple[PendingCallback, str] | None:
        """Resolve a pressed option.

        Removes and returns the stored question together with the label of
        the option that was pressed. Returns ``None`` when the id is unknown
        (expired or already used) or the option index is out of range. An
        invalid option index does not consume the pending entry.

        Args:
            callback_id: The callback id embedded in the button data.
            option_index: The pressed option index (from the button data).

        Returns:
            ``(PendingCallback, option_label)`` or ``None``.
        """
        with self._lock:
            entry = self._pending.get(callback_id)
            if entry is None:
                return None
            if option_index < 0 or option_index >= len(entry.options):
                logger.debug(
                    "Callback %s option index %d out of range (0-%d)",
                    callback_id,
                    option_index,
                    len(entry.options) - 1,
                )
                return None
            del self._pending[callback_id]
            self._save()
        return entry, entry.options[option_index]

    def peek(self, callback_id: str) -> PendingCallback | None:
        """Return the stored question without consuming it."""
        with self._lock:
            return self._pending.get(callback_id)

    def make_callback_data(self, callback_id: str, option_index: int) -> str:
        """Encode a callback id and option index into button ``callback_data``."""
        return f"{callback_id}:{option_index}"

    @staticmethod
    def parse_callback_data(data: str) -> tuple[str, int] | None:
        """Decode data produced by :meth:`make_callback_data`.

        Returns ``(callback_id, option_index)`` or ``None`` when the data has
        an unexpected format.
        """
        parts = data.rsplit(":", 1)
        if len(parts) != 2:
            return None
        callback_id, index_str = parts
        try:
            return callback_id, int(index_str)
        except ValueError:
            return None

    def _cleanup_expired(self) -> None:
        now = time.time()
        expired = [
            cid
            for cid, entry in self._pending.items()
            if now - entry.created_at > self.ttl_seconds
        ]
        for cid in expired:
            del self._pending[cid]

    def _persist_path(self) -> Path:
        if self.persist_dir is None:
            raise RuntimeError("CallbackManager has no persist_dir")
        return self.persist_dir / "pending_callbacks.json"

    def _save(self) -> None:
        if self.persist_dir is None:
            return
        data = {cid: asdict(entry) for cid, entry in self._pending.items()}
        try:
            with self._persist_path().open("w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2)
        except Exception:
            logger.debug("Failed to persist callbacks.", exc_info=True)

    def _load(self) -> None:
        if self.persist_dir is None:
            return
        path = self._persist_path()
        if not path.exists():
            return
        try:
            with path.open(encoding="utf-8") as handle:
                data = json.load(handle)
            for cid, raw in data.items():
                self._pending[cid] = PendingCallback(**raw)
            self._cleanup_expired()
            self._save()
        except Exception:
            logger.debug("Failed to load pending callbacks.", exc_info=True)
