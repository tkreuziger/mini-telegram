"""Tests for CallbackManager."""

import json

from minitelegram.callbacks import CallbackManager, PendingCallback


class TestCallbackManager:
    def test_create_and_make_callback_data(self, tmp_path):
        mgr = CallbackManager(persist_dir=tmp_path)
        cb_id = mgr.create(chat_id=123, question="Pick", options=["A", "B"])
        assert len(cb_id) == 8
        assert mgr.make_callback_data(cb_id, 0) == f"{cb_id}:0"

    def test_roundtrip_parse(self):
        cb_id, index = CallbackManager.parse_callback_data("abc12345:2")
        assert (cb_id, index) == ("abc12345", 2)

    def test_parse_invalid(self):
        assert CallbackManager.parse_callback_data("no-separator") is None
        assert CallbackManager.parse_callback_data("abc:notanumber") is None

    def test_resolve_returns_option(self, tmp_path):
        mgr = CallbackManager(persist_dir=tmp_path)
        cb_id = mgr.create(chat_id=123, question="Pick", options=["A", "B"])
        resolved = mgr.resolve(cb_id, 1)
        assert resolved is not None
        pending, option = resolved
        assert isinstance(pending, PendingCallback)
        assert pending.chat_id == 123
        assert pending.question == "Pick"
        assert option == "B"

    def test_resolve_is_consuming(self, tmp_path):
        mgr = CallbackManager(persist_dir=tmp_path)
        cb_id = mgr.create(chat_id=123, question="Pick", options=["A"])
        assert mgr.resolve(cb_id, 0) is not None
        assert mgr.resolve(cb_id, 0) is None

    def test_resolve_unknown_id(self, tmp_path):
        mgr = CallbackManager(persist_dir=tmp_path)
        assert mgr.resolve("deadbeef", 0) is None

    def test_resolve_out_of_range(self, tmp_path):
        mgr = CallbackManager(persist_dir=tmp_path)
        cb_id = mgr.create(chat_id=123, question="Pick", options=["A"])
        assert mgr.resolve(cb_id, 5) is None
        # Invalid press should not consume the pending entry.
        assert mgr.peek(cb_id) is not None

    def test_empty_options_raise(self, tmp_path):
        mgr = CallbackManager(persist_dir=tmp_path)
        import pytest

        with pytest.raises(ValueError):
            mgr.create(chat_id=1, question="q", options=[])

    def test_persistence_across_instances(self, tmp_path):
        mgr1 = CallbackManager(persist_dir=tmp_path)
        cb_id = mgr1.create(chat_id=123, question="Survive?", options=["Yes", "No"])
        mgr2 = CallbackManager(persist_dir=tmp_path)
        pending = mgr2.peek(cb_id)
        assert pending is not None
        assert pending.question == "Survive?"

    def test_in_memory_when_no_persist_dir(self):
        mgr = CallbackManager()
        cb_id = mgr.create(chat_id=1, question="q", options=["A"])
        assert mgr.peek(cb_id) is not None

    def test_expiry(self, tmp_path):
        mgr = CallbackManager(persist_dir=tmp_path, ttl_seconds=0.01)
        cb_id = mgr.create(chat_id=123, question="Expires?", options=["A"])
        import time

        time.sleep(0.02)
        mgr.create(chat_id=456, question="Trigger cleanup", options=["B"])
        assert mgr.peek(cb_id) is None
        # The persisted file must stay valid JSON after cleanup.
        path = tmp_path / "pending_callbacks.json"
        data = json.loads(path.read_text())
        assert cb_id not in data
