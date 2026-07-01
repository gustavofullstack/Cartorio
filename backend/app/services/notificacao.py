"""Serviço de Notificações para Clientes.

Envia notificações via Telegram, WhatsApp (Evolution), Email e SMS.
Integra com N8N workflows e API endpoints.

LGPD compliance: NUNCA envia PII sem consentimento explícito.
"""

from __future__ import annotations
import enum
import logging
import re
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.cliente import Cliente
from app.services.audit import AuditService


def _strip_emojis(text: str) -> str:
    """Remove emojis de textos, deixando apenas caracteres normais."""
    if not text:
        return text
    pattern = re.compile(
        "["
        "\U0001f600-\U0001f64f"
        "\U0001f300-\U0001f5ff"
        "\U0001f680-\U0001f6ff"
        "\U0001f1e0-\U0001f1ff"
        "\u2700-\u27bf"
        "\u2600-\u26ff"
        "\u200d"
        "\ufe0f"
        "\U0001f900-\U0001f9ff"
        "\U0001fa70-\U0001faff"
        "]+",
        re.UNICODE,
    )
    cleaned = pattern.sub("", text)
    cleaned = re.sub(r"[\u2600-\u27BF]", "", cleaned)
    cleaned = re.sub(r" +", " ", cleaned)
    return cleaned.strip()


_log = logging.getLogger(__name__)


class NotificationMethod(str, enum.Enum):
    """Métodos de notificação suportados."""

    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    SMS = "sms"


class NotificationService:
    """Serviço centralizado para envio de notificações."""

    @staticmethod
    async def enviar_notificacao(
        db: Session,
        cliente_id: int,
        mensagem: str,
        *,
        metodo: NotificationMethod | None = None,
        context: dict[str, Any] | None = None,
        request: Any = None,
    ) -> bool:
        """Envia notificação para cliente usando método preferido ou especificado.

        Args:
            db: Sessão do banco
            cliente_id: ID do cliente
            mensagem: Texto da notificação
            metodo: Método específico (opcional, usa preferido se None)
            context: Contexto adicional para audit log
            request: Objeto request para audit context

        Returns:
            True se notificação enviada com sucesso

        Raises:
            ValueError: Se cliente não encontrado ou sem método válido
        """
        cliente = db.execute(select(Cliente).where(Cliente.id == cliente_id)).scalar_one_or_none()

        if cliente is None:
            raise ValueError(f"Cliente #{cliente_id} não encontrado")

        # Determinar método de notificação
        metodo_final = metodo or cliente.preferred_contact_method
        if metodo_final is None:
            # Usar método preferido: Telegram > WhatsApp > Email > SMS
            if cliente.telegram_chat_id:
                metodo_final = NotificationMethod.TELEGRAM
            elif cliente.whatsapp_number:
                metodo_final = NotificationMethod.WHATSAPP
            elif cliente.email:
                metodo_final = NotificationMethod.EMAIL
            elif cliente.telefone_hash:
                metodo_final = NotificationMethod.SMS
            else:
                raise ValueError(f"Cliente #{cliente_id} não tem método de contato configurado")

        # Verificar consentimento
        if not cliente.consentimento_lgpd:
            _log.warning("Cliente %d sem consentimento LGPD — notificação bloqueada", cliente_id)
            return False

        # Enviar notificação
        success = False
        match metodo_final:
            case NotificationMethod.TELEGRAM:
                if cliente.telegram_chat_id is None:
                    _log.warning("Cliente %d sem telegram_chat_id", cliente_id)
                    return False
                success = await NotificationService._enviar_telegram(
                    cliente.telegram_chat_id, mensagem
                )
            case NotificationMethod.WHATSAPP:
                if cliente.whatsapp_number is None:
                    _log.warning("Cliente %d sem whatsapp_number", cliente_id)
                    return False
                success = await NotificationService._enviar_whatsapp(
                    cliente.whatsapp_number, mensagem
                )
            case NotificationMethod.EMAIL:
                if cliente.email is None:
                    _log.warning("Cliente %d sem email", cliente_id)
                    return False
                success = await NotificationService._enviar_email(cliente.email, mensagem)
            case NotificationMethod.SMS:
                if cliente.telefone_hash is None:
                    _log.warning("Cliente %d sem telefone_hash", cliente_id)
                    return False
                success = await NotificationService._enviar_sms(cliente.telefone_hash, mensagem)

        # Audit log
        if success:
            AuditService.log(
                db,
                actor_id="system:notificacao",
                actor_type="system",
                action="notificacao.sent",
                resource=f"cliente:{cliente_id}",
                payload={
                    "metodo": metodo_final,
                    "mensagem_len": len(mensagem),
                    "context": context or {},
                },
            )

        return success

    @staticmethod
    async def _enviar_telegram(chat_id: str, mensagem: str) -> bool:
        """Envia notificação via Telegram Bot API."""
        if not settings.telegram_bot_token:
            _log.error("TELEGRAM_BOT_TOKEN não configurado")
            return False

        cleaned_msg = _strip_emojis(mensagem)
        url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    url,
                    json={"chat_id": chat_id, "text": cleaned_msg, "parse_mode": "HTML"},
                )
                return response.status_code == 200
        except Exception as e:
            _log.exception("Falha ao enviar Telegram: %s", e)
            return False

    @staticmethod
    async def _enviar_whatsapp(number: str, mensagem: str) -> bool:
        """Envia notificação via Evolution API (WhatsApp)."""
        if not settings.evolution_api_key:
            _log.error("EVOLUTION_API_KEY não configurado")
            return False

        cleaned_msg = _strip_emojis(mensagem)
        url = (
            f"{settings.evolution_base_url.rstrip('/')}/message/sendText/"
            f"{settings.evolution_instance}"
        )

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    url,
                    headers={"apikey": settings.evolution_api_key},
                    json={"number": number, "text": cleaned_msg},
                )
                return response.status_code == 200
        except Exception as e:
            _log.exception("Falha ao enviar WhatsApp: %s", e)
            return False

    @staticmethod
    async def enviar_whatsapp_reaction(number: str, message_id: str, emoji: str) -> bool:
        """Envia reação a uma mensagem do WhatsApp via Evolution API."""
        if not settings.evolution_api_key:
            _log.error("EVOLUTION_API_KEY não configurado")
            return False
        url = f"{settings.evolution_base_url.rstrip('/')}/message/sendReaction/{settings.evolution_instance}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    url,
                    headers={"apikey": settings.evolution_api_key},
                    json={
                        "number": number,
                        "reaction": emoji,
                        "key": {
                            "remoteJid": f"{number}@s.whatsapp.net",
                            "fromMe": False,
                            "id": message_id,
                        },
                    },
                )
                return response.status_code == 200
        except Exception as e:
            _log.exception("Falha ao enviar WhatsApp reaction: %s", e)
            return False

    @staticmethod
    async def enviar_whatsapp_poll(number: str, question: str, options: list[str]) -> bool:
        """Envia enquete no WhatsApp via Evolution API."""
        if not settings.evolution_api_key:
            _log.error("EVOLUTION_API_KEY não configurado")
            return False
        url = f"{settings.evolution_base_url.rstrip('/')}/message/sendPoll/{settings.evolution_instance}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    url,
                    headers={"apikey": settings.evolution_api_key},
                    json={
                        "number": number,
                        "pollName": _strip_emojis(question),
                        "options": [_strip_emojis(o) for o in options],
                        "selectableOptionsCount": 1,
                    },
                )
                return response.status_code == 200
        except Exception as e:
            _log.exception("Falha ao enviar WhatsApp poll: %s", e)
            return False

    @staticmethod
    async def enviar_whatsapp_media(
        number: str, media_url: str, mediatype: str, filename: str, caption: str | None = None
    ) -> bool:
        """Envia mídia (image/document) no WhatsApp via Evolution API."""
        if not settings.evolution_api_key:
            _log.error("EVOLUTION_API_KEY não configurado")
            return False
        url = f"{settings.evolution_base_url.rstrip('/')}/message/sendMedia/{settings.evolution_instance}"
        try:
            media_msg: dict[str, Any] = {
                "mediatype": mediatype,
                "fileName": filename,
                "media": media_url,
            }
            if caption:
                media_msg["caption"] = _strip_emojis(caption)
            payload = {
                "number": number,
                "mediaMessage": media_msg,
            }
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    url, headers={"apikey": settings.evolution_api_key}, json=payload
                )
                return response.status_code == 200
        except Exception as e:
            _log.exception("Falha ao enviar WhatsApp media: %s", e)
            return False

    @staticmethod
    async def _enviar_email(email: str, mensagem: str) -> bool:
        """Envia notificação via email (placeholder para integração futura)."""
        # TODO: Implementar integração com serviço de email (SendGrid, Mailgun, etc.)
        _log.info("Email placeholder: %s → %s", email, mensagem[:50])
        return True  # Simula sucesso para testes

    @staticmethod
    async def _enviar_sms(telefone_hash: str, mensagem: str) -> bool:
        """Envia notificação via SMS (placeholder para integração futura)."""
        # TODO: Implementar integração com gateway SMS
        _log.info("SMS placeholder: %s → %s", telefone_hash[:8], mensagem[:50])
        return True  # Simula sucesso para testes

    @staticmethod
    async def notificar_agendamento_criado(
        db: Session,
        cliente_id: int,
        agendamento_id: int,
        titulo: str,
        data_hora: str,
        local: str,
        *,
        request: Any = None,
    ) -> bool:
        """Notifica cliente sobre novo agendamento criado."""
        mensagem = (
            f"✅ <b>Agendamento criado com sucesso!</b>\n\n"
            f"📋 <b>Título:</b> {titulo}\n"
            f"📅 <b>Data/Hora:</b> {data_hora}\n"
            f"📍 <b>Local:</b> {local}\n\n"
            f"🔔 Lembrete: Chegue 15 minutos antes.\n"
            f"💬 ID do agendamento: #{agendamento_id}"
        )

        return await NotificationService.enviar_notificacao(
            db,
            cliente_id,
            mensagem,
            context={"agendamento_id": agendamento_id, "tipo": "criado"},
            request=request,
        )

    @staticmethod
    async def notificar_agendamento_lembrete(
        db: Session,
        cliente_id: int,
        agendamento_id: int,
        titulo: str,
        data_hora: str,
        local: str,
        *,
        request: Any = None,
    ) -> bool:
        """Notifica cliente com lembrete de agendamento."""
        mensagem = (
            f"🔔 <b>Lembrete de Agendamento</b>\n\n"
            f"📋 <b>Título:</b> {titulo}\n"
            f"📅 <b>Data/Hora:</b> {data_hora}\n"
            f"📍 <b>Local:</b> {local}\n\n"
            f"⏰ <b>Importante:</b> Seu agendamento está próximo!\n"
            f"💬 ID do agendamento: #{agendamento_id}"
        )

        return await NotificationService.enviar_notificacao(
            db,
            cliente_id,
            mensagem,
            context={"agendamento_id": agendamento_id, "tipo": "lembrete"},
            request=request,
        )

    @staticmethod
    async def notificar_agendamento_cancelado(
        db: Session,
        cliente_id: int,
        agendamento_id: int,
        titulo: str,
        *,
        request: Any = None,
    ) -> bool:
        """Notifica cliente sobre cancelamento de agendamento."""
        mensagem = (
            f"❌ <b>Agendamento cancelado</b>\n\n"
            f"📋 <b>Título:</b> {titulo}\n"
            f"💬 ID do agendamento: #{agendamento_id}\n\n"
            f"📅 <b>Observação:</b> Seu agendamento foi cancelado.\n"
            f"Entre em contato se precisar reagendar."
        )

        return await NotificationService.enviar_notificacao(
            db,
            cliente_id,
            mensagem,
            context={"agendamento_id": agendamento_id, "tipo": "cancelado"},
            request=request,
        )
