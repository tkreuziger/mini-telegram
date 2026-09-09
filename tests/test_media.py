"""Tests for media resolution and downloading."""

from pathlib import Path

from minitelegram.media import (
    download_by_file_id,
    download_file,
    get_file,
    get_file_path,
)


class StreamingResponse:
    """Context-manager response that yields chunks of bytes."""

    def __init__(self, chunks: list[bytes]) -> None:
        self.chunks = chunks
        self.status_code = 200
        self.url = "http://file"

    def __enter__(self) -> "StreamingResponse":
        return self

    def __exit__(self, *exc) -> None:
        return None

    def raise_for_status(self) -> None:
        pass

    def iter_content(self, chunk_size: int = 8192):
        yield from self.chunks


class _Session:
    """Scripted session: getFile JSON calls plus one streaming download."""

    def __init__(
        self, get_file_payload: dict, download_chunks: list[bytes] | None = None
    ):
        self.get_file_payload = get_file_payload
        self.download_chunks = download_chunks or []
        self.download_url = None

    def get(self, url, *, params=None, timeout=None, stream=False):
        if stream:
            self.download_url = url
            return StreamingResponse(self.download_chunks)
        return _JsonResponse(self.get_file_payload)


class _JsonResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload
        self.status_code = 200 if payload.get("ok") else 400

    def json(self) -> dict:
        return self._payload


def _file_payload(file_id="FILE1", path="docs/report.pdf") -> dict:
    return {
        "ok": True,
        "result": {
            "file_id": file_id,
            "file_unique_id": "UNIQ1",
            "file_size": 1234,
            "file_path": path,
        },
    }


def test_get_file_parses_result():
    session = _Session(get_file_payload=_file_payload())
    info = get_file(session, "TOKEN", file_id="FILE1")
    assert info is not None
    assert info.file_id == "FILE1"
    assert info.file_path == "docs/report.pdf"
    assert info.file_size == 1234


def test_get_file_path_returns_path():
    session = _Session(get_file_payload=_file_payload())
    assert get_file_path(session, "TOKEN", file_id="FILE1") == "docs/report.pdf"


def test_get_file_path_none_on_error():
    session = _Session(
        get_file_payload={"ok": False, "error_code": 400, "description": "bad"}
    )
    assert get_file_path(session, "TOKEN", file_id="FILE1") is None


def test_download_file_writes_bytes(tmp_path: Path):
    session = _Session(
        get_file_payload=_file_payload(),
        download_chunks=[b"part1-", b"part2"],
    )
    target = tmp_path / "out.pdf"
    assert (
        download_file(session, "TOKEN", file_path="docs/report.pdf", target_path=target)
        is True
    )
    assert target.read_bytes() == b"part1-part2"
    assert session.download_url.endswith("/file/botTOKEN/docs/report.pdf")


def test_download_by_file_id(tmp_path: Path):
    session = _Session(
        get_file_payload=_file_payload(),
        download_chunks=[b"data"],
    )
    target = tmp_path / "out.pdf"
    assert (
        download_by_file_id(session, "TOKEN", file_id="FILE1", target_path=target)
        is True
    )
    assert target.read_bytes() == b"data"
