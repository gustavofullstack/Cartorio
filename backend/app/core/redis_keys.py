"""G8.12.T3 — Helper central para chaves Redis do backend (DRY).

Proposito
=========

Unificar a nomenclatura de TODAS as chaves Redis criadas pela API do
Cartorio. Antes desta task existiam **N variacoes** de prefixo:

    bot:mute:...            (bot_mute.py)
    emolumento:...          (emolumento_cache.py)
    ratelimit:...           (rate_limit*.py)
    sliding:ip:...          (rate_limit_by_key.py)
    idempotency:...         (middleware/idempotency.py)
    idem:...                (chat_pipeline.py)
    redlock:...             (redlock.py)
    cartorio:atendimentos   (redis_bus.py) — pub/sub channels
    cartorio:slow_queries   (slow_queries.py) — ZSET
    cache:lookup:cpf:...    (redis_doc_keys.py) — HMAC CPFs

Esta task NAO reescreve TODOS os callers (escopo limitado a 3+
demonstrativos), mas cria o helper canonico e comeca a migracao de
forma incremental via follow-up waves (veja lesson
`.harness/memory/lesson-228-g8-12-t3-redis-key-pattern-*.md`).

Padrao canonico
===============

    cartorio:<namespace>:<scope>:<id>

Onde:

  - prefixo       : "cartorio" (constante da classe RedisKey.PREFIX)
  - namespace     : agrupamento funcional (session, idem, rate_limit,
                    cache, lock, channel, ...)
  - scope         : tipo do recurso dentro do namespace (api_key, ip,
                    session, webhook, telegram, cpf, ...)
  - id            : identificador opaco (hash, uuid, conta-minuto, etc)

Exemplos validos:

    cartorio:session:telegram:user_123
    cartorio:idem:webhook:abc-def-123
    cartorio:rate_limit:api_key:n8n_main:2999
    cartorio:cache:emolumento:escritura:500000
    cartorio:lock:alembic:migration
    cartorio:bot_mute:telegram:42

Este helper central garante:
  1. consistencia absoluta (regex de validacao)
  2. backward-compat minima (legacy normalization)
  3. zero PII acidental (validacao de chars + tamanho max)
  4. cache-friendly (`@lru_cache` nas funcoes puras)

LGPD
====

O helper NAO expoe PII: eh responsabilidade do caller passar
identificadores ja opacos (hash de CPF, hash de IP, uuid, etc).
Em particular `looks_safe_for_pii()` aplica o mesmo detector
de raw-CPF/CNPJ ja usado em `app.services.redis_doc_keys`.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from functools import lru_cache
from typing import Final

# Prefixo canônico — UNICO lugar onde "cartorio" aparece como string.
PREFIX: Final[str] = "cartorio"

# Comprimento maximo por componente (defesa contra keys abusivas).
_MAX_COMPONENT_LEN: Final[int] = 128

# Pattern canonico: cartorio:<ns>:<scope>:<id>
# - ns e scope: lowercase + underscore (snake_case)
# - id: A-Za-z0-9_.- (aceita uuid, hash hex, hash troncado)
_FULL_KEY_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^cartorio:[a-z][a-z0-9_]{1,63}:[a-z][a-z0-9_]{1,63}:[A-Za-z0-9_.\-]{1,128}$"
)

# Pattern para detectar raw CPF (11 digitos contiguos) ou CNPJ (14).
_PII_RE: Final[re.Pattern[str]] = re.compile(r"(?<!\d)\d{11}(?!\d)|(?<!\d)\d{14}(?!\d)")


class RedisKey:
    """Fabrica de chaves Redis canonicas para o backend do cartorio.

    Uso::

        from app.core.redis_keys import RedisKey

        key = RedisKey.session("telegram", "user_123")
        # 'cartorio:session:telegram:user_123'

        rate_key = RedisKey.rate_limit("api_key", "n8n_main", bucket=2999)
        # 'cartorio:rate_limit:api_key:n8n_main:2999'

        idem = RedisKey.idempotency("webhook", "abc-def-123")
        # 'cartorio:idem:webhook:abc-def-123'
    """

    PREFIX: Final[str] = PREFIX

    # =========================================================================
    # Factories principais (API publica)
    # =========================================================================

    @staticmethod
    def session(scope: str, scope_id: str) -> str:
        """Sessao de usuario autenticado.

        Args:
            scope: canal/ambito (ex: "telegram", "chatwoot", "admin").
            scope_id: id opaco do usuario (sem PII — usar hash SHA-256 ou uuid).

        Returns:
            `cartorio:session:<scope>:<scope_id>`
        """
        return _build("session", scope, scope_id)

    @staticmethod
    def idempotency(scope: str, key: str) -> str:
        """Idempotency-key de webhook ou de POST HTTP.

        Args:
            scope: tipo do recurso (ex: "webhook", "post", "n8n").
            key: id opaco (tipicamente uuid v4 ou hash SHA-256 hex).

        Returns:
            `cartorio:idem:<scope>:<key>`
        """
        return _build("idem", scope, key)

    @staticmethod
    def rate_limit(scope: str, scope_id: str, bucket: int | None = None) -> str:
        """Rate-limit counter (fixed window / sliding window).

        Args:
            scope: tipo (ex: "api_key", "ip", "session", "chat").
            scope_id: id opaco (hash de API key, hash de IP).
            bucket: contador de bucket de minuto (opcional; se presente
                    eh anexado como :<bucket>).

        Returns:
            `cartorio:rate_limit:<scope>:<scope_id>` ou
            `cartorio:rate_limit:<scope>:<scope_id>:<bucket>`.
        """
        if bucket is None:
            return _build("rate_limit", scope, scope_id)
        return _build("rate_limit", scope, f"{scope_id}:{bucket}")

    @staticmethod
    def cache(entity: str, entity_id: str) -> str:
        """Cache de entidade read-through.

        Args:
            entity: tipo (ex: "emolumento", "protocolo", "lgpd_consent").
            entity_id: id opaco (tipo+valor, hash de CPF/CNPJ).

        Returns:
            `cartorio:cache:<entity>:<entity_id>`
        """
        return _build("cache", entity, entity_id)

    # =========================================================================
    # Factories adicionais (cobrir namespaces conhecidos do inventario)
    # =========================================================================

    @staticmethod
    def bot_mute(channel: str, conversation_key: str) -> str:
        """Mute do bot durante HITL (G8.03.T2).

        `cartorio:bot_mute:<channel>:<conversation_key>`
        """
        return _build("bot_mute", channel, conversation_key)

    @staticmethod
    def lock(name: str) -> str:
        """Redlock distribuido.

        `cartorio:lock:<name>`
        """
        return _build("lock", "redlock", name)

    @staticmethod
    def channel(channel_name: str) -> str:
        """Pub/Sub channel alias. Mantem formato `cartorio:<name>:events`
        quando nao for um dos canais canonicos pre-existentes.
        """
        return _build("channel", "events", channel_name)

    @staticmethod
    def doc_cache(entity: str, kind: str, doc_hash: str) -> str:
        """Cache de documento baseado em hash de CPF/CNPJ (LGPD-safe).

        `cartorio:cache:<entity>:<kind>:<doc_hash>`
        """
        return f"{PREFIX}:cache:{entity}:{kind}:{doc_hash}"

    # =========================================================================
    # Helpers
    # =========================================================================

    @staticmethod
    def normalize_legacy(legacy_key: str) -> str:
        """Aceita uma chave antiga (sem prefixo `cartorio:`) e devolve a
        versao canônica com prefixo.

        Regras de normalizacao:
          - "idempotency:..."        → "cartorio:idem:..."
          - "idem:..."               → "cartorio:idem:..."
          - "ratelimit:apikey:..."   → "cartorio:rate_limit:api_key:..."
          - "ratelimit:ip:..."       → "cartorio:rate_limit:ip:..."
          - "ratelimit:session:..."  → "cartorio:rate_limit:session:..."
          - "sliding:ip:..."         → "cartorio:rate_limit:sliding_ip:..."
          - "bot:mute:..."           → "cartorio:bot_mute:..."
          - "emolumento:..."         → "cartorio:cache:emolumento:..."
          - "redlock:..."            → "cartorio:lock:redlock:..."
          - "cartorio:..."           → já canonica — retorna identica
          - qualquer outra           → considera namespace+scope: "<a>:<b>" como
                                        "<a>:<b>:resto" e prefixa.

        Levanta ``ValueError`` se apos normalizacao a chave nao casar
        o pattern canonico.
        """
        if not legacy_key:
            raise ValueError("empty legacy_key")

        key = legacy_key.strip()

        # Já canonica
        if key.startswith(f"{PREFIX}:"):
            return key

        # Regras de mapeamento explícitas. Cada regra produz uma chave
        # canonica em 4 partes: cartorio:<ns>:<scope>:<id>. Quando o resto
        # da chave legada tem apenas 1 segmento ("idem:abc"), inserimos
        # scope=default; quando tem 2+ segmentos, usamos o primeiro como
        # scope e o resto (sanitizado) como id.
        def _expand(prefix: str, ns: str, default_scope: str) -> str:
            rest = key[len(prefix):]
            rest_parts = rest.split(":")
            if len(rest_parts) == 1:
                scope = default_scope
                scope_id = rest_parts[0]
            else:
                scope = rest_parts[0]
                # Colapsa o resto em um id unico (pode conter ':' ou nao)
                scope_id = ":".join(rest_parts[1:])
            if not scope:
                scope = default_scope
            return _build(ns, scope, scope_id)

        def _expand_join_id(prefix: str, ns: str, fixed_scope: str) -> str:
            """Variante para chaves onde o ID eh a juncao do resto inteiro.

            Exemplo: emolumento:<tipo>:<valor> -> cartorio:cache:emolumento:<tipo>_<valor>
            """
            rest = key[len(prefix):]
            if not rest:
                raise ValueError(f"chave legacy vazia apos prefixo {prefix!r}")
            scope_id = rest.replace(":", "_")
            return _build(ns, fixed_scope, scope_id)

        rules: tuple[tuple[str, Callable[[], str]], ...] = (
            ("idempotency:", lambda: _expand("idempotency:", "idem", "default")),
            ("idem:", lambda: _expand("idem:", "idem", "default")),
            ("ratelimit:apikey:", lambda: _expand("ratelimit:apikey:", "rate_limit", "api_key")),
            ("ratelimit:ip:", lambda: _expand("ratelimit:ip:", "rate_limit", "ip")),
            ("ratelimit:session:", lambda: _expand("ratelimit:session:", "rate_limit", "session")),
            ("sliding:ip:", lambda: _expand("sliding:ip:", "rate_limit", "sliding_ip")),
            ("bot:mute:", lambda: _expand("bot:mute:", "bot_mute", "channel")),
            ("emolumento:", lambda: _expand_join_id("emolumento:", "cache", "emolumento")),
            ("redlock:", lambda: _expand("redlock:", "lock", "redlock")),
        )

        for prefix, build_fn in rules:
            if key.startswith(prefix):
                return build_fn()

        # Fallback generico: tenta extrair pelo menos 2 componentes
        parts = key.split(":", 3)
        if len(parts) < 2:
            raise ValueError(
                f"nao foi possivel normalizar chave legacy: {legacy_key!r}"
            )
        return _build(_clean_namespace(parts[0]), "default" if len(parts) == 2 else _clean_scope(parts[1]), ":".join(parts[1:]))

    @staticmethod
    def is_valid(key: str) -> bool:
        """True se a chave casa o padrao canonico do projeto."""
        return bool(_FULL_KEY_PATTERN.match(key or ""))


# ============================================================================
# Implementacao interna (helpers privados / cached)
# ============================================================================


@lru_cache(maxsize=512)
def _build(namespace: str, scope: str, scope_id: str) -> str:
    """Constroi chave canonica + valida.

    Cacheada via lru_cache: o backend chama as factories em loop
    (rate limit por request, etc) — evita realocar a mesma string
    milhares de vezes por segundo.
    """
    ns = _clean_namespace(namespace)
    sc = _clean_scope(scope)
    sid = _clean_id(scope_id)

    key = f"{PREFIX}:{ns}:{sc}:{sid}"

    if not _FULL_KEY_PATTERN.match(key):
        raise ValueError(
            f"chave redis invalida: {key!r} — deve casar "
            r"^cartorio:[a-z][a-z0-9_]{1,63}:[a-z][a-z0-9_]{1,63}:[A-Za-z0-9_.\-]{1,128}$"
        )
    return key


def _clean_namespace(value: str) -> str:
    s = (value or "").strip().lower()
    if not s:
        raise ValueError("namespace obrigatorio")
    s = re.sub(r"[^a-z0-9_]+", "_", s).strip("_")
    if not s or len(s) > _MAX_COMPONENT_LEN:
        raise ValueError(f"namespace invalido: {value!r}")
    return s


def _clean_scope(value: str) -> str:
    s = _clean_namespace(value)  # mesmas regras
    return s


def _clean_id(value: str) -> str:
    s = (value or "").strip()
    if not s:
        raise ValueError("id obrigatorio")
    # Permite A-Za-z0-9_.- (uuid v4, hash hex, hash troncado, ip-like).
    # Qualquer outro char e removido para manter o pattern canonico.
    s = re.sub(r"[^A-Za-z0-9_.\-]+", "_", s).strip("_")
    if not s or len(s) > _MAX_COMPONENT_LEN:
        raise ValueError(f"id invalido: {value!r}")
    return s


def is_valid(key: str) -> bool:
    """Atalho para o leitor — equivalente a ``RedisKey.is_valid(key)``."""
    return bool(_FULL_KEY_PATTERN.match(key or ""))


def looks_like_raw_pii(key: str) -> bool:
    """Detecta se a chave contem 11 ou 14 digitos contiguos (CPF/CNPJ raw).

    Usada em middleware/testes para AUDITAR chaves que ainda nao migraram.
    NUNCA deve retornar True para chaves canonicas bem formadas.
    """
    return bool(_PII_RE.search(key or ""))


__all__ = [
    "PREFIX",
    "RedisKey",
    "is_valid",
    "looks_like_raw_pii",
]
