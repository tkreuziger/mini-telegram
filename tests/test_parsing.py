"""Tests for message parsing (ported from telegram-ai-bots)."""

from minitelegram.parsing import (
    classify_message,
    parse_callback,
    parse_message,
    parse_update,
)
from minitelegram.types import (
    AudioMessage,
    ImageMessage,
    TelegramMessage,
    TextAndAudioMessage,
    TextAndImageMessage,
    TextAndVideoMessage,
    TextMessage,
    VideoMessage,
)


class TestParseMessage:
    def test_text_message(self):
        raw = {
            "message_id": 1,
            "chat": {"id": 100},
            "from": {"id": 42, "is_bot": False},
            "text": "hello",
        }
        msg = parse_message(raw)
        assert msg is not None
        assert msg.message_id == 1
        assert msg.chat_id == 100
        assert msg.from_user_id == 42
        assert msg.text == "hello"
        assert msg.photo_file_id is None

    def test_photo_with_caption(self):
        raw = {
            "message_id": 2,
            "chat": {"id": 100},
            "from": {"id": 42},
            "caption": "nice photo",
            "photo": [{"file_id": "small"}, {"file_id": "large"}],
        }
        msg = parse_message(raw)
        assert msg is not None
        assert msg.text == "nice photo"
        assert msg.photo_file_id == "large"

    def test_photo_without_caption(self):
        raw = {
            "message_id": 3,
            "chat": {"id": 100},
            "from": {"id": 42},
            "photo": [{"file_id": "only"}],
        }
        msg = parse_message(raw)
        assert msg is not None
        assert msg.text is None
        assert msg.photo_file_id == "only"

    def test_video_message_with_caption(self):
        raw = {
            "message_id": 4,
            "chat": {"id": 100},
            "from": {"id": 42},
            "video": {"file_id": "vid123"},
            "caption": "watch this",
        }
        msg = parse_message(raw)
        assert msg is not None
        assert msg.video_file_id == "vid123"
        assert msg.text == "watch this"

    def test_audio_message(self):
        raw = {
            "message_id": 5,
            "chat": {"id": 100},
            "from": {"id": 42},
            "audio": {"file_id": "aud123"},
        }
        msg = parse_message(raw)
        assert msg is not None
        assert msg.audio_file_id == "aud123"

    def test_document_message(self):
        raw = {
            "message_id": 6,
            "chat": {"id": 100},
            "from": {"id": 42},
            "document": {"file_id": "doc123"},
            "caption": "report",
        }
        msg = parse_message(raw)
        assert msg is not None
        assert msg.document_file_id == "doc123"
        assert msg.text == "report"

    def test_none_input(self):
        assert parse_message(None) is None

    def test_malformed_input(self):
        assert parse_message({"bad": "data"}) is None

    def test_sender_chat(self):
        raw = {
            "message_id": 7,
            "chat": {"id": 100},
            "sender_chat": {"id": 999},
            "text": "from channel",
        }
        msg = parse_message(raw)
        assert msg is not None
        assert msg.from_user_id == 999

    def test_bot_sender(self):
        raw = {
            "message_id": 8,
            "chat": {"id": 100},
            "from": {"id": 42, "is_bot": True},
            "text": "bot message",
        }
        msg = parse_message(raw)
        assert msg is not None
        assert msg.is_bot is True


class TestParseCallback:
    def test_valid_callback(self):
        raw = {
            "id": "cb1",
            "from": {"id": 42},
            "data": "option_0",
            "message": {"chat": {"id": 100}},
        }
        cb = parse_callback(raw)
        assert cb is not None
        assert cb.id == "cb1"
        assert cb.from_user_id == 42
        assert cb.data == "option_0"
        assert cb.message_chat_id == 100

    def test_no_message(self):
        raw = {"id": "cb2", "from": {"id": 42}, "data": "option_1"}
        cb = parse_callback(raw)
        assert cb is not None
        assert cb.message_chat_id is None

    def test_none_input(self):
        assert parse_callback(None) is None

    def test_malformed_input(self):
        assert parse_callback({"bad": "data"}) is None


class TestParseUpdate:
    def test_message_update(self):
        raw = {
            "update_id": 100,
            "message": {
                "message_id": 1,
                "chat": {"id": 100},
                "from": {"id": 42},
                "text": "hello",
            },
        }
        update = parse_update(raw)
        assert update is not None
        assert update.update_id == 100
        assert update.message is not None
        assert update.callback is None

    def test_callback_update(self):
        raw = {
            "update_id": 101,
            "callback_query": {
                "id": "cb1",
                "from": {"id": 42},
                "data": "option_0",
            },
        }
        update = parse_update(raw)
        assert update is not None
        assert update.update_id == 101
        assert update.message is None
        assert update.callback is not None

    def test_channel_post(self):
        raw = {
            "update_id": 102,
            "channel_post": {
                "message_id": 1,
                "chat": {"id": -100123},
                "text": "channel update",
            },
        }
        update = parse_update(raw)
        assert update is not None
        assert update.message is not None
        assert update.message.chat_id == -100123

    def test_invalid_update_id(self):
        assert parse_update({"no_update_id": True}) is None


class TestClassifyMessage:
    def _msg(self, **kwargs) -> TelegramMessage:
        text = kwargs.pop("text", None)
        return TelegramMessage(
            message_id=1,
            chat_id=100,
            from_user_id=42,
            text=text,
            **kwargs,
        )

    def test_text_only(self):
        assert isinstance(classify_message(self._msg(text="hello")), TextMessage)

    def test_image_only(self):
        assert isinstance(
            classify_message(self._msg(photo_file_id="photo1")), ImageMessage
        )

    def test_text_and_image(self):
        result = classify_message(self._msg(text="caption", photo_file_id="photo1"))
        assert isinstance(result, TextAndImageMessage)

    def test_audio_only(self):
        assert isinstance(
            classify_message(self._msg(audio_file_id="aud1")), AudioMessage
        )

    def test_text_and_audio(self):
        assert isinstance(
            classify_message(self._msg(text="caption", audio_file_id="aud1")),
            TextAndAudioMessage,
        )

    def test_video_only(self):
        assert isinstance(
            classify_message(self._msg(video_file_id="vid1")), VideoMessage
        )

    def test_text_and_video(self):
        assert isinstance(
            classify_message(self._msg(text="caption", video_file_id="vid1")),
            TextAndVideoMessage,
        )

    def test_no_content(self):
        assert classify_message(self._msg()) is None
