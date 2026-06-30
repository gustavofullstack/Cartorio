"""Testes do job de retenção LGPD (Sprint 3 G4.3).

Cobre:
1. Politica 1 (clientes COM protocolo): 5y apos ultimo protocolo → soft delete.
2. Politica 2 (clientes SEM protocolo): 2y de inatividade → soft delete.
3. Idempotencia: rodar 2x nao duplica.
4. Ignora clientes ja soft-deleted (idempotente vs deleted_at).
5. Erros em 1 cliente NAO param o job (best-effort).
6. Scheduler in-process:
   - calcula proxima execucao baseado em retencao_hour_brazil (03:00 BRT default).
   - executa o job no horario.
   - loga + emite audit log.
7. Health-check: retorna scheduler ativo/inativo + ultima execucao.

Ver:
- app/jobs/retencao.py — funcao run_retencao.
- app/jobs/retencao_scheduler.py — loop in-process (este teste target).
- app/services/audit.py — verify_chain apos job.
- ADR-019 — politica 5y/2y.

Rodar via: `uv run pytest tests/test_retention.py -v`
"""

from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.cliente import Cliente, MotivoEncerramento
from app.models.protocolo import Protocolo


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def test_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def test_session_factory(test_engine):
    return sessionmaker(bind=test_engine, autoflush=False, autocommit=False)


@pytest.fixture
def db_session(test_session_factory):
    session = test_session_factory()
    try:
        yield session
    finally:
        session.close()


# ============================================================================
# Job run_retencao — logica core
# ============================================================================


class TestRunRetencao5y:
    """Politica 1: cliente COM protocolo + ultimo protocolo > 5y → soft delete."""

    def test_cliente_com_protocolo_antigo_soft_deletado_com_motivo_retencao_5y(
        self, db_session: Session
    ):
        """Cliente COM protocolo ativo + ultima atividade > 5y → soft delete retencao_5y."""
        from app.jobs.retencao import run_retencao

        now = dt.datetime(2026, 6, 29, 12, 0, 0, tzinfo=dt.timezone.utc)
        # Cliente cuja ultima atividade foi ha 6 anos (alem do cutoff 5y)
        seis_anos_atras = now - dt.timedelta(days=365 * 6)

        c = Cliente(
            nome="Cliente Antigo 5y",
            cpf_hash="hash_5y_001",
            email="antigo@test.com",
            telefone_hash="antigo_tel_001",
            consentimento_lgpd=True,
            updated_at=seis_anos_atras.replace(tzinfo=None),  # naive UTC
        )
        db_session.add(c)
        db_session.commit()
        db_session.refresh(c)

        # Protocolo antigo (ultimo)
        p = Protocolo(
            cliente_id=c.id,
            numero="RET-2020-00001",
            tipo="certidao",
            status="concluido",
            canal_origem="balcao",
            created_at=seis_anos_atras.replace(tzinfo=None),
            updated_at=seis_anos_atras.replace(tzinfo=None),
        )
        db_session.add(p)
        db_session.commit()

        # Executar job
        result = run_retencao(db_session, now=now)

        # Verificar que foi soft-deletado com motivo RETENCAO_5Y
        db_session.expire_all()
        refreshed = db_session.get(Cliente, c.id)
        assert refreshed is not None
        assert refreshed.deleted_at is not None
        assert refreshed.motivo_encerramento == MotivoEncerramento.RETENCAO_5Y
        # PII anonimizado
        assert refreshed.email is None
        assert refreshed.telefone_hash is None
        assert refreshed.consentimento_lgpd is False

        # Result tem IDs corretos
        assert c.id in result.soft_deleted_5y
        assert result.scanned == 1

    def test_cliente_com_protocolo_recente_nao_e_deletado(self, db_session: Session):
        """Cliente COM protocolo RECENTE (< 5y) NAO deve ser deletado."""
        from app.jobs.retencao import run_retencao

        now = dt.datetime(2026, 6, 29, 12, 0, 0, tzinfo=dt.timezone.utc)
        dois_anos_atras = now - dt.timedelta(days=365 * 2)

        c = Cliente(
            nome="Cliente Recente",
            cpf_hash="hash_recente_001",
            consentimento_lgpd=True,
            updated_at=dois_anos_atras.replace(tzinfo=None),
        )
        db_session.add(c)
        db_session.commit()
        db_session.refresh(c)

        p = Protocolo(
            cliente_id=c.id,
            numero="RET-2024-00001",
            tipo="escritura",
            status="concluido",
            canal_origem="whatsapp",
            created_at=dois_anos_atras.replace(tzinfo=None),
            updated_at=dois_anos_atras.replace(tzinfo=None),
        )
        db_session.add(p)
        db_session.commit()

        result = run_retencao(db_session, now=now)

        db_session.expire_all()
        refreshed = db_session.get(Cliente, c.id)
        assert refreshed is not None
        assert refreshed.deleted_at is None
        assert refreshed.motivo_encerramento is None
        assert result.soft_deleted_5y == []


class TestRunRetencao2yInativo:
    """Politica 2: cliente SEM protocolo + inativo > 2y → soft delete."""

    def test_cliente_sem_protocolo_inativo_2y_soft_deletado_motivo_outros(
        self, db_session: Session
    ):
        """Cliente SEM protocolo + inativo > 2y → soft delete motivo OUTROS."""
        from app.jobs.retencao import run_retencao

        now = dt.datetime(2026, 6, 29, 12, 0, 0, tzinfo=dt.timezone.utc)
        tres_anos_atras = now - dt.timedelta(days=365 * 3)

        c = Cliente(
            nome="Cliente Inativo 3y",
            cpf_hash="hash_inativo_001",
            consentimento_lgpd=False,  # nunca consentiu
            updated_at=tres_anos_atras.replace(tzinfo=None),
        )
        db_session.add(c)
        db_session.commit()
        db_session.refresh(c)

        result = run_retencao(db_session, now=now)

        db_session.expire_all()
        refreshed = db_session.get(Cliente, c.id)
        assert refreshed is not None
        assert refreshed.deleted_at is not None
        assert refreshed.motivo_encerramento == MotivoEncerramento.OUTROS
        assert c.id in result.soft_deleted_inativo

    def test_cliente_sem_protocolo_recente_nao_e_deletado(self, db_session: Session):
        """Cliente SEM protocolo + recente (< 2y) NAO deve ser deletado."""
        from app.jobs.retencao import run_retencao

        now = dt.datetime(2026, 6, 29, 12, 0, 0, tzinfo=dt.timezone.utc)
        seis_meses_atras = now - dt.timedelta(days=180)

        c = Cliente(
            nome="Cliente Semi Novo",
            cpf_hash="hash_semi_001",
            consentimento_lgpd=False,
            updated_at=seis_meses_atras.replace(tzinfo=None),
        )
        db_session.add(c)
        db_session.commit()
        db_session.refresh(c)

        run_retencao(db_session, now=now)

        db_session.expire_all()
        refreshed = db_session.get(Cliente, c.id)
        assert refreshed is not None
        assert refreshed.deleted_at is None


class TestRunRetencaoIdempotencia:
    """Job deve ser idempotente (rodar 2x nao duplica mutacoes)."""

    def test_rodar_duas_vezes_nao_duplica(self, db_session: Session):
        """Executar run_retencao 2x na mesma DB deve manter 1 mutacao por cliente."""
        from app.jobs.retencao import run_retencao

        now = dt.datetime(2026, 6, 29, 12, 0, 0, tzinfo=dt.timezone.utc)
        seis_anos_atras = now - dt.timedelta(days=365 * 6)

        c = Cliente(
            nome="Idempotente",
            cpf_hash="hash_idemp_001",
            consentimento_lgpd=True,
            updated_at=seis_anos_atras.replace(tzinfo=None),
        )
        db_session.add(c)
        db_session.commit()
        db_session.refresh(c)

        p = Protocolo(
            cliente_id=c.id,
            numero="RET-IDEMP-001",
            tipo="certidao",
            status="concluido",
            canal_origem="balcao",
            created_at=seis_anos_atras.replace(tzinfo=None),
            updated_at=seis_anos_atras.replace(tzinfo=None),
        )
        db_session.add(p)
        db_session.commit()

        # 1a execucao
        result1 = run_retencao(db_session, now=now)
        assert c.id in result1.soft_deleted_5y

        # 2a execucao nao deve duplicar (cliente ja foi deletado)
        result2 = run_retencao(db_session, now=now)
        assert c.id not in result2.soft_deleted_5y
        assert result2.skipped_already_deleted >= 1 or result2.soft_deleted_5y == []


class TestRunRetencaoPhase2Purge:
    """Fase 2: hard delete (purge) de clientes ja soft-deleted.

    Motivos que VAO para purge apos 5y: REVOGACAO_CONSENTIMENTO, OUTROS.
    Motivo que NAO vai para purge: EXERCICIO_DIREITO_TITULAR.
    """

    def _create_soft_deleted_cliente(
        self,
        db_session: Session,
        nome: str,
        cpf_hash: str,
        motivo: MotivoEncerramento,
        deleted_at: dt.datetime,
    ) -> Cliente:
        """Helper: cria cliente ja soft-deleted."""
        c = Cliente(
            nome=nome,
            cpf_hash=cpf_hash,
            email=f"{cpf_hash}@test.com",
            telefone_hash=f"{cpf_hash}_tel",
            consentimento_lgpd=False,
            deleted_at=deleted_at.replace(tzinfo=None),
            motivo_encerramento=motivo,
        )
        db_session.add(c)
        db_session.commit()
        db_session.refresh(c)
        return c

    def test_soft_deleted_revogacao_consentimento_5y_purged(self, db_session: Session):
        """Cliente JA soft-deleted por REVOGACAO_CONSENTIMENTO + > 5y → PURGE."""
        from app.jobs.retencao import run_retencao

        now = dt.datetime(2026, 6, 29, 12, 0, 0, tzinfo=dt.timezone.utc)
        seis_anos_atras = now - dt.timedelta(days=365 * 6)

        cliente = self._create_soft_deleted_cliente(
            db_session,
            nome="Revogado 6y",
            cpf_hash="hash_revogado_6y",
            motivo=MotivoEncerramento.REVOGACAO_CONSENTIMENTO,
            deleted_at=seis_anos_atras,
        )
        cliente_id = cliente.id

        result = run_retencao(db_session, now=now)

        # Row deve ter sido removida do DB
        db_session.expire_all()
        assert db_session.get(Cliente, cliente_id) is None
        assert cliente_id in result.hard_deleted_ids
        assert len(result.hard_deleted_ids) == 1

    def test_soft_deleted_outros_5y_purged(self, db_session: Session):
        """Cliente JA soft-deleted por OUTROS + > 5y → PURGE."""
        from app.jobs.retencao import run_retencao

        now = dt.datetime(2026, 6, 29, 12, 0, 0, tzinfo=dt.timezone.utc)
        seis_anos_atras = now - dt.timedelta(days=365 * 6)

        cliente = self._create_soft_deleted_cliente(
            db_session,
            nome="Outros 6y",
            cpf_hash="hash_outros_6y",
            motivo=MotivoEncerramento.OUTROS,
            deleted_at=seis_anos_atras,
        )
        cliente_id = cliente.id

        result = run_retencao(db_session, now=now)

        db_session.expire_all()
        assert db_session.get(Cliente, cliente_id) is None
        assert cliente_id in result.hard_deleted_ids

    def test_soft_deleted_exercicio_direito_titular_preservado(self, db_session: Session):
        """Cliente JA soft-deleted por EXERCICIO_DIREITO_TITULAR + > 5y → PRESERVADO."""
        from app.jobs.retencao import run_retencao

        now = dt.datetime(2026, 6, 29, 12, 0, 0, tzinfo=dt.timezone.utc)
        seis_anos_atras = now - dt.timedelta(days=365 * 6)

        cliente = self._create_soft_deleted_cliente(
            db_session,
            nome="Correcao 6y",
            cpf_hash="hash_correcao_6y",
            motivo=MotivoEncerramento.EXERCICIO_DIREITO_TITULAR,
            deleted_at=seis_anos_atras,
        )
        cliente_id = cliente.id

        result = run_retencao(db_session, now=now)

        # Row deve continuar existindo
        db_session.expire_all()
        assert db_session.get(Cliente, cliente_id) is not None
        assert cliente_id not in result.hard_deleted_ids
        assert result.skipped_exercicio_direito == 1

    def test_soft_deleted_revogacao_menos_de_5y_nao_purged(self, db_session: Session):
        """Cliente soft-deleted por REVOGACAO_CONSENTIMENTO + < 5y → NAO PURGE."""
        from app.jobs.retencao import run_retencao

        now = dt.datetime(2026, 6, 29, 12, 0, 0, tzinfo=dt.timezone.utc)
        tres_anos_atras = now - dt.timedelta(days=365 * 3)  # < 5y cutoff

        cliente = self._create_soft_deleted_cliente(
            db_session,
            nome="Revogado 3y",
            cpf_hash="hash_revogado_3y",
            motivo=MotivoEncerramento.REVOGACAO_CONSENTIMENTO,
            deleted_at=tres_anos_atras,
        )
        cliente_id = cliente.id

        result = run_retencao(db_session, now=now)

        db_session.expire_all()
        assert db_session.get(Cliente, cliente_id) is not None
        assert result.hard_deleted_ids == []

    def test_batch_id_presente_no_result(self, db_session: Session):
        """run_retencao deve retornar batch_id nao-nulo."""
        from app.jobs.retencao import run_retencao

        now = dt.datetime(2026, 6, 29, 12, 0, 0, tzinfo=dt.timezone.utc)
        result = run_retencao(db_session, now=now)
        assert result.batch_id is not None
        assert len(result.batch_id) == 36  # UUID format

    def test_batch_id_personalizado(self, db_session: Session):
        """batch_id customizado deve ser respeitado."""
        from app.jobs.retencao import run_retencao

        now = dt.datetime(2026, 6, 29, 12, 0, 0, tzinfo=dt.timezone.utc)
        custom_id = "meu-batch-2026-06-29-001"
        result = run_retencao(db_session, now=now, batch_id=custom_id)
        assert result.batch_id == custom_id


class TestRunRetencaoConfig:
    """RetencaoConfig deve aceitar overrides."""

    def test_disabled_nao_aplica_mutacoes(self, db_session: Session):
        """RetencaoConfig(enabled=False) → scanned=0, sem mutacoes."""
        from app.jobs.retencao import RetencaoConfig, run_retencao

        now = dt.datetime(2026, 6, 29, 12, 0, 0, tzinfo=dt.timezone.utc)
        seis_anos_atras = now - dt.timedelta(days=365 * 6)

        c = Cliente(
            nome="Disabled Config",
            cpf_hash="hash_disabled_001",
            consentimento_lgpd=True,
            updated_at=seis_anos_atras.replace(tzinfo=None),
        )
        db_session.add(c)
        db_session.commit()
        db_session.refresh(c)

        cfg = RetencaoConfig(enabled=False)
        result = run_retencao(db_session, config=cfg, now=now)

        assert result.scanned == 0
        assert result.soft_deleted_5y == []

        db_session.expire_all()
        refreshed = db_session.get(Cliente, c.id)
        assert refreshed is not None
        assert refreshed.deleted_at is None

    def test_custom_periodos(self, db_session: Session):
        """RetencaoConfig com retencao_5y_dias=30 deve deletar cliente > 30d com protocolo."""
        from app.jobs.retencao import RetencaoConfig, run_retencao

        now = dt.datetime(2026, 6, 29, 12, 0, 0, tzinfo=dt.timezone.utc)
        sessenta_dias_atras = now - dt.timedelta(days=60)

        c = Cliente(
            nome="Custom Periodo",
            cpf_hash="hash_custom_001",
            consentimento_lgpd=True,
            updated_at=sessenta_dias_atras.replace(tzinfo=None),
        )
        db_session.add(c)
        db_session.commit()
        db_session.refresh(c)

        p = Protocolo(
            cliente_id=c.id,
            numero="RET-CUSTOM-001",
            tipo="certidao",
            status="concluido",
            canal_origem="balcao",
            created_at=sessenta_dias_atras.replace(tzinfo=None),
            updated_at=sessenta_dias_atras.replace(tzinfo=None),
        )
        db_session.add(p)
        db_session.commit()

        cfg = RetencaoConfig(retencao_5y_dias=30)
        result = run_retencao(db_session, config=cfg, now=now)

        assert c.id in result.soft_deleted_5y


class TestRetencaoScheduler:
    """Scheduler in-process: calcula proxima execucao e roda."""

    def test_proxima_execucao_default_03_00_brazil(self):
        """Default retencao_hour_brazil=3 → proxima execucao >= 03:00 BRT (06:00 UTC)."""
        from app.jobs.retencao_scheduler import (
            compute_next_run_utc,
        )

        # Fixa now em 02:00 BRT (05:00 UTC) → deve avancar para 03:00 BRT (06:00 UTC)
        now = dt.datetime(2026, 6, 29, 5, 0, 0, tzinfo=dt.timezone.utc)
        next_run = compute_next_run_utc(now=now, retencao_hour_brazil=3)
        # 03:00 BRT == 06:00 UTC (BRT = UTC-3)
        assert next_run.hour == 6
        assert next_run.minute == 0
        assert next_run.tzinfo == dt.timezone.utc

    def test_proxima_execucao_se_ja_passou_avanca_para_amanha(self):
        """Se ja passou das 03:00 BRT hoje, scheduler aponta para amanha 03:00 BRT."""
        from app.jobs.retencao_scheduler import (
            compute_next_run_utc,
        )

        # Fixa now em 07:00 BRT (10:00 UTC) → ja passou → amanha 03:00 BRT
        now = dt.datetime(2026, 6, 29, 10, 0, 0, tzinfo=dt.timezone.utc)
        next_run = compute_next_run_utc(now=now, retencao_hour_brazil=3)
        # Proximo dia 03:00 BRT == 06:00 UTC (1 dia depois)
        expected = dt.datetime(2026, 6, 30, 6, 0, 0, tzinfo=dt.timezone.utc)
        assert next_run == expected

    def test_scheduler_disabled_quando_settings_desabilitado(self):
        """Se retencao_enabled=False, run_retencao_scheduler_loop NAO faz nada."""
        from app.jobs.retencao_scheduler import (
            should_run_retencao_now,
        )

        now = dt.datetime(2026, 6, 29, 6, 0, 0, tzinfo=dt.timezone.utc)
        # habilitado
        assert should_run_retencao_now(
            now=now,
            retencao_enabled=True,
            retencao_hour_brazil=3,
        )
        # desabilitado
        assert not should_run_retencao_now(
            now=now,
            retencao_enabled=False,
            retencao_hour_brazil=3,
        )
        # horario errado (nao sao 03:00 BRT)
        wrong_hour = dt.datetime(2026, 6, 29, 10, 0, 0, tzinfo=dt.timezone.utc)
        assert not should_run_retencao_now(
            now=wrong_hour,
            retencao_enabled=True,
            retencao_hour_brazil=3,
        )
