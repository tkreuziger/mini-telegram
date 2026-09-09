"""Shared constants for the Telegram Bot API."""

TELEGRAM_API_BASE = "https://api.telegram.org"

# Maximum characters Telegram accepts in a single text message.
MAX_MESSAGE_LENGTH = 4096

# Default (connect, read) timeout in seconds for ordinary API calls.
DEFAULT_API_TIMEOUT: tuple[float, float] = (5.0, 15.0)

# Default long-poll seconds for getUpdates when no explicit timeout is given.
DEFAULT_LONG_POLL_SECONDS = 30

# Extra read slack added on top of the long-poll timeout.
LONG_POLL_READ_SLACK = 10
