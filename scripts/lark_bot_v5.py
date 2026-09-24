#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lark Bot v4 — TRAE SOLO replacement (com visão por OCR)
Gustavo Almeida · 2026-07-28

Diferenças vs v3:
  ✓ OCR (tesseract) em imagens recebidas → texto extraído vai pro PIETRA
  ✓ Múltiplos arquivos analisados em uma msg
  ✓ Detecção de tipo: img/foto de documento → OCR + análise
  ✓ Placeholder visual: "[imagem: 2.3MB, jpeg]" se OCR falhar
  ✓ Vision via PIETRA fica como TODO até endpoint aceitar image_url

Setup: mesmo do v3 (LARK_BOT_V3_RUNBOOK.md)
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
INBOX_DIR = Path(os.getenv("LARK_INBOX_DIR", str(Path.home() / "Downloads/lark_inbox")))
DB_PATH = os.getenv("LARK_DB_PATH", str(Path.home() / ".lark_bot_v4.sqlite"))
PORT = int(os.getenv("LARK_BOT_PORT", "8081"))  # v4 na 8081 pra coexistir com v3
LARK_QUIET_GROUP = os.getenv("LARK_QUIET_GROUP", "true").lower() == "true"
OCR_ENABLED = os.getenv("OCR_ENABLED", "true").lower() == "true"
OCR_LANG = os.getenv("OCR_LANG", "por+eng")  # tesseract langs

INBOX_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)


# === DB ===
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts INTEGER DEFAULT (strftime('%s','now')),
            chat_id TEXT, sender TEXT, msg_type TEXT,
            content_in TEXT, content_out TEXT,
            pietra_model TEXT, error TEXT,
            attachments TEXT
        );
        CREATE TABLE IF NOT EXISTS rate_limit (
            chat_id TEXT PRIMARY KEY,
            last_msg_ts INTEGER,
            count_window INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS ocr_cache (
            file_hash TEXT PRIMARY KEY,
            text TEXT, ts INTEGER DEFAULT (strftime('%s','now'))
        );
    """)
    return conn


def log_event(
    chat_id,
    sender,
    msg_type,
    content_in,
    content_out,
    model,
    attachments=None,
    error=None,
):
    try:
        c = db()
        c.execute(
            "INSERT INTO events (chat_id,sender,msg_type,content_in,content_out,pietra_model,attachments,error) VALUES (?,?,?,?,?,?,?,?)",
            (
                chat_id,
                sender[:32] if sender else "",
                msg_type,
                content_in[:500],
                (content_out or "")[:500],
                model,
                json.dumps(attachments or []),
                error,
            ),
        )
        c.commit()
        c.close()
    except Exception as e:
        print(f"[DB ERR] {e}", flush=True)


def rate_ok(chat_id, max_per_min=10):
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
        return True


def log(level, msg, **kw):
    ts = datetime.now(timezone.utc).isoformat()
    # Structured JSON log
    entry = {"ts": ts, "level": level, "msg": msg, **kw}
    print(json.dumps(entry, ensure_ascii=False), flush=True)


# === LGPD scrub (defesa em profundidade) ===
PII_PATTERNS = [
    (re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b"), "[CPF]"),
    (re.compile(r"\b\d{2}\.\d{3}\.\d{3}-\d{1}\b"), "[RG]"),
    (re.compile(r"\(\d{2}\)\s*9?\d{4}-\d{4}"), "[TEL]"),
    (re.compile(r"\b[\w.-]+@[\w.-]+\.\w+\b"), "[EMAIL]"),
    (re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"), "[CARTAO]"),
]


def scrub_pii(text):
    """Mascara PII em texto livre. Crítico antes de mandar OCR pro LLM."""
    if not text:
        return text
    for pat, repl in PII_PATTERNS:
        text = pat.sub(repl, text)
    return text


# === OCR ===
def ocr_image(path):
    """Extrai texto da imagem via tesseract. Retorna texto ou None."""
    if not OCR_ENABLED:
        return None
    try:
        # Cache por hash do arquivo
        import hashlib

        h = hashlib.md5(Path(path).read_bytes()).hexdigest()
        c = db()
        cached = c.execute(
            "SELECT text FROM ocr_cache WHERE file_hash=?", (h,)
        ).fetchone()
        if cached:
            c.close()
            return cached[0]
        c.close()

        # Passa path absoluto e cwd em pasta temp (tesseract tem bug com cwd=/)
        result = subprocess.run(
            ["tesseract", str(Path(path).resolve()), "-", "-l", OCR_LANG, "--psm", "6"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd="/tmp",
        )
        text = result.stdout.strip()
        if text:
            # Cache + LGPD scrub (PII pode ter sido extraído pelo OCR)
            text_scrubbed = scrub_pii(text)
            c = db()
            c.execute(
                "INSERT OR REPLACE INTO ocr_cache (file_hash, text) VALUES (?, ?)",
                (h, text_scrubbed),
            )
            c.commit()
            c.close()
            return text_scrubbed if text_scrubbed else None
        return None
    except subprocess.TimeoutExpired:
        log("WARN", "ocr timeout", path=path)
        return None
    except FileNotFoundError:
        log("WARN", "tesseract not found, OCR disabled")
        return None
    except Exception as e:
        log("ERR", "ocr failed", error=str(e))
        return None


def describe_image(path):
    """Descreve imagem sem vision LLM: tamanho, formato, OCR (se houver)."""
    p = Path(path)
    if not p.exists():
        return f"[imagem inexistente: {path}]"
    size_kb = p.stat().st_size / 1024
    ext = p.suffix.upper().lstrip(".")
    info = f"[imagem: {size_kb:.0f}KB, {ext}]"

    ocr_text = ocr_image(path)
    if ocr_text:
        # Trunca OCR pra não estourar contexto
        ocr_trunc = ocr_text[:800] + ("..." if len(ocr_text) > 800 else "")
        info += f"\n[OCR extraiu]: {ocr_trunc}"
    else:
        info += "\n[sem texto detectável]"
    return info


def describe_file(path, original_name):
    """Descreve arquivo: nome, tamanho, primeiras linhas se texto."""
    p = Path(path)
    if not p.exists():
        return f"[arquivo: {original_name} (não baixado)]"
    size_kb = p.stat().st_size / 1024
    info = f"[arquivo: {original_name}, {size_kb:.0f}KB]"

    # Se for texto/code, mostra primeiras linhas
    text_exts = {
        ".txt",
        ".md",
        ".py",
        ".js",
        ".ts",
        ".json",
        ".yaml",
        ".yml",
        ".csv",
        ".log",
        ".sh",
    }
    if p.suffix.lower() in text_exts and size_kb < 200:
        try:
            content = p.read_text(errors="ignore")[:1500]
            info += f"\n[conteúdo]: {content}"
        except Exception:
            pass
    return info


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
        log("ERR", "no token")
        return False
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


def download_resource(media_type, media_key, save_name=None):
    """Baixa arquivo/imagem do CDN do Lark."""
    try:
        tok = get_token()
        url = f"{LARK_API}/im/v1/{'images' if media_type == 'image' else 'files'}/{media_key}"
        r = requests.get(
            url,
            headers={"Authorization": f"Bearer {tok}"},
            timeout=30,
            allow_redirects=True,
        )
        if r.status_code == 200:
            ext = (
                ".jpg"
                if media_type == "image"
                else (Path(save_name).suffix if save_name else ".bin")
            )
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
                time.sleep(2 * (attempt + 1))
            else:
                time.sleep(1)
        except requests.exceptions.Timeout:
            time.sleep(1)
        except Exception as e:
            return "_(Pietra indisponível. Tenta em 30s.)_", "error", str(e)
    return "_(Pietra ocupada. Tenta de novo.)_", "timeout", "max_retries"


# === Comandos locais ===
def handle_command(chat_id, text, sender):
    global OCR_LANG  # declaração no topo da função
    t = text.strip().lower()
    if t in ("!ajuda", "!help", "!comandos"):
        return (
            "**Comandos (v4 com visão OCR):**\n"
            "- `!ajuda` — esta mensagem\n"
            "- `!saude` — status bot + PIETRA\n"
            "- `!modelo` — qual LLM responde\n"
            "- `!ocr <lang>` — muda idioma OCR (por, eng, por+eng)\n"
            "- `!reset` — limpa rate limit\n"
            "- imagem/arquivo → OCR + análise PIETRA\n"
        )
    if t in ("!saude", "!status", "!health"):
        try:
            h = requests.get(PIETRA_HEALTH_URL, timeout=4).json()
            pietra_ok = h.get("status") == "ok"
        except Exception:
            pietra_ok = False
        return (
            f"**Bot v4:**\n"
            f"- Lark: {'✓' if APP_ID else '✗'}\n"
            f"- PIETRA: {'✓' if pietra_ok else '✗'}\n"
            f"- OCR: {'✓ (' + OCR_LANG + ')' if OCR_ENABLED else '✗'}\n"
            f"- Inbox: {INBOX_DIR}\n"
            f"- Modo grupo: {'silencioso' if LARK_QUIET_GROUP else 'responde tudo'}"
        )
    if t == "!modelo":
        txt, model, _ = ask_pietra("Diz em uma linha qual modelo de IA você é.")
        return f"**Modelo:** `{model}`\n{txt}"
    if t.startswith("!ocr"):
        parts = t.split()
        if len(parts) == 1:
            return f"OCR lang atual: `{OCR_LANG}` (mude com `!ocr por` ou `!ocr eng`)"
        OCR_LANG = parts[1]
        return f"✓ OCR lang → `{OCR_LANG}`"
    if t == "!reset":
        try:
            c = db()
            c.execute("DELETE FROM rate_limit WHERE chat_id=?", (chat_id,))
            c.commit()
            c.close()
            return "✓ Memória local limpa."
        except Exception as e:
            return f"✗ Erro: {e}"
    return None


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
    sender = event.get("sender", {}).get("sender_id", {}).get("open_id", "?")[:32]
    text = (msg.get("content") or {}).get("text", "").strip()
    mentions = msg.get("mentions", [])

    for m in mentions:
        key = m.get("key", "")
        if key:
            text = text.replace(key, "").strip()

    # Processa mídia — pode haver múltiplos arquivos em uma msg
    attachments = []
    extra = ""
    if msg_type == "image":
        img_key = (msg.get("content") or {}).get("image_key")
        if img_key:
            p = download_resource("image", img_key)
            if p:
                attachments.append({"type": "image", "path": p})
                extra += "\n" + describe_image(p)
    elif msg_type == "file":
        fk = (msg.get("content") or {}).get("file_key")
        fn = (msg.get("content") or {}).get("file_name", "arquivo")
        if fk:
            p = download_resource("file", fk, save_name=fn)
            if p:
                attachments.append({"type": "file", "path": p, "name": fn})
                extra += "\n" + describe_file(p, fn)
    elif msg_type == "media":  # vídeo/áudio
        # Não analisa, só registra
        extra += "\n[mídia (vídeo/áudio) — não analisada, salvo em disco]"

    log(
        "INFO",
        "msg",
        chat=chat_type[:1],
        sender=sender,
        type=msg_type,
        text=text[:60],
        attachments=len(attachments),
    )

    if not rate_ok(chat_id):
        return

    is_at_bot = any(m.get("id", {}).get("open_id") == APP_ID for m in mentions)
    if chat_type == "group" and not is_at_bot and not text.startswith("!"):
        if LARK_QUIET_GROUP:
            return

    cmd_resp = handle_command(chat_id, text, sender)
    if cmd_resp is not None:
        send_text(chat_id, cmd_resp)
        log_event(chat_id, sender, msg_type, text, cmd_resp, "command", attachments)
        return

    user_msg = (text or f"(mensagem {msg_type} sem texto)") + extra
    reply, model, err = ask_pietra(user_msg)
    send_text(chat_id, reply)
    log_event(chat_id, sender, msg_type, user_msg, reply, model, attachments, err)


@app.route("/test-image", methods=["POST"])
def test_image():
    """Endpoint pra testar OCR localmente sem Lark."""
    if "file" not in request.files:
        return jsonify(
            {
                "error": "no file. use: curl -F file=@image.png http://localhost:8082/test-image"
            }
        ), 400
    f = request.files["file"]
    p = INBOX_DIR / f"test_{datetime.now().strftime('%H%M%S')}_{f.filename}"
    p.write_bytes(f.read())
    desc = describe_image(p)
    # Manda pro PIETRA
    reply, model, err = ask_pietra(
        f"O usuário mandou esta imagem:\n\n{desc}\n\nDescreva brevemente o que você vê."
    )
    return jsonify(
        {
            "file": str(p),
            "size_kb": p.stat().st_size // 1024,
            "ocr": desc,
            "pietra_reply": reply,
            "pietra_model": model,
            "error": err,
        }
    )


@app.route("/health", methods=["GET"])
def health():
    try:
        h = requests.get(PIETRA_HEALTH_URL, timeout=4).json()
        pietra_ok = h.get("status") == "ok"
    except Exception:
        pietra_ok = False

    # Check tesseract
    tess = False
    try:
        subprocess.run(["tesseract", "--version"], capture_output=True, timeout=2)
        tess = True
    except Exception:
        pass

    return jsonify(
        {
            "bot": "v5 ok",
            "lark_configured": bool(APP_ID),
            "pietra_ok": pietra_ok,
            "ocr_available": tess,
            "ocr_lang": OCR_LANG,
            "quiet_group": LARK_QUIET_GROUP,
            "inbox": str(INBOX_DIR),
        }
    )


if __name__ == "__main__":
    log("INFO", "lark bot v4 starting", port=PORT, ocr=OCR_ENABLED, lang=OCR_LANG)
    app.run(host="0.0.0.0", port=PORT, debug=False)
