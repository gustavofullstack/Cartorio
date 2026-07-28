"""A19 SQUAD A: SoftDeleteMixin + BaseRepository + mixins globais.

Cenarios cobertos:
1. SoftDeleteMixin: soft_delete seta timestamp UTC, restore zera
2. soft_delete eh idempotente (segundo call NAO sobrescreve)
3. query_active filtra soft-deletados
4. query_including_deleted retorna TODOS (incluindo soft-deletados)
5. BaseRepository: find_active / find_including_deleted / find_by_id
6. BaseRepository: soft_delete_by_id + restore
7. Drift fix: Atendimento tem coluna deleted_at (model + migration)
8. WebhookEvent tem coluna deleted_at
9. Audit chain NAO eh afetada (audit_log NAO tem deleted_at)
10. LGPD-style: query com mixin preserva hash chain do audit log

Coverage alvo: >= 90% em mixins.py + base.py (repositories).
"""

from __future__ import annotations

import pytest

from app.models.audit_log import AuditLog
from app.models.atendimento import Atendimento
from app.models.base import utc_now_naive
from app.models.cliente import Cliente
from app.models.conversa import Conversa
from app.models.documento import Documento
from app.models.mixins import (
    query_active,
    query_including_deleted,
    select_active,
)
from app.models.protocolo import Protocolo
from app.models.webhook_event import WebhookEvent
from app.repositories import BaseRepository
from app.services.audit import AuditService


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def cliente_ativo(db_session) -> Cliente:
    """Cliente ativo (deleted_at = None) com cpf_hash deterministico."""
    cliente = Cliente(
        cpf_hash="a" * 64,
        nome="Cliente Ativo",
        email="ativo@example.com",
        consentimento_lgpd=True,
    )
    db_session.add(cliente)
    db_session.commit()
    return cliente


@pytest.fixture
def cliente_repo(db_session) -> BaseRepository:
    return BaseRepository(Cliente, db_session)


# ============================================================================
# SoftDeleteMixin — soft_delete + restore + is_deleted
# ============================================================================


class TestSoftDeleteMixinBehavior:
    """Validacao do mixin na sua forma basica."""

    def test_obj_ativo_is_deleted_false(self, db_session, cliente_ativo):
        """Cliente ativo -> is_deleted == False, deleted_at is None."""
        assert cliente_ativo.is_deleted is False
        assert cliente_ativo.deleted_at is None

    def test_soft_delete_seta_timestamp(self, db_session, cliente_ativo):
        """soft_delete() seta deleted_at para um datetime UTC."""
        antes = utc_now_naive()
        cliente_ativo.soft_delete()
        db_session.commit()
        db_session.refresh(cliente_ativo)

        assert cliente_ativo.deleted_at is not None
        assert cliente_ativo.is_deleted is True
        # Janela de 5s para absorver jitter de clock
        delta = (cliente_ativo.deleted_at - antes).total_seconds()
        assert -1 <= delta <= 6

    def test_soft_delete_idempotente(self, db_session, cliente_ativo):
        """Segundo soft_delete NAO sobrescreve o primeiro timestamp."""
        cliente_ativo.soft_delete()
        primeiro = cliente_ativo.deleted_at
        db_session.commit()

        # Espera 50ms
        import time

        time.sleep(0.05)

        cliente_ativo.soft_delete()
        db_session.commit()
        db_session.refresh(cliente_ativo)

        assert cliente_ativo.deleted_at == primeiro

    def test_restore_zera_timestamp(self, db_session, cliente_ativo):
        """restore() volta deleted_at para None."""
        cliente_ativo.soft_delete()
        db_session.commit()
        assert cliente_ativo.deleted_at is not None

        cliente_ativo.restore()
        db_session.commit()
        db_session.refresh(cliente_ativo)
        assert cliente_ativo.deleted_at is None
        assert cliente_ativo.is_deleted is False


# ============================================================================
# Query helpers — query_active / query_including_deleted / select_active
# ============================================================================


class TestQueryHelpers:
    """Helpers de query filtram soft-deletados por default."""

    def test_query_active_exclui_soft_deletado(self, db_session, cliente_ativo):
        """query_active retorna SOMENTE ativos."""
        # Soft deleta o cliente
        cliente_ativo.soft_delete()
        db_session.commit()

        ativos = query_active(db_session, Cliente).all()
        assert ativos == []  # soft-deletado filtrado

    def test_query_active_retorna_ativo(self, db_session, cliente_ativo):
        """Cliente sem soft delete -> retorna na lista."""
        ativos = query_active(db_session, Cliente).all()
        assert cliente_ativo in ativos

    def test_query_including_deleted_retorna_todos(self, db_session, cliente_ativo):
        """query_including_deleted ignora filtro (uso admin)."""
        cliente_ativo.soft_delete()
        db_session.commit()

        todos = query_including_deleted(db_session, Cliente).all()
        assert len(todos) == 1
        assert todos[0].deleted_at is not None

    def test_select_active_constroi_select(self, db_session, cliente_ativo):
        """select_active gera Select filtrado (SQLAlchemy 2.0 style)."""
        stmt = select_active(Cliente)
        # Compila e executa
        resultado = db_session.execute(stmt).scalars().all()
        assert cliente_ativo in resultado


# ============================================================================
# BaseRepository — operacoes read/write
# ============================================================================


class TestBaseRepository:
    """Testa o BaseRepository generico."""

    def test_find_active_exclui_soft_deletado(self, db_session, cliente_ativo, cliente_repo):
        """Repo.find_active() aplica filtro padrao."""
        cliente_ativo.soft_delete()
        db_session.commit()

        ativos = cliente_repo.find_active().all()
        assert ativos == []

    def test_find_including_deleted_retorna_todos(self, db_session, cliente_ativo, cliente_repo):
        """Repo.find_including_deleted() bypass o filtro."""
        cliente_ativo.soft_delete()
        db_session.commit()

        todos = cliente_repo.find_including_deleted().all()
        assert len(todos) == 1

    def test_find_by_id_padrao_exclui_soft_deletado(self, db_session, cliente_ativo, cliente_repo):
        """find_by_id sem flag -> soft-deletado retorna None."""
        cliente_ativo.soft_delete()
        db_session.commit()

        assert cliente_repo.find_by_id(cliente_ativo.id) is None

    def test_find_by_id_com_flag_retorna_soft_deletado(
        self, db_session, cliente_ativo, cliente_repo
    ):
        """find_by_id(include_deleted=True) bypass."""
        cliente_ativo.soft_delete()
        db_session.commit()

        obj = cliente_repo.find_by_id(cliente_ativo.id, include_deleted=True)
        assert obj is not None
        assert obj.deleted_at is not None

    def test_find_by_id_inexistente(self, db_session, cliente_repo):
        """ID inexistente -> None."""
        assert cliente_repo.find_by_id(999999) is None

    def test_soft_delete_by_id(self, db_session, cliente_ativo, cliente_repo):
        """soft_delete_by_id() Convenience method."""
        result = cliente_repo.soft_delete_by_id(cliente_ativo.id)
        db_session.commit()

        assert result is not None
        assert result.deleted_at is not None
        assert result.is_deleted is True

    def test_soft_delete_by_id_inexistente(self, db_session, cliente_repo):
        """ID inexistente -> None (nao raise)."""
        assert cliente_repo.soft_delete_by_id(999999) is None

    def test_restore_via_repo(self, db_session, cliente_ativo, cliente_repo):
        """Repo.restore() zera deleted_at."""
        cliente_ativo.soft_delete()
        db_session.commit()
        assert cliente_ativo.deleted_at is not None

        cliente_repo.restore(cliente_ativo)
        db_session.commit()
        assert cliente_ativo.deleted_at is None

    def test_find_deleted_retorna_apenas_soft(self, db_session, cliente_ativo, cliente_repo):
        """find_deleted lista apenas os marcados."""
        cliente_ativo.soft_delete()
        db_session.commit()

        deletados = cliente_repo.find_deleted().all()
        assert len(deletados) == 1
        assert deletados[0].id == cliente_ativo.id

    def test_count_active_exclui_soft(self, db_session, cliente_ativo, cliente_repo):
        """count_active considera so ativos."""
        assert cliente_repo.count_active() == 1
        cliente_ativo.soft_delete()
        db_session.commit()
        assert cliente_repo.count_active() == 0


# ============================================================================
# Cobertura: todas as tabelas de dominio tem deleted_at (drift catch)
# ============================================================================


class TestDomainModelsHaveDeletedAt:
    """Garante que todas as tabelas de dominio tem a coluna."""

    def test_cliente_tem_deleted_at(self):
        assert hasattr(Cliente, "deleted_at")
        col = Cliente.__table__.columns["deleted_at"]
        assert col.nullable is True

    def test_protocolo_tem_deleted_at(self):
        assert hasattr(Protocolo, "deleted_at")
        col = Protocolo.__table__.columns["deleted_at"]
        assert col.nullable is True

    def test_documento_tem_deleted_at(self):
        assert hasattr(Documento, "deleted_at")
        col = Documento.__table__.columns["deleted_at"]
        assert col.nullable is True

    def test_conversa_tem_deleted_at(self):
        assert hasattr(Conversa, "deleted_at")
        col = Conversa.__table__.columns["deleted_at"]
        assert col.nullable is True

    def test_atendimento_tem_deleted_at_drift_fix(self):
        """Drift fix 2026-07-02: Atendimento model agora reflete DB."""
        assert hasattr(Atendimento, "deleted_at")
        col = Atendimento.__table__.columns["deleted_at"]
        assert col.nullable is True

    def test_webhook_event_tem_deleted_at(self):
        """WebhookEvent agora tambem tem coluna (gap A19)."""
        assert hasattr(WebhookEvent, "deleted_at")
        col = WebhookEvent.__table__.columns["deleted_at"]
        assert col.nullable is True


# ============================================================================
# Tabelas do sistema NAO devem ter deleted_at
# ============================================================================


class TestSystemModelsSemDeletedAt:
    """audit_log + outbox_message NAO devem ter coluna (por design)."""

    def test_audit_log_nao_tem_deleted_at(self):
        """AuditLog NAO tem coluna soft delete (integridade hash chain)."""
        assert not hasattr(AuditLog, "deleted_at")

    def test_outbox_message_nao_tem_deleted_at(self):
        """OutboxMessage NAO tem coluna (DLQ semantics)."""
        # Lazy import — OutboxMessage has UUID/JSON types that may
        # complicate SQLite test setup
        from app.models.outbox_message import OutboxMessage

        assert not hasattr(OutboxMessage, "deleted_at")


# ============================================================================
# LGPD integration: audit chain NAO afetada por soft delete
# ============================================================================


class TestAuditChainIntegrityAfterSoftDelete:
    """Cenario 5 do briefing: audit chain continua integra apos soft delete."""

    def test_audit_chain_intact_apos_soft_delete_cliente(self, db_session, cliente_ativo):
        """Soft delete nao quebra a hash chain do audit."""
        # Cria 3 entradas
        for i in range(3):
            AuditService.log(
                db_session,
                actor_id="u",
                action="test",
                resource=f"r:{i}",
                payload={"i": i},
            )
        db_session.commit()

        # Soft delete nao mexe em audit_log
        cliente_ativo.soft_delete()
        db_session.commit()

        # Chain deve continuar integra
        ok, count = AuditService.verify_chain(db_session)
        assert ok is True
        assert count == 3

    def test_audit_log_nunca_aparece_em_query_active(self, db_session):
        """AuditLog NAO tem SoftDeleteMixin, mas query_active nao quebra
        se chamado por engano — eh um mixin opcional."""
        # Registra uma entrada
        AuditService.log(
            db_session,
            actor_id="u",
            action="x",
            resource="r",
            payload={"x": 1},
        )
        db_session.commit()

        # AuditLog nao eh SoftDeleteMixin, entao query_active quebra
        # (intencional — callaria problema se aplicado)
        with pytest.raises((AttributeError, KeyError)):
            query_active(db_session, AuditLog).all()


# ============================================================================
# SoftDeleteMixin pode ser reusado em qualquer model
# ============================================================================


class TestSoftDeleteMixinUsabilidade:
    """Mixin eh generico — pode ser aplicado em qualquer tabela."""

    def test_atendimento_suporta_soft_delete(self, db_session, cliente_ativo):
        """Atendimento (drift fix) aceita soft_delete via mixin field."""
        # Cria atendimento simples
        at = Atendimento(
            cliente_id=cliente_ativo.id,
            canal="whatsapp",
            external_id="5534999999999",
            tipo="duvida",
        )
        db_session.add(at)
        db_session.commit()

        # Soft delete
        at.soft_delete()
        db_session.commit()

        # Re-query e verifica
        reloaded = db_session.get(Atendimento, at.id)
        assert reloaded is not None
        assert reloaded.deleted_at is not None

    def test_webhook_event_suporta_soft_delete(self, db_session):
        """WebhookEvent (nova coluna) aceita soft_delete via mixin field."""
        we = WebhookEvent(
            source="evolution",
            event_id="msg-001",
            payload_hash="a" * 64,
        )
        db_session.add(we)
        db_session.commit()

        we.soft_delete()
        db_session.commit()

        reloaded = db_session.get(WebhookEvent, we.id)
        assert reloaded is not None
        assert reloaded.deleted_at is not None
        assert reloaded.is_deleted is True
