"""G8.06.T2 — Dumps criptografados (envelope local) + rota de restore dry-run.

Não executa pg_dump real. Oferece:
- encrypt_dump_bytes / decrypt_dump_bytes (Fernet se disponível, senão XOR+HMAC demo)
- verify_restore_route(plan) checklist seguro
- build_encrypted_backup_manifest

LGPD: payloads de dump tratados como sensíveis; chave via env BACKUP_FERNET_KEY
ou pepper de teste (nunca commitar chave real).

Modified by Gustavo Almeida — Wave 39.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class EncryptedDumpResult:
    ciphertext_b64: str
    key_fingerprint: str
    algo: str
    sha256_plain: str
    created_at: str


@dataclass(slots=True)
class RestoreRouteCheck:
    name: str
    ok: bool
    detail: str


@dataclass(slots=True)
class RestoreRouteReport:
    ready: bool
    checks: list[RestoreRouteCheck] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "checks": [asdict(c) for c in self.checks],
        }


def _key_material() -> bytes:
    raw = (
        os.environ.get("BACKUP_FERNET_KEY")
        or os.environ.get("AUDIT_HMAC_KEY")
        or "dev-backup-pepper-not-prod"
    )
    return hashlib.sha256(str(raw).encode("utf-8")).digest()


def key_fingerprint(key: bytes | None = None) -> str:
    k = key or _key_material()
    return "fp:" + hashlib.sha256(k).hexdigest()[:16]


def encrypt_dump_bytes(plaintext: bytes) -> EncryptedDumpResult:
    """Criptografa bytes do dump. Prefer Fernet; fallback XOR+HMAC."""
    if not plaintext:
        raise ValueError("plaintext required")
    key = _key_material()
    digest = hashlib.sha256(plaintext).hexdigest()
    now = datetime.now(timezone.utc).isoformat()
    try:
        from cryptography.fernet import Fernet

        fkey = base64.urlsafe_b64encode(key)
        token = Fernet(fkey).encrypt(plaintext)
        return EncryptedDumpResult(
            ciphertext_b64=base64.b64encode(token).decode("ascii"),
            key_fingerprint=key_fingerprint(key),
            algo="fernet",
            sha256_plain=digest,
            created_at=now,
        )
    except Exception:  # noqa: BLE001 — fallback sem cryptography
        # demo envelope: HMAC tag + XOR stream (não usar em prod sem Fernet)
        stream = hashlib.sha256(key + b"stream").digest()
        out = bytes(b ^ stream[i % len(stream)] for i, b in enumerate(plaintext))
        tag = hmac.new(key, out, hashlib.sha256).digest()
        blob = tag + out
        return EncryptedDumpResult(
            ciphertext_b64=base64.b64encode(blob).decode("ascii"),
            key_fingerprint=key_fingerprint(key),
            algo="hmac-xor-demo",
            sha256_plain=digest,
            created_at=now,
        )


def decrypt_dump_bytes(result: EncryptedDumpResult) -> bytes:
    key = _key_material()
    raw = base64.b64decode(result.ciphertext_b64.encode("ascii"))
    if result.algo == "fernet":
        from cryptography.fernet import Fernet

        fkey = base64.urlsafe_b64encode(key)
        return Fernet(fkey).decrypt(raw)
    if result.algo == "hmac-xor-demo":
        tag, body = raw[:32], raw[32:]
        expect = hmac.new(key, body, hashlib.sha256).digest()
        if not hmac.compare_digest(tag, expect):
            raise ValueError("integrity check failed")
        stream = hashlib.sha256(key + b"stream").digest()
        return bytes(b ^ stream[i % len(stream)] for i, b in enumerate(body))
    raise ValueError(f"unknown algo: {result.algo}")


def verify_restore_route(
    *,
    dump_path: Path | None = None,
    decrypt_ok: bool = False,
    target_db_private: bool = True,
    dry_run: bool = True,
) -> RestoreRouteReport:
    """Checklist de rota de restore segura (não restaura de verdade)."""
    checks: list[RestoreRouteCheck] = []
    if dump_path is None:
        checks.append(RestoreRouteCheck("dump_present", False, "path missing"))
    else:
        checks.append(
            RestoreRouteCheck(
                "dump_present",
                dump_path.exists(),
                str(dump_path) if dump_path.exists() else "file not found",
            )
        )
    checks.append(
        RestoreRouteCheck(
            "decrypt_verified", decrypt_ok, "decrypt roundtrip" if decrypt_ok else "not verified"
        )
    )
    checks.append(
        RestoreRouteCheck(
            "private_network_only",
            target_db_private,
            "Tailscale/private target" if target_db_private else "public target forbidden",
        )
    )
    checks.append(RestoreRouteCheck("dry_run", dry_run, "must dry-run first"))
    ready = all(c.ok for c in checks)
    return RestoreRouteReport(ready=ready, checks=checks)


def build_encrypted_backup_manifest(
    result: EncryptedDumpResult, source: str = "postgres"
) -> dict[str, Any]:
    return {
        "source": source,
        "algo": result.algo,
        "key_fingerprint": result.key_fingerprint,
        "sha256_plain": result.sha256_plain,
        "created_at": result.created_at,
        "ciphertext_bytes_b64_len": len(result.ciphertext_b64),
        "note": "ciphertext stored separately; never log raw dump",
    }


__all__ = [
    "EncryptedDumpResult",
    "RestoreRouteCheck",
    "RestoreRouteReport",
    "build_encrypted_backup_manifest",
    "decrypt_dump_bytes",
    "encrypt_dump_bytes",
    "key_fingerprint",
    "verify_restore_route",
]
