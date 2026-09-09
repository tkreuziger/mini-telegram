"""Tests for markup builders and public package surface."""

import minitelegram
from minitelegram import inline_button, inline_keyboard, option_keyboard


class TestMarkup:
    def test_inline_button_callback(self):
        assert inline_button("A", callback_data="a") == {
            "text": "A",
            "callback_data": "a",
        }

    def test_inline_button_url(self):
        assert inline_button("Site", url="https://example.com") == {
            "text": "Site",
            "url": "https://example.com",
        }

    def test_inline_keyboard_rows(self):
        rows = [
            [inline_button("A", callback_data="a")],
            [inline_button("B", callback_data="b")],
        ]
        assert inline_keyboard(rows) == {
            "inline_keyboard": [
                [{"text": "A", "callback_data": "a"}],
                [{"text": "B", "callback_data": "b"}],
            ]
        }

    def test_option_keyboard_columns(self):
        markup = option_keyboard(["1", "2", "3"], ["a", "b", "c"], columns=2)
        rows = markup["inline_keyboard"]
        assert rows == [
            [{"text": "1", "callback_data": "a"}, {"text": "2", "callback_data": "b"}],
            [{"text": "3", "callback_data": "c"}],
        ]


class TestPackageSurface:
    def test_public_names(self):
        for name in [
            "telegram_session",
            "get_updates",
            "send_text",
            "send_photo",
            "send_question",
            "CallbackManager",
            "UserWhitelist",
            "parse_update",
            "classify_message",
            "TelegramUpdate",
            "markdown_to_telegram_html",
            "api_call",
        ]:
            assert hasattr(minitelegram, name), name

    def test_version(self):
        assert minitelegram.__version__
