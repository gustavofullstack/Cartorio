"""Pydantic v2 schemas for webhook receiver payloads (G8.17.T2).

LGPD-by-design: cada campo com dado pessoal eh explicitamente marcado via
`PIIField` (prefixo `**LGPD PII**` + json_schema_extra `x-pii: True`).
Ferramentas externas (LGPD scanner, OpenAPI extension) podem filtrar/redatar
sem precisar introspeccao manual.

Schemas cobertos:
- TelegramUpdate / TelegramMessage / TelegramUser / TelegramChat
- EvolutionPayload (nested + legacy dual-format)
- ChatwootWebhookModel (event discriminator)
- N8nErrorRequest / N8nDeletionRequest / N8nMetricsIngest
- AlertManagerPayload / AlertLabel / AlertAnnotation / AlertEntry (G8.15.T2)
- OutboxDispatchRequest (Supabase outbox -> cartorio)

Cada schema:
- `model_config = ConfigDict(strict=True, extra="ignore")` (forward-compat com
  vendor changes - Telegram/Evolution/Chatwoot adicionam campos sem aviso).
- 100% dos campos com `Field(description=...)`.
- Pelo menos 1 `examples=[...]` por schema.
- Defaults explicitos onde faz sentido (chat_id, edit_date, etc).
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.services.pii_marker import PIIField

from app.schemas.chatwoot_webhook import (  # noqa: F401  (re-exported)
    ChatwootAssignee,
    ChatwootConversationRef,
    ChatwootConversationStatusChanged,
    ChatwootMessageCreated,
    ChatwootWebhookModel,
)

_WEBHOOK_CONFIG = ConfigDict(
    strict=True,
    extra="ignore",
    populate_by_name=True,
)


class TelegramUser(BaseModel):
    """Remetente de uma mensagem Telegram.

    LGPD: `id`, `username`, `first_name`, `last_name` sao identificadores
    pessoais. NAO ecoar em logs/responses sem scrubber.
    """

    model_config = _WEBHOOK_CONFIG

    id: Annotated[
        int,
        PIIField(
            description="Identificador unico do usuario no Telegram (LGPD: pseudonimo).",
            examples=[123456789],
        ),
    ]
    is_bot: Annotated[
        bool | None,
        Field(
            default=None,
            description="True se o usuario eh outro bot.",
            examples=[False],
        ),
    ] = None
    first_name: Annotated[
        str | None,
        PIIField(
            default=None,
            description="Primeiro nome (LGPD PII).",
            max_length=255,
        ),
    ] = None
    last_name: Annotated[
        str | None,
        PIIField(
            default=None,
            description="Ultimo nome (LGPD PII).",
            max_length=255,
        ),
    ] = None
    username: Annotated[
        str | None,
        PIIField(
            default=None,
            description="Handle publico do Telegram sem @ (LGPD: pode ser PII se unico).",
            max_length=64,
        ),
    ] = None
    language_code: Annotated[
        str | None,
        Field(
            default=None,
            description="Codigo IETF do idioma preferido (ex: 'pt-BR').",
            max_length=10,
        ),
    ] = None


class TelegramChat(BaseModel):
    """Chat onde a mensagem foi enviada (private, group, supergroup, channel).

    LGPD: `id` eh o identificador do chat. Em grupos, exposto a todos os membros.
    """

    model_config = _WEBHOOK_CONFIG

    id: Annotated[
        int,
        PIIField(
            description="ID do chat no Telegram. Negativo para grupos/canais.",
            examples=[-1004331849032, 123456789],
        ),
    ]
    type: Annotated[
        str,
        Field(
            description="Tipo do chat: 'private', 'group', 'supergroup', 'channel'.",
            pattern="^(private|group|supergroup|channel)$",
            examples=["private", "supergroup"],
        ),
    ]
    title: Annotated[
        str | None,
        Field(
            default=None,
            description="Titulo do chat (apenas para grupos/canais).",
            max_length=255,
        ),
    ] = None
    username: Annotated[
        str | None,
        Field(
            default=None,
            description="Username publico do chat (supergroup/canal).",
            max_length=64,
        ),
    ] = None
    first_name: Annotated[
        str | None,
        PIIField(
            default=None,
            description="Primeiro nome (apenas chat privado).",
            max_length=255,
        ),
    ] = None
    last_name: Annotated[
        str | None,
        PIIField(
            default=None,
            description="Ultimo nome (apenas chat privado).",
            max_length=255,
        ),
    ] = None


class TelegramMessage(BaseModel):
    """Mensagem recebida pelo bot Telegram.

    LGPD: `text`/`caption` sao PII por conter fala do usuario.
    `from_` identifica o remetente. Forward de mensagem preserva origem.
    """

    model_config = _WEBHOOK_CONFIG

    message_id: Annotated[
        int,
        Field(
            description="ID unico da mensagem dentro do chat.",
            ge=1,
            examples=[42],
        ),
    ]
    message_thread_id: Annotated[
        int | None,
        Field(
            default=None,
            description="ID do topico (forum supergroup).",
            ge=1,
        ),
    ] = None
    from_: Annotated[
        TelegramUser | None,
        PIIField(
            default=None,
            alias="from",
            description="Remetente (LGPD PII). Null para mensagens de canal.",
        ),
    ] = None
    sender_chat: Annotated[
        TelegramChat | None,
        PIIField(
            default=None,
            description="Chat que enviou a mensagem (se diferente de from).",
        ),
    ] = None
    date: Annotated[
        int,
        Field(
            description="Unix timestamp de quando a mensagem foi enviada.",
            examples=[1721308800],
        ),
    ]
    chat: Annotated[
        TelegramChat,
        PIIField(description="Chat onde a mensagem foi postada (LGPD PII)."),
    ]
    text: Annotated[
        str | None,
        PIIField(
            default=None,
            description="Texto plain-text da mensagem (LGPD PII: pode conter CPF/RG/nome).",
            max_length=4096,
        ),
    ] = None
    caption: Annotated[
        str | None,
        PIIField(
            default=None,
            description="Legenda de midia (foto/doc/video).",
            max_length=1024,
        ),
    ] = None
    edit_date: Annotated[
        int | None,
        Field(
            default=None,
            description="Unix timestamp da ultima edicao. Presente apenas em edits.",
        ),
    ] = None


class TelegramCallbackQuery(BaseModel):
    """Callback query de botao inline (callback_data).

    LGPD: `from_` identifica o usuario que clicou no botao.
    """

    model_config = _WEBHOOK_CONFIG

    id: Annotated[
        str,
        Field(
            description="ID do callback query (necessario para answerCallbackQuery).",
            examples=["12345678901234567"],
        ),
    ]
    from_: Annotated[
        TelegramUser,
        PIIField(alias="from", description="Usuario que clicou (LGPD PII)."),
    ]
    chat_instance: Annotated[
        str,
        Field(
            description="Identificador global da instancia do chat no client.",
            max_length=64,
        ),
    ]
    data: Annotated[
        str | None,
        PIIField(
            default=None,
            description="callback_data do botao (ate 64 bytes).",
            max_length=64,
            examples=["cmd:agendar", "servico:procuracao"],
        ),
    ] = None
    message: Annotated[
        TelegramMessage | None,
        PIIField(default=None, description="Mensagem que continha o botao."),
    ] = None


class TelegramUpdate(BaseModel):
    """Payload completo de update do Telegram Bot API.

    LGPD: `message.from`, `callback_query.from` sao PII.
    Raw `message.text` NAO deve ir para LLM sem PII scrub (3 camadas).

    Ref: https://core.telegram.org/bots/api#update
    """

    model_config = _WEBHOOK_CONFIG

    update_id: Annotated[
        int,
        Field(
            description="ID unico do update. Usado como idempotency key no Redis SETNX.",
            ge=1,
            examples=[123456789],
        ),
    ]
    message: Annotated[
        TelegramMessage | None,
        PIIField(
            default=None,
            description="Nova mensagem recebida. Ausente para edits/callbacks.",
        ),
    ] = None
    edited_message: Annotated[
        TelegramMessage | None,
        PIIField(
            default=None,
            description="Mensagem editada pelo usuario (LGPD PII).",
        ),
    ] = None
    callback_query: Annotated[
        TelegramCallbackQuery | None,
        PIIField(
            default=None,
            description="Callback query de botao inline (LGPD PII).",
        ),
    ] = None
    my_chat_member: Annotated[
        dict[str, Any] | None,
        Field(
            default=None,
            description="Mudanca de status do bot no chat (added/removed/promoted).",
        ),
    ] = None


class EvolutionKey(BaseModel):
    """Chave de identificacao da mensagem WhatsApp (Evolution API).

    LGPD: `remoteJid` identifica o usuario (formato `5511999999999@s.whatsapp.net`).
    """

    model_config = _WEBHOOK_CONFIG

    remote_jid: Annotated[
        str,
        PIIField(
            alias="remoteJid",
            description="JID do remetente WhatsApp (LGPD PII: phone number).",
            examples=["5511999999999@s.whatsapp.net", "120363@g.us"],
        ),
    ]
    from_me: Annotated[
        bool | None,
        Field(
            default=None,
            alias="fromMe",
            description="True se a mensagem foi enviada pelo bot.",
            examples=[False],
        ),
    ] = None
    id: Annotated[
        str | None,
        Field(
            default=None,
            description="ID da mensagem (idempotency key).",
            examples=["3EB0C8E5C2B6F1A0"],
        ),
    ] = None


class EvolutionMessage(BaseModel):
    """Conteudo da mensagem Evolution (WhatsApp).

    LGPD: `conversation` ou `extendedTextMessage.text` carregam fala do usuario.
    """

    model_config = _WEBHOOK_CONFIG

    conversation: Annotated[
        str | None,
        PIIField(
            default=None,
            description="Texto da mensagem plain (LGPD PII).",
            max_length=10000,
        ),
    ] = None
    extended_text_message: Annotated[
        dict[str, Any] | None,
        PIIField(
            default=None,
            alias="extendedTextMessage",
            description="Mensagem de texto estendida (links, mentions, format).",
        ),
    ] = None


class EvolutionPayload(BaseModel):
    """Payload completo do webhook Evolution API (WhatsApp).

    LGPD: dual-format (nested data.* OU root-level legado). Backend aceita
    ambos - ver `parse_evolution_payload` em whatsapp.py.

    Ref: https://doc.evolution-api.com/v2/api-reference
    """

    model_config = _WEBHOOK_CONFIG

    event: Annotated[
        str | None,
        Field(
            default=None,
            description="Tipo do evento. Aceito: 'messages.upsert'. Outros sao ignorados.",
            examples=["messages.upsert"],
        ),
    ] = None
    instance: Annotated[
        str | None,
        Field(
            default=None,
            description="Nome da instancia Evolution (ex: 'cartorio-2notas').",
            max_length=128,
            examples=["cartorio-2notas"],
        ),
    ] = None
    data: Annotated[
        dict[str, Any] | None,
        PIIField(
            default=None,
            description="Bloco data (formato moderno). Contem key/message/pushName.",
        ),
    ] = None
    key: Annotated[
        EvolutionKey | None,
        PIIField(default=None, description="Chave no root-level (formato legado)."),
    ] = None
    message: Annotated[
        EvolutionMessage | None,
        PIIField(default=None, description="Mensagem no root-level (formato legado)."),
    ] = None
    sender: Annotated[
        str | None,
        PIIField(
            default=None,
            description="Sender no root-level (formato legado, phone number).",
        ),
    ] = None
    message_type: Annotated[
        str | None,
        Field(
            default=None,
            alias="messageType",
            description="Tipo da mensagem (conversation, extendedTextMessage, etc).",
            max_length=64,
        ),
    ] = None
    push_name: Annotated[
        str | None,
        PIIField(
            default=None,
            alias="pushName",
            description="Nome do contato no WhatsApp (LGPD PII).",
            max_length=255,
        ),
    ] = None


class N8nErrorRequest(BaseModel):
    """Payload do webhook N8N Error Workflow Global (B6).

    LGPD: `error.message` pode conter stack traces com paths/dados sensiveis.
    Backend hasheia antes de gravar no audit log (defense in depth).
    """

    model_config = _WEBHOOK_CONFIG

    workflow_name: Annotated[
        str,
        Field(
            description="Nome do workflow N8N que falhou.",
            min_length=1,
            max_length=256,
            examples=["01 - Consulta Emolumento"],
        ),
    ]
    workflow_id: Annotated[
        str | None,
        Field(
            default=None,
            description="ID do workflow N8N (opcional).",
            max_length=128,
            examples=["wf_abc123"],
        ),
    ] = None
    execution_id: Annotated[
        str,
        Field(
            description="ID unico da execucao N8N (idempotency key).",
            min_length=1,
            max_length=128,
            examples=["exec_xyz789"],
        ),
    ]
    error_type: Annotated[
        str | None,
        Field(
            default=None,
            description="Tipo classificado (connection|http_4xx|http_5xx|timeout|validation|auth|unknown).",
            max_length=64,
            examples=["http_5xx"],
        ),
    ] = None
    error: Annotated[
        dict[str, Any] | None,
        Field(
            default=None,
            description="Dict com detalhes: name, message, http_code, stack (opcional).",
        ),
    ] = None
    node: Annotated[
        str | None,
        Field(
            default=None,
            description="Node do N8N que falhou.",
            max_length=128,
            examples=["HTTP Request"],
        ),
    ] = None
    timestamp: Annotated[
        str | None,
        Field(
            default=None,
            description="ISO 8601 UTC do momento do erro.",
            max_length=64,
            examples=["2026-07-18T12:34:56Z"],
        ),
    ] = None


class N8nDeletionRequest(BaseModel):
    """Payload do webhook N8N Deletion Log (S2.T2 - LGPD Art. 18).

    LGPD: registra purga fisica de dados (categoria + count). Backend grava
    no audit_log com action='n8n.deletion' para fins de compliance.
    """

    model_config = _WEBHOOK_CONFIG

    execution_id: Annotated[
        str,
        Field(
            description="ID unico da execucao N8N (idempotency key).",
            min_length=1,
            max_length=128,
        ),
    ]
    target_category: Annotated[
        str,
        Field(
            description="Categoria de registros deletados.",
            min_length=1,
            max_length=128,
            examples=["conversas", "clientes", "audit_logs"],
        ),
    ]
    deleted_count: Annotated[
        int,
        Field(
            description="Quantidade de linhas fisicas removidas.",
            ge=0,
            examples=[42],
        ),
    ]
    details: Annotated[
        dict[str, Any] | None,
        Field(
            default=None,
            description="Informacoes adicionais da execucao (opcional).",
        ),
    ] = None


class N8nMetricsIngest(BaseModel):
    """Payload do webhook N8N Metrics Ingest.

    LGPD: contadores agregados NAO carregam PII. So incrementam Prometheus
    counters. Seguro sem scrub.
    """

    model_config = _WEBHOOK_CONFIG

    workflow_name: Annotated[
        str,
        Field(
            description="Nome do workflow N8N que executou.",
            min_length=1,
            max_length=256,
            examples=["02 - Criar Protocolo"],
        ),
    ]
    execution_id: Annotated[
        str,
        Field(
            description="ID unico da execucao.",
            min_length=1,
            max_length=128,
        ),
    ]
    status: Annotated[
        Literal["success", "error", "running"],
        Field(
            description="Status final da execucao.",
            examples=["success", "error"],
        ),
    ]
    duration_ms: Annotated[
        int,
        Field(
            description="Duracao da execucao em ms.",
            ge=0,
            examples=[1234],
        ),
    ]
    items_processed: Annotated[
        int | None,
        Field(
            default=None,
            description="Quantidade de items processados (se aplicavel).",
            ge=0,
        ),
    ] = None
    error: Annotated[
        str | None,
        Field(
            default=None,
            description="Mensagem de erro (apenas se status='error').",
            max_length=2048,
        ),
    ] = None


class OutboxDispatchRequest(BaseModel):
    """Payload do webhook Supabase outbox_messages -> cartorio.

    LGPD: pode carregar qualquer tipo de mensagem (chat/text/etc).
    Conteudo passa por PII scrub antes de qualquer LLM call.
    """

    model_config = _WEBHOOK_CONFIG

    outbox_id: Annotated[
        str,
        Field(
            description="ID do registro em outbox_messages (idempotency key).",
            min_length=1,
            max_length=64,
        ),
    ]
    canal: Annotated[
        Literal["whatsapp", "telegram", "email", "sms"],
        Field(
            description="Canal destino da mensagem.",
            examples=["whatsapp"],
        ),
    ]
    recipient_id: Annotated[
        str,
        PIIField(
            description="Identificador do destinatario (phone/chat_id/email).",
            max_length=255,
        ),
    ]
    content: Annotated[
        str,
        PIIField(
            description="Conteudo da mensagem (LGPD PII: pode conter dados pessoais).",
            max_length=8192,
        ),
    ]
    priority: Annotated[
        int | None,
        Field(
            default=None,
            description="Prioridade (0=normal, 1=alta, 2=P0).",
            ge=0,
            le=2,
        ),
    ] = None


from app.schemas.webhook_alertmanager import (  # noqa: E402, F401
    AlertAnnotation,
    AlertEntry,
    AlertLabel,
    AlertManagerPayload,
)

__all__ = [
    "TelegramUpdate",
    "TelegramMessage",
    "TelegramUser",
    "TelegramChat",
    "TelegramCallbackQuery",
    "EvolutionPayload",
    "EvolutionKey",
    "EvolutionMessage",
    "N8nErrorRequest",
    "N8nDeletionRequest",
    "N8nMetricsIngest",
    "ChatwootWebhookModel",
    "ChatwootMessageCreated",
    "ChatwootConversationStatusChanged",
    "ChatwootConversationRef",
    "ChatwootAssignee",
    "AlertManagerPayload",
    "AlertEntry",
    "AlertLabel",
    "AlertAnnotation",
    "OutboxDispatchRequest",
]
