"""Synthetic Evolution API v2.3.7 message-type payloads (G8.22.T1).

LGPD Art. 46: dados 100% fictícios. Todos os números/telefones/CPFs são
fabricados (start com `99*` ou `000*` — placeholder conhecido). Nunca use
dados reais de clientes.

Referência: https://doc.evolution-api.com/v2/api-reference (Baileys-derived).

Cada fixture é um webhook payload COMPLETO recebido via
``POST /api/v1/webhook/evolution``:

    {
      "event": "messages.upsert",
      "instance": "cartorio-2notas",
      "data": {
        "key": { "remoteJid": "...", "fromMe": false, "id": "..." },
        "pushName": "...",
        "messageType": "<evolutionType>",
        "message": { <typeSpecific> },
        "messageTimestamp": <unix>
      }
    }

Tipos cobertos:
- text       (conversation / extendedTextMessage)
- image      (imageMessage com caption opcional)
- audio      (audioMessage — PTT)
- document   (documentMessage — PDF etc)
- video      (videoMessage com caption opcional)
- sticker    (stickerMessage)
- location   (locationMessage — lat/lon + address)
- contact    (contactMessage — vCard embutido)
"""

from __future__ import annotations

FAKE_INSTANCE = "cartorio-2notas"
FAKE_REMOTE_JID = "5511999990001@s.whatsapp.net"
FAKE_GROUP_JID = "120363999999999999@g.us"
FAKE_PUSH_NAME = "Cliente Fixture"
FAKE_BASE_TS = 1712345678  # 2024-04-05 12:34:38 UTC — epoch estável


def _base(
    msg_id: str,
    message_type: str,
    message_body: dict,
    *,
    remote_jid: str = FAKE_REMOTE_JID,
    push_name: str = FAKE_PUSH_NAME,
    instance: str = FAKE_INSTANCE,
    timestamp: int = FAKE_BASE_TS,
    from_me: bool = False,
) -> dict:
    """Build the canonical Evolution API nested-format envelope.

    All 8 type fixtures reuse this so the only delta is the inner ``message``
    shape — which is exactly what real Evolution/Baileys does (varies only by
    ``messageType`` + the per-type inner payload).
    """
    return {
        "event": "messages.upsert",
        "instance": instance,
        "data": {
            "key": {
                "remoteJid": remote_jid,
                "fromMe": from_me,
                "id": msg_id,
            },
            "pushName": push_name,
            "messageType": message_type,
            "message": message_body,
            "messageTimestamp": timestamp,
        },
    }


# =============================================================================
#  1) TEXT — base de toda conversa. conversation OU extendedTextMessage.
# =============================================================================
EVOLUTION_TEXT: dict = _base(
    msg_id="FIX-text-001",
    message_type="conversation",
    message_body={
        "conversation": "Bom dia, gostaria de agendar uma autenticacao de copia",
    },
)


# =============================================================================
#  2) IMAGE — imageMessage com mimetype JPEG/PNG + caption opcional.
# =============================================================================
EVOLUTION_IMAGE: dict = _base(
    msg_id="FIX-image-002",
    message_type="imageMessage",
    message_body={
        "imageMessage": {
            "mimetype": "image/jpeg",
            "caption": "Segue foto do RG para conferencia",
            "fileLength": 184320,
            "height": 1080,
            "width": 1920,
            "jpegThumbnail": "/9j/4AAQSkZJRgABAQEA...",  # fake base64 prefix
            "url": "https://mmg.whatsapp.net/v/t62.7161-24/fake-mmid-placeholder",
            "mediaKey": "fake-media-key-9-placeholder=",
            "fileEncSha256": "a" * 64,
            "directPath": "/v/t62.7161-24/fake-direct-path",
        }
    },
)


# =============================================================================
#  3) AUDIO — audioMessage (PTT push-to-talk). ptt=true em audios de voz.
# =============================================================================
EVOLUTION_AUDIO: dict = _base(
    msg_id="FIX-audio-003",
    message_type="audioMessage",
    message_body={
        "audioMessage": {
            "mimetype": "audio/ogg; codecs=opus",
            "ptt": True,
            "fileLength": 12340,
            "seconds": 17,
            "url": "https://mmg.whatsapp.net/v/t62.7161-24/fake-audio-placeholder",
            "mediaKey": "fake-audio-key-placeholder=",
            "fileEncSha256": "b" * 64,
            "directPath": "/v/t62.7161-24/fake-audio-path",
            "waveform": "UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=",
        }
    },
)


# =============================================================================
#  4) DOCUMENT — documentMessage (PDF/DOCX etc). fileName obrigatório.
# =============================================================================
EVOLUTION_DOCUMENT: dict = _base(
    msg_id="FIX-doc-004",
    message_type="documentMessage",
    message_body={
        "documentMessage": {
            "mimetype": "application/pdf",
            "fileName": "documento_ficticio.pdf",
            "fileLength": 512000,
            "pageCount": 3,
            "url": "https://mmg.whatsapp.net/v/t62.7161-24/fake-doc-placeholder",
            "mediaKey": "fake-doc-key-placeholder=",
            "fileEncSha256": "c" * 64,
            "directPath": "/v/t62.7161-24/fake-doc-path",
        }
    },
)


# =============================================================================
#  5) VIDEO — videoMessage com mimetype MP4 + caption opcional.
# =============================================================================
EVOLUTION_VIDEO: dict = _base(
    msg_id="FIX-video-005",
    message_type="videoMessage",
    message_body={
        "videoMessage": {
            "mimetype": "video/mp4",
            "caption": "Video da assinatura gravada",
            "fileLength": 5242880,
            "height": 720,
            "width": 1280,
            "seconds": 42,
            "url": "https://mmg.whatsapp.net/v/t62.7161-24/fake-video-placeholder",
            "mediaKey": "fake-video-key-placeholder=",
            "fileEncSha256": "d" * 64,
            "directPath": "/v/t62.7161-24/fake-video-path",
            "jpegThumbnail": "/9j/4AAQSkZJRgABAQEA...",
        }
    },
)


# =============================================================================
#  6) STICKER — stickerMessage. Sem caption. mimetype image/webp.
# =============================================================================
EVOLUTION_STICKER: dict = _base(
    msg_id="FIX-sticker-006",
    message_type="stickerMessage",
    message_body={
        "stickerMessage": {
            "mimetype": "image/webp",
            "fileLength": 28672,
            "height": 512,
            "width": 512,
            "url": "https://mmg.whatsapp.net/v/t62.7161-24/fake-sticker-placeholder",
            "mediaKey": "fake-sticker-key-placeholder=",
            "fileEncSha256": "e" * 64,
            "directPath": "/v/t62.7161-24/fake-sticker-path",
        }
    },
)


# =============================================================================
#  7) LOCATION — locationMessage. lat/lon + address + name (opcional).
# =============================================================================
EVOLUTION_LOCATION: dict = _base(
    msg_id="FIX-loc-007",
    message_type="locationMessage",
    message_body={
        "locationMessage": {
            "degreesLatitude": -18.9128,  # Uberlândia MG (sintético)
            "degreesLongitude": -48.2755,
            "name": "Cartorio Sintetico",
            "address": "Rua Ficticia 1234, Centro, Uberlandia MG",
            "jpegThumbnail": "/9j/4AAQSkZJRgABAQEA...",
        }
    },
)


# =============================================================================
#  8) CONTACT (vCard) — contactMessage. displayName + vcard string.
# =============================================================================
EVOLUTION_CONTACT: dict = _base(
    msg_id="FIX-contact-008",
    message_type="contactMessage",
    message_body={
        "contactMessage": {
            "displayName": "Maria Ficticia",
            "vcard": (
                "BEGIN:VCARD\n"
                "VERSION:3.0\n"
                "FN:Maria Ficticia\n"
                "TEL;type=CELL:+551199990000\n"
                "END:VCARD"
            ),
        }
    },
)


# =============================================================================
#  Aggregate — index by name for pytest parametrize.
# =============================================================================
EVOLUTION_FIXTURES: dict[str, dict] = {
    "text": EVOLUTION_TEXT,
    "image": EVOLUTION_IMAGE,
    "audio": EVOLUTION_AUDIO,
    "document": EVOLUTION_DOCUMENT,
    "video": EVOLUTION_VIDEO,
    "sticker": EVOLUTION_STICKER,
    "location": EVOLUTION_LOCATION,
    "contact": EVOLUTION_CONTACT,
}
