"""G8.06.T2 — testes dumps criptografados + restore route.

Modified by Gustavo Almeida — Wave 39.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.encrypted_dump import (
    build_encrypted_backup_manifest,
    decrypt_dump_bytes,
    encrypt_dump_bytes,
    key_fingerprint,
    verify_restore_route,
)


def test_roundtrip_encrypt_decrypt() -> None:
    plain = b"-- postgres dump fixture\nSELECT 1;\n"
    enc = encrypt_dump_bytes(plain)
    assert enc.ciphertext_b64
    assert enc.key_fingerprint.startswith("fp:")
    back = decrypt_dump_bytes(enc)
    assert back == plain
    assert enc.sha256_plain


def test_empty_raises() -> None:
    with pytest.raises(ValueError):
        encrypt_dump_bytes(b"")


def test_fingerprint_stable() -> None:
    a = key_fingerprint()
    b = key_fingerprint()
    assert a == b


def test_manifest() -> None:
    enc = encrypt_dump_bytes(b"data")
    m = build_encrypted_backup_manifest(enc)
    assert m["algo"]
    assert "sha256_plain" in m


def test_restore_route_not_ready_without_file(tmp_path: Path) -> None:
    report = verify_restore_route(dump_path=tmp_path / "missing.dump", decrypt_ok=True)
    assert report.ready is False


def test_restore_route_ready(tmp_path: Path) -> None:
    p = tmp_path / "dump.enc"
    p.write_bytes(b"x")
    report = verify_restore_route(
        dump_path=p, decrypt_ok=True, target_db_private=True, dry_run=True
    )
    assert report.ready is True
    assert report.to_dict()["ready"] is True


def test_restore_rejects_public_target(tmp_path: Path) -> None:
    p = tmp_path / "d.enc"
    p.write_bytes(b"1")
    report = verify_restore_route(dump_path=p, decrypt_ok=True, target_db_private=False)
    assert report.ready is False
