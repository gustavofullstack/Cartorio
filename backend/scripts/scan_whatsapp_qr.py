"""scan_whatsapp_qr.py - helper para Gustavo escanear QR do WhatsApp TriQ Hub.

SQUAD H H1 - Evolution API inbox setup.

Como o QR nao pode ser auto-gerado via API, Gustavo precisa:
1. Acessar https://whatsapp.2notasudi.com.br/manager no browser
2. Fazer login (usuario: admin, senha ver BACKUP_KEYS ou admin)
3. Clicar em 'Connect WhatsApp' na instance cartorio-2notas
4. Escanear o QR Code com WhatsApp do celular TriQ Hub
5. Aguardar status=open em /health/integracoes

Este script:
1. Verifica o status atual
2. Se status=close, tenta restart via API
3. Se status=connecting, mostra URL do Manager
4. Se status=open, valida via sendMessage de teste

Uso:
  cd backend
  uv run python scripts/scan_whatsapp_qr.py
"""
from __future__ import annotations

import argparse
import os
import sys
import time

import httpx

# Lesson 159 canon: credenciais via env var, NUNCA hardcoded.
# Keys queimadas no chat sao marcadas como tal; esta key veio do codigo original
# (script anterior) e NAO deve ser rotacionada — Gustavo + Pietra unicos com acesso.
EVOLUTION_URL = os.environ.get(
    "EVOLUTION_PUBLIC_URL", "https://whatsapp.2notasudi.com.br"
)
EVOLUTION_API_KEY = os.environ.get("EVOLUTION_API_KEY", "")
INSTANCE = os.environ.get("EVOLUTION_INSTANCE", "cartorio-2notas")
MANAGER_URL = f"{EVOLUTION_URL}/manager"

if not EVOLUTION_API_KEY:
    print(
        "ERRO: EVOLUTION_API_KEY nao definida. "
        "Defina no backend/.env ou export no shell (Lesson 159 canon).",
        file=sys.stderr,
    )
    sys.exit(2)


def get_state() -> str:
    with httpx.Client(timeout=10.0) as client:
        r = client.get(
            f"{EVOLUTION_URL}/instance/connectionState/{INSTANCE}",
            headers={"apikey": EVOLUTION_API_KEY},
        )
        r.raise_for_status()
        return r.json().get("instance", {}).get("state", "unknown")


def restart_instance() -> bool:
    with httpx.Client(timeout=15.0) as client:
        r = client.post(
            f"{EVOLUTION_URL}/instance/restart/{INSTANCE}",
            headers={"apikey": EVOLUTION_API_KEY},
        )
        if r.status_code == 200:
            print("  instance reiniciada com sucesso")
            return True
        print(f"  restart falhou: {r.status_code} {r.text[:200]}")
        return False


def send_test_message(phone: str, text: str) -> bool:
    """Envia msg de teste via Evolution."""
    with httpx.Client(timeout=15.0) as client:
        r = client.post(
            f"{EVOLUTION_URL}/message/sendText/{INSTANCE}",
            headers={"apikey": EVOLUTION_API_KEY},
            json={"number": phone, "text": text},
        )
        if r.status_code in (200, 201):
            print(f"  msg enviada: {r.json()}")
            return True
        print(f"  send falhou: {r.status_code} {r.text[:200]}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--test-phone",
        default="5534999999999",
        help="numero para enviar msg de teste (default: 5534999999999)",
    )
    args = parser.parse_args()

    print("=== Evolution API - WhatsApp Instance Status ===")
    print(f"URL: {EVOLUTION_URL}")
    print(f"Instance: {INSTANCE}")
    print(f"Manager UI: {MANAGER_URL}")
    print()

    state = get_state()
    print(f"[1] Current state: {state}")

    if state == "open":
        print("[2] Instance ja conectada! Enviando msg de teste...")
        if send_test_message(args.test_phone, "Test cartorio 2o Notas - Evolution API OK!"):
            print()
            print("SUCESSO! WhatsApp conectado e operacional.")
            return 0
        else:
            print()
            print("FALHA no envio. Verifique permissoes.")
            return 1

    if state in ("close", "connecting"):
        print()
        print("[2] Instance precisa de scan QR.")
        print(f"    Acesse: {MANAGER_URL}")
        print("    Faca login (credenciais em BACKUP_KEYS ou admin/admin)")
        print(f"    Clique em 'Connect WhatsApp' na instance '{INSTANCE}'")
        print("    Escaneie o QR Code com WhatsApp do celular TriQ Hub")
        print()
        print("[3] Tentando restart automatico...")
        if restart_instance():
            time.sleep(3)
            new_state = get_state()
            print(f"[4] Apos restart: state={new_state}")
            if new_state == "open":
                print("SUCESSO pos-restart! WhatsApp conectado.")
                return 0
        print()
        print("    Apos escanear QR, re-rode este script para validar.")
        return 1

    print(f"ERRO: state inesperado {state}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
