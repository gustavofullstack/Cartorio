"""HMAC key registry para o audit_log (G8.19.T2).

Permite rotacionar a chave HMAC do audit sem invalidar entries antigos:
cada entry referencia qual ``kid`` assinou. O registry eh um singleton
thread-safe mantido em memoria (init de processo). Boot do modulo
registra a chave de ``settings.audit_hmac_key`` como kid ``legacy`` para
compatibilidade com entries pre-rotacao.

LGPD-by-design:
- Art. 46 (seguranca e sigilo): rotacao periodica eh boa pratica de
  gestao de chaves; manter entries antigos verificaveis preserva a
  cadeia de auditoria (Art. 37).
- Art. 50 (boas praticas e governanca): grace period documentado.

Estados de uma key:

- active   -> usada para assinar entries novos (uma por vez)
- rotating -> key antiga apos rotacao; ainda usada para verify
             de entries historicos ate expirar grace period
- deprecated -> key removida; entries novos NAO sao mais assinados
              com ela; verify dela retorna erro

Concurrencia:
- ``threading.RLock`` no registry. Toda mutacao (register, rotate,
  cleanup) e leitura coordenada passa pelo lock.

Failure modes:
- Key duplicada (kid reuse) -> ValueError
- Rotacao sem active key -> RuntimeError (deve chamar register_key antes)
- Verify com kid desconhecido / deprecated -> raises KeyError
- Sem active key no sign -> RuntimeError
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import threading
from datetime import datetime, timedelta, UTC

logger = logging.getLogger(__name__)


DEFAULT_LEGACY_KID = "legacy"
DEFAULT_GRACE_PERIOD_DAYS = 30


class KeyStatus:
    ACTIVE = "active"
    ROTATING = "rotating"
    DEPRECATED = "deprecated"


class HmacKeyRouter:
    """Registry singleton de chaves HMAC para o audit log.

    Cada key tem:
      - ``kid`` (str, unico): key id usado para assinar/verificar
      - ``secret`` (bytes): chave criptografica
      - ``status`` (str): active | rotating | deprecated
      - ``created_at`` (datetime): quando foi registrada
      - ``rotated_at`` (datetime | None): quando deixou de ser active
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._keys: dict[str, dict] = {}
        self._active_kid: str = ""
        self._bootstrapped: bool = False

    def bootstrap_legacy(self, secret: bytes, kid: str = DEFAULT_LEGACY_KID) -> None:
        """Inicializa com a chave historica (settings.audit_hmac_key).

        Idempotente. Se chamada novamente com kid diferente, NAO sobrescreve
        (preserva audit chain). Se ``self._active_kid`` ja esta setado, noop.
        """
        with self._lock:
            if self._bootstrapped:
                return
            if kid in self._keys:
                # Permite re-bootstrap idempotente (mesma key)
                if hmac.compare_digest(self._keys[kid]["secret"], secret):
                    self._bootstrapped = True
                    return
            self._keys[kid] = {
                "secret": secret,
                "status": KeyStatus.ACTIVE,
                "created_at": datetime.now(UTC),
                "rotated_at": None,
            }
            self._active_kid = kid
            self._bootstrapped = True
            logger.info(
                "audit_keys: bootstrapped legacy kid=%s (length=%d)",
                kid,
                len(secret),
            )

    def register_key(
        self,
        kid: str,
        secret: bytes,
        status: str = KeyStatus.ACTIVE,
    ) -> None:
        """Registra nova key no registry.

        Raises:
            ValueError: kid duplicado (reuse de key id NAO permitido).
        """
        if not kid or not isinstance(kid, str):
            raise ValueError("kid deve ser str nao-vazia")
        if not isinstance(secret, (bytes, bytearray)) or len(secret) < 16:
            raise ValueError("secret deve ser bytes com pelo menos 16 bytes")
        if status not in {KeyStatus.ACTIVE, KeyStatus.ROTATING, KeyStatus.DEPRECATED}:
            raise ValueError(f"status invalido: {status}")
        with self._lock:
            if kid in self._keys:
                raise ValueError(f"kid duplicado: {kid!r}")
            self._keys[kid] = {
                "secret": bytes(secret),
                "status": status,
                "created_at": datetime.now(UTC),
                "rotated_at": None,
            }
            if status == KeyStatus.ACTIVE:
                if self._active_kid and self._active_kid != kid:
                    # Ja existe outra active; marca como rotating (uso normal: rotate_to_new_key)
                    self._keys[kid]["status"] = KeyStatus.ROTATING
                    raise ValueError(
                        f"ja existe active kid={self._active_kid!r}; "
                        f"use rotate_to_new_key() em vez de register(active)"
                    )
                self._active_kid = kid
            logger.info(
                "audit_keys: registered kid=%s status=%s length=%d",
                kid,
                status,
                len(secret),
            )

    def rotate_to_new_key(self, new_kid: str, new_secret: bytes) -> str:
        """Rotaciona HMAC key sem quebrar audit logs antigos.

        Fluxo:
        1. Marca chave ativa anterior como ``rotating`` (com ``rotated_at``).
        2. Registra ``new_kid`` como ``active``.

        Returns:
            kid da chave anterior (agora em estado ``rotating``). Vazio
            se nao havia chave ativa antes.

        Raises:
            ValueError: kid duplicado, secret invalido.
            RuntimeError: nova key nao conseguiu ser marcada active.
        """
        if not new_kid or not isinstance(new_kid, str):
            raise ValueError("new_kid deve ser str nao-vazia")
        if not isinstance(new_secret, (bytes, bytearray)) or len(new_secret) < 16:
            raise ValueError("new_secret deve ser bytes com pelo menos 16 bytes")
        with self._lock:
            if new_kid in self._keys:
                raise ValueError(f"kid duplicado: {new_kid!r}")
            old_kid = self._active_kid
            now = datetime.now(UTC)
            if old_kid:
                self._keys[old_kid]["status"] = KeyStatus.ROTATING
                self._keys[old_kid]["rotated_at"] = now
            self._keys[new_kid] = {
                "secret": bytes(new_secret),
                "status": KeyStatus.ACTIVE,
                "created_at": now,
                "rotated_at": None,
            }
            self._active_kid = new_kid
            logger.warning(
                "audit_keys: ROTATION old_kid=%s -> new_kid=%s (old agora rotating)",
                old_kid or "<none>",
                new_kid,
            )
            return old_kid

    def get_key_for_signing(self) -> tuple[str, bytes]:
        """Retorna ``(kid, secret)`` da chave ativa.

        Raises:
            RuntimeError: nenhuma chave ativa registrada.
        """
        with self._lock:
            if not self._active_kid:
                raise RuntimeError("No active HMAC key registered")
            entry = self._keys[self._active_kid]
            return self._active_kid, entry["secret"]

    def get_key_by_kid(self, kid: str) -> bytes:
        """Retorna secret da key com ``kid`` dado.

        Raises:
            KeyError: kid desconhecido OU key em estado deprecated.
        """
        with self._lock:
            if kid not in self._keys:
                raise KeyError(f"Unknown HMAC kid: {kid!r}")
            entry = self._keys[kid]
            if entry["status"] == KeyStatus.DEPRECATED:
                raise KeyError(f"HMAC kid {kid!r} deprecated; past grace period")
            return entry["secret"]

    def has_kid(self, kid: str) -> bool:
        with self._lock:
            return kid in self._keys

    def status_of(self, kid: str) -> str | None:
        with self._lock:
            if kid not in self._keys:
                return None
            return self._keys[kid]["status"]

    def cleanup_rotated_keys(self, grace_period_days: int = DEFAULT_GRACE_PERIOD_DAYS) -> list[str]:
        """Marca keys em ``rotating`` alem do grace period como ``deprecated``.

        Returns:
            Lista de kids que foram marcados deprecated nesta chamada.

        Keys deprecated NAO verificam mais entries antigos (assinatura
        eh perdida — pra re-verificar, restaurar a key). Por isso a janela
        de grace period default de 30 dias.
        """
        with self._lock:
            now = datetime.now(UTC)
            cutoff = now - timedelta(days=grace_period_days)
            promoted: list[str] = []
            for kid, entry in self._keys.items():
                if entry["status"] != KeyStatus.ROTATING:
                    continue
                rotated_at = entry.get("rotated_at") or entry["created_at"]
                if rotated_at <= cutoff:
                    entry["status"] = KeyStatus.DEPRECATED
                    promoted.append(kid)
                    logger.warning(
                        "audit_keys: DEPRECATED kid=%s (rotated_at=%s)",
                        kid,
                        rotated_at.isoformat(),
                    )
            return promoted

    def snapshot(self) -> dict[str, dict]:
        """Snapshot read-only do registry (para debug / health endpoint)."""
        with self._lock:
            return {
                kid: {
                    "status": entry["status"],
                    "created_at": entry["created_at"].isoformat(),
                    "rotated_at": (
                        entry["rotated_at"].isoformat() if entry.get("rotated_at") else None
                    ),
                    "length": len(entry["secret"]),
                }
                for kid, entry in self._keys.items()
            }

    def reset_for_tests(self) -> None:
        """Limpa registry (uso EXCLUSIVO de testes)."""
        with self._lock:
            self._keys.clear()
            self._active_kid = ""
            self._bootstrapped = False


_ROUTER = HmacKeyRouter()


def get_router() -> HmacKeyRouter:
    """Retorna singleton do router."""
    return _ROUTER


def bootstrap_legacy(secret: bytes, kid: str = DEFAULT_LEGACY_KID) -> None:
    """Atalho para ``HmacKeyRouter().bootstrap_legacy`` no singleton."""
    _ROUTER.bootstrap_legacy(secret, kid)


def _ensure_bootstrapped() -> None:
    """Lazy bootstrap do singleton a partir de settings (thread-safe)."""
    if _ROUTER._bootstrapped:  # noqa: SLF001 (intencional)
        return
    try:
        from app.config import settings

        _ROUTER.bootstrap_legacy(settings.audit_hmac_key.encode("utf-8"))
    except Exception as exc:  # pragma: no cover - guard
        logger.error("audit_keys: bootstrap falhou (%s)", exc)


def sign_audit_entry(canonical_payload: bytes) -> tuple[str, str]:
    """Assina entrada do audit log retornando ``(kid, hmac_sig_hex)``.

    Args:
        canonical_payload: bytes do payload canonico (ja serializado).

    Returns:
        Tupla ``(kid, hmac_sig)`` onde ``hmac_sig`` eh hex digest SHA256
        do HMAC da chave ativa aplicado em ``canonical_payload``.
    """
    _ensure_bootstrapped()
    kid, secret = _ROUTER.get_key_for_signing()
    sig = hmac.new(secret, canonical_payload, hashlib.sha256).hexdigest()
    return kid, sig


def verify_audit_entry(canonical_payload: bytes, kid: str | None, sig: str) -> bool:
    """Verifica assinatura HMAC do entry do audit log.

    Args:
        canonical_payload: bytes do payload canonico.
        kid: key id que assinou o entry. ``None`` para entries pre-rotacao
            (vai usar a kid ``legacy`` registrada no bootstrap).
        sig: hex digest da assinatura.

    Returns:
        ``True`` se assinatura confere com a chave de ``kid``.

    Compatibilidade:
        - ``kid=None``: usa a kid ``legacy`` registrada no bootstrap.
        - ``kid`` apontando pra kid desconhecida: retorna ``False``
          (silencioso — entry suspeito).
        - ``kid`` deprecated: retorna ``False``.
    """
    _ensure_bootstrapped()
    target_kid = kid or DEFAULT_LEGACY_KID
    try:
        secret = _ROUTER.get_key_by_kid(target_kid)
    except KeyError:
        return False
    expected = hmac.new(secret, canonical_payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)


def generate_new_secret(nbytes: int = 32) -> bytes:
    """Gera secret aleatorio criptograficamente seguro.

    Wrapper sobre ``secrets.token_bytes`` pra padronizar tamanho (32 bytes
    = 256 bits, suitable para HMAC-SHA256).
    """
    if nbytes < 16:
        raise ValueError("nbytes deve ser >= 16 (HMAC-SHA256 minimo 128 bits)")
    return secrets.token_bytes(nbytes)


__all__ = [
    "DEFAULT_GRACE_PERIOD_DAYS",
    "DEFAULT_LEGACY_KID",
    "HmacKeyRouter",
    "KeyStatus",
    "bootstrap_legacy",
    "cleanup_rotated_keys_thunk",
    "generate_new_secret",
    "get_router",
    "sign_audit_entry",
    "verify_audit_entry",
]


def cleanup_rotated_keys_thunk(
    grace_period_days: int = DEFAULT_GRACE_PERIOD_DAYS,
) -> list[str]:
    """Atalho pra scheduler/cron chamar cleanup de chaves rotating.

    Idempotente. Logs warns para cada kid promovido a deprecated.
    """
    return _ROUTER.cleanup_rotated_keys(grace_period_days)
