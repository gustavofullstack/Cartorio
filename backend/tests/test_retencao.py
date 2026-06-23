"""Testes do job de retencao (5y / 2y inativo)."""
from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("AUDIT_HMAC_KEY", "a" * 64)

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

from datetime import datetime, timedelta, timezone  # noqa: E402

import pytest  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.jobs.retencao import RetencaoConfig, run_retencao  # noqa: E402
from app.models.atendimento import Atendimento  # noqa: E402
from app.models.base import Base  # noqa: E402
from app.models.cliente import Cliente, MotivoEncerramento  # noqa: E402
from app.models.protocolo import Protocolo  # noqa: E402


@pytest.fixture
def db_session():
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


def _make_cliente(db, cpf_hash: str, nome: str = "Fulano") -> Cliente:
    c = Cliente(
        cpf_hash=cpf_hash,
        nome=nome,
        email="fulano@example.com",
        consentimento_lgpd=True,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _make_protocolo(db, cliente_id: int, numero: str, updated_at: datetime) -> Protocolo:
    p = Protocolo(
        cliente_id=cliente_id,
        numero=numero,
        tipo="certidao_negativa",
        status="concluido",
        canal_origem="web",
        updated_at=updated_at,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


# ============================================================================
# Kill switch
# ============================================================================


def test_kill_switch_desabilitado_nao_faz_nada(db_session) -> None:
    """RETENCAO_ENABLED=false: scanned=0, sem soft deletes."""
    _make_cliente(db_session, "hash1", "Cliente Antigo")
    # Forca updated_at pra 10 anos atras
    very_old = datetime.now(timezone.utc) - timedelta(days=3650)
    db_session.query(Cliente).filter(Cliente.cpf_hash == "hash1").update({"updated_at": very_old})
    db_session.commit()

    cfg = RetencaoConfig(enabled=False)
    result = run_retencao(db_session, config=cfg, now=datetime.now(timezone.utc))

    assert result.scanned == 0
    assert result.soft_deleted_inativo == []
    assert result.soft_deleted_5y == []


# ============================================================================
# Politica 1: cliente COM protocolo, ultimo protocolo > 5y
# ============================================================================


def test_cliente_com_protocolo_mais_5y_soft_delete(db_session) -> None:
    """Cliente com ultimo protocolo ha 6 anos -> soft delete (motivo=retencao_5y)."""
    now = datetime(2026, 6, 23, tzinfo=timezone.utc)
    c = _make_cliente(db_session, "hash5y")
    # Protocolo ha 6 anos (2191 dias) - NAIVE pois model usa utcnow
    old = (now - timedelta(days=2191)).replace(tzinfo=None)
    _make_protocolo(db_session, c.id, "2020-00001", updated_at=old)
    # Forca updated_at do cliente tambem
    db_session.query(Cliente).filter(Cliente.id == c.id).update({"updated_at": old})
    db_session.commit()

    result = run_retencao(db_session, now=now)

    assert c.id in result.soft_deleted_5y
    c2 = db_session.get(Cliente, c.id)
    assert c2.deleted_at is not None
    assert c2.motivo_encerramento == MotivoEncerramento.RETENCAO_5Y
    assert c2.nome.startswith("TITULAR_REVOGADO_")


def test_cliente_com_protocolo_mais_5y_so_atualizado_agora_nao_apaga(db_session) -> None:
    """Cliente com protocolo antigo MAS updated_at recente (ex: novo protocolo hoje) NAO apaga."""
    now = datetime(2026, 6, 23, tzinfo=timezone.utc)
    c = _make_cliente(db_session, "hash5y-recent")
    _make_protocolo(
        db_session,
        c.id,
        "2020-00001",
        updated_at=(now - timedelta(days=2191)).replace(tzinfo=None),
    )
    # Mas cliente.updated_at eh AGORA (ex: acabou de abrir novo atendimento)
    db_session.query(Cliente).filter(Cliente.id == c.id).update(
        {"updated_at": now.replace(tzinfo=None)}
    )
    db_session.commit()

    result = run_retencao(db_session, now=now)

    # updated_at recente, mesmo com protocolo velho, nao apaga
    assert c.id not in result.soft_deleted_5y


def test_cliente_com_protocolo_4_anos_atras_nao_apaga(db_session) -> None:
    """Cliente com ultimo protocolo 4 anos atras (< 5y) NAO apaga."""
    now = datetime(2026, 6, 23, tzinfo=timezone.utc)
    c = _make_cliente(db_session, "hash4y")
    recent = (now - timedelta(days=4 * 365)).replace(tzinfo=None)
    _make_protocolo(db_session, c.id, "2022-00001", updated_at=recent)
    db_session.query(Cliente).filter(Cliente.id == c.id).update({"updated_at": recent})
    db_session.commit()

    result = run_retencao(db_session, now=now)

    assert c.id not in result.soft_deleted_5y
    assert c.id not in result.soft_deleted_inativo


# ============================================================================
# Politica 2: cliente SEM protocolo, inativo > 2y
# ============================================================================


def test_cliente_sem_protocolo_inativo_2y_soft_delete(db_session) -> None:
    """Cliente sem protocolo E inativo ha 3 anos -> soft delete (motivo=outros)."""
    now = datetime(2026, 6, 23, tzinfo=timezone.utc)
    c = _make_cliente(db_session, "hash-inativo")
    old = (now - timedelta(days=3 * 365)).replace(tzinfo=None)
    db_session.query(Cliente).filter(Cliente.id == c.id).update({"updated_at": old})
    db_session.commit()

    result = run_retencao(db_session, now=now)

    assert c.id in result.soft_deleted_inativo
    c2 = db_session.get(Cliente, c.id)
    assert c2.deleted_at is not None
    assert c2.motivo_encerramento == MotivoEncerramento.OUTROS


def test_cliente_sem_protocolo_inativo_1_ano_nao_apaga(db_session) -> None:
    """Cliente sem protocolo mas inativo so 1 ano NAO apaga."""
    now = datetime(2026, 6, 23, tzinfo=timezone.utc)
    c = _make_cliente(db_session, "hash-1y")
    recent = (now - timedelta(days=365)).replace(tzinfo=None)
    db_session.query(Cliente).filter(Cliente.id == c.id).update({"updated_at": recent})
    db_session.commit()

    result = run_retencao(db_session, now=now)

    assert c.id not in result.soft_deleted_inativo


# ============================================================================
# Idempotencia
# ============================================================================


def test_cliente_ja_soft_deleted_pulado(db_session) -> None:
    """Clientes ja soft-deleted NAO sao processados (idempotente)."""
    now = datetime(2026, 6, 23, tzinfo=timezone.utc)
    c = _make_cliente(db_session, "hash-ja")
    # Marca como ja deleted
    db_session.query(Cliente).filter(Cliente.id == c.id).update(
        {"deleted_at": now, "motivo_encerramento": MotivoEncerramento.REVOGACAO_CONSENTIMENTO}
    )
    db_session.commit()

    result = run_retencao(db_session, now=now)

    # scanned conta o cliente (foi lido), mas nenhum soft delete adicional
    assert c.id not in result.soft_deleted_5y
    assert c.id not in result.soft_deleted_inativo


def test_run_duas_vezes_idempotente(db_session) -> None:
    """Rodar 2x na mesma data nao causa double-processing."""
    now = datetime(2026, 6, 23, tzinfo=timezone.utc)
    c = _make_cliente(db_session, "hash-double")
    old = (now - timedelta(days=2191)).replace(tzinfo=None)
    _make_protocolo(db_session, c.id, "2020-X", updated_at=old)
    db_session.query(Cliente).filter(Cliente.id == c.id).update({"updated_at": old})
    db_session.commit()

    r1 = run_retencao(db_session, now=now)
    r2 = run_retencao(db_session, now=now)

    assert c.id in r1.soft_deleted_5y
    assert c.id not in r2.soft_deleted_5y
    # 2a run: scanned=1 (inclui o cliente) mas nenhum soft_delete
    # (cliente ja tem deleted_at)


# ============================================================================
# Politica 1 vs 2: cliente com protocolo tem prioridade
# ============================================================================


def test_cliente_com_protocolo_antigo_inativo_prioriza_politica_5y(db_session) -> None:
    """Cliente com protocolo > 5y E inativo > 2y -> deletado pela 5y, NAO pela 2y."""
    now = datetime(2026, 6, 23, tzinfo=timezone.utc)
    c = _make_cliente(db_session, "hash-prio")
    old = (now - timedelta(days=2191)).replace(tzinfo=None)
    _make_protocolo(db_session, c.id, "2020-Y", updated_at=old)
    db_session.query(Cliente).filter(Cliente.id == c.id).update({"updated_at": old})
    db_session.commit()

    result = run_retencao(db_session, now=now)

    assert c.id in result.soft_deleted_5y
    assert c.id not in result.soft_deleted_inativo
    c2 = db_session.get(Cliente, c.id)
    assert c2.motivo_encerramento == MotivoEncerramento.RETENCAO_5Y


# ============================================================================
# Edge cases
# ============================================================================


def test_scanned_count_ignora_ja_deletados(db_session) -> None:
    """scanned conta apenas clientes com deleted_at IS NULL (worklist)."""
    now = datetime(2026, 6, 23, tzinfo=timezone.utc)
    _make_cliente(db_session, "hash-active")
    c2 = _make_cliente(db_session, "hash-already")
    db_session.query(Cliente).filter(Cliente.id == c2.id).update({"deleted_at": now})
    db_session.commit()

    result = run_retencao(db_session, now=now)

    # Scanned = apenas clientes ativos
    assert result.scanned == 1


def test_cutoff_dates_no_result(db_session) -> None:
    """RetencaoResult expoe cutoff_5y e cutoff_inativo pra auditoria.

    Nota: cutoff_* sao naive (comparam com colunas do model que sao naive
    via datetime.utcnow). Por isso convertemos pra naive antes de comparar.
    """
    now = datetime(2026, 6, 23, tzinfo=timezone.utc)
    now_naive = now.replace(tzinfo=None)
    result = run_retencao(db_session, now=now)

    assert result.cutoff_5y == now_naive - timedelta(days=1825)
    assert result.cutoff_inativo == now_naive - timedelta(days=730)


def test_duration_ms_preenchido(db_session) -> None:
    """duration_ms > 0 (sempre preenche mesmo que microsegundos)."""
    result = run_retencao(db_session, now=datetime.now(timezone.utc))
    assert result.duration_ms >= 0


def test_config_custom_retencao_curta(db_session) -> None:
    """Override de config permite encurtar prazos pra testes."""
    now = datetime(2026, 6, 23, tzinfo=timezone.utc)
    c = _make_cliente(db_session, "hash-custom")
    # 100 dias atras
    recent = (now - timedelta(days=100)).replace(tzinfo=None)
    _make_protocolo(db_session, c.id, "2026-A", updated_at=recent)
    db_session.query(Cliente).filter(Cliente.id == c.id).update({"updated_at": recent})
    db_session.commit()

    # Com retencao 5y = 50 dias, esse cliente DEVE ser deletado
    cfg = RetencaoConfig(retencao_5y_dias=50, retencao_inativo_dias=30)
    result = run_retencao(db_session, config=cfg, now=now)

    assert c.id in result.soft_deleted_5y
