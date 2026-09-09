"""Lightweight formatting helpers for Telegram message text.

Telegram supports an HTML subset and MarkdownV2.  This module converts a
small, deliberately safe Markdown subset to Telegram HTML (used with
``parse_mode="HTML"``), and provides helpers to strip markup again when a
message needs to be re-sent as plain text.
"""

import html
import re

_MARKDOWN = re.compile(
    r"```([\s\S]*?)```"
    r"|`([^`]+)`"
    r"|\*\*\*(.+?)\*\*\*"
    r"|\*\*(.+?)\*\*"
    r"|\*(.+?)\*"
    r"|\[([^\]]+)\]\(([^)]+)\)"
    r"|#{1,6} (.+?)\n"
    r"|&gt; (.+?)\n"
)

_REPLACEMENTS = {
    1: lambda m: f"<pre>{m.group(1)}</pre>",
    2: lambda m: f"<code>{m.group(2)}</code>",
    3: lambda m: f"<b><i>{m.group(3)}</i></b>",
    4: lambda m: f"<b>{m.group(4)}</b>",
    5: lambda m: f"<i>{m.group(5)}</i>",
    6: lambda m: f'<a href="{m.group(7)}">{m.group(6)}</a>',
}


def markdown_to_telegram_html(text: str) -> str:
    """Convert a limited Markdown subset to Telegram-compatible HTML.

    Escapes HTML first, then converts markdown patterns in a single pass
    to avoid overlapping tag issues.

    Supported syntax: fenced/backtick code, ``**bold**``, ``*italic*``,
    ``***bold italic***``, ``[text](url)`` links, ``#`` headings and
    ``> `` blockquotes.

    Args:
        text: Input text with Markdown formatting.

    Returns:
        HTML string safe for Telegram's ``parse_mode="HTML"``.
    """
    escaped = html.escape(text, quote=False)

    def _replace(match: re.Match) -> str:
        # Headings: recursively process inner markdown before wrapping in <b>.
        if match.group(8) is not None:
            inner = _MARKDOWN.sub(_replace, match.group(8))
            return f"<b>{inner}</b>\n"
        # Blockquotes: recursively process inner markdown before wrapping in <i>.
        if match.group(9) is not None:
            inner = _MARKDOWN.sub(_replace, match.group(9))
            return f"<i>{inner}</i>\n"
        for group_idx, formatter in _REPLACEMENTS.items():
            if match.group(group_idx) is not None:
                return formatter(match)
        return match.group(0)

    return _MARKDOWN.sub(_replace, escaped)


_TAG_RE = re.compile(r"<[^>]+>")


def strip_html(text: str) -> str:
    """Remove HTML tags, leaving only the inner text."""
    return _TAG_RE.sub("", text)
