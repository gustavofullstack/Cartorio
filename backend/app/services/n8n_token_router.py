"""N8N token registry with rotation + grace period (G8.23.T4).

Permite rotacionar o token da API N8N sem downtime e sem quebrar
integracoes em curso: cada requisicao carrega ``X-N8N-KEY-ID`` (kid) e
``X-N8N-API-KEY`` (token). O registry eh um singleton thread-safe
mantido em memoria (init de processo).

Estados de um token:

- active   -> usado para chamadas atuais (um por vez)
- rotating -> token antigo apos ``rotate()``; ainda aceito ate grace
- revoked  -> token revogado (grace expirado); ``get_token()`` recusa

Concurrencia:
- ``threading.RLock`` no registry. Toda mutacao (register, rotate,
  revoke_old) e leitura coordenada passa pelo lock.

Failure modes:
- kid duplicado -> ``ValueError``
- rotate sem active -> ``RuntimeError`` (chame ``register`` antes)
- get_token sem active -> ``RuntimeError``
- get_token apontando para token revoked -> ``RuntimeError``

LGPD-by-design:
- Art. 46 (seguranca e sigilo): rotacao periodica reduz blast radius
  de vazamento e habilita revogacao rapida em incidente.
- Art. 50 (governanca): grace period documentado (audit-friendly).

Modified by Gustavo Almeida + cartorio-n8n -- G8.23.T4 (Wave 53).
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timedelta, UTC

logger = logging.getLogger(__name__)


DEFAULT_LEGACY_KID = "legacy"
DEFAULT_TTL_DAYS = 30
DEFAULT_GRACE_PERIOD_DAYS = 7


class TokenStatus:
    """Estados de um token no registry."""

    ACTIVE = "active"
    ROTATING = "rotating"
    REVOKED = "revoked"


class N8NTokenRouter:
    """Registry singleton de tokens N8N com rotacao + grace period.

    Cada token tem:
      - ``kid`` (str, unico): key id retornado em ``X-N8N-KEY-ID``
      - ``token`` (str): valor enviado em ``X-N8N-API-KEY``
      - ``status`` (str): active | rotating | revoked
      - ``created_at`` (datetime): quando foi registrado
      - ``rotated_at`` (datetime | None): quando deixou de ser active
      - ``expires_at`` (datetime): now + ttl_days
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._tokens: dict[str, dict] = {}
        self._active_kid: str = ""
        self._bootstrapped: bool = False

    def bootstrap_legacy(self, token: str, kid: str = DEFAULT_LEGACY_KID) -> None:
        """Inicializa com o token historico (``settings.n8n_api_key``).

        Idempotente quando chamado com o mesmo kid+token.
        Raises quando o kid ja esta registrado com token diferente ou
        quando o router ja tem um ACTIVE (clobber eh proibido).

        Raises:
            ValueError: kid duplicado com token diferente.
            RuntimeError: router ja bootstrapped com outro kid ou ja tem
                um ACTIVE registrado. Use ``register()`` ou ``rotate()``.
        """
        with self._lock:
            if not token:
                logger.warning("n8n_token_router: bootstrap_legacy called with empty token")
                return
            existing = self._tokens.get(kid)
            if existing is not None:
                if existing["token"] == token:
                    self._bootstrapped = True
                    return
                raise ValueError(
                    f"n8n_token_router: kid={kid} already registered with a different token"
                )
            if self._active_kid or self._bootstrapped:
                raise RuntimeError(
                    f"n8n_token_router: router already bootstrapped with kid="
                    f"{self._active_kid or '(unset)'}; use register() or rotate()"
                )
            now = datetime.now(UTC)
            self._tokens[kid] = {
                "token": token,
                "status": TokenStatus.ACTIVE,
                "created_at": now,
                "rotated_at": None,
                "expires_at": now + timedelta(days=DEFAULT_TTL_DAYS),
            }
            self._active_kid = kid
            self._bootstrapped = True
            logger.info(
                "n8n_token_router: bootstrapped legacy kid=%s (token_length=%d)",
                kid,
                len(token),
            )

    def register(
        self,
        kid: str,
        token: str,
        ttl_days: int = DEFAULT_TTL_DAYS,
        status: str = TokenStatus.ACTIVE,
    ) -> None:
        """Registra um novo token no registry.

        Raises:
            ValueError: kid duplicado ou status invalido.
            RuntimeError: registro de novo ACTIVE quando ja existe ACTIVE.
                          Use ``rotate()`` nesse caso.
        """
        if status not in {TokenStatus.ACTIVE, TokenStatus.ROTATING, TokenStatus.REVOKED}:
            raise ValueError(f"n8n_token_router: invalid status {status!r}")
        if not kid or not token:
            raise ValueError("n8n_token_router: kid and token must be non-empty")

        with self._lock:
            if kid in self._tokens:
                raise ValueError(f"n8n_token_router: kid={kid} already registered")
            if (
                status == TokenStatus.ACTIVE
                and self._active_kid
                and self._active_kid != kid
            ):
                raise RuntimeError(
                    f"n8n_token_router: cannot register active kid={kid} while "
                    f"kid={self._active_kid} is active; use rotate()"
                )
            now = datetime.now(UTC)
            self._tokens[kid] = {
                "token": token,
                "status": status,
                "created_at": now,
                "rotated_at": None,
                "expires_at": now + timedelta(days=ttl_days),
            }
            if status == TokenStatus.ACTIVE:
                self._active_kid = kid
            logger.info(
                "n8n_token_router: registered kid=%s status=%s ttl_days=%d",
                kid,
                status,
                ttl_days,
            )

    def rotate(
        self,
        new_kid: str,
        new_token: str,
        ttl_days: int = DEFAULT_TTL_DAYS,
    ) -> str:
        """Rotaciona: novo kid vira ACTIVE, antigo vira ROTATING.

        Returns:
            kid do token anterior (agora em ROTATING).

        Raises:
            RuntimeError: sem token ACTIVE para rotacionar.
            ValueError: new_kid duplicado.
        """
        with self._lock:
            old_kid = self._active_kid
            if not old_kid:
                raise RuntimeError(
                    "n8n_token_router: cannot rotate without an active token; "
                    "call register() or bootstrap_legacy() first"
                )
            if old_kid == new_kid:
                raise ValueError(f"n8n_token_router: new_kid={new_kid} == active kid")
            if new_kid in self._tokens:
                raise ValueError(f"n8n_token_router: new_kid={new_kid} already registered")

            now = datetime.now(UTC)
            old_entry = self._tokens[old_kid]
            old_entry["status"] = TokenStatus.ROTATING
            old_entry["rotated_at"] = now

            self._tokens[new_kid] = {
                "token": new_token,
                "status": TokenStatus.ACTIVE,
                "created_at": now,
                "rotated_at": None,
                "expires_at": now + timedelta(days=ttl_days),
            }
            self._active_kid = new_kid
            logger.info(
                "n8n_token_router: rotated old_kid=%s -> new_kid=%s (grace_until=%s)",
                old_kid,
                new_kid,
                (now + timedelta(days=DEFAULT_GRACE_PERIOD_DAYS)).isoformat(),
            )
            return old_kid

    def get_token(self) -> tuple[str, str]:
        """Retorna ``(kid, token)`` do token ACTIVE atual.

        Raises:
            RuntimeError: nenhum token ACTIVE registrado.
        """
        with self._lock:
            if not self._active_kid:
                raise RuntimeError("n8n_token_router: no active token configured")
            info = self._tokens[self._active_kid]
            if info["status"] != TokenStatus.ACTIVE:
                raise RuntimeError(
                    f"n8n_token_router: active_kid={self._active_kid} "
                    f"is not in ACTIVE state (status={info['status']})"
                )
            return self._active_kid, info["token"]

    def status_of(self, kid: str) -> str | None:
        """Retorna status do token, ou ``None`` se kid nao existe."""
        with self._lock:
            entry = self._tokens.get(kid)
            return entry["status"] if entry else None

    def revoke_old(self, grace_period_days: int = DEFAULT_GRACE_PERIOD_DAYS) -> list[str]:
        """Promove ROTATING com grace expirado para REVOKED.

        Returns:
            Lista de kids que foram promovidos a REVOKED.
        """
        with self._lock:
            now = datetime.now(UTC)
            cutoff = now - timedelta(days=grace_period_days)
            promoted: list[str] = []
            for kid, entry in self._tokens.items():
                if entry["status"] != TokenStatus.ROTATING:
                    continue
                rotated_at = entry.get("rotated_at")
                if rotated_at and rotated_at <= cutoff:
                    entry["status"] = TokenStatus.REVOKED
                    promoted.append(kid)
            if promoted:
                logger.info(
                    "n8n_token_router: revoked kids past grace: %s", promoted
                )
            return promoted

    def list_active(self) -> list[str]:
        """Lista kids em estado ACTIVE (normalmente 1)."""
        with self._lock:
            return [
                kid
                for kid, entry in self._tokens.items()
                if entry["status"] == TokenStatus.ACTIVE
            ]

    def snapshot(self) -> dict[str, dict]:
        """Snapshot serializavel do registry (sem expor tokens).

        Os campos ``token`` sao hash-prefixados (sha256[:8]) para audit
        log. Use ``get_token()`` quando precisar do valor real.
        """
        import hashlib

        with self._lock:
            out: dict[str, dict] = {}
            for kid, entry in self._tokens.items():
                token_hash = hashlib.sha256(entry["token"].encode("utf-8")).hexdigest()[:8]
                out[kid] = {
                    "status": entry["status"],
                    "created_at": entry["created_at"].isoformat(),
                    "rotated_at": entry["rotated_at"].isoformat() if entry["rotated_at"] else None,
                    "expires_at": entry["expires_at"].isoformat(),
                    "token_hash": token_hash,
                }
            return out

    def reset_for_tests(self) -> None:
        """Reset do singleton para testes. NAO use em producao."""
        with self._lock:
            self._tokens.clear()
            self._active_kid = ""
            self._bootstrapped = False


_ROUTER = N8NTokenRouter()


def get_router() -> N8NTokenRouter:
    """Retorna o singleton do router."""
    return _ROUTER
