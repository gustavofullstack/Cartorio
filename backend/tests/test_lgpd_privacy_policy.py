"""Testes do LGPD Privacy Policy Generator (D22).

Cobre:
- shape (markdown com 8 secoes)
- anonimizacao (cliente com deleted_at -> mascara especial)
- contact DPO (Gustavo Almeida, telegram 6682284055)
"""

from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.cliente import Cliente
from app.services.lgpd_privacy_policy import (
    DPO_NOME,
    DPO_TELEGRAM_CHAT_ID,
    _mask_email_personalizado,
    _mask_nome_personalizado,
    generate_privacy_policy,
    generate_privacy_policy_structured,
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
        cpf_hash="hash_gustavo_priv",
        email="gustavo@example.com",
        telefone_hash="hash_tel_gustavo",
        consentimento_lgpd=True,
        consentimento_em=datetime.now(tz=timezone.utc),
        consentimento_ip="192.168.1.100",
        consentimento_canal="whatsapp",
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@pytest.fixture
def cliente_anonimizado(db: Session) -> Cliente:
    c = Cliente(
        nome="[ANONIMIZADO art.18 V]",
        cpf_hash="hash_anon",
        email=None,
        telefone_hash=None,
        consentimento_lgpd=False,
        deleted_at=datetime.now(tz=timezone.utc),
        motivo_encerramento=__import__(
            "app.models.cliente", fromlist=["MotivoEncerramento"]
        ).MotivoEncerramento.REVOGACAO_CONSENTIMENTO,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


class TestLGPDPrivacyPolicyShape:
    """D22 — Shape basico do documento Privacy Policy."""

    def test_generate_retorna_str_markdown(self, db, cliente):
        """generate_privacy_policy retorna string markdown."""
        md = generate_privacy_policy(db, cliente_id=cliente.id)
        assert isinstance(md, str)
        assert len(md) > 100
        assert md.startswith("# ")

    def test_contem_8_secoes(self, db, cliente):
        """Documento tem 8 secoes principais (## headers)."""
        md = generate_privacy_policy(db, cliente_id=cliente.id)
        # 8 secoes principais
        assert md.count("\n## ") >= 8

    def test_contem_id_cliente(self, db, cliente):
        """Documento cita o cliente_id."""
        md = generate_privacy_policy(db, cliente_id=cliente.id)
        assert str(cliente.id) in md

    def test_contem_agente_tratamento(self, db, cliente):
        """Documento cita o nome do agente de tratamento."""
        md = generate_privacy_policy(db, cliente_id=cliente.id)
        assert "2o Servico Notarial" in md

    def test_contem_direitos_art_18(self, db, cliente):
        """Lista os 6 direitos principais do art. 18."""
        md = generate_privacy_policy(db, cliente_id=cliente.id)
        for d in (
            "Acesso",
            "Correcao",
            "Anonimizacao",
            "Portabilidade",
            "Revogacao",
            "Oposicao",
        ):
            assert d in md, f"Direito '{d}' ausente"

    def test_contem_endpoints_enderecados_a_cliente(self, db, cliente):
        """Endpoints referenciados contem o cliente_id."""
        md = generate_privacy_policy(db, cliente_id=cliente.id)
        assert f"/cliente/{cliente.id}/lgpd/acesso" in md
        assert f"/cliente/{cliente.id}/lgpd/corrigir" in md
        assert f"/cliente/{cliente.id}/lgpd/anonimizar" in md
        assert f"/cliente/{cliente.id}/lgpd/oposicao" in md
        assert f"/lgpd/export/{cliente.id}" in md

    def test_retorna_valor_error_para_cliente_inexistente(self, db):
        """Cliente inexistente -> ValueError."""
        with pytest.raises(ValueError, match="99999"):
            generate_privacy_policy(db, cliente_id=99999)


class TestLGPDPrivacyPolicyAnonimizacao:
    """D22 — Anonimizacao do documento personalizado."""

    def test_nome_pessoa_mascarado(self, db, cliente):
        """Nome pessoal sai mascarado (LGPD-by-design)."""
        md = generate_privacy_policy(db, cliente_id=cliente.id)
        # NAO expoe nome completo no bloco do Titular
        # (Gustavo Almeida aparece como DPO — extrair bloco entre inicio e 1ra secao)
        # O bloco "Titular" vem antes do "---" separador
        titular_section = md.split("---")[0]
        assert "Gustavo Almeida" not in titular_section
        # Expoe forma mascarada
        assert "G*** A***" in md

    def test_email_pessoa_mascarado(self, db, cliente):
        """Email pessoal sai mascarado."""
        md = generate_privacy_policy(db, cliente_id=cliente.id)
        # NAO expoe email completo do TITULAR (DPO email dpo@2notasudi.com.br eh diferente)
        assert "gustavo@example.com" not in md
        # Expoe forma mascarada (f***@example.com — 1a letra + dominio)
        assert "g***@example.com" in md

    def test_cpf_nunca_aparece_raw(self, db, cliente):
        """CPF plain numerico nao eh exposto (LGPD-by-design)."""
        md = generate_privacy_policy(db, cliente_id=cliente.id)
        # Nenhum CPF raw formato XXX.XXX.XXX-XX
        import re

        cpf_pattern = re.compile(r"\d{3}\.\d{3}\.\d{3}-\d{2}")
        assert not cpf_pattern.search(md), "CPF plain foi vazado no documento"

    def test_cliente_anonimizado_placeholder(self, db, cliente_anonimizado):
        """Cliente com deleted_at tem nome placeholder (titular anonimizado)."""
        md = generate_privacy_policy(db, cliente_id=cliente_anonimizado.id)
        # Placeholder para cliente ja anonimizado
        assert "anonimizado" in md.lower()
        # Inclui alerta explicito
        assert "anonimizados" in md.lower() or "ATENCAO" in md

    def test_helper_mask_nome_personalizado(self):
        """_mask_nome_personalizado segue o padrao do projeto."""
        assert _mask_nome_personalizado("Gustavo Almeida") == "G*** A***"
        assert _mask_nome_personalizado("Joao") == "J***"
        assert _mask_nome_personalizado("") == "[titular anonimizado]"
        assert _mask_nome_personalizado(None) == "[titular anonimizado]"

    def test_helper_mask_email_personalizado(self):
        """_mask_email_personalizado segue o padrao do projeto."""
        assert _mask_email_personalizado("gustavo@example.com") == "g***@example.com"
        assert _mask_email_personalizado("") == "[email indisponivel]"
        assert _mask_email_personalizado("sem-arroba") == "[email indisponivel]"
        assert _mask_email_personalizado(None) == "[email indisponivel]"


class TestLGPDPrivacyPolicyContactDPO:
    """D22 — Contact do DPO (LGPD art. 41)."""

    def test_contem_nome_dpo(self, db, cliente):
        """Documento cita Gustavo Almeida como DPO."""
        md = generate_privacy_policy(db, cliente_id=cliente.id)
        assert DPO_NOME in md
        assert "Gustavo Almeida" in md

    def test_contem_telegram_dpo(self, db, cliente):
        """Documento cita o Telegram do DPO (chat_id 6682284055)."""
        md = generate_privacy_policy(db, cliente_id=cliente.id)
        assert DPO_TELEGRAM_CHAT_ID in md
        assert "6682284055" in md

    def test_contem_email_dpo(self, db, cliente):
        """Documento cita e-mail do DPO."""
        md = generate_privacy_policy(db, cliente_id=cliente.id)
        assert "dpo@2notasudi.com.br" in md

    def test_contem_papel_dpo(self, db, cliente):
        """Documento cita que Gustavo eh Encarregado de Dados (LGPD art. 41)."""
        md = generate_privacy_policy(db, cliente_id=cliente.id)
        assert "Encarregado" in md or "DPO" in md
        assert "41" in md  # LGPD art. 41


class TestLGPDPrivacyPolicyStructured:
    """D22 — Variante estruturada (dict, nao markdown)."""

    def test_structured_retorna_dict(self, db, cliente):
        """generate_privacy_policy_structured retorna dict."""
        data = generate_privacy_policy_structured(db, cliente_id=cliente.id)
        assert isinstance(data, dict)

    def test_structured_tem_direitos_art_18(self, db, cliente):
        """Dict tem pelo menos 5 direitos mapeados."""
        data = generate_privacy_policy_structured(db, cliente_id=cliente.id)
        assert len(data["direitos_art_18"]) >= 5
        for d in data["direitos_art_18"]:
            assert "direito" in d
            assert "artigo" in d
            assert "endpoint" in d

    def test_structured_dpo_info(self, db, cliente):
        """Dict tem bloco contact_dpo com telegram 6682284055."""
        data = generate_privacy_policy_structured(db, cliente_id=cliente.id)
        dpo = data["contact_dpo"]
        assert dpo["telegram_chat_id"] == "6682284055"
        assert "Gustavo Almeida" in dpo["nome"]

    def test_structured_cliente_anonimizado(self, db, cliente_anonimizado):
        """Dict para cliente anonimizado tem flag=True."""
        data = generate_privacy_policy_structured(db, cliente_id=cliente_anonimizado.id)
        assert data["cliente"]["anonimizado"] is True
        assert "[titular anonimizado]" in data["cliente"]["nome_mascarado"]


class TestLGPDPrivacyPolicyFinalidades:
    """D22 — Coleta de finalidades via audit log."""

    def test_finalidades_aceitas_aparecem_no_md(self, db, cliente):
        """Se cliente tem grant de finalidade, aparece no markdown."""
        from app.services.audit import AuditService

        AuditService.log(
            db=db,
            actor_id=str(cliente.id),
            actor_type="cliente",
            action="lgpd.consent.granted",
            resource=f"cliente/{cliente.id}",
            payload={"finalidades": ["marketing", "pesquisa_satisfacao"]},
        )
        db.commit()

        md = generate_privacy_policy(db, cliente_id=cliente.id)
        assert "marketing" in md
        assert "pesquisa_satisfacao" in md

    def test_finalidades_revogadas_aparecem_no_md(self, db, cliente):
        """Se cliente tem revoke, aparece marcado como revogada."""
        from app.services.audit import AuditService

        AuditService.log(
            db=db,
            actor_id=str(cliente.id),
            actor_type="cliente",
            action="lgpd.consent.revoked",
            resource=f"cliente/{cliente.id}",
            payload={"finalidades_revogadas": ["marketing"]},
        )
        db.commit()

        md = generate_privacy_policy(db, cliente_id=cliente.id)
        # Secao 4 (revogadas)
        assert "REVOGADAS" in md
        assert "marketing" in md
