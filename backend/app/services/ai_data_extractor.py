"""Motor de Extração de Dados Jurídicos via IA com PII Scrubbing e Auditoria Imutável.

Analisa requisições de clientes do 2º Ofício Notarial de Uberlândia (Tabelionato Djalma),
extrai parâmetros notariais de forma segura e calcula o orçamento com discriminativo fiscal real.

Fase 2 (docs/DADOS_PRECOS_E_PAINEL_AGENT_AI.md): camada LLM OPCIONAL sobre o regex
(setting ``ai_extractor_llm_enabled``, default False). Quando ligada, envia SOMENTE o
texto pós-scrub ao LiteLLM proxy e faz merge por confiança (>= 0.8 usa o LLM, senão
regex). Qualquer falha/timeout/JSON inválido cai no regex silenciosamente, com
contador ``cartorio_agent_ai_llm_fallback_total{reason}``.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Final

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models.emolumento_catalogo import EmolumentoItem
from app.services.emolumento_catalogo import consultar_preco
from app.services.emolumento_real_djalma import (
    ALIASES_SLUG,
    ATOS_PUBLICADOS_2026,
    CARTORIO,
    STATUS_PUBLISHED,
    TABELA_REFERENCIA,
    TABELIAO,
    EmolumentoDetalhados,
    calcular_emolumento_real_djalma,
)
from app.services.metrics import store
from app.services.pii import scrub

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Atos sensíveis (spec Fase 2) — nunca preço final pelo agente: HITL forçado
# mesmo que exista item publicado. Cobre: escritura com conteúdo financeiro,
# inventário com partilha, divórcio com partilha, procuração em causa própria,
# usucapião, gratuidade/isenção, diligências, arquivamentos, atos acessórios.
# ---------------------------------------------------------------------------

# Slugs que o LLM pode retornar para atos sensíveis (fora do catálogo publicado).
SLUGS_ATOS_SENSIVEIS: Final[frozenset[str]] = frozenset(
    {
        "escritura_com_conteudo_financeiro",
        "inventario_com_partilha",
        "divorcio_com_partilha",
        "procuracao_causa_propria",
        "usucapiao",
        "gratuidade_isencao",
        "diligencias",
        "arquivamentos",
        "atos_acessorios",
    }
)

# Padrões de texto (pós-scrub) que identificam ato sensível no caminho regex.
ATOS_SENSIVEIS_PATTERNS: Final[tuple[re.Pattern[str], ...]] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"usucapi[aã]o",
        r"causa\s+pr[óo]pria",
        r"invent[áa]rio[^.]{0,60}partilha|partilha[^.]{0,60}invent[áa]rio",
        r"div[óo]rcio[^.]{0,60}partilha|partilha[^.]{0,60}div[óo]rcio",
        r"gratuidade|isen[çc][ãa]o",
        r"dilig[êe]ncia",
        r"arquivamento",
        r"atos?\s+acess[óo]rios?",
    )
)

SLUG_DESCONHECIDO: Final[str] = "desconhecido"


def _slugs_validos() -> set[str]:
    """Slugs aceitos do LLM: catálogo publicado + aliases + sensíveis + desconhecido."""
    return (
        set(ATOS_PUBLICADOS_2026)
        | set(ALIASES_SLUG)
        | set(SLUGS_ATOS_SENSIVEIS)
        | {SLUG_DESCONHECIDO}
    )


def _ato_sensivel(tipo_ato: str, texto_sanitizado: str) -> bool:
    """True se o ato identificado exige HITL forçado (spec Fase 2)."""
    slug = ALIASES_SLUG.get(tipo_ato, tipo_ato)
    if slug in SLUGS_ATOS_SENSIVEIS or tipo_ato in SLUGS_ATOS_SENSIVEIS:
        return True
    return any(p.search(texto_sanitizado) for p in ATOS_SENSIVEIS_PATTERNS)


@dataclass
class ExtraçaoResultado:
    texto_sanitizado: str
    tipo_ato_identificado: str
    valor_declarado_identificado: Decimal | None
    folhas_identificadas: int
    urgencia_identificada: bool
    calculo: EmolumentoDetalhados
    hitl_obrigatorio: bool
    status_auditoria: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "texto_sanitizado": self.texto_sanitizado,
            "tipo_ato_identificado": self.tipo_ato_identificado,
            "valor_declarado_identificado": float(self.valor_declarado_identificado)
            if self.valor_declarado_identificado is not None
            else None,
            "folhas_identificadas": self.folhas_identificadas,
            "urgencia_identificada": self.urgencia_identificada,
            "calculo": self.calculo.to_dict(),
            "hitl_obrigatorio": self.hitl_obrigatorio,
            "status_auditoria": self.status_auditoria,
        }


def extrair_valor_monetario(texto: str) -> Decimal | None:
    """Extrai valores monetários em formato R$ X.XXX,XX ou X,XX do texto."""
    # Exemplo: R$ 350.000,00 ou 350000 ou R$350.000
    padrao = r"(?:R\$\s*)?(\d{1,3}(?:\.\d{3})*(?:,\d{2})?|\d+(?:,\d{2})?)"
    matches = re.findall(padrao, texto, re.IGNORECASE)
    for m in matches:
        limpo = m.replace(".", "").replace(",", ".")
        try:
            val = Decimal(limpo)
            if val > Decimal("100"):  # Ignora números de folhas ou artigos
                return val
        except Exception:
            continue
    return None


def extrair_folhas(texto: str) -> int:
    """Extrai quantidade de folhas mencionada no texto."""
    match = re.search(r"(\d+)\s*(?:folhas?|pág|páginas?)", texto, re.IGNORECASE)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            pass
    return 1


def extrair_tipo_ato(texto: str) -> str:
    """Classifica o tipo de ato notarial no texto com base nas palavras-chave do Tabelionato Djalma."""
    t = texto.lower()
    if "compra e venda" in t or "imóvel" in t or "escritura de compra" in t:
        return "escritura_compra_venda"
    elif "escritura" in t and (
        "divórcio" in t or "emancipação" in t or "pacto" in t or "sem valor" in t
    ):
        return "escritura_sem_valor"
    elif "ata notarial" in t or "constatação" in t or "whatsapp" in t:
        return "ata_notarial_primeira_folha"
    elif "procuração previdenciária" in t or "inss" in t:
        return "procuracao_previdenciaria"
    elif "procuração" in t and ("veículo" in t or "carro" in t or "imóvel" in t):
        return "procuracao_imovel_veiculo"
    elif "procuração" in t:
        return "procuracao_geral"
    elif "autenticação" in t or "autenticar" in t or "cópia" in t:
        return "autenticacao_pagina"
    elif "reconhecimento" in t or "firma" in t:
        if "autenticidade" in t or "presencial" in t:
            return "reconhecimento_firma_autenticidade"
        return "reconhecimento_firma_semelhanca"
    elif "testamento" in t:
        return "testamento_publico"
    elif "certidão" in t and "inteiro teor" in t:
        return "certidao_inteiro_teor"
    elif "certidão" in t:
        return "certidao_breve_relato"
    return "procuracao_geral"


# ---------------------------------------------------------------------------
# Camada LLM (Fase 2) — opcional, defensiva, sempre com fallback para regex
# ---------------------------------------------------------------------------

_LLM_SYSTEM_PROMPT = """Voce extrai parametros de atos notariais do 2o Oficio de Notas de Uberlandia/MG.

Responda APENAS com um JSON estrito (sem markdown, sem texto extra), no formato:
{"tipo_ato": "<slug>", "valor_declarado": <number|null>, "folhas": <int>=1,
 "urgencia": <bool>, "confianca": <0..1>}

Regras:
- "tipo_ato" DEVE ser um dos slugs validos listados no bloco SLUGS_VALIDOS, ou
  "desconhecido" se o ato nao for identificavel com seguranca.
- "valor_declarado": valor monetario do negocio (ex.: valor do imovel), ou null.
- "folhas": quantidade de folhas mencionada; minimo 1.
- "urgencia": true somente se o cliente pedir urgencia/hoje/rapido.
- "confianca": 0.0 a 1.0 — sua confianca na extracao como um todo.
- NUNCA inclua dados pessoais (CPF, RG, nomes) na resposta.

SLUGS_VALIDOS:
{slugs}"""


@dataclass(frozen=True)
class _LLMExtracao:
    tipo_ato: str
    valor_declarado: Decimal | None
    folhas: int
    urgencia: bool
    confianca: float


def _inc_llm_fallback(reason: str) -> None:
    """Contador de fallback do LLM (labels categoricos, sem PII)."""
    try:
        store.inc_counter("cartorio_agent_ai_llm_fallback_total", labels={"reason": reason})
    except Exception:  # noqa: BLE001 — metrica nunca derruba extracao
        logger.warning("ai_data_extractor: falha ao registrar fallback metric (%s)", reason)


def _strip_think_tags(text: str) -> str:
    """Remove blocos <think>/<reasoning> de modelos com thinking (ex.: MiniMax-M3)."""
    cleaned = re.sub(r"<think>[\s\S]*?(?:</think>|$)", "", text, flags=re.I)
    cleaned = re.sub(r"<reasoning>[\s\S]*?(?:</reasoning>|$)", "", cleaned, flags=re.I)
    return cleaned.strip()


def _parse_llm_extracao(content: str) -> _LLMExtracao | None:
    """Parse defensivo do JSON do LLM. Qualquer desvio retorna None (fallback regex)."""
    cleaned = _strip_think_tags(content)
    obj: Any = None
    try:
        obj = json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if match:
            try:
                obj = json.loads(match.group(0))
            except (json.JSONDecodeError, TypeError):
                pass
    if not isinstance(obj, dict):
        _inc_llm_fallback("invalid_json")
        return None

    try:
        confianca_raw = obj.get("confianca")
        if isinstance(confianca_raw, bool) or not isinstance(confianca_raw, (int, float, str)):
            raise ValueError("confianca invalida")
        confianca = float(confianca_raw)
        if not 0.0 <= confianca <= 1.0:
            raise ValueError("confianca fora de 0..1")

        tipo_ato = obj.get("tipo_ato")
        if not isinstance(tipo_ato, str) or not tipo_ato.strip():
            raise ValueError("tipo_ato invalido")
        tipo_ato = tipo_ato.strip().lower()
        if tipo_ato not in _slugs_validos():
            tipo_ato = SLUG_DESCONHECIDO

        valor_raw = obj.get("valor_declarado")
        valor_declarado: Decimal | None = None
        if valor_raw is not None:
            if isinstance(valor_raw, bool) or not isinstance(valor_raw, (int, float, str)):
                raise ValueError("valor_declarado invalido")
            valor_declarado = Decimal(str(valor_raw))
            if valor_declarado < 0:
                raise ValueError("valor_declarado negativo")

        folhas_raw = obj.get("folhas", 1)
        if isinstance(folhas_raw, bool) or not isinstance(folhas_raw, (int, float)):
            raise ValueError("folhas invalido")
        folhas = max(1, int(folhas_raw))

        urgencia = bool(obj.get("urgencia", False))
    except (TypeError, ValueError, InvalidOperation):
        _inc_llm_fallback("invalid_schema")
        return None

    return _LLMExtracao(
        tipo_ato=tipo_ato,
        valor_declarado=valor_declarado,
        folhas=folhas,
        urgencia=urgencia,
        confianca=confianca,
    )


def _extrair_via_llm(texto_sanitizado: str) -> _LLMExtracao | None:
    """Extrai parametros via LiteLLM proxy (OpenAI-compatible /chat/completions).

    Recebe SOMENTE o texto pos-scrub — o texto original nunca cruza a fronteira
    do provider. Falha/timeout/JSON invalido retornam None (fallback regex).
    """
    if not settings.ai_extractor_llm_enabled:
        return None
    if not settings.litellm_api_key:
        _inc_llm_fallback("no_api_key")
        return None

    url = f"{settings.litellm_base_url.rstrip('/')}/v1/chat/completions"
    payload: dict[str, Any] = {
        "model": settings.ai_extractor_llm_model,
        "temperature": 0,
        "max_tokens": 256,
        "messages": [
            {
                "role": "system",
                "content": _LLM_SYSTEM_PROMPT.replace(
                    "{slugs}", "\n".join(sorted(_slugs_validos()))
                ),
            },
            {"role": "user", "content": texto_sanitizado},
        ],
    }
    try:
        with httpx.Client(
            timeout=httpx.Timeout(settings.ai_extractor_llm_timeout_s, connect=3.0)
        ) as client:
            resp = client.post(
                url,
                headers={
                    "Authorization": f"Bearer {settings.litellm_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
    except httpx.TimeoutException:
        _inc_llm_fallback("timeout")
        return None
    except httpx.HTTPError as exc:
        _inc_llm_fallback("connection_error")
        logger.warning("ai_data_extractor LLM connection fail: %s", type(exc).__name__)
        return None

    if resp.status_code != 200:
        _inc_llm_fallback("http_error")
        logger.warning("ai_data_extractor LLM HTTP %s", resp.status_code)
        return None

    try:
        data = resp.json()
        content = (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""
    except (ValueError, AttributeError, IndexError, TypeError):
        _inc_llm_fallback("invalid_json")
        return None

    return _parse_llm_extracao(content)


# ---------------------------------------------------------------------------
# Catálogo versionado no banco (Fase 1) — preferido quando há item PUBLISHED
# ---------------------------------------------------------------------------


def _emolumento_do_item_catalogo(item: EmolumentoItem, slug: str) -> EmolumentoDetalhados:
    """Monta EmolumentoDetalhados PUBLISHED a partir do item vigente do banco."""
    return EmolumentoDetalhados(
        cartorio=CARTORIO,
        tabeliao=TABELIAO,
        tipo_ato=slug,
        valor_declarado=None,
        folhas=1,
        status=STATUS_PUBLISHED,
        emolumento_base=Decimal(item.emolumentos),
        tfj=Decimal(item.tfj),
        total=Decimal(item.valor_final),
        item_portaria=item.item_portaria,
        motivo_hitl=None,
        tabela_referencia=TABELA_REFERENCIA,
    )


def _consultar_catalogo_db(db: Session, calculo: EmolumentoDetalhados) -> EmolumentoDetalhados:
    """Prefere o item PUBLISHED vigente do catálogo versionado quando o cálculo é simples.

    Ausência de item vigente (ou falha de DB) mantém o catálogo em código —
    mesma fonte validada (Portaria CGJ/TJMG 8.664/2025).
    """
    if calculo.status != STATUS_PUBLISHED:
        return calculo
    try:
        item = consultar_preco(db, calculo.tipo_ato)
    except Exception as exc:  # noqa: BLE001 — DB indisponivel nao derruba extracao
        logger.warning("ai_data_extractor catalogo db fail-open: %s", type(exc).__name__)
        return calculo
    if item is None:
        return calculo
    return _emolumento_do_item_catalogo(item, calculo.tipo_ato)


def extrair_e_calcular_solicitacao(
    texto_usuario: str,
    *,
    forcar_urgencia: bool = False,
    db: Session | None = None,
) -> ExtraçaoResultado:
    """Sanitiza, extrai sinais e consulta somente itens oficiais publicados.

    A função não persiste uma entrada de auditoria; a rota chamadora deve fazê-lo
    quando houver uma operação de negócio. Esse contrato evita declarar uma
    cadeia de auditoria validada sem ter gravado evento algum.

    Fase 2: quando ``ai_extractor_llm_enabled`` está ligado, uma camada LLM
    (texto pós-scrub apenas) refina a extração do regex por confiança. Quando
    ``db`` é fornecido e o cálculo é simples, o preço PUBLISHED vigente do
    catálogo versionado no banco tem precedência sobre o catálogo em código.
    """
    # 1. PII Scrubbing (Garantia LGPD Art. 18 / 3-Camadas)
    texto_sanitizado = scrub(texto_usuario).text

    # 2. Extração de Entidades via Regex (baseline determinístico)
    tipo_ato = extrair_tipo_ato(texto_sanitizado)
    valor_declarado = extrair_valor_monetario(texto_sanitizado)
    folhas = extrair_folhas(texto_sanitizado)
    urgencia = forcar_urgencia or bool(
        re.search(r"\b(urgente|urgência|hoje|rápido)\b", texto_sanitizado, re.IGNORECASE)
    )

    # 2b. Camada LLM opcional: merge por confiança (>= threshold usa o LLM).
    # Urgência é OR-conservadora: regex ou LLM marcando urgência força HITL.
    llm = _extrair_via_llm(texto_sanitizado)
    if llm is not None and llm.confianca >= settings.ai_extractor_llm_min_confidence:
        tipo_ato = llm.tipo_ato
        valor_declarado = llm.valor_declarado
        folhas = llm.folhas
        urgencia = forcar_urgencia or urgencia or llm.urgencia

    # 3. Consulta de item publicado; atos compostos retornam HITL_REQUIRED.
    calculo = calcular_emolumento_real_djalma(
        tipo_ato=tipo_ato,
        valor_declarado=valor_declarado,
        folhas=folhas,
        urgencia=urgencia,
    )

    # 3b. Catálogo versionado no banco tem precedência no cálculo simples.
    if db is not None:
        calculo = _consultar_catalogo_db(db, calculo)

    # 4. Human-in-the-Loop Obrigatório para atos que exijam conferência de documentos
    #    ou que caiam no conjunto de atos sensíveis da spec (nunca preço final).
    hitl_obrigatorio = calculo.status == "HITL_REQUIRED" or _ato_sensivel(
        tipo_ato, texto_sanitizado
    )

    return ExtraçaoResultado(
        texto_sanitizado=texto_sanitizado,
        tipo_ato_identificado=tipo_ato,
        valor_declarado_identificado=valor_declarado,
        folhas_identificadas=folhas,
        urgencia_identificada=urgencia,
        calculo=calculo,
        hitl_obrigatorio=hitl_obrigatorio,
        status_auditoria="NOT_PERSISTED",
    )
