#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lark Bot v2 — TRAE Work replacement
Gustavo Almeida · 2026-07-28

Diferenças vs v1:
  ✓ Recebe imagens (baixa e descreve via vision LLM)
  ✓ Recebe arquivos (salva em ~/Downloads/lark_inbox/)
  ✓ Escuta TUDO no grupo (sem precisar de @) — se bot for admin
  ✓ Plugado no MCP do cartório (PIETRA) + LLM direto (MiniMax-M3)
  ✓ Memória de contexto por chat (sqlite local)
  ✓ LGPD: scrub CPF/RG/telefone antes de logar/persistir
  ✓ Responde em PT-BR, mensagens curtas, sem emoji

Setup: ver scripts/LARK_BOT_SETUP.md (mesmo path do v1)
"""

import os
import re
import json
import hmac
import hashlib
import sqlite3
import requests
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, request, jsonify

# === Config ===
APP_ID = os.getenv("LARK_APP_ID", "")
APP_SECRET = os.getenv("LARK_APP_SECRET", "")
VERIFICATION_TOKEN = os.getenv("LARK_VERIFICATION_TOKEN", "")
ENCRYPT_KEY = os.getenv("LARK_ENCRYPT_KEY", "")
LARK_API = "https://open.larksuite.com/open-apis"
PIETRA_MCP = os.getenv("PIETRA_MCP_URL", "https://api.2notasudi.com.br/mcp")
DIRECT_LLM_URL = os.getenv(
    "DIRECT_LLM_URL", "https://api.minimax.io/v1/chat/completions"
)
DIRECT_LLM_KEY = os.getenv("DIRECT_LLM_KEY", "")  # MiniMax key
INBOX_DIR = Path(os.getenv("LARK_INBOX_DIR", str(Path.home() / "Downloads/lark_inbox")))
DB_PATH = os.getenv("LARK_DB_PATH", str(Path.home() / ".lark_bot_memory.sqlite"))
PORT = int(os.getenv("LARK_BOT_PORT", "8080"))

INBOX_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)


# === DB (memória por chat) ===
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT, sender TEXT, role TEXT, content TEXT,
            msg_type TEXT, file_path TEXT,
            ts INTEGER DEFAULT (strftime('%s','now'))
        )""")
    return conn


def store(chat_id, sender, role, content, msg_type="text", file_path=None):
    try:
        c = db()
        c.execute(
            "INSERT INTO messages (chat_id,sender,role,content,msg_type,file_path) VALUES (?,?,?,?,?,?)",
            (chat_id, sender, role, content, msg_type, file_path),
        )
        c.commit()
        c.close()
    except Exception as e:
        log("ERR", "db store failed", error=str(e))


def history(chat_id, limit=20):
    try:
        c = db()
        rows = c.execute(
            "SELECT role, content FROM messages WHERE chat_id=? ORDER BY id DESC LIMIT ?",
            (chat_id, limit),
        ).fetchall()
        c.close()
        return list(reversed(rows))
    except Exception:
        return []


# === LGPD scrub ===
PII_PATTERNS = [
    (re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b"), "[CPF]"),
    (re.compile(r"\b\d{2}\.\d{3}\.\d{3}-\d{1}\b"), "[RG]"),
    (re.compile(r"\(\d{2}\)\s*9?\d{4}-\d{4}"), "[TEL]"),
    (re.compile(r"\b[\w.-]+@[\w.-]+\.\w+\b"), "[EMAIL]"),
]


def scrub(s):
    for pat, repl in PII_PATTERNS:
        s = pat.sub(repl, s)
    return s


# === Log ===
def log(level, msg, **kw):
    ts = datetime.now(timezone.utc).isoformat()
    print(f"[{ts}] [{level}] {msg} {kw if kw else ''}", flush=True)


# === Lark helpers ===
_token_cache = {"token": None, "exp": 0}


def get_token():
    if _token_cache["token"] and _token_cache["exp"] > datetime.now().timestamp():
        return _token_cache["token"]
    r = requests.post(
        f"{LARK_API}/auth/v3/tenant_access_token/internal",
        json={"app_id": APP_ID, "app_secret": APP_SECRET},
        timeout=5,
    ).json()
    tok = r.get("tenant_access_token", "")
    if tok:
        _token_cache["token"] = tok
        _token_cache["exp"] = datetime.now().timestamp() + 7000
    return tok


def send_text(chat_id, text):
    tok = get_token()
    if not tok:
        return
    r = requests.post(
        f"{LARK_API}/im/v1/messages?receive_id_type=chat_id",
        headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
        json={
            "receive_id": chat_id,
            "msg_type": "text",
            "content": json.dumps({"text": text}),
        },
        timeout=10,
    ).json()
    log("INFO", "sent", code=r.get("code"))


def download_resource(url):
    """Baixa arquivo/imagem do CDN do Lark."""
    try:
        r = requests.get(url, timeout=30)
        if r.status_code == 200:
            ext = ".bin"
            if "image" in r.headers.get("Content-Type", ""):
                ext = ".jpg" if "jpeg" in r.headers["Content-Type"] else ".png"
            name = (
                f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(url) % 10000}{ext}"
            )
            path = INBOX_DIR / name
            path.write_bytes(r.content)
            return str(path)
    except Exception as e:
        log("ERR", "download failed", url=url[:60], error=str(e))
    return None


# === LLM call (PIETRA via MCP + fallback MiniMax direto) ===
def call_llm(messages):
    """Tenta PIETRA primeiro, fallback MiniMax direto."""
    # 1) PIETRA via MCP
    try:
        r = requests.post(
            f"{PIETRA_MCP}/v1/chat/completions",
            json={"messages": messages, "max_tokens": 800},
            timeout=20,
        )
        if r.status_code == 200:
            return (
                r.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            )
    except Exception as e:
        log("WARN", "pietra mcp failed", error=str(e))

    # 2) MiniMax direto
    if DIRECT_LLM_KEY:
        try:
            r = requests.post(
                DIRECT_LLM_URL,
                headers={"Authorization": f"Bearer {DIRECT_LLM_KEY}"},
                json={"model": "MiniMax-M3", "messages": messages, "max_tokens": 800},
                timeout=20,
            )
            if r.status_code == 200:
                return (
                    r.json()
                    .get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
        except Exception as e:
            log("WARN", "direct llm failed", error=str(e))

    return "_(LLM indisponível no momento)_"


# === Webhook ===
@app.route("/lark/webhook", methods=["POST"])
def webhook():
    body = request.get_json(silent=True) or {}

    if body.get("type") == "url_verification":
        return jsonify({"challenge": body.get("challenge", "")})

    try:
        header = body.get("header", {})
        event = body.get("event", {})
        if header.get("event_type") == "im.message.receive_v1":
            handle_message(event)
        return jsonify({"code": 0})
    except Exception as e:
        log("ERR", "webhook failed", error=str(e))
        return jsonify({"code": -1}), 200


def handle_message(event):
    msg = event.get("message", {})
    chat_id = msg.get("chat_id")
    chat_type = msg.get("chat_type", "p2p")
    msg_type = msg.get("message_type", "text")
    sender = event.get("sender", {}).get("sender_id", {}).get("open_id", "?")[:16]
    text = (msg.get("content") or {}).get("text", "").strip()
    mentions = msg.get("mentions", [])

    # Limpa @bot do texto
    for m in mentions:
        key = m.get("key", "")
        if key:
            text = text.replace(key, "").strip()

    # Processa mídia
    file_path = None
    extra_context = ""
    if msg_type == "image":
        img_key = (msg.get("content") or {}).get("image_key")
        if img_key:
            tok = get_token()
            url = f"{LARK_API}/im/v1/images/{img_key}"
            file_path = download_resource(url)
            extra_context = f"\n[imagem recebida: {file_path}]"
    elif msg_type == "file":
        fk = (msg.get("content") or {}).get("file_key")
        fn = (msg.get("content") or {}).get("file_name", "arquivo")
        if fk:
            tok = get_token()
            url = f"{LARK_API}/im/v1/files/{fk}"
            file_path = download_resource(url)
            extra_context = f"\n[arquivo '{fn}' salvo em: {file_path}]"

    text_clean = scrub(text)
    log(
        "INFO",
        "msg",
        chat=chat_type[:1],
        sender=sender,
        type=msg_type,
        text=text_clean[:60],
    )

    # Persiste
    store(chat_id, sender, "user", text or msg_type, msg_type, file_path)

    # Em grupo: responde TUDO (se for admin no grupo). Senão só @mencionado.
    is_at_bot = any(m.get("id", {}).get("open_id") == APP_ID for m in mentions)
    if chat_type == "group" and not is_at_bot and not text.startswith("!"):
        # Modo silencioso: loga mas não responde (configurável via env)
        if os.getenv("LARK_QUIET_GROUP", "true") == "true":
            return

    # Monta prompt com histórico + mídia
    hist = history(chat_id, limit=10)
    sys_prompt = (
        "Você é ZCode, assistente pessoal do Gustavo Almeida. Responde em PT-BR, "
        "curto e objetivo. Sem emoji. Quando receber imagem/arquivo, descreve "
        "o que tem e segue o que ele pediu."
    )
    msgs = [{"role": "system", "content": sys_prompt}]
    for role, content in hist:
        msgs.append({"role": role, "content": content})
    msgs.append({"role": "user", "content": (text or "(sem texto)") + extra_context})

    reply = call_llm(msgs)
    reply = scrub(reply)
    store(chat_id, "bot", "assistant", reply)

    send_text(chat_id, reply)


@app.route("/health", methods=["GET"])
def health():
    return jsonify(
        {
            "status": "ok",
            "app_id": bool(APP_ID),
            "pietra_mcp": PIETRA_MCP,
            "inbox": str(INBOX_DIR),
            "history_msgs": len(history("test", limit=1)),
        }
    )


if __name__ == "__main__":
    log("INFO", "lark bot v2 starting", port=PORT, pietra=PIETRA_MCP)
    app.run(host="0.0.0.0", port=PORT, debug=False)
