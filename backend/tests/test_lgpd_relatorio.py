"""Testes do Relatorio ANPD anual LGPD (D9)."""

from __future__ import annotations

import re
from collections.abc import Generator
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.cliente import Cliente
from app.services.lgpd_relatorio import (
    _hash_anchor,
    gerar_relatorio_anual,
    render_markdown,
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


class TestRelatorioANPD:
    """TDD strict - D9 LGPD relatorio anual."""

    def test_relatorio_basico(self, db):
        """Relatorio tem todas as 12 secoes obrigatorias."""
        rel = gerar_relatorio_anual(db, ano=2026)
        assert rel["ano"] == 2026
        assert "gerado_em" in rel
        assert "gerado_por" in rel
        assert "hash_anchor" in rel

        # 12 secoes principais
        required = {
            "titulares",
            "operacoes",
            "direitos_titulares",
            "incidentes_seguranca",
            "tipos_dados_tratados",
            "finalidades_uso",
            "medidas_seguranca",
            "encarregado_dpo",
            "base_legal",
            "transferencias_internacionais",
            "observacoes",
        }
        assert required.issubset(set(rel.keys()))

    def test_titulares_contagem(self, db):
        """Conta titulares ativos vs total."""
        # 2 clientes ativos
        for i in range(2):
            db.add(
                Cliente(
                    nome=f"Cliente {i}",
                    cpf_hash=f"hash_cliente_{i}",
                    email=f"c{i}@test.com",
                )
            )
        db.commit()

        rel = gerar_relatorio_anual(db, ano=2026)
        assert rel["titulares"]["total"] == 2
        assert rel["titulares"]["ativos"] == 2
        assert rel["titulares"]["anonimizados_ou_deletados"] == 0

    def test_titulares_com_deleted_at(self, db):
        """Cliente soft-deleted NAO conta como ativo."""
        from datetime import datetime

        now = datetime.now(tz=timezone.utc)
        c1 = Cliente(nome="A", cpf_hash="hash_a", email="a@t.com")
        c2 = Cliente(
            nome="B",
            cpf_hash="hash_b",
            email="b@t.com",
            deleted_at=now,
            motivo_encerramento="LGPD",
        )
        db.add_all([c1, c2])
        db.commit()

        rel = gerar_relatorio_anual(db, ano=2026)
        assert rel["titulares"]["total"] == 2
        assert rel["titulares"]["ativos"] == 1
        assert rel["titulares"]["anonimizados_ou_deletados"] == 1

    def test_gerado_em_iso_format(self, db):
        """gerado_em eh ISO 8601."""
        rel = gerar_relatorio_anual(db, ano=2026)
        # Parse OK
        datetime.fromisoformat(rel["gerado_em"])

    def test_hash_anchor_is_sha256(self, db):
        """hash_anchor eh SHA256 (64 chars hex)."""
        rel = gerar_relatorio_anual(db, ano=2026)
        h = rel["hash_anchor"]
        assert len(h) == 64
        assert re.match(r"^[a-f0-9]{64}$", h)

    def test_hash_anchor_changes_with_data(self, db):
        """Hash muda quando dados do relatorio mudam."""
        rel1 = gerar_relatorio_anual(db, ano=2026)
        # Adiciona 1 cliente
        db.add(Cliente(nome="X", cpf_hash="hash_x", email="x@t.com"))
        db.commit()
        rel2 = gerar_relatorio_anual(db, ano=2026)

        assert rel1["hash_anchor"] != rel2["hash_anchor"]

    def test_tipos_dados_tratados_nao_vazio(self, db):
        """tipos_dados_tratados tem pelo menos 5 tipos."""
        rel = gerar_relatorio_anual(db, ano=2026)
        assert len(rel["tipos_dados_tratados"]) >= 5

    def test_finalidades_uso_inclui_atendimento(self, db):
        """finalidades_uso menciona atendimento."""
        rel = gerar_relatorio_anual(db, ano=2026)
        finalidades = " ".join(rel["finalidades_uso"]).lower()
        assert "atendimento" in finalidades

    def test_medidas_seguranca_inclui_criptografia(self, db):
        """medidas_seguranca menciona criptografia."""
        rel = gerar_relatorio_anual(db, ano=2026)
        medidas = " ".join(rel["medidas_seguranca"]).lower()
        assert "criptografia" in medidas or "tls" in medidas

    def test_encarregado_dpo_tem_nome(self, db):
        """Encarregado tem nome e email."""
        rel = gerar_relatorio_anual(db, ano=2026)
        assert "nome" in rel["encarregado_dpo"]
        assert "email" in rel["encarregado_dpo"]

    def test_base_legal_menciona_lgpd(self, db):
        """Base legal menciona LGPD Lei 13.709/2018."""
        rel = gerar_relatorio_anual(db, ano=2026)
        base = str(rel["base_legal"])
        assert "13.709" in base

    def test_direitos_titulares_7_direitos(self, db):
        """Direitos do art. 18 tem 7 tipos (confirmacao, acesso, correcao, etc)."""
        rel = gerar_relatorio_anual(db, ano=2026)
        detalhes = rel["direitos_titulares"]["detalhes"]
        assert len(detalhes) == 7
        # Cada valor inicial eh 0
        for v in detalhes.values():
            assert v == 0

    def test_incidentes_inicial_zero(self, db):
        """Incidentes inicia em 0 (sem incidentes reportados)."""
        rel = gerar_relatorio_anual(db, ano=2026)
        assert rel["incidentes_seguranca"]["total"] == 0

    def test_render_markdown_has_hash_anchor(self, db):
        """Markdown renderizado contem hash_anchor."""
        rel = gerar_relatorio_anual(db, ano=2026)
        md = render_markdown(rel)
        assert rel["hash_anchor"] in md
        assert "Relatorio ANPD" in md
        assert "## 1. Titulares" in md
        assert "## 8. Encarregado" in md

    def test_hash_anchor_helper(self):
        """_hash_anchor retorna SHA256 deterministico."""
        data1 = {"a": 1, "b": [1, 2, 3]}
        data2 = {"a": 1, "b": [1, 2, 3]}
        data3 = {"a": 1, "b": [1, 2, 4]}
        assert _hash_anchor(data1) == _hash_anchor(data2)
        assert _hash_anchor(data1) != _hash_anchor(data3)
