"""Helpers for building Telegram keyboards and inline buttons."""

from typing import Any


def inline_button(
    text: str,
    *,
    callback_data: str | None = None,
    url: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """Build one inline keyboard button.

    Args:
        text: Button label.
        callback_data: Data sent back to the bot when pressed. Mutually
            exclusive with ``url``.
        url: HTTPS URL opened when pressed instead of a callback.
        **extra: Any additional button fields forwarded verbatim.

    Returns:
        A button dict ready for ``inline_keyboard``.
    """
    button: dict[str, Any] = {"text": text}
    if callback_data is not None:
        button["callback_data"] = callback_data
    if url is not None:
        button["url"] = url
    button.update(extra)
    return button


def inline_keyboard(rows: list[list[dict[str, Any]]]) -> dict[str, Any]:
    """Build a ``reply_markup`` payload for an inline keyboard.

    Args:
        rows: Button rows; each row is a list of button dicts (see
            :func:`inline_button`).

    Returns:
        A dict to pass as ``reply_markup`` to a send/edit method.
    """
    return {"inline_keyboard": rows}


def option_keyboard(
    options: list[str],
    callback_data: list[str],
    columns: int = 1,
) -> dict[str, Any]:
    """Build an inline keyboard of one-option-per-row callback buttons.

    Args:
        options: Labels of each option.
        callback_data: Callback data for each option; must match ``options``
            in length and order.
        columns: Number of options per keyboard row.

    Returns:
        A ``reply_markup`` dict, or ``None`` when lists are empty.

    Raises:
        ValueError: If ``options`` and ``callback_data`` have different
            lengths, or ``columns`` is not positive.
    """
    if len(options) != len(callback_data):
        raise ValueError("options and callback_data must have equal length")
    if columns < 1:
        raise ValueError("columns must be at least 1")
    if not options:
        return {"inline_keyboard": []}

    buttons = [
        inline_button(label, callback_data=data)
        for label, data in zip(options, callback_data, strict=True)
    ]
    rows = [
        buttons[i : i + columns]  # noqa: E203
        for i in range(0, len(buttons), columns)
    ]
    return inline_keyboard(rows)
