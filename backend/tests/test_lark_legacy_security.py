"""Regression coverage for legacy Lark ingress paths kept outside the live router."""

from __future__ import annotations

import hashlib
import hmac
import importlib.util
import io
import json
import os
import sys
import time
import uuid
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from types import ModuleType

import pytest


ROOT = Path(__file__).resolve().parents[2]
LEGACY_SCRIPT = ROOT / "scripts" / "lark_bot_v6.py"


class _Response:
    def __init__(self, content_type: str, chunks: list[bytes]) -> None:
        self.status_code = 200
        self.headers = {"Content-Type": content_type}
        self._chunks = chunks

    def iter_content(self, chunk_size: int) -> Iterator[bytes]:
        del chunk_size
        yield from self._chunks


def _signed_callback_request(module: ModuleType, body: dict, nonce: str = "n" * 16) -> SimpleNamespace:
    raw = json.dumps(body, separators=(",", ":")).encode("utf-8")
    timestamp = str(int(time.time()))
    signature = hmac.new(
        module.WEBHOOK_SIGNING_SECRET.encode("utf-8"),
        f"{timestamp}{nonce}{raw.decode('utf-8')}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return SimpleNamespace(
        get_data=lambda cache: raw,
        headers={
            "X-Lark-Timestamp": timestamp,
            "X-Lark-Nonce": nonce,
            "X-Lark-Signature": signature,
        },
    )


@pytest.fixture
def legacy_lark_bot(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[ModuleType]:
    """Load the standalone legacy script with an isolated inbox and no secrets."""
    monkeypatch.setenv("LARK_INBOX_DIR", str(tmp_path / "inbox"))
    monkeypatch.setenv("LARK_DB_PATH", str(tmp_path / "legacy.sqlite"))
    monkeypatch.setenv("LARK_ENABLE_LOCAL_OCR_TEST", "false")
    monkeypatch.delenv("LARK_LOCAL_OCR_TEST_TOKEN", raising=False)
    monkeypatch.setenv("LARK_APP_ID", "test-app")
    monkeypatch.setenv("LARK_APP_SECRET", "test-app-secret")
    monkeypatch.setenv("LARK_VERIFICATION_TOKEN", "test-verification-token")
    monkeypatch.setenv("LARK_WEBHOOK_SIGNING_SECRET", "test-webhook-signing-secret")
    flask_stub = ModuleType("flask")

    class _Flask:
        def __init__(self, name: str) -> None:
            self.name = name

        def route(self, *args: object, **kwargs: object):
            del args, kwargs
            return lambda function: function

    flask_stub.Flask = _Flask
    flask_stub.request = SimpleNamespace()
    flask_stub.jsonify = lambda value: value
    monkeypatch.setitem(sys.modules, "flask", flask_stub)
    module_name = f"lark_bot_v6_test_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, LEGACY_SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    try:
        yield module
    finally:
        sys.modules.pop(module_name, None)


def test_download_uses_internal_name_not_remote_filename(
    legacy_lark_bot: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A Lark filename cannot select the local destination path."""
    module = legacy_lark_bot
    response = _Response("application/pdf", [b"%PDF-1.7 test"])
    monkeypatch.setattr(module, "get_token", lambda: "test-token")
    monkeypatch.setattr(module.requests, "get", lambda *args, **kwargs: response)

    result = module.download_resource("file", "valid_file_key")

    assert result is not None
    destination = Path(result)
    assert destination.parent == module.INBOX_DIR.resolve()
    assert destination.suffix == ".pdf"
    assert "outside" not in destination.name
    assert destination.read_bytes() == b"%PDF-1.7 test"
    assert not (module.INBOX_DIR.parent / "outside.pdf").exists()


def test_download_rejects_disallowed_mime_before_writing(
    legacy_lark_bot: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = legacy_lark_bot
    response = _Response("application/octet-stream", [b"untrusted"])
    monkeypatch.setattr(module, "get_token", lambda: "test-token")
    monkeypatch.setattr(module.requests, "get", lambda *args, **kwargs: response)

    assert module.download_resource("file", "valid_file_key") is None
    assert list(module.INBOX_DIR.iterdir()) == []


def test_download_removes_partial_file_when_stream_exceeds_limit(
    legacy_lark_bot: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = legacy_lark_bot
    module.MAX_ATTACHMENT_BYTES = 4
    response = _Response("text/plain", [b"safe", b"oversize"])
    monkeypatch.setattr(module, "get_token", lambda: "test-token")
    monkeypatch.setattr(module.requests, "get", lambda *args, **kwargs: response)

    assert module.download_resource("file", "valid_file_key") is None
    assert list(module.INBOX_DIR.iterdir()) == []


@pytest.mark.parametrize("media_key", ["../../outside", "/absolute", "key/child", "key\u2215child"])
def test_download_rejects_path_like_or_unicode_resource_keys(
    legacy_lark_bot: ModuleType, monkeypatch: pytest.MonkeyPatch, media_key: str
) -> None:
    module = legacy_lark_bot
    monkeypatch.setattr(module, "get_token", lambda: "test-token")
    request_called = False

    def fake_get(*args: object, **kwargs: object) -> _Response:
        nonlocal request_called
        del args, kwargs
        request_called = True
        return _Response("text/plain", [b"safe"])

    monkeypatch.setattr(module.requests, "get", fake_get)
    assert module.download_resource("file", media_key) is None
    assert not request_called
    assert list(module.INBOX_DIR.iterdir()) == []


def test_download_rejects_mime_spoof_before_persisting(
    legacy_lark_bot: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = legacy_lark_bot
    response = _Response("image/png", [b"%PDF-1.7 spoof"])
    monkeypatch.setattr(module, "get_token", lambda: "test-token")
    monkeypatch.setattr(module.requests, "get", lambda *args, **kwargs: response)

    assert module.download_resource("image", "valid_image_key") is None
    assert list(module.INBOX_DIR.iterdir()) == []


def test_download_rejects_symlinked_inbox(legacy_lark_bot: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    module = legacy_lark_bot
    target = tmp_path / "target"
    target.mkdir()
    symlink = tmp_path / "symlinked-inbox"
    symlink.symlink_to(target, target_is_directory=True)
    module.INBOX_DIR = symlink
    response = _Response("text/plain", [b"safe"])
    monkeypatch.setattr(module, "get_token", lambda: "test-token")
    monkeypatch.setattr(module.requests, "get", lambda *args, **kwargs: response)

    assert module.download_resource("file", "valid_file_key") is None
    assert list(target.iterdir()) == []


def test_download_rejects_parent_swap_to_symlink(
    legacy_lark_bot: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module = legacy_lark_bot
    target = tmp_path / "replacement-target"
    target.mkdir()

    def swap_inbox() -> None:
        module.INBOX_DIR.rmdir()
        module.INBOX_DIR.symlink_to(target, target_is_directory=True)

    response = _Response("text/plain", [b"safe"])
    monkeypatch.setattr(module, "_purge_expired_attachments", swap_inbox)
    monkeypatch.setattr(module, "get_token", lambda: "test-token")
    monkeypatch.setattr(module.requests, "get", lambda *args, **kwargs: response)

    assert module.download_resource("file", "valid_file_key") is None
    assert list(target.iterdir()) == []


def test_download_does_not_overwrite_preexisting_hardlink(
    legacy_lark_bot: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = legacy_lark_bot
    protected = module.INBOX_DIR / "protected.txt"
    protected.write_bytes(b"protected")
    os.link(protected, module.INBOX_DIR / "fixed.txt")
    response = _Response("text/plain", [b"safe"])
    monkeypatch.setattr(module, "_new_attachment_name", lambda *args: "fixed.txt")
    monkeypatch.setattr(module, "get_token", lambda: "test-token")
    monkeypatch.setattr(module.requests, "get", lambda *args, **kwargs: response)

    assert module.download_resource("file", "valid_file_key") is None
    assert protected.read_bytes() == b"protected"


def test_text_attachment_content_is_scrubbed_before_description(legacy_lark_bot: ModuleType) -> None:
    attachment = legacy_lark_bot.INBOX_DIR / "internal.txt"
    attachment.write_text("CPF 123.456.789-00", encoding="utf-8")

    description = legacy_lark_bot.describe_file(attachment)

    assert "123.456.789-00" not in description
    assert "[CPF]" in description


def test_local_ocr_endpoint_is_disabled_by_default(legacy_lark_bot: ModuleType) -> None:
    legacy_lark_bot.request = SimpleNamespace(
        remote_addr="127.0.0.1",
        headers={},
        files={"file": SimpleNamespace(content_type="image/png", stream=io.BytesIO(b"not-an-image"))},
    )
    _, status_code = legacy_lark_bot.test_image()

    assert status_code == 404
    assert list(legacy_lark_bot.INBOX_DIR.iterdir()) == []


def test_local_ocr_endpoint_never_echoes_path_or_ocr(legacy_lark_bot: ModuleType) -> None:
    module = legacy_lark_bot
    module.LOCAL_OCR_TEST_ENABLED = True
    module.LOCAL_OCR_TEST_TOKEN = "local-test-token"
    module.OCR_ENABLED = False
    module._validate_attachment_payload = lambda *args: True

    module.request = SimpleNamespace(
        remote_addr="127.0.0.1",
        headers={"X-Lark-Local-OCR-Test-Token": "local-test-token"},
        files={"file": SimpleNamespace(content_type="image/png", stream=io.BytesIO(b"image-data"))},
    )
    payload = module.test_image()

    assert payload == {"ocr_attempted": False, "size_kb": 0, "status": "accepted"}
    assert "cpf" not in str(payload).lower()
    assert len(list(module.INBOX_DIR.iterdir())) == 1


def test_webhook_requires_signature_freshness_and_one_time_nonce(legacy_lark_bot: ModuleType) -> None:
    module = legacy_lark_bot
    body = {
        "type": "url_verification",
        "token": "test-verification-token",
        "challenge": "strict-challenge",
    }
    module.request = _signed_callback_request(module, body)
    assert module.webhook() == {"challenge": "strict-challenge"}

    module.request = _signed_callback_request(module, body)
    _, replay_status = module.webhook()
    assert replay_status == 409

    module.request = SimpleNamespace(
        get_data=lambda cache: json.dumps(body).encode("utf-8"),
        headers={"X-Lark-Timestamp": "1", "X-Lark-Nonce": "x" * 16, "X-Lark-Signature": "bad"},
    )
    _, stale_status = module.webhook()
    assert stale_status == 401


def test_webhook_rejects_missing_event_id_after_authentication(legacy_lark_bot: ModuleType) -> None:
    module = legacy_lark_bot
    body = {"token": "test-verification-token", "header": {}, "event": {}}
    module.request = _signed_callback_request(module, body, nonce="z" * 16)

    _, status_code = module.webhook()
    assert status_code == 400


def test_fastapi_lark_signature_and_token_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.api.v1 import lark

    payload = b'{"token":"event-token"}'
    monkeypatch.setattr(lark, "LARK_ENCRYPT_KEY", None)
    monkeypatch.setattr(lark, "LARK_VERIFICATION_TOKEN", None)
    assert not lark._lark_webhook_configuration_ready()
    assert not lark._verify_lark_signature(payload, "signature", "1", "nonce")

    monkeypatch.setattr(lark, "LARK_ENCRYPT_KEY", "encryption-key")
    monkeypatch.setattr(lark, "LARK_VERIFICATION_TOKEN", "event-token")
    signature = hmac.new(
        b"encryption-key", b'1nonce{"token":"event-token"}', hashlib.sha256
    ).hexdigest()
    assert lark._lark_webhook_configuration_ready()
    assert lark._verify_lark_signature(payload, signature, "1", "nonce")
    assert not lark._verify_lark_signature(payload, signature, None, "nonce")
    assert lark._verify_lark_event_token({"token": "event-token"})
    assert not lark._verify_lark_event_token({"token": "wrong-token"})
