"""Thread-safe whitelist of allowed Telegram user ids.

An empty whitelist allows everyone; once at least one id is present only
those users are allowed. All reads and mutations take the internal lock, so
the whitelist can be shared across the polling thread and admin commands.
"""

from dataclasses import dataclass, field
from threading import Lock

from .types import TelegramUpdate


@dataclass
class UserWhitelist:
    """A set of allowed user ids guarded by a lock.

    Attributes:
        allowed: Set of whitelisted user ids. Empty means "allow everyone".
    """

    allowed: set[int] = field(default_factory=set)
    _lock: Lock = field(default_factory=Lock, repr=False)


def is_active(wl: UserWhitelist) -> bool:
    """Return True when the whitelist is restricting access."""
    with wl._lock:
        return len(wl.allowed) > 0


def is_allowed(wl: UserWhitelist, user_id: int | None) -> bool:
    """Check whether a user id may interact.

    An empty whitelist allows everyone; a ``None`` user id is only allowed
    when the whitelist is inactive.

    Args:
        wl: The whitelist.
        user_id: Telegram user id, or None when unavailable.

    Returns:
        True if the user is allowed.
    """
    with wl._lock:
        if not wl.allowed:
            return True
        return user_id is not None and user_id in wl.allowed


def add(wl: UserWhitelist, user_id: int) -> None:
    """Allow a user id."""
    with wl._lock:
        wl.allowed.add(user_id)


def remove(wl: UserWhitelist, user_id: int) -> None:
    """Revoke a user id (no-op when absent)."""
    with wl._lock:
        wl.allowed.discard(user_id)


def clear(wl: UserWhitelist) -> None:
    """Remove every id, effectively allowing all users."""
    with wl._lock:
        wl.allowed.clear()


def snapshot(wl: UserWhitelist) -> set[int]:
    """Return a copy of the currently allowed ids."""
    with wl._lock:
        return set(wl.allowed)


def filter_update(wl: UserWhitelist, update: TelegramUpdate) -> bool:
    """Decide whether an update should be processed.

    Checks the sender of the message (or the callback query) against the
    whitelist.

    Args:
        wl: The whitelist.
        update: A parsed :class:`TelegramUpdate`.

    Returns:
        True when the update should be processed.
    """
    if update.message is not None:
        return is_allowed(wl, update.message.from_user_id)
    if update.callback is not None:
        return is_allowed(wl, update.callback.from_user_id)
    return True
