"""Tests for polling (get_updates)."""

from minitelegram.polling import get_updates


def _update_payload(update_id, text=None, callback_data=None) -> dict:
    update: dict = {"update_id": update_id}
    if text is not None:
        update["message"] = {
            "message_id": update_id,
            "chat": {"id": 100},
            "from": {"id": 42},
            "text": text,
        }
    if callback_data is not None:
        update["callback_query"] = {
            "id": f"cb{update_id}",
            "from": {"id": 42},
            "data": callback_data,
            "message": {"chat": {"id": 100}},
        }
    return update


def test_returns_parsed_updates(fake_session):
    fake_session.responses = [
        {
            "ok": True,
            "result": [
                _update_payload(1, text="hello"),
                _update_payload(2, callback_data="x"),
            ],
        }
    ]
    updates = get_updates(fake_session, "TOKEN")
    assert [u.update_id for u in updates] == [1, 2]
    assert updates[0].message is not None and updates[0].message.text == "hello"
    assert updates[1].callback is not None and updates[1].callback.data == "x"
    assert updates[1].message is None


def test_passes_offset_and_params(fake_session):
    fake_session.responses = [{"ok": True, "result": []}]
    get_updates(
        fake_session,
        "TOKEN",
        offset=7,
        timeout=(5, 15),
        allowed_updates=["message", "callback_query"],
        limit=50,
    )
    req = fake_session.requests[-1]
    assert req.method == "GET"
    assert req.url.endswith("/botTOKEN/getUpdates")
    assert req.params["offset"] == 7
    assert req.params["timeout"] == 15
    assert req.params["limit"] == 50
    assert req.params["allowed_updates"] == '["message", "callback_query"]'


def test_default_long_poll_timeout(fake_session):
    fake_session.responses = [{"ok": True, "result": []}]
    get_updates(fake_session, "TOKEN")
    req = fake_session.requests[-1]
    assert req.params["timeout"] == 30
    assert req.timeout == (5, 40)


def test_empty_result(fake_session):
    fake_session.responses = [{"ok": True, "result": []}]
    assert get_updates(fake_session, "TOKEN") == []


def test_api_error_returns_empty_list(fake_session):
    fake_session.responses = [
        {"ok": False, "error_code": 409, "description": "conflict"}
    ]
    assert get_updates(fake_session, "TOKEN") == []


def test_skips_malformed_updates(fake_session):
    fake_session.responses = [{"ok": True, "result": [{"no_update_id": True}]}]
    assert get_updates(fake_session, "TOKEN") == []
