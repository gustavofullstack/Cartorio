#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lark Bot Server — webhook receiver + responder
Gustavo Almeida · 2026-07-28

Minimal Flask server que:
1. Recebe challenge handshake do Lark (URL verification)
2. Recebe eventos im.message.receive_v1
3. Verifica signature com Verification Token
4. Responde com texto simples (sem precisar de LLM por enquanto)

Setup:
  1. Cria app custom bot em https://open.larksuite.com (Developer Console)
  2. Liga permissões (ver SETUP.md):
     - im:message, im:message.group_at_msg, im:message.p2_msg
  3. Event Subscription → Request URL: https://<seu-tunnel>/lark/webhook
  4. Copia App ID + App Secret + Verification Token → preenche em .env
  5. Roda: python3 lark_bot_server.py

Pra expor o webhook publicamente (teste local):
  cloudflared tunnel --url http://localhost:8080
"""
import os
import json
import hmac
import hashlib
import base64
from datetime import datetime
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# Config (via env vars)
APP_ID = os.getenv("LARK_APP_ID", "")
APP_SECRET = os.getenv("LARK_APP_SECRET", "")
VERIFICATION_TOKEN = os.getenv("LARK_VERIFICATION_TOKEN", "")
ENCRYPT_KEY = os.getenv("LARK_ENCRYPT_KEY", "")
PORT = int(os.getenv("LARK_BOT_PORT", "8080"))

# Log estruturado
def log(level, msg, **kw):
    ts = datetime.utcnow().isoformat()
    print(f"[{ts}] [{level}] {msg} {kw if kw else ''}", flush=True)


# === Handshake (URL verification) ===
@app.route("/lark/webhook", methods=["POST"])
def webhook():
    body = request.get_json(silent=True) or {}

    # 1. Challenge handshake
    if body.get("type") == "url_verification":
        log("INFO", "challenge received", challenge_len=len(body.get("challenge", "")))
        return jsonify({"challenge": body.get("challenge", "")})

    # 2. Evento assinado (header tem token + event_type)
    # Lark envia: header { app_id, event_id, event_type, tenant_key, token, timestamp }
    try:
        # Em produção, validar signature aqui
        header = body.get("header", {})
        event = body.get("event", {})
        event_type = header.get("event_type", "")

        log("INFO", "event received", type=event_type, event_id=header.get("event_id"))

        if event_type == "im.message.receive_v1":
            handle_message(event)
        # Outros eventos (bot added to chat, etc.)
        else:
            log("DEBUG", "unhandled event", type=event_type)

        return jsonify({"code": 0, "msg": "ok"})

    except Exception as e:
        log("ERROR", "webhook handler failed", error=str(e))
        return jsonify({"code": -1, "msg": str(e)}), 200


def handle_message(event):
    """Processa mensagem recebida e responde."""
    msg = event.get("message", {})
    chat_id = msg.get("chat_id")
    chat_type = msg.get("chat_type", "p2p")  # 'p2p' ou 'group'
    sender_id = event.get("sender", {}).get("sender_id", {}).get("open_id", "unknown")
    text = (msg.get("content") or {}).get("text", "").strip()
    mentions = msg.get("mentions", [])

    # Log
    log("INFO", "message", chat=chat_type, sender=sender_id[:12], text=text[:80])

    # Em grupo, só responde se @mencionado OU se for trigger manual "!"
    is_at_bot = any(m.get("id", {}).get("open_id") == APP_ID for m in mentions)
    if chat_type == "group" and not is_at_bot and not text.startswith("!"):
        log("DEBUG", "skipping group msg (not @bot)")
        return

    # Limpa @bot do texto
    clean_text = text
    for m in mentions:
        key = m.get("key", "")
        if key:
            clean_text = clean_text.replace(key, "").strip()
    clean_text = clean_text.lstrip("!").strip()

    if not clean_text:
        reply = "Oi! Manda uma pergunta (ex: 'que dia é hoje', 'calcula emolumento procuração')."
    else:
        # Aqui você pluga o agent real (PIETRA, LLM, etc.)
        # Por enquanto, echo + timestamp
        reply = f"Recebi: **{clean_text}**\n\n_(bot respondendo, sem LLM plugado ainda)_\n⏰ {datetime.utcnow().isoformat()}Z"

    send_message(chat_id, reply, chat_type)


def send_message(chat_id, text, chat_type="p2p"):
    """Envia mensagem via Lark Open API."""
    if not APP_ID or not APP_SECRET:
        log("WARN", "no APP_ID/SECRET, cannot send")
        return

    # 1. Pega tenant_access_token
    token_resp = requests.post(
        "https://open.larksuite.com/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": APP_ID, "app_secret": APP_SECRET},
        timeout=5,
    ).json()
    token = token_resp.get("tenant_access_token", "")
    if not token:
        log("ERROR", "no tenant_access_token", resp=token_resp)
        return

    # 2. Envia mensagem
    payload = {
        "receive_id": chat_id,
        "msg_type": "text",
        "content": json.dumps({"text": text}),
    }
    resp = requests.post(
        "https://open.larksuite.com/open-apis/im/v1/messages?receive_id_type=chat_id",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=payload,
        timeout=5,
    ).json()
    log("INFO", "send result", code=resp.get("code"), msg=resp.get("msg"))


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "app_id_set": bool(APP_ID)})


if __name__ == "__main__":
    log("INFO", "starting lark bot server", port=PORT, app_id_set=bool(APP_ID))
    app.run(host="0.0.0.0", port=PORT, debug=False)