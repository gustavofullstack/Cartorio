"""G8.23.T3 — Envelope encryption (DEK wrapped by KEK) para PII at-rest.

LGPD Art. 46 — Medidas técnicas adequadas para proteção de dados pessoais
contra acesso não autorizado. Padrão de mercado: cada registro PII tem sua
própria DEK (Data Encryption Key, AES-256 random) criptografada por uma
KEK (Key Encryption Key) carregada de variável de ambiente (HSM-style).

Por que envelope (e não Fernet/PGP direto)?
    - **Rotação de chaves barata**: para girar a KEK, basta re-envelopar
      cada DEK armazenada (não precisa ler+re-cifrar toda a coluna PII).
    - **Granularidade**: cada registro tem DEK única. Vazamento de uma
      DEK não compromete os outros registros.
    - **Auditoria**: `kek_id` registrado na coluna `_kek_id` permite
      rastrear qual KEK protege cada envelope.
    - **Defesa em profundidade**: combina com `crypto.encrypt_pii` (Fernet)
      já existente e com `pgcrypto` (D15) em camadas diferentes.

Envelope binary layout (versão 1):
    [version:1] [kek_id_len:1] [kek_id:N] [dek_nonce:12] [enc_dek:60]
    [data_nonce:12] [ciphertext+tag:variável] [aad_ctx_hash:32 opcional]

- DEK gerada a cada `encrypt()` (AES-256 random 32 bytes via `os.urandom`).
- Algoritmo: **AES-256-GCM** (authenticated encryption + 16-byte tag).
- AAD (Additional Authenticated Data) opcional via `context` dict —
  protege contra ataques de "swap" entre registros.
- KEK cacheada em memória (não re-lê env a cada `encrypt()`).
- `kek_id` registrado nos metadados (coluna `<field>_kek_id`) para
  suportar rotação de chaves sem re-encrypt all.

**LGPD-REVIEW-PENDING** antes de aplicar em produção.

References:
- LGPD Art. 46 — Medidas de segurança técnicas adequadas.
- NIST SP 800-57 — Key management (envelope encryption).
- RFC 5116 — AEAD (AES-256-GCM).
- docs/ENVELOPE_ENCRYPTION_G8.md — operational guide.
"""

from __future__ import annotations

import hashlib
import logging
import os
import secrets
import struct
from dataclasses import dataclass, field
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

ENVELOPE_VERSION: int = 1
DEK_LEN_BYTES: int = 32  # AES-256
NONCE_LEN_BYTES: int = 12  # GCM standard
GCM_TAG_LEN_BYTES: int = 16  # GCM auth tag (AESGCM appends automatically)
KEK_LEN_BYTES: int = 32  # AES-256 KEK
MAX_KEK_ID_LEN: int = 64  # fits in 1 byte (u8)

_ENV_KEK_ID = "KMS_KEK_ID"
_ENV_KEK_B64 = "KMS_KEK_B64"  # base64-encoded 32-byte KEK
_ENV_KEK_DEV = "KMS_KEK_DEV_FALLBACK"  # dev-only toggle (set false in prod)


# =============================================================================
# Exceptions
# =============================================================================


class EnvelopeError(Exception):
    """Base error for envelope encryption layer."""


class KekUnavailableError(EnvelopeError):
    """KEK could not be loaded (missing env var or invalid base64)."""


class EnvelopeDecodeError(EnvelopeError):
    """Envelope binary is malformed or unsupported version."""


class EnvelopeAuthError(EnvelopeError):
    """Authentication failed (wrong KEK, tampered ciphertext, or AAD mismatch)."""


# =============================================================================
# KEK source (env-only, no DB fallback)
# =============================================================================


def _load_kek_from_env() -> tuple[str, bytes]:
    """Load KEK from environment.

    Returns:
        Tuple `(kek_id, kek_bytes)` where `kek_bytes` is exactly 32 bytes.

    Raises:
        KekUnavailableError: if `KMS_KEK_B64` is missing/invalid or if
            `KMS_KEK_DEV_FALLBACK` is not enabled and the env var is missing.
    """
    import base64

    kek_id = os.getenv(_ENV_KEK_ID, "kek-dev-001")
    kek_b64 = os.getenv(_ENV_KEK_B64)
    allow_dev = os.getenv(_ENV_KEK_DEV, "true").lower() in ("1", "true", "yes")

    if kek_b64:
        try:
            kek_bytes = base64.b64decode(kek_b64, validate=True)
        except (ValueError, TypeError) as exc:
            raise KekUnavailableError(
                f"{_ENV_KEK_B64} is not valid base64: {exc}"
            ) from exc
    elif allow_dev:
        # DEV-ONLY deterministic fallback so tests/CI work without KMS.
        # Production MUST set KMS_KEK_B64 (see KekUnavailableError when allow_dev=False).
        logger.warning(
            "ENVELOPE KEK USING DEV FALLBACK — set KMS_KEK_B64 + KMS_KEK_DEV_FALLBACK=false in prod"
        )
        kek_bytes = hashlib.sha256(b"cartorio-dev-kek-do-not-use-in-prod").digest()
    else:
        raise KekUnavailableError(
            f"{_ENV_KEK_B64} is required (KMS_KEK_DEV_FALLBACK=false)"
        )

    if len(kek_bytes) != KEK_LEN_BYTES:
        raise KekUnavailableError(
            f"KEK must be exactly {KEK_LEN_BYTES} bytes, got {len(kek_bytes)}"
        )
    if len(kek_id) > MAX_KEK_ID_LEN:
        raise KekUnavailableError(
            f"kek_id too long: {len(kek_id)} > {MAX_KEK_ID_LEN}"
        )
    return kek_id, kek_bytes


# =============================================================================
# Envelope metadata
# =============================================================================


@dataclass(frozen=True)
class EnvelopeMeta:
    """Decoded envelope metadata (after successful decrypt)."""

    version: int
    kek_id: str
    aad_ctx_hash: bytes | None = field(default=None)


# =============================================================================
# EnvelopeEncryption
# =============================================================================


class EnvelopeEncryption:
    """Envelope encryption primitive.

    Each `encrypt()` call generates a fresh DEK (AES-256 random), encrypts
    the plaintext with that DEK using AES-GCM, then wraps the DEK with the
    loaded KEK. The returned envelope is a single binary blob safe to
    store in a `LargeBinary` column.
    """

    def __init__(self, kek_id: str | None = None, kek_bytes: bytes | None = None) -> None:
        """Initialize envelope cipher.

        Args:
            kek_id: Override KEK identifier (default: load from env).
            kek_bytes: Override KEK material (default: load from env).
                Must be exactly 32 bytes (AES-256).
        """
        if kek_id is not None and kek_bytes is not None:
            if len(kek_bytes) != KEK_LEN_BYTES:
                raise KekUnavailableError(
                    f"KEK must be exactly {KEK_LEN_BYTES} bytes, got {len(kek_bytes)}"
                )
            if len(kek_id) > MAX_KEK_ID_LEN:
                raise KekUnavailableError(
                    f"kek_id too long: {len(kek_id)} > {MAX_KEK_ID_LEN}"
                )
            self._kek_id = kek_id
            self._kek_bytes = kek_bytes
        else:
            self._kek_id, self._kek_bytes = _load_kek_from_env()

        # Cache AESGCM(KEK) for wrap/unwrap (avoids recreating cipher per call).
        self._kek_cipher = AESGCM(self._kek_bytes)

    @property
    def kek_id(self) -> str:
        """Return the active KEK identifier (for column <field>_kek_id)."""
        return self._kek_id

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------

    def encrypt(
        self,
        plaintext: bytes,
        context: dict[str, Any] | None = None,
    ) -> bytes:
        """Encrypt plaintext into a binary envelope.

        Args:
            plaintext: Raw bytes to encrypt (e.g. CPF encoded as utf-8).
            context: Optional dict of contextual fields (e.g. `{"cliente_id": 42,
                "field": "cpf"}`) bound to the ciphertext as AAD. Protects
                against swap attacks between records.

        Returns:
            Envelope bytes, safe to store in a `LargeBinary` column.
        """
        if plaintext is None:
            raise EnvelopeError("plaintext must not be None")

        # 1. Generate DEK (fresh random AES-256 key per record).
        dek = secrets.token_bytes(DEK_LEN_BYTES)

        # 2. Encrypt data with DEK (AES-256-GCM, random nonce per record).
        data_nonce = secrets.token_bytes(NONCE_LEN_BYTES)
        dek_cipher = AESGCM(dek)
        aad = _encode_aad(context)
        ciphertext = dek_cipher.encrypt(data_nonce, plaintext, aad)

        # 3. Wrap DEK with KEK (AES-256-GCM).
        kek_nonce = secrets.token_bytes(NONCE_LEN_BYTES)
        kek_aad = self._kek_id.encode("ascii")
        enc_dek = self._kek_cipher.encrypt(kek_nonce, dek, kek_aad)

        # 4. Serialize envelope (versioned binary).
        kek_id_bytes = self._kek_id.encode("ascii")
        aad_hash = _hash_aad(context) if context is not None else b""
        return (
            struct.pack("!BB", ENVELOPE_VERSION, len(kek_id_bytes))
            + kek_id_bytes
            + kek_nonce
            + enc_dek
            + data_nonce
            + ciphertext
            + aad_hash
        )

    def decrypt(
        self,
        envelope: bytes,
        context: dict[str, Any] | None = None,
    ) -> bytes:
        """Decrypt envelope back to plaintext bytes.

        Args:
            envelope: Binary envelope produced by `encrypt()`.
            context: Same dict passed to `encrypt()`. Required if
                `encrypt()` was called with a context (the AAD hash is
                part of the envelope and is verified before decryption).

        Returns:
            Original plaintext bytes.

        Raises:
            EnvelopeDecodeError: Malformed envelope or unsupported version.
            EnvelopeAuthError: Wrong KEK, tampered ciphertext, or AAD mismatch.
        """
        if envelope is None or len(envelope) < 4:
            raise EnvelopeDecodeError("envelope too short")

        version, kek_id_len = struct.unpack("!BB", envelope[:2])
        if version != ENVELOPE_VERSION:
            raise EnvelopeDecodeError(f"unsupported envelope version: {version}")
        if kek_id_len == 0 or kek_id_len > MAX_KEK_ID_LEN:
            raise EnvelopeDecodeError(f"invalid kek_id_len: {kek_id_len}")

        offset = 2
        kek_id_bytes = envelope[offset : offset + kek_id_len]
        offset += kek_id_len
        kek_id = kek_id_bytes.decode("ascii")

        # Layout: [kek_nonce:12][enc_dek:48][data_nonce:12][ciphertext+N][aad_hash:32]
        # (enc_dek = 32 byte DEK + 16 byte GCM tag; the nonce is stored separately
        # because AESGCM.encrypt does NOT prepend the nonce to its output.)
        kek_nonce = envelope[offset : offset + NONCE_LEN_BYTES]
        offset += NONCE_LEN_BYTES

        enc_dek_len = DEK_LEN_BYTES + GCM_TAG_LEN_BYTES  # 48 bytes
        enc_dek = envelope[offset : offset + enc_dek_len]
        offset += enc_dek_len

        data_nonce = envelope[offset : offset + NONCE_LEN_BYTES]
        offset += NONCE_LEN_BYTES

        # Remaining bytes: ciphertext + tag + (optional aad_hash 32 bytes)
        rest = envelope[offset:]
        # AAD hash is the last 32 bytes if present (only when context was set).
        aad_hash: bytes | None
        if context is not None and len(rest) >= 32:
            ciphertext = rest[: -32]
            aad_hash = rest[-32:]
        else:
            ciphertext = rest
            aad_hash = None

        # Unwrap DEK with KEK.
        kek_aad = kek_id.encode("ascii")
        try:
            dek = self._kek_cipher.decrypt(kek_nonce, enc_dek, kek_aad)
        except InvalidTag as exc:
            raise EnvelopeAuthError(
                f"KEK unwrap failed (wrong kek or tampered envelope): kek_id={kek_id}"
            ) from exc

        # Verify AAD hash (defense against swap attacks between records).
        if aad_hash is not None:
            expected = _hash_aad(context)
            if not secrets.compare_digest(aad_hash, expected):
                raise EnvelopeAuthError("AAD context hash mismatch (tampering or wrong context)")

        # Decrypt data with DEK.
        dek_cipher = AESGCM(dek)
        aad = _encode_aad(context)
        try:
            plaintext = dek_cipher.decrypt(data_nonce, ciphertext, aad)
        except InvalidTag as exc:
            raise EnvelopeAuthError("data auth tag mismatch (tampered ciphertext)") from exc

        logger.debug(
            "envelope decrypt ok kek_id=%s aad_present=%s", kek_id, aad_hash is not None
        )
        return plaintext

    def encrypt_str(self, plaintext: str, context: dict[str, Any] | None = None) -> bytes:
        """Convenience: encrypt a UTF-8 string. Returns envelope bytes."""
        return self.encrypt(plaintext.encode("utf-8"), context=context)

    def decrypt_str(self, envelope: bytes, context: dict[str, Any] | None = None) -> str:
        """Convenience: decrypt envelope to UTF-8 string."""
        return self.decrypt(envelope, context=context).decode("utf-8")

    def metadata(self, envelope: bytes) -> EnvelopeMeta:
        """Decode envelope header (kek_id, version) WITHOUT decrypting.

        Useful for key rotation audits: read which KEK protects each row
        without touching the DEK or the plaintext.
        """
        if envelope is None or len(envelope) < 3:
            raise EnvelopeDecodeError("envelope too short")
        version, kek_id_len = struct.unpack("!BB", envelope[:2])
        if version != ENVELOPE_VERSION:
            raise EnvelopeDecodeError(f"unsupported envelope version: {version}")
        if kek_id_len == 0 or kek_id_len > MAX_KEK_ID_LEN:
            raise EnvelopeDecodeError(f"invalid kek_id_len: {kek_id_len}")
        kek_id = envelope[2 : 2 + kek_id_len].decode("ascii")
        aad_hash: bytes | None = None
        if len(envelope) > 2 + kek_id_len + NONCE_LEN_BYTES + NONCE_LEN_BYTES + DEK_LEN_BYTES + GCM_TAG_LEN_BYTES + 32:
            aad_hash = envelope[-32:]
        return EnvelopeMeta(version=version, kek_id=kek_id, aad_ctx_hash=aad_hash)


# =============================================================================
# Helpers
# =============================================================================


def _encode_aad(context: dict[str, Any] | None) -> bytes | None:
    """Serialize a context dict into stable AAD bytes (None → None)."""
    if context is None:
        return None
    # Stable JSON with sorted keys + sha256 for bounded size.
    import json

    payload = json.dumps(context, sort_keys=True, separators=(",", ":"), default=str)
    return payload.encode("utf-8")


def _hash_aad(context: dict[str, Any] | None) -> bytes:
    """SHA-256 of the canonical context JSON (32 bytes, fits AAD hash slot)."""
    aad = _encode_aad(context)
    if aad is None:
        return b"\x00" * 32
    return hashlib.sha256(aad).digest()


# =============================================================================
# Default singleton (loads KEK from env at module init; cached per-process)
# =============================================================================


_default: EnvelopeEncryption | None = None


def get_default_envelope() -> EnvelopeEncryption:
    """Return the process-wide cached `EnvelopeEncryption` (loads KEK lazily).

    The KEK material lives in memory for the lifetime of the process —
    never written to logs, never returned in plaintext. Refreshing the
    KEK requires a process restart (or explicit `reset_default_envelope`).
    """
    global _default
    if _default is None:
        _default = EnvelopeEncryption()
    return _default


def reset_default_envelope() -> None:
    """Drop the cached default (test helper / key rotation)."""
    global _default
    _default = None


__all__ = [
    "DEK_LEN_BYTES",
    "ENVELOPE_VERSION",
    "EnvelopeAuthError",
    "EnvelopeDecodeError",
    "EnvelopeEncryption",
    "EnvelopeError",
    "EnvelopeMeta",
    "KekUnavailableError",
    "MAX_KEK_ID_LEN",
    "NONCE_LEN_BYTES",
    "get_default_envelope",
    "reset_default_envelope",
]