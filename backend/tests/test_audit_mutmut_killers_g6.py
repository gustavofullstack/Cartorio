"""Mutation killers para app/services/audit.py (G6.A.T1.1).

Baseline mutmut 2026-07-16: audit.py tem 42/42 mutantes sobreviventes.
Este arquivo adiciona testes que validam o formato EXATO do canonical_block
e da chain, matando mutantes tipo:
- _canonical_block: trocar "0" * 64 por "0" * 63 / 65
- _canonical_block: sort_keys=True -> False
- _canonical_block: separators=(",", ":") -> (", ", ": ")
- _compute_hash: hashlib.sha256 -> hashlib.md5 / sha1
- _compute_hmac: hmac.new(...).hexdigest() -> sem hexdigest()
- log: actor_id/action fora do HMAC string

Refs: docs/MUTMUT_REPORT_G6.md (2026-07-16 baseline).
Modified by Gustavo Almeida + Pietra orquestrador.
"""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("AUDIT_HMAC_KEY", "a" * 64)

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

import hashlib  # noqa: E402
import hmac as hmac_mod  # noqa: E402
import re  # noqa: E402

import pytest  # noqa: E402

from app.services.audit import AuditService  # noqa: E402


# ============================================================================
# Canonical block format (mata _canonical_block mutantes)
# ============================================================================


def test_canonical_block_format_exato() -> None:
    """O canonical_block DEVE ter formato exato:
    - sort_keys=True (chaves ordenadas alfabeticamente)
    - separators=(',', ':') (sem espaços)
    - prev_hash quando None -> "0" * 64 (zero-fill 64 chars)
    - timestamp + payload como strings literais (default=str)
    """
    canonical = AuditService._canonical_block(
        prev_hash=None,
        payload={"actor_id": "u1", "action": "login"},
        timestamp="2026-07-16T10:00:00.000000",
    )

    # 1) Comeca com '{"payload":...}' porque sort_keys=True + payload vem antes de prev_hash/timestamp
    # Ordem alfabetica: payload, prev_hash, timestamp
    assert canonical.startswith('{"payload":'), f"sort_keys=True esperado. Got: {canonical[:80]}"
    # 2) Sem espacos entre virgulas (separators=(',', ':'))
    assert ", " not in canonical, f"sem espacos entre virgulas. Got: {canonical}"
    assert ": " not in canonical, f"sem espacos apos dois-pontos. Got: {canonical}"
    # 3) prev_hash quando None -> 64 zeros
    assert (
        '"prev_hash":"0000000000000000000000000000000000000000000000000000000000000000"'
        in canonical
    )
    # 4) timestamp eh string literal
    assert '"timestamp":"2026-07-16T10:00:00.000000"' in canonical


def test_canonical_block_prev_hash_quando_nao_none() -> None:
    """Quando prev_hash nao eh None, DEVE usar exatamente o valor passado (NAO zeros)."""
    prev = "a" * 64
    canonical = AuditService._canonical_block(
        prev_hash=prev,
        payload={"x": 1},
        timestamp="2026-07-16T11:00:00.000000",
    )
    assert '"prev_hash":"' + prev + '"' in canonical
    assert '"prev_hash":"0000' not in canonical


def test_canonical_block_payload_com_default_str() -> None:
    """Payload com tipos nao-JSON (datetime, Decimal) DEVE ser serializado via default=str."""
    from datetime import datetime
    from decimal import Decimal

    canonical = AuditService._canonical_block(
        prev_hash=None,
        payload={"ts": datetime(2026, 7, 16, 10, 0, 0), "valor": Decimal("100.50")},
        timestamp="2026-07-16T12:00:00.000000",
    )
    # default=str converte datetime -> '2026-07-16 10:00:00' (sem T nem tz)
    assert '"ts":"2026-07-16 10:00:00"' in canonical
    assert '"valor":"100.50"' in canonical


# ============================================================================
# Compute hash (mata _compute_hash mutantes)
# ============================================================================


def test_compute_hash_usa_sha256_nao_md5() -> None:
    """Hash DEVE ser SHA256 (64 chars hex). MD5 = 32 chars, SHA1 = 40 chars."""
    h = AuditService._compute_hash(None, {"a": 1}, "2026-07-16T10:00:00.000000")
    assert len(h) == 64, f"SHA256 hex = 64 chars. Got {len(h)}: {h!r}"
    assert re.fullmatch(r"[0-9a-f]{64}", h), f"hex lowercase 64 chars. Got: {h!r}"


def test_compute_hash_deterministic() -> None:
    """Mesmo input -> mesmo hash. Mutante que adiciona random/UUID seria detectado."""
    payload = {"k": "v"}
    ts = "2026-07-16T13:00:00.000000"
    h1 = AuditService._compute_hash(None, payload, ts)
    h2 = AuditService._compute_hash(None, payload, ts)
    assert h1 == h2
    # Diferente payload -> hash diferente
    h3 = AuditService._compute_hash(None, {"k": "w"}, ts)
    assert h1 != h3


def test_compute_hash_prev_hash_altera_resultado() -> None:
    """prev_hash diferente DEVE produzir hash diferente (chain link)."""
    payload = {"k": "v"}
    ts = "2026-07-16T13:00:00.000000"
    h_no_prev = AuditService._compute_hash(None, payload, ts)
    h_with_prev = AuditService._compute_hash("a" * 64, payload, ts)
    assert h_no_prev != h_with_prev, "prev_hash DEVE influenciar hash"


# ============================================================================
# Compute HMAC (mata _compute_hmac mutantes)
# ============================================================================


def test_compute_hmac_usa_chave_das_settings() -> None:
    """HMAC DEVE usar settings.audit_hmac_key (NAO string vazia / chave hardcoded)."""
    msg = "abc123"
    _kid, sig = AuditService._compute_hmac(msg)
    assert sig != msg, "HMAC nao pode ser identidade"
    assert len(sig) == 64, "SHA256 hex = 64 chars"
    # Recalcular manualmente para garantir que usa a mesma chave
    expected = hmac_mod.new(
        settings.audit_hmac_key.encode("utf-8"),
        msg.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    assert sig == expected


def test_compute_hmac_mensagens_diferentes_produzem_sig_diferente() -> None:
    """Mensagens diferentes -> HMACs diferentes."""
    _k1, sig1 = AuditService._compute_hmac("message-1")
    _k2, sig2 = AuditService._compute_hmac("message-2")
    assert sig1 != sig2


# ============================================================================
# Chain integrity (mata verify_chain mutantes)
# ============================================================================


@pytest.fixture
def db_session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from app.models.base import Base

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def test_verify_chain_detecta_hash_tampered(db_session) -> None:
    """verify_chain DEVE detectar tamper no campo hash de QUALQUER entrada."""
    from app.services.audit import AuditService

    e1 = AuditService.log(db_session, actor_id="u1", action="login", resource="r", payload={"x": 1})

    # Tamper no e1.hash
    e1.hash = "f" * 64
    db_session.commit()

    chain_ok, last_valid = AuditService.verify_chain(db_session)
    assert chain_ok is False, "verify_chain DEVE detectar tamper no hash"
    assert last_valid < 2


def test_verify_chain_detecta_payload_tampered(db_session) -> None:
    """verify_chain DEVE detectar tamper no payload (mata mutantes que ignoram payload)."""
    from app.services.audit import AuditService

    AuditService.log(db_session, actor_id="u1", action="login", resource="r", payload={"x": 1})

    # Tamper direto no payload
    entry = db_session.query(
        __import__("app.models.audit_log", fromlist=["AuditLog"]).AuditLog
    ).first()
    entry.payload = {"x": 999}  # mudou
    db_session.commit()

    chain_ok, _last_valid = AuditService.verify_chain(db_session)
    assert chain_ok is False, "verify_chain DEVE detectar tamper no payload"


def test_verify_chain_chain_intacta_2_entradas(db_session) -> None:
    """verify_chain DEVE retornar chain_ok=True para 2 entradas legitimas."""
    from app.services.audit import AuditService

    AuditService.log(db_session, actor_id="u1", action="login", resource="r", payload={"x": 1})
    AuditService.log(db_session, actor_id="u2", action="logout", resource="r", payload={"x": 2})

    chain_ok, last_valid = AuditService.verify_chain(db_session)
    assert chain_ok is True
    assert last_valid == 2


def test_log_chain_increments_prev_hash(db_session) -> None:
    """Cada log DEVE usar o hash da entrada anterior como prev_hash (chain link)."""
    from app.services.audit import AuditService

    e1 = AuditService.log(db_session, actor_id="u1", action="a", resource="r", payload={})
    e2 = AuditService.log(db_session, actor_id="u2", action="b", resource="r", payload={})
    e3 = AuditService.log(db_session, actor_id="u3", action="c", resource="r", payload={})

    # e1 deve ter prev_hash=None
    assert e1.prev_hash is None
    # e2 deve ter prev_hash == e1.hash
    assert e2.prev_hash == e1.hash, f"e2.prev_hash={e2.prev_hash} != e1.hash={e1.hash}"
    # e3 deve ter prev_hash == e2.hash
    assert e3.prev_hash == e2.hash, f"e3.prev_hash={e3.prev_hash} != e2.hash={e2.hash}"


def test_log_hmac_contem_actor_e_action(db_session) -> None:
    """HMAC DEVE incluir actor_id e action (mata mutante que remove campos do HMAC string)."""
    from app.services.audit import AuditService

    e = AuditService.log(
        db_session,
        actor_id="u-critico-123",
        action="acao-especial-xyz",
        resource="r",
        payload={},
    )
    # Recalcular HMAC com a string canônica
    _kid, expected = AuditService._compute_hmac(
        f"{e.hash}:{e.timestamp.replace(tzinfo=None).isoformat()}:u-critico-123:acao-especial-xyz"
    )
    assert e.hmac_signature == expected, (
        f"HMAC deve incluir actor_id/action. Got {e.hmac_signature[:16]}... "
        f"expected {expected[:16]}..."
    )


def test_log_ip_truncated_automatico_para_ipv4(db_session) -> None:
    """log DEVE gerar ip_truncated automaticamente (IPv4 /24). Mata mutante que remove truncate_ip()."""
    from app.services.audit import AuditService

    e = AuditService.log(
        db_session,
        actor_id="u1",
        action="login",
        resource="r",
        payload={},
        ip="192.168.1.42",
    )
    assert e.ip == "192.168.1.42"  # IP completo preservado
    assert e.ip_truncated == "192.168.1.0/24", f"ip_truncated deve ser /24. Got: {e.ip_truncated}"


def test_log_ip_truncated_automatico_para_ipv6(db_session) -> None:
    """log DEVE truncar IPv6 para /32 (LGPD D5)."""
    from app.services.audit import AuditService

    e = AuditService.log(
        db_session,
        actor_id="u1",
        action="login",
        resource="r",
        payload={},
        ip="2001:db8:abcd:0012:3456:7890:1234:5678",
    )
    # IPv6 /32 preserva primeiros 32 bits = primeiros 2 grupos: 2001:db8::
    assert e.ip_truncated is not None
    assert e.ip_truncated.startswith("2001:db8")
    assert e.ip_truncated.endswith("/32")


def test_log_actor_type_default_user(db_session) -> None:
    """actor_type default DEVE ser 'user' (mata mutante que troca default)."""
    from app.services.audit import AuditService

    e = AuditService.log(db_session, actor_id="u1", action="a", resource="r", payload={})
    assert e.actor_type == "user"


# Need to import settings for test_compute_hmac_usa_chave_das_settings
from app.config import settings  # noqa: E402
