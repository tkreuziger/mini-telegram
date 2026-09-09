"""Tests for the sending helpers (uses FakeSession, no network)."""

from pathlib import Path

import pytest

from minitelegram.sending import (
    answer_callback_query,
    send_chat_action,
    send_document,
    send_photo,
    send_question,
    send_text,
    send_text_with_retry,
)

TOKEN = "123:TOKEN"


def _ok() -> dict:
    return {"ok": True, "result": {"message_id": 1}}


class TestSendText:
    def test_sends_html_payload(self, fake_session):
        assert send_text(fake_session, TOKEN, chat_id=100, text="hello") is True
        req = fake_session.requests[-1]
        assert req.method == "POST"
        assert req.url.endswith("/bot123:TOKEN/sendMessage")
        assert req.json["chat_id"] == 100
        assert req.json["text"] == "hello"
        assert req.json["parse_mode"] == "HTML"

    def test_converts_markdown(self, fake_session):
        send_text(fake_session, TOKEN, chat_id=100, text="**bold**")
        assert fake_session.requests[-1].json["text"] == "<b>bold</b>"

    def test_parse_mode_none_sends_verbatim(self, fake_session):
        send_text(fake_session, TOKEN, chat_id=100, text="**bold**", parse_mode="")
        req = fake_session.requests[-1]
        assert req.json["text"] == "**bold**"
        assert "parse_mode" not in req.json

    def test_long_text_is_split(self, fake_session):
        para = "word " * 900  # ~4500 chars
        ok = send_text(fake_session, TOKEN, chat_id=100, text=para)
        assert ok is True
        assert len(fake_session.requests) == 2
        for req in fake_session.requests:
            assert len(req.json["text"]) <= 4096

    def test_split_prefers_paragraph_boundaries(self, fake_session):
        big = "a" * 3000
        text = f"{big}\n\n{big}\n\n{big}"
        send_text(fake_session, TOKEN, chat_id=100, text=text)
        chunks = [req.json["text"] for req in fake_session.requests]
        assert len(chunks) == 3
        assert all(len(c) <= 4096 for c in chunks)

    def test_falls_back_to_plain_text_on_parse_error(self):
        from tests.conftest import FakeSession

        session = FakeSession(
            responses=[
                {
                    "ok": False,
                    "error_code": 400,
                    "description": "can't parse entities: ...",
                },
                _ok(),
            ]
        )
        assert send_text(session, TOKEN, chat_id=100, text="**bold**") is True
        first, second = session.requests
        assert first.json["text"] == "<b>bold</b>"
        assert second.json["text"] == "bold"
        assert "parse_mode" not in second.json

    def test_returns_false_on_api_error(self, fake_session):
        fake_session.responses = [
            {"ok": False, "error_code": 403, "description": "blocked"}
        ]
        assert send_text(fake_session, TOKEN, chat_id=100, text="hi") is False

    def test_extra_fields_forwarded(self, fake_session):
        send_text(
            fake_session,
            TOKEN,
            chat_id=100,
            text="hi",
            disable_notification=True,
        )
        assert fake_session.requests[-1].json["disable_notification"] is True


class TestSendQuestion:
    def test_builds_option_keyboard(self, fake_session):
        ok = send_question(
            fake_session,
            TOKEN,
            chat_id=100,
            text="Pick one",
            options=["A", "B"],
            callback_data=["a", "b"],
        )
        assert ok is True
        req = fake_session.requests[-1]
        markup = req.json["reply_markup"]
        assert markup == {
            "inline_keyboard": [
                [{"text": "A", "callback_data": "a"}],
                [{"text": "B", "callback_data": "b"}],
            ]
        }

    def test_mismatched_lists_raise(self, fake_session):
        with pytest.raises(ValueError):
            send_question(
                fake_session,
                TOKEN,
                chat_id=100,
                text="x",
                options=["A", "B"],
                callback_data=["a"],
            )


class TestMiscSends:
    def test_answer_callback_query(self, fake_session):
        assert (
            answer_callback_query(fake_session, TOKEN, callback_query_id="cb1") is True
        )
        req = fake_session.requests[-1]
        assert req.url.endswith("/answerCallbackQuery")
        assert req.json == {"callback_query_id": "cb1"}

    def test_answer_callback_query_with_text(self, fake_session):
        answer_callback_query(
            fake_session, TOKEN, callback_query_id="cb1", text="done", show_alert=True
        )
        assert fake_session.requests[-1].json["text"] == "done"
        assert fake_session.requests[-1].json["show_alert"] is True

    def test_send_chat_action(self, fake_session):
        assert (
            send_chat_action(fake_session, TOKEN, chat_id=100, action="typing") is True
        )
        assert fake_session.requests[-1].url.endswith("/sendChatAction")
        assert fake_session.requests[-1].json == {"chat_id": 100, "action": "typing"}


class TestMediaSends:
    def test_send_photo_uploads_file(self, fake_session, tmp_path: Path):
        photo = tmp_path / "pic.jpg"
        photo.write_bytes(b"JPEGDATA")
        assert send_photo(fake_session, TOKEN, chat_id=100, photo_path=photo) is True
        req = fake_session.requests[-1]
        assert req.url.endswith("/sendPhoto")
        assert req.data["chat_id"] == 100
        handle = req.files["photo"]
        assert handle.name == str(photo)

    def test_send_document(self, fake_session, tmp_path: Path):
        doc = tmp_path / "file.txt"
        doc.write_text("content")
        assert (
            send_document(
                fake_session, TOKEN, chat_id=100, document_path=doc, caption="hi"
            )
            is True
        )
        req = fake_session.requests[-1]
        assert req.url.endswith("/sendDocument")
        assert req.data["caption"] == "hi"

    def test_missing_file_returns_false(self, fake_session, tmp_path: Path):
        missing = tmp_path / "nope.jpg"
        assert send_photo(fake_session, TOKEN, chat_id=100, photo_path=missing) is False
        assert fake_session.requests == []


class TestSendTextWithRetry:
    def test_immediate_success(self, fake_session):
        assert send_text_with_retry(fake_session, TOKEN, chat_id=100, text="hi") is True
        assert len(fake_session.requests) == 1

    def test_failure_schedules_retry(self):
        from tests.conftest import FakeSession

        session = FakeSession(
            responses=[{"ok": False, "error_code": 500, "description": "boom"}]
        )
        # First call fails -> schedules a deferred retry; give it time to fire.
        assert (
            send_text_with_retry(
                session, TOKEN, chat_id=100, text="hi", retry_delay=0.05
            )
            is False
        )
        import time

        deadline = time.time() + 5
        while len(session.requests) < 2 and time.time() < deadline:
            time.sleep(0.05)
        assert len(session.requests) == 2  # retry fired on background thread
