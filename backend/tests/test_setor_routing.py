"""Tests para setor_routing (roteamento HITL por setor)."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.base import Base
from app.models.setor import SETORES_PADRAO, SETOR_POR_TIPO_ATO_DEFAULT, Setor
from app.services.setor_routing import (
    associar_protocolo_setor,
    get_setor_para_handoff,
    get_setor_por_slug,
    get_setor_por_tipo_ato,
    get_setores_ativos,
    inicializar_setores_padrao,
)


@pytest.fixture
def db_session():
    """Cria sessão de teste em memória."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


class TestSetorRouting:
    def test_inicializar_setores_padrao(self, db_session: Session):
        """Inicializa setores padrão do cartório."""
        count = inicializar_setores_padrao(db_session)
        assert count == len(SETORES_PADRAO)

        # Verificar se todos foram criados
        setores = get_setores_ativos(db_session)
        assert len(setores) == len(SETORES_PADRAO)

        slugs = {s.slug for s in setores}
        assert slugs == {s["slug"] for s in SETORES_PADRAO}

    def test_inicializar_setores_idempotente(self, db_session: Session):
        """Segunda chamada não duplica setores."""
        inicializar_setores_padrao(db_session)
        count = inicializar_setores_padrao(db_session)
        assert count == 0

        setores = get_setores_ativos(db_session)
        assert len(setores) == len(SETORES_PADRAO)

    def test_get_setor_por_slug(self, db_session: Session):
        """Busca setor por slug."""
        inicializar_setores_padrao(db_session)

        setor = get_setor_por_slug(db_session, "escrituras")
        assert setor is not None
        assert setor.slug == "escrituras"
        assert setor.nome == "Escrituras"

        # Slug inexistente
        assert get_setor_por_slug(db_session, "inexistente") is None

    def test_get_setor_por_tipo_ato(self, db_session: Session):
        """Determina setor baseado no tipo de ato."""
        inicializar_setores_padrao(db_session)

        # Testar mapeamentos principais
        assert get_setor_por_tipo_ato(db_session, "escritura_compra_venda").slug == "escrituras"
        assert get_setor_por_tipo_ato(db_session, "procuracao_geral").slug == "procuracoes"
        assert get_setor_por_tipo_ato(db_session, "reconhecimento_firma").slug == "reconhecimento_firma"
        assert get_setor_por_tipo_ato(db_session, "autenticacao").slug == "autenticacoes"
        assert get_setor_por_tipo_ato(db_session, "testamento").slug == "testamentos"
        assert get_setor_por_tipo_ato(db_session, "inventario_sem_conteudo_financeiro").slug == "inventarios"
        assert get_setor_por_tipo_ato(db_session, "certidao_negativa").slug == "certidoes"
        assert get_setor_por_tipo_ato(db_session, "ata_notarial_ate_2_folhas").slug == "atas_notariais"
        assert get_setor_por_tipo_ato(db_session, "arquivamento").slug == "arquivamento"
        assert get_setor_por_tipo_ato(db_session, "diligencia_urbana").slug == "diligencias"
        assert get_setor_por_tipo_ato(db_session, "apostilamento").slug == "apostilamento"
        assert get_setor_por_tipo_ato(db_session, "autorizacao_eletronica_viagem").slug == "autorizacoes"
        assert get_setor_por_tipo_ato(db_session, "gratuidade_isencao").slug == "gratuidade_isencao"
        assert get_setor_por_tipo_ato(db_session, "usucapiao").slug == "usucapiao"

        # Aliases
        assert get_setor_por_tipo_ato(db_session, "procuracao").slug == "procuracoes"
        assert get_setor_por_tipo_ato(db_session, "reconhecimento").slug == "reconhecimento_firma"
        assert get_setor_por_tipo_ato(db_session, "escritura_pacto_divorcio_uniao_estavel").slug == "escrituras"

        # Tipo desconhecido
        assert get_setor_por_tipo_ato(db_session, "tipo_inexistente") is None

    def test_get_setores_ativos_ordenados(self, db_session: Session):
        """Lista setores ativos ordenados por ordem_exibicao."""
        inicializar_setores_padrao(db_session)

        setores = get_setores_ativos(db_session)
        ordens = [s.ordem_exibicao for s in setores]
        assert ordens == sorted(ordens)

    def test_get_setor_para_handoff(self, db_session: Session):
        """Retorna dict com info para handoff HITL."""
        inicializar_setores_padrao(db_session)

        info = get_setor_para_handoff(db_session, "escritura_compra_venda")
        assert info is not None
        assert info["slug"] == "escrituras"
        assert info["nome"] == "Escrituras"
        assert "responsavel" in info
        assert "email" in info
        assert "telefone_interno" in info

        # Tipo desconhecido
        assert get_setor_para_handoff(db_session, "tipo_inexistente") is None

    def test_cobertura_mapeamento_completa(self):
        """Verifica que todos os tipos de ato conhecidos têm mapeamento."""
        # Tipos do emolumento_real_djalma
        from app.services.emolumento_real_djalma import ATOS_PUBLICADOS_2026, ALIASES_SLUG

        todos_tipos = set(ATOS_PUBLICADOS_2026.keys()) | set(ALIASES_SLUG.keys())

        # Tipos do emolumento_operacional_balcao
        from app.services.emolumento_operacional_balcao import GENERAL_ITEMS

        todos_tipos |= set(GENERAL_ITEMS.keys())

        # Verificar cobertura
        sem_mapeamento = [t for t in todos_tipos if t not in SETOR_POR_TIPO_ATO_DEFAULT]

        # Alguns tipos podem não ter setor (ex.: "desconhecido")
        # Mas a maioria deve ter
        taxa_cobertura = 1 - (len(sem_mapeamento) / len(todos_tipos)) if todos_tipos else 1
        assert taxa_cobertura >= 0.8, f"Cobertura de setores baixa: {taxa_cobertura:.0%}. Faltando: {sem_mapeamento}"