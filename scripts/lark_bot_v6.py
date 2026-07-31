#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lark Bot v6 — TRAE SOLO replacement (visão OCR + memória + admin)
Gustavo Almeida · 2026-07-28

Diferenças vs v5:
  ✓ Detecção automática de tipo de documento (CPF/RG/procuração/escritura)
  ✓ Resumo automático se msg > 500 chars
  ✓ Memória por telefone (integra com PIETRA /memoria/{telefone})
  ✓ Comandos admin: !stats, !bot stop, !broadcast (só owner)
  ✓ LGPD scrub em OCR (CPF/RG/telefone/email/cartão)
  ✓ Log estruturado JSON
  ✓ Endpoint /test-image standalone

Setup: mesmo do v5 (LARK_BOT_V3_RUNBOOK.md)
"""
import os
import re
import json
import io
import time
import sqlite3
import stat
import subprocess
import hashlib
import hmac
import secrets
import tempfile
import requests
import zipfile
import sys
if "/Users/gustavoalmeida/Cartorio" not in sys.path:
    sys.path.insert(0, "/Users/gustavoalmeida/Cartorio")
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from flask import Flask, request, jsonify

# === Config ===
APP_ID = os.getenv("LARK_APP_ID", "")
APP_SECRET = os.getenv("LARK_APP_SECRET", "")
VERIFICATION_TOKEN: str = os.getenv("LARK_VERIFICATION_TOKEN", "")
WEBHOOK_SIGNING_SECRET: str = os.getenv("LARK_WEBHOOK_SIGNING_SECRET", "")
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
OWNER_OPEN_ID = os.getenv("LARK_OWNER_OPEN_ID", "")  # só esse user usa !bot stop / !broadcast
SUMMARY_THRESHOLD = int(os.getenv("SUMMARY_THRESHOLD", "500"))  # chars
MEMORY_ENABLED = os.getenv("MEMORY_ENABLED", "true").lower() == "true"
MAX_ATTACHMENT_BYTES = min(max(int(os.getenv("LARK_MAX_ATTACHMENT_BYTES", "10485760")), 1), 52428800)
MAX_WEBHOOK_BODY_BYTES = min(max(int(os.getenv("LARK_MAX_WEBHOOK_BODY_BYTES", "1048576")), 1024), 10485760)
WEBHOOK_MAX_AGE_SECONDS = min(max(int(os.getenv("LARK_WEBHOOK_MAX_AGE_SECONDS", "300")), 30), 900)
WEBHOOK_MAX_FUTURE_SKEW_SECONDS = min(
    max(int(os.getenv("LARK_WEBHOOK_MAX_FUTURE_SKEW_SECONDS", "30")), 0), 300
)
ATTACHMENT_RETENTION_SECONDS = min(
    max(int(os.getenv("LARK_ATTACHMENT_RETENTION_SECONDS", "3600")), 60), 86400
)
LOCAL_OCR_TEST_ENABLED = os.getenv("LARK_ENABLE_LOCAL_OCR_TEST", "false").lower() == "true"
LOCAL_OCR_TEST_TOKEN = os.getenv("LARK_LOCAL_OCR_TEST_TOKEN", "")

IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
FILE_CONTENT_TYPES = {
    "application/pdf",
    "application/json",
    "text/csv",
    "text/plain",
    "application/zip",
    "application/x-zip-compressed",
    "application/x-zip",
    "application/octet-stream",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
}

INBOX_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_WEBHOOK_BODY_BYTES


def _open_inbox_dirfd() -> int:
    """Open the inbox itself (not a resolved string) to resist symlink and parent races."""
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    return os.open(INBOX_DIR, flags)


def _attachment_content_type(response: requests.Response) -> str:
    """Return a normalized MIME type, discarding parameters supplied by the peer."""
    return response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()


def _attachment_extension(media_type: str, content_type: str) -> str:
    """Choose an internal extension from the validated media type, never the remote name."""
    if media_type == "image":
        return {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
        }[content_type]
    return {
        "application/pdf": ".pdf",
        "application/json": ".json",
        "text/csv": ".csv",
        "text/plain": ".txt",
    }[content_type]


def _new_attachment_name(media_type: str, content_type: str) -> str:
    """Create an opaque filename; remote names never become local path components."""
    suffix = _attachment_extension(media_type, content_type)
    return f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{secrets.token_hex(16)}{suffix}"


def _validate_attachment_payload(media_type: str, content_type: str, payload: bytes) -> bool:
    """Reject MIME spoofing before an attachment is persisted or sent to OCR."""
    if media_type == "image":
        magic = {
            "image/jpeg": payload.startswith(b"\xff\xd8\xff"),
            "image/png": payload.startswith(b"\x89PNG\r\n\x1a\n"),
            "image/webp": len(payload) >= 12 and payload[:4] == b"RIFF" and payload[8:12] == b"WEBP",
        }
        if not magic.get(content_type, False):
            return False
        try:
            from PIL import Image  # type: ignore[import-untyped]

            with Image.open(io.BytesIO(payload)) as image:
                image.verify()
        except (ImportError, OSError, ValueError):
            return False
        return True
    if content_type == "application/pdf":
        return payload.startswith(b"%PDF-")
    if content_type == "application/json":
        try:
            json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return False
        return True
    if content_type in {"text/csv", "text/plain"}:
        try:
            payload.decode("utf-8")
        except UnicodeDecodeError:
            return False
        return True
    return False


def _purge_expired_attachments() -> None:
    """Bound local document exposure to the configured short diagnostic retention window."""
    cutoff = time.time() - ATTACHMENT_RETENTION_SECONDS
    try:
        dirfd = _open_inbox_dirfd()
    except OSError as exc:
        log("WARN", "attachment retention unavailable", error=type(exc).__name__)
        return
    try:
        for name in os.listdir(dirfd):
            if not re.fullmatch(r"\d{8}T\d{6}Z_[0-9a-f]{32}\.(?:jpg|png|webp|pdf|json|csv|txt)", name):
                continue
            try:
                info = os.stat(name, dir_fd=dirfd, follow_symlinks=False)
                if stat.S_ISREG(info.st_mode) and info.st_mtime < cutoff:
                    os.unlink(name, dir_fd=dirfd)
            except OSError:
                continue
    finally:
        os.close(dirfd)


def _write_attachment(response: requests.Response, media_type: str) -> Path | None:
    """Validate in a temporary buffer, then atomically write through an inbox dirfd."""
    content_type = _attachment_content_type(response)
    allowed_types = IMAGE_CONTENT_TYPES if media_type == "image" else FILE_CONTENT_TYPES
    if content_type not in allowed_types:
        log("WARN", "attachment rejected: unsupported media type", media_type=media_type)
        return None

    declared_size = response.headers.get("Content-Length")
    if declared_size:
        try:
            if int(declared_size) > MAX_ATTACHMENT_BYTES:
                log("WARN", "attachment rejected: declared size exceeds limit", media_type=media_type)
                return None
        except ValueError:
            log("WARN", "attachment rejected: invalid content length", media_type=media_type)
            return None

    total = 0
    try:
        with tempfile.SpooledTemporaryFile(max_size=MAX_ATTACHMENT_BYTES, mode="w+b") as staged_file:
            for chunk in response.iter_content(chunk_size=65536):
                if not chunk:
                    continue
                total += len(chunk)
                if total > MAX_ATTACHMENT_BYTES:
                    raise ValueError("attachment exceeds limit")
                staged_file.write(chunk)
            staged_file.seek(0)
            payload = staged_file.read()
            if not _validate_attachment_payload(media_type, content_type, payload):
                raise ValueError("attachment content validation failed")
            _purge_expired_attachments()
            name = _new_attachment_name(media_type, content_type)
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            dirfd = _open_inbox_dirfd()
            try:
                descriptor = os.open(name, flags, 0o600, dir_fd=dirfd)
                with os.fdopen(descriptor, "wb") as attachment_file:
                    attachment_file.write(payload)
                info = os.stat(name, dir_fd=dirfd, follow_symlinks=False)
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                    os.unlink(name, dir_fd=dirfd)
                    raise OSError("attachment file safety check failed")
            finally:
                os.close(dirfd)
    except (OSError, ValueError) as exc:
        log("WARN", "attachment download rejected", media_type=media_type, error=type(exc).__name__)
        return None
    return INBOX_DIR / name


def _local_ocr_test_authorized() -> bool:
    """Keep the diagnostic upload surface disabled unless an operator enables it locally."""
    remote_address = request.remote_addr or ""
    provided_token = request.headers.get("X-Lark-Local-OCR-Test-Token", "")
    return (
        LOCAL_OCR_TEST_ENABLED
        and bool(LOCAL_OCR_TEST_TOKEN)
        and remote_address in {"127.0.0.1", "::1"}
        and hmac.compare_digest(provided_token, LOCAL_OCR_TEST_TOKEN)
    )


def _redact_identifier(value):
    """Return a stable, non-reversible identifier suitable for local audit logs."""
    if not value:
        return ""
    return f"id:{hashlib.sha256(str(value).encode('utf-8')).hexdigest()[:12]}"


def _safe_attachment_metadata(attachments):
    """Keep only attachment types in the local audit database, never paths or names."""
    return [{"type": item.get("type", "unknown")} for item in attachments or []]


def _scrub_value(value):
    """Prevent structured logger callers from accidentally emitting PII or attachment paths."""
    if isinstance(value, str):
        return scrub_pii(value)
    if isinstance(value, dict):
        return {key: _scrub_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_scrub_value(item) for item in value]
    return value


def _lark_configuration_ready():
    """Only accept callbacks with all required, separately configured credentials."""
    return bool(APP_ID and APP_SECRET and VERIFICATION_TOKEN and WEBHOOK_SIGNING_SECRET)


def _provided_verification_token(body: dict) -> str:
    """Return the Lark verification token from either supported payload shape."""
    header = body.get("header") if isinstance(body.get("header"), dict) else {}
    provided = body.get("token") or header.get("token") or ""
    return provided if isinstance(provided, str) else ""


def _valid_lark_callback(body: dict) -> bool:
    """Validate the configured Lark verification token without logging it."""
    provided = _provided_verification_token(body)
    return bool(provided and VERIFICATION_TOKEN) and hmac.compare_digest(provided, VERIFICATION_TOKEN)


def _valid_webhook_freshness(timestamp: str | None) -> bool:
    """Require a recent Unix timestamp to constrain replay of otherwise valid callbacks."""
    if not timestamp or not timestamp.isdigit():
        return False
    request_time = int(timestamp)
    now = int(time.time())
    return now - WEBHOOK_MAX_AGE_SECONDS <= request_time <= now + WEBHOOK_MAX_FUTURE_SKEW_SECONDS


def _valid_lark_signature(
    body_raw: bytes, signature: str | None, timestamp: str | None, nonce: str | None
) -> bool:
    """Validate HMAC-SHA256 over timestamp, nonce and exact request bytes, fail-closed."""
    if (
        not WEBHOOK_SIGNING_SECRET
        or not signature
        or not nonce
        or not re.fullmatch(r"[A-Za-z0-9_-]{16,256}", nonce)
        or not _valid_webhook_freshness(timestamp)
    ):
        return False
    try:
        body = body_raw.decode("utf-8")
    except UnicodeDecodeError:
        return False
    expected = hmac.new(
        WEBHOOK_SIGNING_SECRET.encode("utf-8"),
        f"{timestamp}{nonce}{body}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)

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
        CREATE TABLE IF NOT EXISTS received_events (
            event_id TEXT PRIMARY KEY,
            received_at INTEGER DEFAULT (strftime('%s','now'))
        );
        CREATE TABLE IF NOT EXISTS received_nonces (
            nonce TEXT PRIMARY KEY,
            expires_at INTEGER NOT NULL
        );
    """)
    return conn


def claim_event(event_id):
    """Atomically claim a Lark event before any side effect is attempted.

    A duplicate is acknowledged but never reaches downloads, OCR, Pietra, or
    outbound delivery.  Keeping a claim after a handler failure is intentional:
    replaying a partially processed inbound message can duplicate an external
    response.
    """
    if not isinstance(event_id, str) or not event_id or len(event_id) > 256:
        return False
    try:
        c = db()
        cur = c.execute("INSERT OR IGNORE INTO received_events (event_id) VALUES (?)", (event_id,))
        c.commit()
        c.close()
        return cur.rowcount == 1
    except Exception as exc:
        log("ERR", "event claim failed", error=type(exc).__name__)
        # Fail closed: otherwise a transient local DB issue can duplicate a
        # message after Lark retries it.
        return False


def claim_callback_nonce(nonce: str) -> bool:
    """Atomically consume a validated callback nonce; SQLite failure is an authentication failure."""
    if not re.fullmatch(r"[A-Za-z0-9_-]{16,256}", nonce):
        return False
    now = int(time.time())
    try:
        connection = db()
        connection.execute("DELETE FROM received_nonces WHERE expires_at < ?", (now,))
        cursor = connection.execute(
            "INSERT OR IGNORE INTO received_nonces (nonce, expires_at) VALUES (?, ?)",
            (nonce, now + WEBHOOK_MAX_AGE_SECONDS + WEBHOOK_MAX_FUTURE_SKEW_SECONDS),
        )
        connection.commit()
        connection.close()
        return cursor.rowcount == 1
    except Exception as exc:
        log("ERR", "nonce claim failed", error=type(exc).__name__)
        return False

def log_event(chat_id, sender, msg_type, content_in, content_out, model, attachments=None, error=None):
    """Persist a minimal, scrubbed audit record without raw identifiers or attachments."""
    try:
        c = db()
        c.execute("INSERT INTO events (chat_id,sender,msg_type,content_in,content_out,pietra_model,attachments,error) VALUES (?,?,?,?,?,?,?,?)",
                  (_redact_identifier(chat_id), _redact_identifier(sender), msg_type,
                   scrub_pii(content_in)[:500], scrub_pii(content_out or "")[:500], model,
                   json.dumps(_safe_attachment_metadata(attachments)), scrub_pii(error or "")[:500]))
        c.commit()
        c.close()
    except Exception as e:
        print(f"[DB ERR] {e}", flush=True)

def rate_ok(chat_id, max_per_min=10):
    try:
        now = int(time.time())
        c = db()
        row = c.execute("SELECT last_msg_ts, count_window FROM rate_limit WHERE chat_id=?", (chat_id,)).fetchone()
        if row:
            last, count = row
            if now - last < 60:
                if count >= max_per_min:
                    c.close()
                    return False
                c.execute("UPDATE rate_limit SET last_msg_ts=?, count_window=count_window+1 WHERE chat_id=?", (now, chat_id))
            else:
                c.execute("UPDATE rate_limit SET last_msg_ts=?, count_window=1 WHERE chat_id=?", (now, chat_id))
        else:
            c.execute("INSERT INTO rate_limit (chat_id,last_msg_ts,count_window) VALUES (?,?,1)", (chat_id, now))
        c.commit()
        c.close()
        return True
    except Exception:
        return True

def log(level, msg, **kw):
    ts = datetime.now(timezone.utc).isoformat()
    # Structured JSON log
    entry = {"ts": ts, "level": level, "msg": scrub_pii(msg), **_scrub_value(kw)}
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

# === Detector de tipo de documento ===
DOC_PATTERNS = [
    ("CPF",         re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b"), "documento com CPF"),
    ("RG",          re.compile(r"\b\d{2}\.\d{3}\.\d{3}-\d{1}\b|\bRG[:\s]*\d"), "RG"),
    ("CNH",         re.compile(r"\bCNH\b|\bcnh\b|\bhabilitacao\b", re.I), "CNH"),
    ("PROCURAÇÃO",  re.compile(r"\bprocuracao\b|\bprocuração\b|\bsubstabelecimento\b", re.I), "procuração"),
    ("ESCRITURA",   re.compile(r"\bescritura\b|\bcompra\s*e\s*venda\b|\bdoacao\b", re.I), "escritura"),
    ("CONTRATO",    re.compile(r"\bcontrato\b|\bclausula\b", re.I), "contrato"),
    ("RECEITA",     re.compile(r"\breceita\b|\bprescri[cç]ao\b|\bdosagem\b|\bmedicamento\b", re.I), "receita médica"),
    ("FATURA",      re.compile(r"\bfatura\b|\bboleto\b|\bvencimento\b|\bvalor\s*a\s*pagar\b", re.I), "fatura/boleto"),
    ("PROTOCOLO",   re.compile(r"\bprotocolo\s*[:#]?\s*\d+", re.I), "protocolo cartório"),
]

def detect_doc_type(text):
    """Detecta tipo de documento pelo texto. Retorna (tipo, hint) ou (None, None)."""
    if not text:
        return None, None
    matches = []
    for name, pat, hint in DOC_PATTERNS:
        if pat.search(text):
            matches.append((name, hint))
    if not matches:
        return None, None
    if len(matches) == 1:
        return matches[0]
    # Prioriza ordem da lista
    for name, hint in matches:
        for orig_name, _, _ in DOC_PATTERNS:
            if orig_name == name:
                return name, hint
    return matches[0]

# === Memória PIETRA (integração com Postgres do cartório) ===
def memory_append(telefone, content, role="user"):
    """Salva msg na memória do PIETRA VPS (vinculada ao telefone)."""
    if not MEMORY_ENABLED or not telefone:
        return False
    try:
        url = f"{PIETRA_BASE}/api/v1/pietra/memoria/{telefone}/append"
        r = requests.post(url, json={"content": content, "role": role}, timeout=5)
        return r.status_code == 200
    except Exception as e:
        log("WARN", "memory_append failed", error=str(e))
        return False

def memory_get(telefone):
    """Recupera histórico do telefone."""
    if not MEMORY_ENABLED or not telefone:
        return []
    try:
        url = f"{PIETRA_BASE}/api/v1/pietra/memoria/{telefone}"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            return r.json().get("messages", [])
    except Exception:
        pass
    return []

def summarize_if_long(text):
    """Se texto > SUMMARY_THRESHOLD chars, pede resumo pro PIETRA."""
    if not text or len(text) <= SUMMARY_THRESHOLD:
        return text
    summary, _, _ = ask_pietra(f"Resuma em 2 frases (PT-BR, sem emoji):\n\n{text[:3000]}")
    return f"[resumo automático, {len(text)} chars → {len(summary)} chars]\n{summary}"

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
        cached = c.execute("SELECT text FROM ocr_cache WHERE file_hash=?", (h,)).fetchone()
        if cached:
            c.close()
            return cached[0]
        c.close()

        # Passa path absoluto e cwd em pasta temp (tesseract tem bug com cwd=/)
        result = subprocess.run(
            ["tesseract", str(Path(path).resolve()), "-", "-l", OCR_LANG, "--psm", "6"],
            capture_output=True, text=True, timeout=30,
            cwd="/tmp"
        )
        text = result.stdout.strip()
        if text:
            # Cache + LGPD scrub (PII pode ter sido extraído pelo OCR)
            text_scrubbed = scrub_pii(text)
            c = db()
            c.execute("INSERT OR REPLACE INTO ocr_cache (file_hash, text) VALUES (?, ?)", (h, text_scrubbed))
            c.commit()
            c.close()
            return text_scrubbed if text_scrubbed else None
        return None
    except subprocess.TimeoutExpired:
        log("WARN", "ocr timeout")
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

def describe_file(path):
    """Descreve arquivo e extrai ZIPs/documentos para o banco BRAIN."""
    p = Path(path)
    if not p.exists():
        return "[arquivo não disponível para análise]"
    size_kb = p.stat().st_size / 1024
    info = f"[arquivo recebido: {size_kb:.0f}KB]"

    # Se for ZIP, descompacta e indexa no BRAIN imediatamente
    if p.suffix.lower() == ".zip" or zipfile.is_zipfile(p):
        try:
            from brain.lark_zip_handler import LarkZipHandler
            handler = LarkZipHandler()
            res = handler.process_incoming_zip(str(p))
            if res.get("success"):
                cnt = res.get("total_files_extracted", 0)
                sample = ", ".join(res.get("files_sample", [])[:5])
                info += f"\n[ZIP PROCESSADO E INDEXADO NO BRAIN]: {cnt} documentos extraídos com sucesso ({sample}...)"
            else:
                info += f"\n[ERRO AO DESCOMPACTAR ZIP]: {res.get('error')}"
        except Exception as e:
            info += f"\n[ERRO AO PROCESSAR ZIP]: {e}"
        return info

    # Se for texto/code, mostra primeiras linhas
    text_exts = {".txt", ".md", ".py", ".js", ".ts", ".json", ".yaml", ".yml", ".csv", ".log", ".sh"}
    if p.suffix.lower() in text_exts and size_kb < 200:
        try:
            content = scrub_pii(p.read_text(errors="ignore"))[:1500]
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
        r = requests.post(f"{LARK_API}/auth/v3/tenant_access_token/internal",
                          json={"app_id": APP_ID, "app_secret": APP_SECRET}, timeout=5).json()
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
        chunk = text[i:i+4000]
        r = requests.post(f"{LARK_API}/im/v1/messages?receive_id_type=chat_id",
            headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
            json={"receive_id": chat_id, "msg_type": "text",
                  "content": json.dumps({"text": chunk})}, timeout=10).json()
        if r.get("code") != 0:
            log("ERR", "send failed", code=r.get("code"), msg=r.get("msg"))
            return False
    return True

def download_resource(media_type, media_key):
    """Baixa mídia validada para um nome interno, sem usar metadados remotos no path."""
    if media_type not in {"image", "file"}:
        return None
    if not isinstance(media_key, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,512}", media_key):
        log("WARN", "attachment rejected: invalid resource key", media_type=media_type)
        return None
    try:
        tok = get_token()
        if not tok:
            return None
        resource_kind = "images" if media_type == "image" else "files"
        url = f"{LARK_API}/im/v1/{resource_kind}/{quote(media_key, safe='')}"
        r = requests.get(
            url,
            headers={"Authorization": f"Bearer {tok}"},
            timeout=30,
            allow_redirects=False,
            stream=True,
        )
        if r.status_code == 200:
            path = _write_attachment(r, media_type)
            return str(path) if path else None
    except Exception as e:
        log("ERR", "download failed", media_type=media_type, error=type(e).__name__)
    return None

# === PIETRA brain ===
def ask_pietra(user_msg, max_retries=2):
    payload = {"messages": [{"role": "user", "content": user_msg}], "max_tokens": 800, "temperature": 0.7}
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
    is_owner = bool(OWNER_OPEN_ID) and sender == OWNER_OPEN_ID

    if t in ("!ajuda", "!help", "!comandos"):
        cmds = (
            "**Comandos (v6):**\n"
            "- `!ajuda` — esta mensagem\n"
            "- `!saude` — status bot + PIETRA\n"
            "- `!modelo` — qual LLM responde\n"
            "- `!ocr <lang>` — muda idioma OCR (por, eng, por+eng)\n"
            "- `!stats` — estatísticas do bot\n"
            "- `!reset` — limpa rate limit\n"
            "- `!doc <texto>` — detecta tipo de documento\n"
            "- imagem/arquivo → OCR + detecção + análise PIETRA\n"
        )
        if is_owner:
            cmds += (
                "\n**Owner only:**\n"
                "- `!bot stop` — encerra o bot\n"
                "- `!bot restart` — reinicia (via launchctl)\n"
                "- `!broadcast <msg>` — envia msg pra todos os chats conhecidos\n"
            )
        return cmds
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
            f"- OCR: {'✓ ('+OCR_LANG+')' if OCR_ENABLED else '✗'}\n"
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

    if t == "!stats":
        try:
            c = db()
            n_msgs = c.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            n_chats = c.execute("SELECT COUNT(DISTINCT chat_id) FROM events").fetchone()[0]
            n_ocr = c.execute("SELECT COUNT(*) FROM ocr_cache").fetchone()[0]
            c.close()
            return (
                f"**Stats:**\n"
                f"- Mensagens processadas: {n_msgs}\n"
                f"- Chats únicos: {n_chats}\n"
                f"- OCR cache: {n_ocr}\n"
                f"- DB: `{DB_PATH}`"
            )
        except Exception as e:
            return f"✗ Erro: {e}"

    if t.startswith("!doc"):
        sample = t[4:].strip() or "Procuracao para Joao da Silva, CPF 123.456.789-00, valor R$ 156,40"
        doc_type, hint = detect_doc_type(sample)
        if doc_type:
            return f"🔎 Detectado: **{doc_type}** ({hint})"
        return f"🤷 Não detectei tipo de documento. Texto: `{sample[:60]}`"

    # === Comandos admin (só owner) ===
    if not is_owner:
        if t.startswith("!bot") or t.startswith("!broadcast"):
            return "⛔ Comando restrito ao owner do bot."

    if t == "!bot stop":
        log("WARN", "owner requested stop", sender=sender)
        # Agenda shutdown em 2s pra resposta chegar antes
        import threading
        def _kill():
            time.sleep(2)
            os._exit(0)
        threading.Thread(target=_kill, daemon=True).start()
        return "🛑 Bot encerrando em 2s..."

    if t == "!bot restart":
        return (
            "↻ Pra reiniciar via launchctl:\n"
            "```\nlaunchctl kickstart -k gui/$(id -u)/ai.zcode.lark-bot\n```"
        )

    if t.startswith("!broadcast"):
        msg = text.strip()[len("!broadcast"):].strip()
        if not msg:
            return "uso: `!broadcast <mensagem>`"
        try:
            c = db()
            chats = [r[0] for r in c.execute("SELECT DISTINCT chat_id FROM events").fetchall()]
            c.close()
            ok, fail = 0, 0
            for ch in chats:
                if send_text(ch, f"📢 {msg}"):
                    ok += 1
                else:
                    fail += 1
            return f"📢 Broadcast: {ok}/{ok+fail} chats enviados"
        except Exception as e:
            return f"✗ Erro: {e}"

    return None

# === Webhook ===
@app.route("/lark/webhook", methods=["POST"])
def webhook():
    if not _lark_configuration_ready():
        log("WARN", "lark callback rejected: configuration incomplete")
        return jsonify({"code": -1}), 503

    body_raw = request.get_data(cache=True)
    if not body_raw or len(body_raw) > MAX_WEBHOOK_BODY_BYTES:
        log("WARN", "lark callback rejected: invalid body size")
        return jsonify({"code": -1}), 413

    timestamp = request.headers.get("X-Lark-Timestamp")
    nonce = request.headers.get("X-Lark-Nonce")
    signature = request.headers.get("X-Lark-Signature")
    if not _valid_lark_signature(body_raw, signature, timestamp, nonce):
        log("WARN", "lark callback rejected: invalid request signature")
        return jsonify({"code": -1}), 401

    try:
        body = json.loads(body_raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        body = {}
    if not isinstance(body, dict):
        log("WARN", "lark callback rejected: invalid JSON payload")
        return jsonify({"code": -1}), 400

    if not _valid_lark_callback(body):
        log("WARN", "lark callback rejected: invalid verification token")
        return jsonify({"code": -1}), 401

    if not claim_callback_nonce(nonce or ""):
        log("WARN", "lark callback rejected: replay or nonce store unavailable")
        return jsonify({"code": -1}), 409

    if body.get("type") == "url_verification":
        challenge = body.get("challenge")
        if not isinstance(challenge, str) or not challenge or len(challenge) > 512:
            log("WARN", "lark callback rejected: invalid challenge")
            return jsonify({"code": -1}), 400
        return jsonify({"challenge": challenge})

    try:
        header = body.get("header")
        event = body.get("event")
        if not isinstance(header, dict) or not isinstance(event, dict):
            log("WARN", "lark callback rejected: invalid event envelope")
            return jsonify({"code": -1}), 400
        event_id = header.get("event_id")
        if not isinstance(event_id, str) or not event_id or len(event_id) > 256:
            log("WARN", "lark callback rejected: missing event id")
            return jsonify({"code": -1}), 400
        if not claim_event(event_id):
            log("WARN", "lark event rejected: replay or event store unavailable")
            return jsonify({"code": -1}), 409
        if header.get("event_type") == "im.message.receive_v1":
            handle_message(event)
        return jsonify({"code": 0})
    except Exception as exc:
        log("ERR", "webhook failed", error=type(exc).__name__)
        return jsonify({"code": -1}), 500

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
        if fk:
            p = download_resource("file", fk)
            if p:
                attachments.append({"type": "file", "path": p})
                extra += "\n" + describe_file(p)
    elif msg_type == "media":  # vídeo/áudio
        # Não analisa, só registra
        extra += "\n[mídia (vídeo/áudio) — não analisada, salvo em disco]"

    log("INFO", "msg", chat=chat_type[:1], sender=sender, type=msg_type, text=text[:60],
        attachments=len(attachments))

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

    user_msg = scrub_pii((text or f"(mensagem {msg_type} sem texto)") + extra)

    # Detector de tipo de documento (se tiver OCR ou texto)
    if extra:
        doc_type, doc_hint = detect_doc_type(extra + " " + text)
        if doc_type:
            user_msg = f"[DOC DETECTADO: {doc_type} — {doc_hint}]\n" + user_msg

    # Resumo automático se msg for muito longa
    if len(user_msg) > SUMMARY_THRESHOLD:
        user_msg = summarize_if_long(user_msg) or user_msg[:SUMMARY_THRESHOLD]

    # Memória PIETRA (vinculada ao chat_id como telefone proxy)
    # chat_id formato: oc_xxx... → usa primeiros 13 chars + prefixo +55
    chat_clean = chat_id.replace("oc_", "")[:13]
    telefone_proxy = f"+55{chat_clean}" if not chat_clean.startswith("+") else chat_clean
    memory_append(telefone_proxy, user_msg[:500], "user")

    reply, model, err = ask_pietra(user_msg)
    reply = scrub_pii(reply or "")
    memory_append(telefone_proxy, reply[:500], "assistant")

    send_text(chat_id, reply)
    log_event(chat_id, sender, msg_type, user_msg, reply, model, attachments, err)

@app.route("/test-image", methods=["POST"])
def test_image():
    """Endpoint diagnóstico, deliberadamente indisponível fora do loopback autenticado."""
    if not _local_ocr_test_authorized():
        # A 404 avoids advertising a diagnostic upload endpoint in production.
        return jsonify({"error": "not found"}), 404
    if 'file' not in request.files:
        return jsonify({"error": "missing file"}), 400
    f = request.files['file']
    content_type = (f.content_type or "").lower()
    if content_type not in IMAGE_CONTENT_TYPES:
        return jsonify({"error": "unsupported media type"}), 415
    try:
        stream = f.stream
        class _LocalUpload:
            headers = {"Content-Type": content_type}

            def iter_content(self, chunk_size=65536):
                while chunk := stream.read(chunk_size):
                    yield chunk

        p = _write_attachment(_LocalUpload(), "image")
    except OSError:
        p = None
    if not p:
        return jsonify({"error": "upload rejected"}), 413
    # OCR remains local and scrubbed; its output is intentionally not returned or sent upstream.
    describe_image(p)
    return jsonify({
        "status": "accepted",
        "size_kb": p.stat().st_size // 1024,
        "ocr_attempted": OCR_ENABLED,
    })

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

    return jsonify({
        "bot": "v6 ok",
        "lark_configured": bool(APP_ID),
        "pietra_ok": pietra_ok,
        "ocr_available": tess,
        "ocr_lang": OCR_LANG,
        "quiet_group": LARK_QUIET_GROUP,
        "attachment_retention_seconds": ATTACHMENT_RETENTION_SECONDS,
    })

if __name__ == "__main__":
    log("INFO", "lark bot v4 starting", port=PORT, ocr=OCR_ENABLED, lang=OCR_LANG)
    app.run(host="0.0.0.0", port=PORT, debug=False)
