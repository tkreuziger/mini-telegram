"""Tests for the user whitelist (ported from telegram-ai-bots)."""

from minitelegram.types import TelegramCallback, TelegramMessage, TelegramUpdate
from minitelegram.whitelist import (
    UserWhitelist,
    add,
    clear,
    filter_update,
    is_active,
    is_allowed,
    remove,
    snapshot,
)


class TestUserWhitelist:
    def test_empty_whitelist_allows_all(self):
        wl = UserWhitelist()
        assert is_active(wl) is False
        assert is_allowed(wl, 42) is True
        assert is_allowed(wl, None) is True

    def test_nonempty_whitelist_restricts(self):
        wl = UserWhitelist(allowed={42, 99})
        assert is_active(wl) is True
        assert is_allowed(wl, 42) is True
        assert is_allowed(wl, 99) is True
        assert is_allowed(wl, 7) is False

    def test_none_user_id_rejected_when_active(self):
        wl = UserWhitelist(allowed={42})
        assert is_allowed(wl, None) is False


class TestWhitelistMutations:
    def test_add(self):
        wl = UserWhitelist()
        add(wl, 42)
        assert 42 in wl.allowed
        assert is_active(wl) is True

    def test_remove(self):
        wl = UserWhitelist(allowed={42, 99})
        remove(wl, 42)
        assert wl.allowed == {99}

    def test_remove_nonexistent(self):
        wl = UserWhitelist(allowed={42})
        remove(wl, 99)
        assert wl.allowed == {42}

    def test_clear(self):
        wl = UserWhitelist(allowed={42, 99, 7})
        clear(wl)
        assert len(wl.allowed) == 0
        assert is_active(wl) is False

    def test_snapshot_is_a_copy(self):
        wl = UserWhitelist(allowed={42, 99})
        snap = snapshot(wl)
        assert snap == {42, 99}
        snap.add(7)
        assert 7 not in wl.allowed


class TestFilterUpdate:
    def _message_update(self, from_user_id):
        return TelegramUpdate(
            update_id=1,
            message=TelegramMessage(
                message_id=1,
                chat_id=100,
                from_user_id=from_user_id,
                text="hello",
            ),
        )

    def _callback_update(self, from_user_id):
        return TelegramUpdate(
            update_id=2,
            callback=TelegramCallback(
                id="cb1", from_user_id=from_user_id, data="x", message_chat_id=100
            ),
        )

    def test_message_from_allowed_user(self):
        assert (
            filter_update(UserWhitelist(allowed={42}), self._message_update(42)) is True
        )

    def test_message_from_disallowed_user(self):
        assert (
            filter_update(UserWhitelist(allowed={42}), self._message_update(99))
            is False
        )

    def test_callback_from_allowed_user(self):
        assert (
            filter_update(UserWhitelist(allowed={42}), self._callback_update(42))
            is True
        )

    def test_callback_from_disallowed_user(self):
        assert (
            filter_update(UserWhitelist(allowed={42}), self._callback_update(99))
            is False
        )

    def test_empty_whitelist_allows_all(self):
        assert filter_update(UserWhitelist(), self._message_update(999)) is True

    def test_update_with_no_content(self):
        wl = UserWhitelist(allowed={42})
        update = TelegramUpdate(update_id=1, message=None, callback=None)
        assert filter_update(wl, update) is True
