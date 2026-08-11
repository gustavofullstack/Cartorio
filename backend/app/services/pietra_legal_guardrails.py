"""Guardrails juridicos determinísticos da Pietra (auditoria WhatsApp 2026-08-11).

Aplicados DEPOIS do LLM e ANTES do send. Nao substituem HITL: forcam fatos
oficiais (2 testemunhas, legitima, PDF eletronico R$ 12,99, cartao de autografo,
ITBI 2% Uberlandia) e bloqueiam identidade corrompida ("pedra").

Nao chamam LLM, nao tocam producao.
"""

from __future__ import annotations

import re
from typing import Final

from app.services.pii import scrub

_HITL: Final[str] = (
    "Essa providencia depende da validacao de um escrevente antes de qualquer andamento."
)

_OFFICIAL_EMAILS: Final[tuple[tuple[str, str], ...]] = (
    ("dpo@2notasudi.com.br", "\x00DPO_EMAIL\x00"),
    ("contato@2notasudi.com.br", "\x00CONTATO_EMAIL\x00"),
)


def _protect_official(text: str) -> str:
    out = text
    for real, token in _OFFICIAL_EMAILS:
        out = re.sub(re.escape(real), token, out, flags=re.IGNORECASE)
    return out


def _restore_official(text: str) -> str:
    out = text
    for real, token in _OFFICIAL_EMAILS:
        out = out.replace(token, real)
    return out


def _has(user: str, *needles: str) -> bool:
    low = user.lower()
    return any(n in low for n in needles)


def apply_legal_guardrails(*, user_text: str, bot_text: str) -> str:
    """Corrige fatos criticos e identidade no texto de saida."""
    user = user_text or ""
    text = bot_text or ""
    if not text:
        return text

    text = re.sub(r"(?i)\bpedra do cart[oó]rio\b", "Pietra, a agente do cartorio", text)
    text = re.sub(r"(?i)\beu sou a pedra\b", "Eu sou a Pietra", text)

    if _has(user, "testamento"):
        text = re.sub(r"(?i)\bs[aã]o quatro\b[^.]*testemunhas[^.]*\.?", "", text)
        text = re.sub(r"(?i)\bquatro testemunhas\b", "duas testemunhas", text)
        text = re.sub(r"(?i)\b4 testemunhas\b", "2 testemunhas", text)
        text = re.sub(r"(?i)\bcreio\b", "", text)
        if "duas testemunhas" not in text.lower() and "2 testemunhas" not in text.lower():
            text = "O testamento publico exige duas testemunhas. " + text
        if _has(user, "exclu", "filho", "filhos", "herdeiro"):
            text += (
                "\n\nFilhos sao herdeiros necessarios. Voce pode dispor da parte "
                "disponivel, mas nao retirar a legitima dos demais sem hipotese "
                "legal de exclusao ou deserdacao. " + _HITL
            )
        elif "herdeiros necessarios" not in text.lower() and "legitima" not in text.lower():
            text += (
                "\n\nFilhos sao herdeiros necessarios. A parte disponivel e a "
                "legitima seguem o Codigo Civil e o Codigo de Normas mineiro. " + _HITL
            )
        if re.search(r"R\$\s*437", text) and _has(user, "patrim", "todo"):
            text += (
                "\n\nO valor de R$ 437,24 e o item basico de testamento sem "
                "conteudo financeiro avaliado. Com patrimonio declarado, o "
                "escrevente calcula pela faixa propria. " + _HITL
            )

    if _has(user, "pdf") or _has(user, "assinado digital", "assinatura digital"):
        text = re.sub(
            r"(?i)basta trazer o pdf no celular[^.]*\.?",
            "O original eletronico precisa ser acessado e impresso pela serventia, "
            "com endereco eletronico verificavel, QR Code ou codigo de validacao. ",
            text,
        )
        if "12,99" not in text and "12.99" not in text:
            text += (
                "\n\nAutenticacao de documento eletronico ou digital custa "
                "R$ 12,99 (Tabela 1 MG 2026). Autenticacao de copia fisica "
                "e R$ 11,21 por folha. A classificacao do ato e do escrevente. " + _HITL
            )
        elif "escrevente" not in text.lower():
            text += "\n\n" + _HITL

    if _has(user, "semelhan", "autenticidade") or _has(user, "contrato ja assinado"):
        text = re.sub(
            r"(?i)documento de identifica[cç][aã]o",
            "cartao ou livro de autografos da propria serventia",
            text,
        )
        if (
            "cartao" not in text.lower()
            and "ficha" not in text.lower()
            and "livro" not in text.lower()
        ):
            text += (
                "\n\nNo reconhecimento por semelhanca, a assinatura e confrontada "
                "com o autografo do cartao ou livro desta serventia, nao com um "
                "RG avulso. A modalidade depende da exigencia do destinatario."
            )

    if _has(user, "apartamento", "itbi", "escritura") and _has(user, "420", "compr", "uberlandia"):
        text = re.sub(r"(?i)entre 2%\s*e\s*3%", "2%", text)
        text = re.sub(r"(?i)2%\s*a\s*3%", "2%", text)
        text = re.sub(
            r"(?i)de R\$ 8\.400 a R\$ 12\.600",
            "estimativa de R$ 8.400 se a base for R$ 420 mil",
            text,
        )
        if "2%" not in text:
            text += (
                "\n\nEm Uberlandia a aliquota municipal de ITBI para transmicoes "
                "onerosas e 2%, sujeita a avaliacao fiscal."
            )
        if "escrevente" not in text.lower():
            text += (
                "\n\nA escritura com valor declarado e calculada pela Tabela 1 MG 2026 "
                "e so e confirmada pelo escrevente. Registro de Imoveis e cobrado "
                "em cartorio de registro, separado. " + _HITL
            )
        elif (
            "registro de imoveis" not in text.lower() and "registro de imóveis" not in text.lower()
        ):
            text += "\n\nRegistro de Imoveis continua cobrado em separado pelo registro competente."

    if _has(user, "hospital") and _has(user, "procuracao", "procuração"):
        text = re.sub(r"(?i)lavrar a escritura", "lavrar procuracao publica", text)
        if "procuracao publica" not in text.lower() and "procuração pública" not in text.lower():
            text = (
                "Atendimento externo pode lavrar procuracao publica, com agenda e avaliacao da capacidade. "
                + text
            )
        if "laudo nao e obrigatorio" in text.lower() or "laudo não é obrigatório" in text.lower():
            text = re.sub(
                r"(?i)laudo n[aã]o [eé] obrigat[oó]rio\.?",
                "A capacidade e avaliada pela serventia; documentos medicos podem ser solicitados.",
                text,
            )
        if "escrevente" not in text.lower():
            text += "\n\n" + _HITL

    if _has(user, "ata notarial") or (
        _has(user, "ata ") and _has(user, "whatsapp", "instagram", "prova")
    ):
        text = re.sub(
            r"(?i)verifica a autenticidade[^.]*",
            "constata e descreve o que consegue perceber no dispositivo ou ambiente apresentado",
            text,
        )
        if "constata" not in text.lower() and "descreve" not in text.lower():
            text += (
                "\n\nA ata registra o que o tabeliao constata e descreve; "
                "nao garante que o perfil seja da pessoa alegada nem que o "
                "conteudo nunca tenha sido manipulado. " + _HITL
            )

    if _has(user, "horario", "funcionamento", "expediente") or _has(
        user, "sabado", "sábado", "abre o cartorio", "abre o cartório"
    ):
        text = re.sub(r"(?i)08h00", "09h00", text)
        text = re.sub(r"(?i)das\s+8h", "das 09h", text)
        text = re.sub(
            r"(?i)s[aá]bado[s]?(?:\s*:\s*|\s+)(?:08h00|8h)\s*[àaá]s\s*12h00",
            "sabados sem expediente regular",
            text,
        )
        if re.search(r"(?i)s[aá]bado", text) and re.search(
            r"(?i)(atende|abre|funcion|12h|08h)", text
        ):
            text += (
                "\n\nNao ha expediente regular aos sabados, domingos e feriados. "
                "Atendimento de balcao: segunda a sexta, das 09h as 17h."
            )
        elif "09h" not in text.lower() or "17h" not in text.lower():
            text += "\n\nAtendimento de balcao: segunda a sexta, das 09h as 17h."

    if _has(user, "protocolo", "segunda via", "horarios", "horários"):
        if re.search(r"(?i)catalogo do 2o|catálogo do 2", text):
            text = (
                "Nao localizei o protocolo informado nesta consulta automatica. "
                "Segunda via e horarios dependem de conferencia na serventia. " + _HITL
            )
        elif "catalogo" in text.lower() and "protocolo" in user.lower():
            text = (
                "Nao substituo consulta de protocolo por catalogo de servicos. "
                "Vou registrar o pedido em rascunho para o escrevente. " + _HITL
            )

    if _has(user, "tres firmas", "três firmas") or (
        _has(user, "firmas") and _has(user, "paginas", "páginas", "calcule")
    ):
        if "78,47" in text and "cartao" not in text.lower() and "ficha" not in text.lower():
            text += (
                "\n\nO total-base de R$ 78,47 considera tres reconhecimentos e "
                "quatro copias fisicas a R$ 11,21. Nao inclui a confeccao e "
                "guarda do cartao/ficha de assinatura (mais R$ 11,21 por "
                "signatario sem ficha nesta serventia)."
            )

    if _has(user, "lgpd", "exclusao", "exclusão", "consentimento", "dados pessoais", "cpf"):
        text = _protect_official(text)
        text = scrub(text).text
        text = _restore_official(text)
        if "dpo@2notasudi.com.br" not in text.lower():
            text += "\n\nDireitos LGPD: dpo@2notasudi.com.br."
        if (
            "draft" not in text.lower()
            and "escrevente" not in text.lower()
            and "dpo" not in text.lower()
        ):
            text += (
                "\n\nVou registrar o pedido em DRAFT e encaminhar ao DPO/escrevente. "
                "A eliminacao pode ser limitada por hipotese legal de conservacao."
            )
        elif "draft" not in text.lower():
            text += "\n\nPedido em DRAFT, com verificacao de identidade pelo DPO/escrevente."

    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
