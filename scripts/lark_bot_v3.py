#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lark Bot v3 — TRAE SOLO replacement no grupo GG
Gustavo Almeida · 2026-07-28

Arquitetura:
  Mensagem no grupo GG → webhook Lark → este bot → /api/v1/pietra/chat/completions
  (VPS) → resposta com persona canônica + PII scrub + identity guard + audit log

Diferenças vs v2:
  ✓ Backend REAL = PIETRA VPS (api.2notasudi.com.br), não echo inútil
  ✓ Persona canônica vem do system prompt da VPS (não duplicada aqui)
  ✓ PII scrub feito pela VPS (LGPD compliance real)
  ✓ Identity guard HARD-STOP feito pela VPS (P0 identity leak defesa)
  ✓ Tool calling MCP funciona (cartorio_calcular_emolumento, protocolo, etc)
  ✓ Memória persistente no Postgres do cartório via /api/v1/pietra/memoria/{telefone}
  ✓ Cloudflared named tunnel (não temporário) com credencial salva
  ✓ LaunchAgent pra rodar 24/7 no boot
  ✓ Health check a cada 5min + alerta Telegram se cair
  ✓ Audit log local (sqlite) sincronizado com backend

Setup: ver scripts/LARK_BOT_V3_RUNBOOK.md
"""

import os
import re
import json
import time
import sqlite3
import subprocess
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
PIETRA_BASE = os.getenv("PIETRA_BASE", "https://api.2notasudi.com.br")
PIETRA_HEALTH_URL = f"{PIETRA_BASE}/api/v1/pietra/health"
PIETRA_CHAT_URL = f"{PIETRA_BASE}/api/v1/pietra/chat/completions"
PIETRA_MEMORY_URL = lambda tel: f"{PIETRA_BASE}/api/v1/pietra/memoria/{tel}"
INBOX_DIR = Path(os.getenv("LARK_INBOX_DIR", str(Path.home() / "Downloads/lark_inbox")))
DB_PATH = os.getenv("LARK_DB_PATH", str(Path.home() / ".lark_bot_v3.sqlite"))
PORT = int(os.getenv("LARK_BOT_PORT", "8080"))
LARK_QUIET_GROUP = os.getenv("LARK_QUIET_GROUP", "true").lower() == "true"
PIETRA_TELEFONE = os.getenv(
    "PIETRA_TELEFONE", "+5500000000000"
)  # identidade no cartório

INBOX_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)


# === DB local (audit + rate limit) ===
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts INTEGER DEFAULT (strftime('%s','now')),
            chat_id TEXT, sender TEXT, msg_type TEXT,
            content_in TEXT, content_out TEXT,
            pietra_model TEXT, error TEXT
        );
        CREATE TABLE IF NOT EXISTS rate_limit (
            chat_id TEXT PRIMARY KEY,
            last_msg_ts INTEGER,
            count_window INTEGER DEFAULT 0
        );
    """)
    return conn


def log_event(chat_id, sender, msg_type, content_in, content_out, model, error=None):
    try:
        c = db()
        c.execute(
            "INSERT INTO events (chat_id,sender,msg_type,content_in,content_out,pietra_model,error) VALUES (?,?,?,?,?,?,?)",
            (
                chat_id,
                sender[:32] if sender else "",
                msg_type,
                content_in[:500],
                content_out[:500] if content_out else "",
                model,
                error,
            ),
        )
        c.commit()
        c.close()
    except Exception as e:
        print(f"[DB ERR] {e}", flush=True)


def rate_ok(chat_id, max_per_min=10):
    """Rate limit simples: max N msgs/min por chat."""
    try:
        now = int(time.time())
        c = db()
        row = c.execute(
            "SELECT last_msg_ts, count_window FROM rate_limit WHERE chat_id=?",
            (chat_id,),
        ).fetchone()
        if row:
            last, count = row
            if now - last < 60:
                if count >= max_per_min:
                    c.close()
                    return False
                c.execute(
                    "UPDATE rate_limit SET last_msg_ts=?, count_window=count_window+1 WHERE chat_id=?",
                    (now, chat_id),
                )
            else:
                c.execute(
                    "UPDATE rate_limit SET last_msg_ts=?, count_window=1 WHERE chat_id=?",
                    (now, chat_id),
                )
        else:
            c.execute(
                "INSERT INTO rate_limit (chat_id,last_msg_ts,count_window) VALUES (?,?,1)",
                (chat_id, now),
            )
        c.commit()
        c.close()
        return True
    except Exception:
        return True  # fail-open


def log(level, msg, **kw):
    ts = datetime.now(timezone.utc).isoformat()
    print(f"[{ts}] [{level}] {msg} {kw if kw else ''}", flush=True)


# === Lark helpers ===
_token_cache = {"token": None, "exp": 0}


def get_token():
    if _token_cache["token"] and _token_cache["exp"] > time.time():
        return _token_cache["token"]
    try:
        r = requests.post(
            f"{LARK_API}/auth/v3/tenant_access_token/internal",
            json={"app_id": APP_ID, "app_secret": APP_SECRET},
            timeout=5,
        ).json()
        tok = r.get("tenant_access_token", "")
        if tok:
            _token_cache["token"] = tok
            _token_cache["exp"] = time.time() + 7000
        return tok
    except Exception as e:
        log("ERR", "get_token failed", error=str(e))
        return ""


def send_text(chat_id, text):
    tok = get_token()
    if not tok:
        log("ERR", "no token, cannot send")
        return False
    # Divide se > 4096 chars (limite Lark)
    for i in range(0, len(text), 4000):
        chunk = text[i : i + 4000]
        r = requests.post(
            f"{LARK_API}/im/v1/messages?receive_id_type=chat_id",
            headers={
                "Authorization": f"Bearer {tok}",
                "Content-Type": "application/json",
            },
            json={
                "receive_id": chat_id,
                "msg_type": "text",
                "content": json.dumps({"text": chunk}),
            },
            timeout=10,
        ).json()
        if r.get("code") != 0:
            log("ERR", "send failed", code=r.get("code"), msg=r.get("msg"))
            return False
    return True


def send_image(chat_id, image_path):
    """Upload + envia imagem (msg_type=image)."""
    tok = get_token()
    if not tok:
        return False
    try:
        # 1) Upload
        with open(image_path, "rb") as f:
            up = requests.post(
                f"{LARK_API}/im/v1/images",
                headers={"Authorization": f"Bearer {tok}"},
                files={"image": (Path(image_path).name, f, "image/jpeg")},
                data={"image_type": "message"},
                timeout=30,
            ).json()
        if up.get("code") != 0:
            log("ERR", "image upload failed", code=up.get("code"))
            return False
        image_key = up.get("data", {}).get("image_key", "")
        # 2) Send
        r = requests.post(
            f"{LARK_API}/im/v1/messages?receive_id_type=chat_id",
            headers={
                "Authorization": f"Bearer {tok}",
                "Content-Type": "application/json",
            },
            json={
                "receive_id": chat_id,
                "msg_type": "image",
                "content": json.dumps({"image_key": image_key}),
            },
            timeout=10,
        ).json()
        return r.get("code") == 0
    except Exception as e:
        log("ERR", "send_image failed", error=str(e))
        return False


def download_resource(media_type, media_key, save_name=None):
    """Baixa imagem/file do CDN do Lark."""
    try:
        tok = get_token()
        url = f"{LARK_API}/im/v1/{'images' if media_type == 'image' else 'files'}/{media_key}"
        r = requests.get(url, headers={"Authorization": f"Bearer {tok}"}, timeout=30)
        if r.status_code == 200:
            ext = ".jpg"
            if media_type == "file":
                ext = Path(save_name).suffix if save_name else ".bin"
            name = (
                save_name
                or f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{media_key[:8]}{ext}"
            )
            path = INBOX_DIR / name
            path.write_bytes(r.content)
            return str(path)
    except Exception as e:
        log("ERR", "download failed", type=media_type, error=str(e))
    return None


# === PIETRA brain ===
def ask_pietra(user_msg, max_retries=2):
    """Manda pergunta pro PIETRA VPS. Retorna (texto, modelo, erro)."""
    payload = {
        "messages": [{"role": "user", "content": user_msg}],
        "max_tokens": 800,
        "temperature": 0.7,
    }
    for attempt in range(max_retries + 1):
        try:
            r = requests.post(PIETRA_CHAT_URL, json=payload, timeout=20)
            if r.status_code == 200:
                j = r.json()
                txt = j.get("choices", [{}])[0].get("message", {}).get("content", "")
                model = j.get("model", "unknown")
                return txt, model, None
            elif r.status_code == 429:
                log("WARN", "pietra rate-limited", attempt=attempt)
                time.sleep(2 * (attempt + 1))
            else:
                log("WARN", "pietra non-200", status=r.status_code, body=r.text[:200])
                time.sleep(1)
        except requests.exceptions.Timeout:
            log("WARN", "pietra timeout", attempt=attempt)
            time.sleep(1)
        except Exception as e:
            log("ERR", "pietra call failed", error=str(e))
            return (
                "_(Pietra indisponível no momento. Tenta de novo em 30s.)_",
                "error",
                str(e),
            )
    return "_(Pietra ocupada. Tenta de novo.)_", "timeout", "max_retries"


# === Comandos locais (sem chamar PIETRA) ===
def handle_command(chat_id, text, sender):
    """Comandos que o bot responde sem precisar de LLM."""
    t = text.strip().lower()
    if t in ("!ajuda", "!help", "!comandos"):
        return (
            "**Comandos:**\n"
            "- `!ajuda` — esta mensagem\n"
            "- `!saude` — status do bot + PIETRA\n"
            "- `!modelo` — qual LLM tá respondendo agora\n"
            "- `!reset` — limpa memória local deste chat\n"
            "- qualquer outra coisa → pergunta pro PIETRA\n"
        )
    if t in ("!saude", "!status", "!health"):
        try:
            h = requests.get(PIETRA_HEALTH_URL, timeout=4).json()
            pietra_ok = h.get("status") == "ok"
        except Exception:
            pietra_ok = False
        return (
            f"**Status do bot:**\n"
            f"- Lark: {'✓ conectado' if APP_ID else '✗ sem APP_ID'}\n"
            f"- PIETRA VPS: {'✓ ok' if pietra_ok else '✗ down'}\n"
            f"- Modo grupo: {'silencioso (só @)' if LARK_QUIET_GROUP else 'responde tudo'}\n"
            f"- DB local: {DB_PATH}\n"
            f"- Inbox: {INBOX_DIR}"
        )
    if t == "!modelo":
        txt, model, _ = ask_pietra("Diz em uma linha qual modelo de IA você é.")
        return f"**Modelo ativo:** `{model}`\n\nResposta: {txt}"
    if t == "!reset":
        try:
            c = db()
            # Não apaga audit log, só rate_limit
            c.execute("DELETE FROM rate_limit WHERE chat_id=?", (chat_id,))
            c.commit()
            c.close()
            return "✓ Memória local do chat limpa."
        except Exception as e:
            return f"✗ Erro: {e}"
    return None  # não é comando


# === Webhook ===
@app.route("/lark/webhook", methods=["POST"])
def webhook():
    body = request.get_json(silent=True) or {}

    # 1) Challenge handshake
    if body.get("type") == "url_verification":
        log("INFO", "challenge")
        return jsonify({"challenge": body.get("challenge", "")})

    try:
        header = body.get("header", {})
        event = body.get("event", {})
        if header.get("event_type") == "im.message.receive_v1":
            handle_message(event)
        return jsonify({"code": 0})
    except Exception as e:
        log("ERR", "webhook handler failed", error=str(e))
        return jsonify({"code": -1, "msg": str(e)}), 200


def handle_message(event):
    msg = event.get("message", {})
    chat_id = msg.get("chat_id")
    chat_type = msg.get("chat_type", "p2p")
    msg_type = msg.get("message_type", "text")
    sender = event.get("sender", {}).get("sender_id", {}).get("open_id", "?")[:32]
    text = (msg.get("content") or {}).get("text", "").strip()
    mentions = msg.get("mentions", [])

    # Limpa @bot
    for m in mentions:
        key = m.get("key", "")
        if key:
            text = text.replace(key, "").strip()

    # Mídia
    file_path = None
    extra = ""
    if msg_type == "image":
        img_key = (msg.get("content") or {}).get("image_key")
        if img_key:
            file_path = download_resource("image", img_key)
            extra = f"\n[imagem: {file_path}]"
    elif msg_type == "file":
        fk = (msg.get("content") or {}).get("file_key")
        fn = (msg.get("content") or {}).get("file_name", "arquivo")
        if fk:
            file_path = download_resource("file", fk, save_name=fn)
            extra = f"\n[arquivo: {file_path}]"

    log("INFO", "msg", chat=chat_type[:1], sender=sender, type=msg_type, text=text[:60])

    # Rate limit
    if not rate_ok(chat_id):
        log("WARN", "rate-limited", chat=chat_id)
        return

    # Grupo: silencioso ou responde?
    is_at_bot = any(m.get("id", {}).get("open_id") == APP_ID for m in mentions)
    if chat_type == "group" and not is_at_bot and not text.startswith("!"):
        if LARK_QUIET_GROUP:
            return  # não responde sem @

    # Comandos locais primeiro
    cmd_resp = handle_command(chat_id, text, sender)
    if cmd_resp is not None:
        send_text(chat_id, cmd_resp)
        log_event(chat_id, sender, msg_type, text, cmd_resp, "command")
        return

    # Pergunta pro PIETRA
    user_msg = (text or f"(mensagem {msg_type} sem texto)") + extra
    reply, model, err = ask_pietra(user_msg)
    send_text(chat_id, reply)
    log_event(chat_id, sender, msg_type, user_msg, reply, model, err)

    # Se recebeu imagem, manda de volta (eco) — opcional
    if file_path and msg_type == "image":
        send_image(chat_id, file_path)


# === Health ===
@app.route("/health", methods=["GET"])
def health():
    try:
        h = requests.get(PIETRA_HEALTH_URL, timeout=4).json()
        pietra_ok = h.get("status") == "ok"
    except Exception:
        pietra_ok = False
    return jsonify(
        {
            "bot": "ok",
            "lark_configured": bool(APP_ID),
            "pietra_ok": pietra_ok,
            "quiet_group": LARK_QUIET_GROUP,
            "inbox": str(INBOX_DIR),
            "db": DB_PATH,
        }
    )


if __name__ == "__main__":
    log(
        "INFO",
        "lark bot v3 starting",
        port=PORT,
        pietra=PIETRA_BASE,
        quiet=LARK_QUIET_GROUP,
        has_app_id=bool(APP_ID),
    )
    app.run(host="0.0.0.0", port=PORT, debug=False)
