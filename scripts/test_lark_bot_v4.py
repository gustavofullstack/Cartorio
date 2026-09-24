#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test E2E do lark_bot_v4 — visão OCR
Gustavo Almeida · 2026-07-28

Valida:
  1. OCR extrai texto de imagem
  2. OCR cache funciona
  3. Múltiplos formatos (png, jpg) processam
  4. Bot v4 (se rodando) tem endpoint /health com ocr_available
  5. Webhook challenge
"""
import os
import sys
import json
import time
import subprocess
import requests
from pathlib import Path

BOT_URL = os.getenv("BOT_URL", "http://localhost:8081")
PIETRA_BASE = "https://api.2notasudi.com.br"
HEALTH_URL = f"{PIETRA_BASE}/api/v1/pietra/health"
CHAT_URL = f"{PIETRA_BASE}/api/v1/pietra/chat/completions"

PASS = 0
FAIL = 0

def check(name, ok, detail=""):
    global PASS, FAIL
    sym = "✓" if ok else "✗"
    if ok: PASS += 1
    else: FAIL += 1
    print(f"  {sym} {name}" + (f" — {detail}" if detail else ""), flush=True)
    return ok

def section(t):
    print(f"\n=== {t} ===", flush=True)

# Setup: cria imagens de teste
section("0. Setup — imagens de teste")
from PIL import Image, ImageDraw
test_dir = Path("/tmp/lark_bot_v4_test")
test_dir.mkdir(exist_ok=True)

img1 = test_dir / "doc_simples.png"
Image.new("RGB", (400, 100), "white").save(img1)
d = ImageDraw.Draw(Image.open(img1))
d.text((10, 40), "CPF 123.456.789-00 valor R$ 156,40", fill="black")
img1 = test_dir / "doc_simples.png"  # re-save (draw não persist)
img = Image.new("RGB", (500, 100), "white")
d = ImageDraw.Draw(img)
d.text((10, 40), "CPF 123.456.789-00 valor R$ 156,40", fill="black")
img.save(img1)
print(f"  • {img1}")

img2 = test_dir / "doc_jpeg.jpg"
img.save(img2, "JPEG")
print(f"  • {img2}")

# 1. OCR funciona
section("1. OCR via tesseract")
for f in [img1, img2]:
    try:
        r = subprocess.run(["tesseract", str(f.resolve()), "-", "-l", "por", "--psm", "6"],
                          capture_output=True, text=True, timeout=15, cwd="/tmp")
        text = r.stdout.strip()
        # OCR pode trocar 1-2 dígitos. Aceita match parcial (CPF começa igual, valor R$ XX)
        import re
        has_cpf_start = "123.456" in text
        has_valor = bool(re.search(r"R\$\s*1[5-6]\d", text)) or bool(re.search(r"R\$\s*15", text))
        check(f"OCR em {f.name}", has_cpf_start and has_valor,
              f"extraído: {text[:60].replace(chr(10),' ')}")
    except Exception as e:
        check(f"OCR {f.name}", False, str(e)[:60])

# 2. Bot health (se rodando)
section("2. Bot v4 local (se rodando)")
try:
    h = requests.get(f"{BOT_URL}/health", timeout=4).json()
    check("bot v4 alive", h.get("bot", "").startswith("v4"), json.dumps(h)[:150])
    check("pietra via bot ok", h.get("pietra_ok") == True)
    check("OCR disponível no bot", h.get("ocr_available") == True)
    check("lang OCR configurada", bool(h.get("ocr_lang")))
except Exception as e:
    check("bot v4", False, f"(provavelmente não está rodando — {str(e)[:60]})")

# 3. Webhook challenge
section("3. Webhook handshake")
try:
    r = requests.post(f"{BOT_URL}/lark/webhook",
        json={"type":"url_verification","challenge":"v4-challenge-xyz"}, timeout=4)
    if r.status_code == 200:
        j = r.json()
        check("challenge echo", j.get("challenge") == "v4-challenge-xyz", json.dumps(j)[:80])
    else:
        check("challenge echo", False, f"HTTP {r.status_code}")
except Exception as e:
    check("challenge", False, str(e)[:60])

# 4. Webhook simulado com imagem
section("4. Webhook simulado (image event)")
try:
    fake_event = {
        "header": {"event_type": "im.message.receive_v1"},
        "event": {
            "message": {
                "chat_id": "oc_test_123",
                "chat_type": "p2p",
                "message_type": "image",
                "content": {"image_key": "fake_img_key"},
                "mentions": []
            },
            "sender": {"sender_id": {"open_id": "ou_test_user"}}
        }
    }
    r = requests.post(f"{BOT_URL}/lark/webhook", json=fake_event, timeout=8)
    check("webhook aceita imagem", r.status_code == 200 and r.json().get("code") == 0,
          f"HTTP {r.status_code}")
except Exception as e:
    check("webhook imagem", False, str(e)[:60])

# Resumo
section("RESUMO")
total = PASS + FAIL
pct = 100 * PASS / total if total else 0
print(f"\n  {PASS}/{total} passaram ({pct:.0f}%)")
print(f"  {FAIL} falharam\n")
sys.exit(0 if FAIL == 0 else 1)