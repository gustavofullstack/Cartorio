"""Testes do LGPD Consent Service (D11)."""

from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.cliente import Cliente
from app.services.lgpd_consent import (
    FINALIDADES_OBRIGATORIAS,
    FINALIDADES_OPCIONAIS,
    Finalidade,
    consent_history,
    registrar_consentimento,
    revogar_consentimento,
    verificar_consentimento,
)


@pytest.fixture
def db() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def cliente(db: Session) -> Cliente:
    c = Cliente(
        nome="Gustavo",
        cpf_hash="hash_gustavo",
        email="gustavo@test.com",
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


class TestLGPDConsent:
    """TDD strict - D11 LGPD consent service."""

    def test_finalidades_obrigatorias_definidas(self):
        """Finalidades obrigatorias sao protocolo + emolumento."""
        assert Finalidade.PROTOCOLO_CRIACAO in FINALIDADES_OBRIGATORIAS
        assert Finalidade.EMOLUMENTO_CONSULTA in FINALIDADES_OBRIGATORIAS

    def test_finalidades_opcionais_definidas(self):
        """Finalidades opcionais sao marketing + pesquisa + canais."""
        assert Finalidade.MARKETING in FINALIDADES_OPCIONAIS
        assert Finalidade.PESQUISA_SATISFACAO in FINALIDADES_OPCIONAIS
        assert Finalidade.ATENDIMENTO_WHATSAPP in FINALIDADES_OPCIONAIS
        assert Finalidade.ATENDIMENTO_TELEGRAM in FINALIDADES_OPCIONAIS

    def test_registrar_consentimento_basico(self, db, cliente):
        """Registrar consentimento basico atualiza cliente + gera audit."""
        consent = registrar_consentimento(
            db=db,
            cliente_id=cliente.id,
            finalidades=[Finalidade.ATENDIMENTO_WHATSAPP, Finalidade.MARKETING],
            ip="192.168.1.100",
            canal="whatsapp",
        )

        assert consent.cliente_id == cliente.id
        assert "atendimento_whatsapp" in consent.finalidades_aceitas
        assert "marketing" in consent.finalidades_aceitas
        assert consent.consentido_ip == "192.168.1.100"
        assert consent.consentido_canal == "whatsapp"
        assert consent.revogado_em is None

    def test_registrar_consentimento_marca_cliente(self, db, cliente):
        """Cliente.consentimento_lgpd vira True apos registrar."""
        assert cliente.consentimento_lgpd is False
        registrar_consentimento(
            db=db,
            cliente_id=cliente.id,
            finalidades=[Finalidade.ATENDIMENTO_WHATSAPP],
            ip="10.0.0.1",
            canal="web",
        )
        db.refresh(cliente)
        assert cliente.consentimento_lgpd is True
        assert cliente.consentimento_em is not None
        assert cliente.consentimento_ip == "10.0.0.1"
        assert cliente.consentimento_canal == "web"

    def test_registrar_consentimento_inexistente_levanta(self, db):
        """Cliente inexistente levanta ValueError."""
        with pytest.raises(ValueError, match="nao existe"):
            registrar_consentimento(
                db=db,
                cliente_id=99999,
                finalidades=[Finalidade.ATENDIMENTO_WHATSAPP],
                ip="127.0.0.1",
                canal="web",
            )

    def test_revogar_consentimento_especifico(self, db, cliente):
        """Revogar apenas marketing deixa outras finalidades intactas."""
        registrar_consentimento(
            db=db,
            cliente_id=cliente.id,
            finalidades=[Finalidade.ATENDIMENTO_WHATSAPP, Finalidade.MARKETING],
            ip="192.168.1.100",
            canal="whatsapp",
        )

        result = revogar_consentimento(
            db=db,
            cliente_id=cliente.id,
            finalidades=[Finalidade.MARKETING],
            ip="192.168.1.100",
            canal="web",
        )

        assert "marketing" in result.finalidades_revogadas
        # Finalidades obrigatorias + opcionais nao-revogadas NAO sao marcadas
        # como revogadas (ainda tem consentimento para elas)
        assert "atendimento_whatsapp" not in result.finalidades_revogadas

    def test_revogar_consentimento_total(self, db, cliente):
        """Revogar tudo (None) marca cliente sem consentimento."""
        registrar_consentimento(
            db=db,
            cliente_id=cliente.id,
            finalidades=[Finalidade.ATENDIMENTO_WHATSAPP],
            ip="192.168.1.100",
            canal="whatsapp",
        )

        revogar_consentimento(
            db=db,
            cliente_id=cliente.id,
            finalidades=None,  # revoga TUDO
            ip="192.168.1.100",
            canal="email",
        )

        db.refresh(cliente)
        assert cliente.consentimento_lgpd is False
        assert cliente.consentimento_em is None

    def test_revogar_consentimento_obrigatorias_log_warn(self, db, cliente, caplog):
        """Revogar obrigatorias gera WARNING (LGPD art. 9 - perder servico)."""
        import logging

        registrar_consentimento(
            db=db,
            cliente_id=cliente.id,
            finalidades=[Finalidade.PROTOCOLO_CRIACAO],
            ip="192.168.1.100",
            canal="web",
        )

        with caplog.at_level(logging.WARNING):
            revogar_consentimento(
                db=db,
                cliente_id=cliente.id,
                finalidades=[Finalidade.PROTOCOLO_CRIACAO],
                ip="192.168.1.100",
                canal="web",
            )

        # Log warning emitido
        assert any("obrigatorias" in r.message.lower() for r in caplog.records)

    def test_verificar_consentimento_ativo(self, db, cliente):
        """verificar_consentimento retorna True se ativo."""
        assert verificar_consentimento(db, cliente.id) is False
        registrar_consentimento(
            db=db,
            cliente_id=cliente.id,
            finalidades=[Finalidade.ATENDIMENTO_WHATSAPP],
            ip="192.168.1.100",
            canal="whatsapp",
        )
        assert verificar_consentimento(db, cliente.id) is True

    def test_verificar_consentimento_inexistente(self, db):
        """Cliente inexistente retorna False."""
        assert verificar_consentimento(db, 99999) is False

    def test_verificar_consentimento_soft_deleted(self, db, cliente):
        """Cliente soft-deleted NAO tem consentimento valido."""
        registrar_consentimento(
            db=db,
            cliente_id=cliente.id,
            finalidades=[Finalidade.ATENDIMENTO_WHATSAPP],
            ip="192.168.1.100",
            canal="whatsapp",
        )
        cliente.deleted_at = datetime.now(tz=timezone.utc)
        db.commit()
        assert verificar_consentimento(db, cliente.id) is False

    def test_consent_history_basico(self, db, cliente):
        """Historico retorna eventos de granted + revoked."""
        registrar_consentimento(
            db=db,
            cliente_id=cliente.id,
            finalidades=[Finalidade.ATENDIMENTO_WHATSAPP, Finalidade.MARKETING],
            ip="192.168.1.100",
            canal="whatsapp",
        )
        revogar_consentimento(
            db=db,
            cliente_id=cliente.id,
            finalidades=[Finalidade.MARKETING],
            ip="192.168.1.100",
            canal="web",
        )

        history = consent_history(db, cliente.id)
        assert len(history) == 2
        # Ordem crescente por timestamp
        assert history[0]["action"] == "lgpd.consent.granted"
        assert history[1]["action"] == "lgpd.consent.revoked"
        assert "atendimento_whatsapp" in history[0]["finalidades"]
        assert "marketing" in history[1]["finalidades"]

    def test_consent_history_cliente_sem_eventos(self, db, cliente):
        """Cliente sem eventos retorna lista vazia."""
        history = consent_history(db, cliente.id)
        assert history == []

    def test_consent_history_outros_clientes_isolados(self, db, cliente):
        """Historico NAO mistura eventos de outros clientes."""
        # Cria outro cliente + registra consent
        c2 = Cliente(nome="Maria", cpf_hash="hash_maria", email="m@t.com")
        db.add(c2)
        db.commit()
        db.refresh(c2)

        registrar_consentimento(
            db=db,
            cliente_id=cliente.id,
            finalidades=[Finalidade.ATENDIMENTO_WHATSAPP],
            ip="192.168.1.100",
            canal="whatsapp",
        )
        registrar_consentimento(
            db=db,
            cliente_id=c2.id,
            finalidades=[Finalidade.ATENDIMENTO_TELEGRAM],
            ip="192.168.1.200",
            canal="telegram",
        )

        h1 = consent_history(db, cliente.id)
        h2 = consent_history(db, c2.id)

        assert len(h1) == 1
        assert len(h2) == 1
        assert "whatsapp" in h1[0]["finalidades"][0]
        assert "telegram" in h2[0]["finalidades"][0]
