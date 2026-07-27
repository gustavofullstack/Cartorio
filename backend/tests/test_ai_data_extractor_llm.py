"""Testes da Fase 2 do extrator: camada LLM opcional, atos sensíveis e catálogo DB.

Todo tráfego LLM é mockado com respx — nenhum teste faz chamada real a provider
(o conftest força LLM_DEFAULT_PROVIDER="opencode_go", mas aqui nem isso importa:
a setting `ai_extractor_llm_enabled` é monkeypatched por teste).
"""

import json
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import httpx
import pytest
import respx

from app.config import settings
from app.models.emolumento_catalogo import EmolumentoItem
from app.services import ai_data_extractor
from app.services.ai_data_extractor import extrair_e_calcular_solicitacao
from app.services.metrics import store

LLM_URL = "http://litellm.test/v1/chat/completions"


@pytest.fixture
def llm_on(monkeypatch: pytest.MonkeyPatch) -> None:
    """Liga a camada LLM apontando para um proxy LiteLLM fake (mockado via respx)."""
    monkeypatch.setattr(settings, "ai_extractor_llm_enabled", True)
    monkeypatch.setattr(settings, "litellm_base_url", "http://litellm.test")
    monkeypatch.setattr(settings, "litellm_api_key", "test-key")
    monkeypatch.setattr(settings, "ai_extractor_llm_timeout_s", 5.0)


def _llm_response(
    *,
    tipo_ato: str = "procuracao_geral",
    valor_declarado: float | None = None,
    folhas: int = 1,
    urgencia: bool = False,
    confianca: float = 0.95,
) -> httpx.Response:
    content = json.dumps(
        {
            "tipo_ato": tipo_ato,
            "valor_declarado": valor_declarado,
            "folhas": folhas,
            "urgencia": urgencia,
            "confianca": confianca,
        }
    )
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


def _fallback_count() -> int:
    return sum(store.counters.get("cartorio_agent_ai_llm_fallback_total", {}).values())


def test_llm_desligado_mantem_comportamento_regex() -> None:
    # Sem nenhuma rota registrada: se o codigo tentar chamar o LLM com o gate
    # desligado, o respx estoura AllMockedAssertionError e o teste falha.
    with respx.mock:
        res = extrair_e_calcular_solicitacao("Quero fazer uma procuração para meu filho")
    assert res.tipo_ato_identificado == "procuracao_geral"
    assert res.calculo.status == "PUBLISHED"
    assert res.calculo.total == Decimal("68.94")
    assert res.hitl_obrigatorio is False


def test_llm_ligado_alta_confianca_usa_llm(llm_on: None) -> None:
    with respx.mock:
        respx.post(LLM_URL).mock(
            return_value=_llm_response(tipo_ato="ata_notarial_ate_2_folhas", confianca=0.95)
        )
        # Regex classificaria como testamento_publico; LLM (conf. alta) vence.
        res = extrair_e_calcular_solicitacao("Preciso lavrar um testamento")
    assert res.tipo_ato_identificado == "ata_notarial_ate_2_folhas"
    assert res.calculo.status == "PUBLISHED"
    assert res.calculo.total == Decimal("218.42")


def test_llm_baixa_confianca_usa_regex(llm_on: None) -> None:
    with respx.mock:
        respx.post(LLM_URL).mock(
            return_value=_llm_response(tipo_ato="ata_notarial_ate_2_folhas", confianca=0.4)
        )
        res = extrair_e_calcular_solicitacao("Preciso lavrar um testamento")
    assert res.tipo_ato_identificado == "testamento_publico"
    assert res.calculo.status == "PUBLISHED"
    assert res.calculo.total == Decimal("437.24")


def test_llm_http_500_fallback_regex_com_contador(llm_on: None) -> None:
    before = _fallback_count()
    with respx.mock:
        respx.post(LLM_URL).mock(return_value=httpx.Response(500, text="boom"))
        res = extrair_e_calcular_solicitacao("Preciso lavrar um testamento")
    assert res.tipo_ato_identificado == "testamento_publico"
    assert _fallback_count() == before + 1


def test_llm_timeout_fallback_regex_com_contador(llm_on: None) -> None:
    before = _fallback_count()
    with respx.mock:
        respx.post(LLM_URL).mock(side_effect=httpx.ConnectTimeout("timeout"))
        res = extrair_e_calcular_solicitacao("Preciso lavrar um testamento")
    assert res.tipo_ato_identificado == "testamento_publico"
    assert _fallback_count() == before + 1


def test_llm_json_invalido_fallback_regex(llm_on: None) -> None:
    before = _fallback_count()
    with respx.mock:
        respx.post(LLM_URL).mock(
            return_value=httpx.Response(
                200, json={"choices": [{"message": {"content": "isso não é JSON {{{"}}]}
            )
        )
        res = extrair_e_calcular_solicitacao("Preciso lavrar um testamento")
    assert res.tipo_ato_identificado == "testamento_publico"
    assert _fallback_count() == before + 1


def test_llm_slug_fora_da_lista_vira_desconhecido(llm_on: None) -> None:
    with respx.mock:
        respx.post(LLM_URL).mock(
            return_value=_llm_response(tipo_ato="slug_inventado_pelo_llm", confianca=0.99)
        )
        res = extrair_e_calcular_solicitacao("Preciso lavrar um testamento")
    assert res.tipo_ato_identificado == "desconhecido"
    assert res.calculo.status == "HITL_REQUIRED"
    assert res.hitl_obrigatorio is True


def test_payload_llm_nao_contem_cpf(llm_on: None) -> None:
    texto = "Quero fazer uma procuração, meu CPF é 111.222.333-44"
    with respx.mock:
        route = respx.post(LLM_URL).mock(return_value=_llm_response())
        res = extrair_e_calcular_solicitacao(texto)
    assert route.call_count == 1
    body = route.calls[0].request.content.decode("utf-8")
    assert "111.222.333-44" not in body
    payload = json.loads(body)
    user_msg = payload["messages"][1]["content"]
    assert user_msg == res.texto_sanitizado
    assert "111.222.333-44" not in user_msg


def test_ato_sensivel_usucapiao_forca_hitl_mesmo_com_preco_publicado() -> None:
    # Regex cai no default procuracao_geral (PUBLISHED), mas usucapião é sensível.
    res = extrair_e_calcular_solicitacao("Quero fazer usucapião do meu terreno")
    assert res.calculo.status == "PUBLISHED"
    assert res.hitl_obrigatorio is True


def test_ato_sensivel_procuracao_causa_propria_forca_hitl() -> None:
    res = extrair_e_calcular_solicitacao("Preciso de uma procuração em causa própria")
    assert res.hitl_obrigatorio is True


def test_ato_sensivel_divorcio_com_partilha_forca_hitl() -> None:
    res = extrair_e_calcular_solicitacao("Quero fazer divórcio com partilha de bens")
    assert res.hitl_obrigatorio is True


def test_db_catalogo_retorna_item_published_do_banco(monkeypatch: pytest.MonkeyPatch) -> None:
    item = EmolumentoItem(
        captura_id=1,
        tipo_ato="procuracao_geral",
        item_portaria="Tabela 1, item 4.f.1",
        ato="Procuração genérica, por outorgante",
        emolumentos=Decimal("52.43"),
        tfj=Decimal("17.57"),
        valor_final=Decimal("70.00"),  # difere do catálogo em código (68.94)
        estado="PUBLISHED",
        vigencia_inicio=date(2026, 1, 1),
        vigencia_fim=None,
    )
    monkeypatch.setattr(ai_data_extractor, "consultar_preco", lambda db, slug: item)
    res = extrair_e_calcular_solicitacao("Quero fazer uma procuração", db=MagicMock())
    assert res.calculo.status == "PUBLISHED"
    assert res.calculo.total == Decimal("70.00")
    assert res.calculo.tfj == Decimal("17.57")


def test_db_catalogo_sem_item_mantem_catalogo_em_codigo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ai_data_extractor, "consultar_preco", lambda db, slug: None)
    res = extrair_e_calcular_solicitacao("Quero fazer uma procuração", db=MagicMock())
    assert res.calculo.status == "PUBLISHED"
    assert res.calculo.total == Decimal("68.94")
