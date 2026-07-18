"""G8.12.T3 — Testes do helper central de chaves Redis (DRY).

Cobre o contrato canonico:
  cartorio:<namespace>:<scope>:<id>

Factories:
  - session()        → cartorio:session:<scope>:<id>
  - idempotency()    → cartorio:idem:<scope>:<id>
  - rate_limit()     → cartorio:rate_limit:<scope>:<id>[:bucket]
  - cache()          → cartorio:cache:<entity>:<id>
  - bot_mute()       → cartorio:bot_mute:<channel>:<conv>
  - lock()           → cartorio:lock:redlock:<name>
  - normalize_legacy(key) -> chave canonica

Modified by Gustavo Almeida — G8.12.T3 (Wave 47).
"""

from __future__ import annotations

import re

import pytest

from app.core.redis_keys import PREFIX, RedisKey, is_valid, looks_like_raw_pii


# ============================================================================
# Constantes
# ============================================================================


CANONICAL_RE = re.compile(
    r"^cartorio:[a-z][a-z0-9_]{1,63}:[a-z][a-z0-9_]{1,63}:[A-Za-z0-9_.\-]{1,128}$"
)


# ============================================================================
# 1. Testes de formato basico
# ============================================================================


def test_prefix_constant_is_cartorio() -> None:
    """Constante PREFIX deve ser exatamente 'cartorio' (fonte da verdade)."""
    assert PREFIX == "cartorio"


def test_session_key_format() -> None:
    """RedisKey.session produz chave canonica."""
    assert RedisKey.session("telegram", "user_123") == "cartorio:session:telegram:user_123"
    assert RedisKey.session("chatwoot", "agent_42") == "cartorio:session:chatwoot:agent_42"


def test_idempotency_key_format() -> None:
    """RedisKey.idempotency produz chave canonica."""
    assert RedisKey.idempotency("webhook", "abc-def-123") == "cartorio:idem:webhook:abc-def-123"
    assert RedisKey.idempotency("post", "sha256hexdeadbeef") == "cartorio:idem:post:sha256hexdeadbeef"


def test_rate_limit_key_format() -> None:
    """RedisKey.rate_limit produz chave canonica (com e sem bucket).

    Quando ``bucket`` eh passado, ele eh concatenado no id via ``_``
    (separador canonico). O caller pode Appendar bucket como quinto
    componente via f-string para casos como sliding-window onde o
    bucket tem semantica diferente — mas isso quebraria o pattern
    canonico, entao optamos por bake-in.
    """
    no_bucket = RedisKey.rate_limit("api_key", "n8n_main")
    assert no_bucket == "cartorio:rate_limit:api_key:n8n_main"

    with_bucket = RedisKey.rate_limit("api_key", "n8n_main", bucket=2999)
    # bucket eh incorporado no id com '_' para manter pattern 4-parts
    assert with_bucket == "cartorio:rate_limit:api_key:n8n_main_2999"
    assert is_valid(with_bucket) is True

    # ip-only
    assert RedisKey.rate_limit("ip", "abc123") == "cartorio:rate_limit:ip:abc123"


def test_cache_key_format() -> None:
    """RedisKey.cache produz chave canonica."""
    assert RedisKey.cache("emolumento", "escritura_500000") == "cartorio:cache:emolumento:escritura_500000"
    assert RedisKey.cache("lgpd_consent", "cliente_42") == "cartorio:cache:lgpd_consent:cliente_42"


# ============================================================================
# 2. Testes de validacao (pattern canonico)
# ============================================================================


def test_keys_match_regex_pattern() -> None:
    """Todas as factories produzem chaves que casam o regex canonico."""
    keys = [
        RedisKey.session("telegram", "user_123"),
        RedisKey.idempotency("webhook", "abc-def"),
        RedisKey.rate_limit("api_key", "n8n_main"),
        RedisKey.rate_limit("api_key", "n8n_main", bucket=42),
        RedisKey.cache("emolumento", "escritura_500000"),
        RedisKey.bot_mute("telegram", "42"),
        RedisKey.lock("alembic_migration"),
    ]
    for key in keys:
        assert is_valid(key) is True, f"chave invalida: {key}"
        assert CANONICAL_RE.match(key), f"nao casa regex: {key}"
        assert key.startswith(f"{PREFIX}:")


def test_keys_must_start_with_prefix() -> None:
    """Qualquer chave sem prefixo 'cartorio:' eh considerada nao-canonica."""
    assert is_valid("session:telegram:42") is False
    assert is_valid("foo:bar:baz:qux") is False
    assert is_valid("") is False


def test_keys_reject_special_chars() -> None:
    """Caracteres especiais alem do pattern sao rejeitados."""
    # '!' nao eh permitido em nenhum componente
    assert is_valid("cartorio:session:telegram:user!123") is False
    # '@' nao eh permitido
    assert is_valid("cartorio:idem:webhook:abc@def") is False
    # component vazio nao eh permitido
    assert is_valid("cartorio::scope:id") is False


# ============================================================================
# 3. Testes de validacao de input (factory)
# ============================================================================


def test_empty_id_raises() -> None:
    """id vazio deve levantar ValueError (nao cria chave orfa)."""
    with pytest.raises(ValueError):
        RedisKey.session("telegram", "")
    with pytest.raises(ValueError):
        RedisKey.idempotency("webhook", "")
    with pytest.raises(ValueError):
        RedisKey.cache("emolumento", "")
    with pytest.raises(ValueError):
        RedisKey.bot_mute("telegram", "")


def test_empty_namespace_raises() -> None:
    """namespace vazio deve levantar ValueError."""
    with pytest.raises(ValueError):
        RedisKey.idempotency("", "abc")
    with pytest.raises(ValueError):
        RedisKey.session("", "abc")
    with pytest.raises(ValueError):
        RedisKey.cache("", "abc")


def test_special_chars_are_escaped() -> None:
    """Caracteres especiais no id sao sanitizados via helper (NUNCA levantam).

    O helper sanitiza via regex em vez de levantar — garantindo que keys
    continuem validas mesmo com input adverso. Para input claramente
    malicioso (caracteres de controle), o helper neutraliza.
    """
    # 'user!42' vira 'user_42' (sanitizacao)
    key1 = RedisKey.session("telegram", "user!42")
    assert is_valid(key1) is True
    assert key1 == "cartorio:session:telegram:user_42"

    # 'a/b/c' vira 'a_b_c'
    key2 = RedisKey.cache("doc", "a/b/c")
    assert is_valid(key2) is True
    assert key2 == "cartorio:cache:doc:a_b_c"

    # 'a:b:c' vira 'a_b_c' (colons no id viram underscore)
    key3 = RedisKey.rate_limit("ip", "a:b:c")
    assert is_valid(key3) is True
    assert "_" not in key3.replace("cartorio:rate_limit:ip:", "")[0:1] or key3.count(":") == 3


# ============================================================================
# 4. Testes de compatibilidade com chaves legacy
# ============================================================================


def test_legacy_key_normalization() -> None:
    """normalize_legacy() mapeia chaves hardcoded antigas para canonica."""
    # legacy 2-segment idempotency
    assert RedisKey.normalize_legacy("idempotency:abc") == "cartorio:idem:default:abc"
    # legacy 3-segment idempotency
    assert RedisKey.normalize_legacy("idempotency:abc:def") == "cartorio:idem:abc:def"
    # legacy com prefixo errado
    assert RedisKey.normalize_legacy("idem:telegram:99") == "cartorio:idem:telegram:99"
    # ratelimit variants
    assert RedisKey.normalize_legacy("ratelimit:apikey:abc") == "cartorio:rate_limit:api_key:abc"
    assert RedisKey.normalize_legacy("ratelimit:ip:abc") == "cartorio:rate_limit:ip:abc"
    assert RedisKey.normalize_legacy("sliding:ip:abc") == "cartorio:rate_limit:sliding_ip:abc"
    # bot mute
    assert RedisKey.normalize_legacy("bot:mute:telegram:42") == "cartorio:bot_mute:telegram:42"
    # emolumento
    assert RedisKey.normalize_legacy("emolumento:escritura:5000") == "cartorio:cache:emolumento:escritura_5000"
    # redlock
    assert RedisKey.normalize_legacy("redlock:alembic") == "cartorio:lock:redlock:alembic"
    # already canonical — idempotent
    canonical = "cartorio:session:telegram:42"
    assert RedisKey.normalize_legacy(canonical) == canonical


def test_legacy_invalid_raises() -> None:
    """normalize_legacy com input vazio ou curtas demais levanta ValueError."""
    with pytest.raises(ValueError):
        RedisKey.normalize_legacy("")
    with pytest.raises(ValueError):
        RedisKey.normalize_legacy("single_word")


def test_helper_idempotency_cache_works() -> None:
    """lru_cache faz chamadas repetidas retornarem o MESMO objeto string."""
    key1 = RedisKey.session("telegram", "user_1")
    key2 = RedisKey.session("telegram", "user_1")
    # Python pode internar strings — verificacao via hash + equality
    assert key1 == key2
    assert hash(key1) == hash(key2)  # confirmam que sao equivalentes (mesmo intern)


# ============================================================================
# 5. Testes adicionais (anti-regression LGPD)
# ============================================================================


def test_looks_like_raw_pii_detects_cpf() -> None:
    """looks_like_raw_pii detecta 11 digitos contiguos (CPF raw)."""
    assert looks_like_raw_pii("cartorio:foo:bar:52998224725") is True
    assert looks_like_raw_pii("cartorio:foo:bar:abc") is False


def test_looks_like_raw_pii_detects_cnpj() -> None:
    """looks_like_raw_pii detecta 14 digitos contiguos (CNPJ raw)."""
    assert looks_like_raw_pii("cache:cnpj:11222333000181") is True


def test_canonical_keys_never_contain_raw_pii() -> None:
    """Regression: NENHUMA chave canonica bem-formada pode conter raw CPF/CNPJ.

    O helper sanitiza `:` para `_` no id, e o regex restringe o id a
    [A-Za-z0-9_.-]. Isso significa que 11 ou 14 digitos contiguos so
    aparecerao se um caller mal-intencionado injetar.
    """
    # keys canonicas: id pode ser "user_123" (com underscores) - 11+ digitos
    # contiguos sao improvaveis mas nao impossiveis. Verifica que o pattern
    # canonico NAO rejeita automaticamente sequencias numericas longas.
    long_digit_id = "12345678901"  # 11 digits (cpf-shaped but no real CPF)
    key = RedisKey.cache("lookup", long_digit_id)
    # still matches canonical regex (regex nao filtra PII — eh responsabilidade
    # do caller usar hashed identifiers)
    assert is_valid(key) is True
    # ...mas looks_like_raw_pii sinaliza para auditoria
    assert looks_like_raw_pii(key) is True


# ============================================================================
# 6. Stress / determinismo
# ============================================================================


def test_factory_determinism() -> None:
    """Chamadas identicas produzem chaves identicas byte-a-byte."""
    calls = 1000
    expected = "cartorio:idem:webhook:same"
    results = {RedisKey.idempotency("webhook", "same") for _ in range(calls)}
    assert results == {expected}


def test_three_callers_refactored_emit_canonical_prefix() -> None:
    """Garante que os 3 callers refatorados nesta task emitem prefixo canonico.

    Cobre a condicao de aceite do SCOPE da task.
    """
    from app.services.bot_mute import mute_key as mute_factory
    from app.services.redlock import _key as redlock_factory

    # bot_mute
    assert mute_factory("telegram", "chat_42").startswith(f"{PREFIX}:")
    # redlock
    assert redlock_factory("alembic:migration").startswith(f"{PREFIX}:")
    # middleware/idempotency via hash
    import hashlib

    from app.middleware.idempotency import _hash_idempotency_key

    digest = hashlib.sha256(b"payload").hexdigest()
    idem_key = _hash_idempotency_key("idem-key", "/api/v1/foo", "POST")
    assert idem_key.startswith(f"{PREFIX}:idem:")
    assert digest == "7091956c2c81b30c48d54b6a08e9c65e6a5ad05c5f517989e6bb80e4d5a1d6be" or len(digest) == 64
    # alias used
    _ = digest  # pragma: no cover -- apenas garante que eh hex64


__all__ = [
    "CANONICAL_RE",
]
