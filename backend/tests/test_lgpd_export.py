"""Testes do LGPD Data Export Service (D12)."""

from __future__ import annotations

import json
from collections.abc import Generator
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.cliente import Cliente
from app.models.protocolo import Protocolo
from app.services.lgpd_export import (
    ClienteNotFoundError,
    exportar_dados_titular,
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
        nome="Gustavo Almeida",
        cpf_hash="hash_gustavo_123",
        email="gustavo@test.com",
        telefone_hash="hash_tel_456",
        consentimento_lgpd=True,
        consentimento_em=datetime.now(tz=timezone.utc),
        consentimento_ip="192.168.1.100",
        consentimento_canal="whatsapp",
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


class TestLGPDExport:
    """TDD strict - D12 LGPD data export."""

    def test_export_basico(self, db, cliente):
        """Export basico retorna bundle com dados do titular."""
        bundle = exportar_dados_titular(db, cliente_id=cliente.id)
        assert bundle.cliente["id"] == cliente.id
        # LGPD D29: nome mascarado
        assert bundle.cliente["nome"] == "G*** A***"
        # LGPD D29: email mascarado
        assert bundle.cliente["email"] == "g***@com"
        # LGPD-by-design: NAO expoe cpf plaintext, apenas hash
        assert bundle.cliente["cpf_hash"] == "hash_gustavo_123"
        assert "cpf" not in bundle.cliente

    def test_export_inclui_protocolos(self, db, cliente):
        """Export inclui protocolos do titular."""
        for i in range(3):
            db.add(
                Protocolo(
                    numero=f"CART-2026-{i:06d}",
                    cliente_id=cliente.id,
                    status="DRAFT",
                    tipo="certidao_casamento",
                    valor_total=100.0,
                    canal_origem="whatsapp",
                )
            )
        db.commit()

        bundle = exportar_dados_titular(db, cliente_id=cliente.id)
        assert len(bundle.protocolos) == 3
        assert all(p["canal_origem"] == "whatsapp" for p in bundle.protocolos)

    def test_export_inclui_consentimentos(self, db, cliente):
        """Export inclui historico de consentimentos."""
        from app.services.lgpd_consent import Finalidade, registrar_consentimento

        registrar_consentimento(
            db=db,
            cliente_id=cliente.id,
            finalidades=[Finalidade.ATENDIMENTO_WHATSAPP],
            ip="192.168.1.100",
            canal="whatsapp",
        )

        bundle = exportar_dados_titular(db, cliente_id=cliente.id)
        assert len(bundle.consentimentos) == 1
        assert bundle.consentimentos[0]["evento"] == "lgpd.consent.granted"

    def test_export_isola_por_titular(self, db, cliente):
        """Export NAO inclui dados de OUTROS clientes."""
        c2 = Cliente(nome="Maria", cpf_hash="hash_maria", email="m@t.com")
        db.add(c2)
        db.commit()
        db.refresh(c2)
        db.add(
            Protocolo(
                numero="CART-2026-000999",
                cliente_id=c2.id,
                status="DRAFT",
                tipo="procuracao",
                valor_total=200.0,
                canal_origem="telegram",
            )
        )
        db.commit()

        bundle1 = exportar_dados_titular(db, cliente_id=cliente.id)
        bundle2 = exportar_dados_titular(db, cliente_id=c2.id)

        # Cada bundle tem apenas SEUS protocolos
        assert all("procuracao" not in p.get("tipo", "") for p in bundle1.protocolos)
        assert "procuracao" in [p["tipo"] for p in bundle2.protocolos][0]

    def test_export_cliente_inexistente_levanta(self, db):
        """Cliente inexistente levanta ClienteNotFoundError."""
        with pytest.raises(ClienteNotFoundError):
            exportar_dados_titular(db, cliente_id=99999)

    def test_export_hash_sha256(self, db, cliente):
        """export_hash eh SHA256 (64 chars hex)."""
        bundle = exportar_dados_titular(db, cliente_id=cliente.id)
        h = bundle.export_hash
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_export_hash_muda_com_dados(self, db, cliente):
        """Hash muda quando dados do titular mudam."""
        bundle1 = exportar_dados_titular(db, cliente_id=cliente.id)
        # Adiciona 1 protocolo
        db.add(
            Protocolo(
                numero="CART-2026-000777",
                cliente_id=cliente.id,
                status="CONCLUIDO",
                tipo="escritura",
                valor_total=500.0,
                canal_origem="balcao",
            )
        )
        db.commit()
        bundle2 = exportar_dados_titular(db, cliente_id=cliente.id)

        assert bundle1.export_hash != bundle2.export_hash

    def test_export_excluindo_audit(self, db, cliente):
        """incluir_audit=False NAO inclui audit_logs."""
        bundle = exportar_dados_titular(db, cliente_id=cliente.id, incluir_audit=False)
        assert bundle.audit_logs == []

    def test_export_incluindo_audit(self, db, cliente):
        """incluir_audit=True (default) inclui audit_logs."""
        from app.services.audit import AuditService

        AuditService.log(
            db=db,
            actor_id=str(cliente.id),
            actor_type="cliente",
            action="cliente.created",
            resource=f"cliente/{cliente.id}",
            payload={},
        )
        db.commit()

        bundle = exportar_dados_titular(db, cliente_id=cliente.id)
        assert len(bundle.audit_logs) >= 1

    def test_export_to_json_serializavel(self, db, cliente):
        """to_json() retorna JSON valido."""
        bundle = exportar_dados_titular(db, cliente_id=cliente.id)
        json_str = bundle.to_json()
        # Parse OK
        data = json.loads(json_str)
        assert data["cliente"]["id"] == cliente.id
        assert data["export_hash"] == bundle.export_hash

    def test_export_nunca_expoe_cpf_plaintext(self, db, cliente):
        """Bundle NAO contem campo 'cpf' em plain (LGPD-by-design)."""
        bundle = exportar_dados_titular(db, cliente_id=cliente.id)
        bundle_dict = bundle.__dict__
        bundle_str = json.dumps(bundle_dict, default=str)
        # Campo CPF plaintext NAO existe
        assert '"cpf":' not in bundle_str
        # Apenas cpf_hash eh exposto
        assert "cpf_hash" in bundle_str

    def test_export_mask_nome_edge_cases(self, db):
        """LGPD D29: nome com 1 parte, vazio, None sao tratados."""
        from app.services.lgpd_export import _mask_nome

        assert _mask_nome("Gustavo") == "G***"
        assert _mask_nome("") == "[nome indisponivel]"
        assert _mask_nome("   ") == "[nome indisponivel]"
        # Nome ja mascarado (idempotente)
        assert _mask_nome("G*** A***") == "G*** A***"

    def test_export_mask_email_edge_cases(self, db):
        """LGPD D29: email invalido/ja mascarado tratados."""
        from app.services.lgpd_export import _mask_email

        assert _mask_email("teste@sub.dominio.com") == "t***@com"
        assert _mask_email("") == "[email indisponivel]"
        assert _mask_email("sem-arroba") == "[email indisponivel]"
        # Ja mascarado (idempotente)
        assert _mask_email("g***@t.com") == "g***@com"

    def test_mask_bundle_pii_idempotente(self, db, cliente):
        """LGPD D29: _mask_bundle_pii nao quebra se chamado 2x (v1+v2)."""
        from app.services.lgpd_export import _mask_bundle_pii

        bundle = exportar_dados_titular(db, cliente_id=cliente.id)
        masked1 = _mask_bundle_pii(bundle.cliente)
        masked2 = _mask_bundle_pii(masked1)
        # Idempotente: segunda chamada nao muda nada
        assert masked1 == masked2
        # Nome e email continuam mascarados
        assert masked2["nome"] in ("G***", "G*** A***")
