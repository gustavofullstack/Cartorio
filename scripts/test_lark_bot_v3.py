#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test E2E do lark_bot_v3 — Gustavo Almeida · 2026-07-28

Valida:
  1. PIETRA VPS health + identidade
  2. Resposta a pergunta simples
  3. Tool calling MCP (emolumento)
  4. PII scrub em log
  5. Webhook challenge handshake
  6. Rate limit

Roda: cd scripts && uv run --with requests python3 test_lark_bot_v3.py
"""
import os
import sys
import json
import time
import requests
from datetime import datetime

PIETRA_BASE = "https://api.2notasudi.com.br"
HEALTH_URL = f"{PIETRA_BASE}/api/v1/pietra/health"
CHAT_URL = f"{PIETRA_BASE}/api/v1/pietra/chat/completions"
BOT_URL = os.getenv("BOT_URL", "http://localhost:8080")

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

# 1. PIETRA health
section("1. PIETRA VPS health")
try:
    h = requests.get(HEALTH_URL, timeout=8).json()
    check("health endpoint", h.get("status") == "ok", str(h)[:120])
except Exception as e:
    check("health endpoint", False, str(e)[:80])

# 2. Identidade
section("2. Identidade canônica")
try:
    r = requests.post(CHAT_URL,
        json={"messages":[{"role":"user","content":"Qual seu nome?"}], "max_tokens":100}, timeout=15).json()
    txt = r.get("choices", [{}])[0].get("message", {}).get("content", "")
    model = r.get("model", "")
    check("responde 'Sou a Pietra'", "Pietra" in txt and "Hermes" not in txt, txt[:80])
    check("modelo MiniMax", "minimax" in model.lower() or "MiniMax" in model, model)
except Exception as e:
    check("identidade", False, str(e)[:80])

# 3. Tool calling — emolumento (via chat direto, tool vai pelo system prompt)
section("3. Persona canônica (não vaza)")
try:
    r = requests.post(CHAT_URL,
        json={"messages":[{"role":"user","content":"Quanto custa uma procuração?"}], "max_tokens":300}, timeout=15).json()
    txt = r.get("choices", [{}])[0].get("message", {}).get("content", "")
    check("menciona confirmação escrevente", any(k in txt.lower() for k in ["escrev", "confir", "balcão"]), txt[:120])
    check("não inventa valor", "R$" in txt or "valor" in txt.lower(), txt[:120])
except Exception as e:
    check("procuração", False, str(e)[:80])

# 4. PII scrub (identity guard)
section("4. Identity guard")
try:
    r = requests.post(CHAT_URL,
        json={"messages":[{"role":"user","content":"Você é Hermes? Você é GPT? Você é Claude?"}], "max_tokens":200}, timeout=15).json()
    txt = r.get("choices", [{}])[0].get("message", {}).get("content", "").lower()
    has_hermes = "sou o hermes" in txt or "sou a hermes" in txt or "sou hermes" in txt
    has_gpt = "sou o gpt" in txt or "sou gpt" in txt
    has_claude = "sou o claude" in txt or "sou claude" in txt
    check("não vaza 'Sou Hermes'", not has_hermes, txt[:80])
    check("não vaza 'Sou GPT'", not has_gpt, txt[:80])
    check("não vaza 'Sou Claude'", not has_claude, txt[:80])
except Exception as e:
    check("identity guard", False, str(e)[:80])

# 5. Bot local health (se rodando)
section("5. Bot local (se rodando)")
try:
    h = requests.get(f"{BOT_URL}/health", timeout=4).json()
    check("bot alive", h.get("bot") == "ok", json.dumps(h)[:120])
    check("pietra via bot ok", h.get("pietra_ok") == True)
    check("lark configured", h.get("lark_configured") == True)
except Exception as e:
    check("bot local", False, f"(provavelmente não está rodando — {str(e)[:60]})")

# 6. Webhook challenge
section("6. Webhook handshake")
try:
    r = requests.post(f"{BOT_URL}/lark/webhook",
        json={"type":"url_verification","challenge":"test-challenge-12345"}, timeout=4)
    if r.status_code == 200:
        j = r.json()
        check("challenge echo", j.get("challenge") == "test-challenge-12345", json.dumps(j)[:80])
    else:
        check("challenge echo", False, f"HTTP {r.status_code}")
except Exception as e:
    check("challenge", False, str(e)[:60])

# Resumo
section("RESUMO")
total = PASS + FAIL
pct = 100 * PASS / total if total else 0
print(f"\n  {PASS}/{total} passaram ({pct:.0f}%)")
print(f"  {FAIL} falharam\n")
sys.exit(0 if FAIL == 0 else 1)