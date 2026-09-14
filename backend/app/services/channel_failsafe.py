"""Respostas fail-safe para capacidades indisponiveis nos canais do cartorio.

Este modulo e deliberadamente puro: ele nao chama N8N, Chatwoot, agenda ou LLM.
O pipeline usa as respostas abaixo quando uma acao nao pode ser concluida com
seguranca, evitando promessas de transferencia ou agendamento inexistentes.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChannelFailSafe:
    """Resposta institucional deterministica e seu motivo auditavel."""

    reason: str
    text: str


_HUMAN_HANDOFF = ChannelFailSafe(
    reason="human_handoff_unavailable",
    text=(
        "Entendi que você quer falar com um escrevente. "
        "Este canal automático não consegue transferir a conversa neste momento. "
        "Procure o atendimento humano do 2º Tabelionato de Notas, de segunda a sexta, "
        "das 9h às 17h."
    ),
)

_SCHEDULING = ChannelFailSafe(
    reason="scheduling_confirmation_unavailable",
    text=(
        "Posso ajudar a organizar o pedido, mas este canal automático não confirma "
        "agendamentos. A data e o horário precisam ser validados por um escrevente. "
        "Procure o atendimento humano do 2º Tabelionato de Notas, de segunda a sexta, "
        "das 9h às 17h."
    ),
)

_HUMAN_REQUEST_REGISTERED = ChannelFailSafe(
    reason="human_request_registered",
    text=(
        "Seu pedido foi registrado na fila local para análise de um escrevente. "
        "Isso não confirma uma transferência imediata nem um prazo de resposta. "
        "O atendimento humano funciona de segunda a sexta, das 9h às 17h."
    ),
)

_SCHEDULING_REQUEST_REGISTERED = ChannelFailSafe(
    reason="scheduling_request_registered",
    text=(
        "Seu pedido de agendamento foi registrado na fila local para validação de um "
        "escrevente. Nenhuma data ou horário está confirmado. O atendimento humano "
        "funciona de segunda a sexta, das 9h às 17h."
    ),
)

_UNSUPPORTED_MEDIA = ChannelFailSafe(
    reason="unsupported_media",
    text=(
        "Recebi uma mídia, mas este canal automático ainda não consegue analisar esse "
        "conteúdo com segurança. Não vou interpretar nem confirmar o documento, áudio "
        "ou imagem. Reenvie a solicitação em texto ou procure um escrevente, de segunda "
        "a sexta, das 9h às 17h."
    ),
)

_WHATSAPP_TEXT_TYPES = frozenset(
    {
        "conversation",
        "extendedtextmessage",
        "pollupdatemessage",
        "pollcreationmessage",
        "pollcreationmessagev2",
        "pollcreationmessagev3",
    }
)


def action_failsafe(action: str | None) -> ChannelFailSafe | None:
    """Retorna resposta segura para acoes sem integracao operacional ativa."""

    normalized = (action or "").strip().lower()
    if normalized == "humano":
        return _HUMAN_HANDOFF
    if normalized == "agendar":
        return _SCHEDULING
    return None


def registered_action_failsafe(action: str | None) -> ChannelFailSafe | None:
    """Retorna texto verdadeiro apenas depois da persistencia local auditada."""

    normalized = (action or "").strip().lower()
    if normalized == "humano":
        return _HUMAN_REQUEST_REGISTERED
    if normalized == "agendar":
        return _SCHEDULING_REQUEST_REGISTERED
    return None


def unsupported_whatsapp_media(message_type: object) -> ChannelFailSafe | None:
    """Classifica como midia qualquer tipo Evolution que nao seja texto conhecido.

    Um tipo vazio permanece fora deste gate para preservar compatibilidade com os
    payloads legados da Evolution API, que podem omitir ``messageType``.
    """

    if not isinstance(message_type, str):
        return None
    normalized = message_type.strip().lower()
    if not normalized or normalized in _WHATSAPP_TEXT_TYPES:
        return None
    return _UNSUPPORTED_MEDIA
