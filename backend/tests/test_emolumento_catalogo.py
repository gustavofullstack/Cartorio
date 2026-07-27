"""Testes do catalogo versionado de emolumentos (Fase 1 — ciclo de vida do dado)."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.emolumento_catalogo import EmolumentoItem, EstadoEmolumento, FonteCaptura
from app.services.emolumento_catalogo import (
    CatalogoNaoEncontradoError,
    EstadoInvalidoError,
    ItemExtraido,
    consultar_preco,
    marcar_revisao_humana,
    promover,
    registrar_extracao,
)
from app.services.emolumento_catalogo_seed import seed_catalogo
from app.services.emolumento_real_djalma import (
    ATOS_PUBLICADOS_2026,
    FAIXAS_ESCRITURA_COM_VALOR,
    FONTE_SHA256,
)

HOJE = date(2026, 7, 27)


def _item_teste(**overrides) -> ItemExtraido:
    base: ItemExtraido = {
        "tipo_ato": "testamento",
        "item_portaria": "Tabela 1, item 4.h.1",
        "ato": "Testamento",
        "emolumentos": Decimal("400.00"),
        "tfj": Decimal("120.00"),
        "valor_final": Decimal("520.00"),
    }
    base.update(overrides)  # type: ignore[typeddict-item]
    return base


def _extrair(
    db: Session,
    sha256: str = "b" * 64,
    itens: list[ItemExtraido] | None = None,
    **kwargs,
) -> FonteCaptura:
    return registrar_extracao(
        db,
        url="https://www8.tjmg.jus.br/institucional/at/pdf/cpo99992026.pdf",
        sha256=sha256,
        capturado_em=date(2026, 7, 27),
        vigencia_inicio=date(2026, 1, 1),
        itens=itens if itens is not None else [_item_teste()],
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Seed (E0.S0.5.T4)
# ---------------------------------------------------------------------------


def test_seed_cria_captura_publicada_com_itens(db_session: Session) -> None:
    captura = seed_catalogo(db_session)

    assert captura.estado == EstadoEmolumento.PUBLISHED
    assert captura.sha256 == FONTE_SHA256
    assert captura.revisado_por == "seed-validacao-pdf"
    assert captura.revisado_em is not None

    itens = (
        db_session.execute(select(EmolumentoItem).where(EmolumentoItem.captura_id == captura.id))
        .scalars()
        .all()
    )
    assert len(itens) == len(ATOS_PUBLICADOS_2026) + len(FAIXAS_ESCRITURA_COM_VALOR)

    publicados = [i for i in itens if i.estado == EstadoEmolumento.PUBLISHED]
    referencia = [i for i in itens if i.estado == EstadoEmolumento.HUMAN_REVIEWED]
    assert len(publicados) == len(ATOS_PUBLICADOS_2026)
    assert len(referencia) == len(FAIXAS_ESCRITURA_COM_VALOR)
    assert all(i.tipo_ato == "escritura_com_conteudo_financeiro" for i in referencia)
    assert all(i.componentes and "de" in i.componentes for i in referencia)


def test_seed_idempotente(db_session: Session) -> None:
    primeira = seed_catalogo(db_session)
    segunda = seed_catalogo(db_session)

    assert segunda.id == primeira.id
    total = db_session.execute(select(func.count(FonteCaptura.id))).scalar_one()
    assert total == 1


# ---------------------------------------------------------------------------
# consultar_preco
# ---------------------------------------------------------------------------


def test_consultar_preco_retorna_item_publicado_vigente(db_session: Session) -> None:
    seed_catalogo(db_session)

    item = consultar_preco(db_session, "testamento", hoje=HOJE)

    assert item is not None
    assert item.estado == EstadoEmolumento.PUBLISHED
    assert item.valor_final == Decimal("437.24")
    assert item.item_portaria == "Tabela 1, item 4.h.1"


def test_consultar_preco_slug_inexistente_retorna_none(db_session: Session) -> None:
    seed_catalogo(db_session)

    assert consultar_preco(db_session, "ato_que_nao_existe", hoje=HOJE) is None


def test_consultar_preco_item_nao_publicado_retorna_none(db_session: Session) -> None:
    """Faixas do escrevente (HUMAN_REVIEWED) nunca vazam para o agente."""
    seed_catalogo(db_session)

    assert consultar_preco(db_session, "escritura_com_conteudo_financeiro", hoje=HOJE) is None


def test_consultar_preco_vigencia_expirada_retorna_none(db_session: Session) -> None:
    captura = _extrair(db_session)
    marcar_revisao_humana(db_session, captura.id, "escrevente-x")
    promover(db_session, captura.id, "escrevente-x")
    # Expira o item retroativamente.
    item = consultar_preco(db_session, "testamento", hoje=HOJE)
    assert item is not None
    item.vigencia_fim = date(2026, 6, 30)
    db_session.commit()

    assert consultar_preco(db_session, "testamento", hoje=HOJE) is None


def test_consultar_preco_vigencia_futura_retorna_none(db_session: Session) -> None:
    captura = _extrair(
        db_session,
        itens=[_item_teste(vigencia_inicio=date(2027, 1, 1))],
    )
    marcar_revisao_humana(db_session, captura.id, "escrevente-x")
    promover(db_session, captura.id, "escrevente-x")

    assert consultar_preco(db_session, "testamento", hoje=HOJE) is None
    assert consultar_preco(db_session, "testamento", hoje=date(2027, 1, 2)) is not None


# ---------------------------------------------------------------------------
# registrar_extracao
# ---------------------------------------------------------------------------


def test_registrar_extracao_cria_captura_e_itens_extracted(db_session: Session) -> None:
    captura = _extrair(db_session)

    assert captura.estado == EstadoEmolumento.EXTRACTED
    assert len(captura.itens) == 1
    assert captura.itens[0].estado == EstadoEmolumento.EXTRACTED
    assert captura.itens[0].vigencia_inicio == captura.vigencia_inicio


def test_registrar_extracao_idempotente_por_sha256(db_session: Session) -> None:
    primeira = _extrair(db_session)
    segunda = _extrair(db_session)

    assert segunda.id == primeira.id
    total_capturas = db_session.execute(select(func.count(FonteCaptura.id))).scalar_one()
    total_itens = db_session.execute(select(func.count(EmolumentoItem.id))).scalar_one()
    assert total_capturas == 1
    assert total_itens == 1


# ---------------------------------------------------------------------------
# Fluxo EXTRACTED -> HUMAN_REVIEWED -> PUBLISHED (+ supersede)
# ---------------------------------------------------------------------------


def test_fluxo_completo_com_supersede_da_versao_anterior(db_session: Session) -> None:
    v1 = seed_catalogo(db_session)
    preco_v1 = consultar_preco(db_session, "testamento", hoje=HOJE)
    assert preco_v1 is not None and preco_v1.valor_final == Decimal("437.24")

    v2 = _extrair(db_session)
    marcar_revisao_humana(db_session, v2.id, "escrevente-y")
    assert v2.estado == EstadoEmolumento.HUMAN_REVIEWED
    assert v2.revisado_por == "escrevente-y"
    assert v2.revisado_em is not None

    promover(db_session, v2.id, "escrevente-y")

    db_session.refresh(v1)
    assert v1.estado == EstadoEmolumento.SUPERSEDED
    assert all(i.estado == EstadoEmolumento.SUPERSEDED for i in v1.itens)
    assert v2.estado == EstadoEmolumento.PUBLISHED
    assert all(i.estado == EstadoEmolumento.PUBLISHED for i in v2.itens)

    preco_v2 = consultar_preco(db_session, "testamento", hoje=HOJE)
    assert preco_v2 is not None
    assert preco_v2.valor_final == Decimal("520.00")
    assert preco_v2.captura_id == v2.id


def test_promover_estado_invalido_levanta_erro(db_session: Session) -> None:
    captura = _extrair(db_session)  # EXTRACTED, pulou revisao humana

    with pytest.raises(EstadoInvalidoError):
        promover(db_session, captura.id, "escrevente-y")


def test_marcar_revisao_humana_estado_invalido_levanta_erro(db_session: Session) -> None:
    captura = seed_catalogo(db_session)  # ja PUBLISHED

    with pytest.raises(EstadoInvalidoError):
        marcar_revisao_humana(db_session, captura.id, "escrevente-y")


def test_promover_captura_inexistente_levanta_erro(db_session: Session) -> None:
    with pytest.raises(CatalogoNaoEncontradoError):
        promover(db_session, 99999, "escrevente-y")


def test_promover_grava_audit_log(db_session: Session) -> None:
    captura = _extrair(db_session)
    marcar_revisao_humana(db_session, captura.id, "escrevente-y")
    promover(db_session, captura.id, "escrevente-y")

    entry = (
        db_session.execute(
            select(AuditLog).where(AuditLog.action == "emolumento_catalogo.promover")
        )
        .scalars()
        .first()
    )
    assert entry is not None
    assert entry.actor_id == "escrevente-y"
    assert entry.resource == f"fonte_captura:{captura.id}"
    assert entry.payload["captura_id"] == captura.id
    assert entry.payload["itens_publicados"] == 1
