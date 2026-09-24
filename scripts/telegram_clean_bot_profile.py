#!/usr/bin/env python3
"""Limpa descricao do bot (remove spam porn de "What can this bot do?") e
atualiza nome curto + descricao profissional do cartorio.

Uso:
  export TELEGRAM_BOT_TOKEN=...
  python scripts/telegram_clean_bot_profile.py

Ou:
  TELEGRAM_BOT_TOKEN=xxx python scripts/telegram_clean_bot_profile.py
"""

from __future__ import annotations

import os
import sys

import httpx

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
API = os.environ.get("TELEGRAM_API_BASE", "https://api.telegram.org")

DESC = (
    "Assistente do 2o Oficio de Notas de Uberlandia/MG. "
    "Informacoes, valores de referencia, agendamento e pre-qualificacao. "
    "Atos oficiais com validacao humana. Privacidade: LGPD — /lgpd"
)

SHORT = (
    "Cartorio 2o Oficio de Notas — Uberlandia/MG. "
    "Atendimento, agendamento e pre-qualificacao com LGPD."
)

ABOUT = (
    "Canal oficial de atendimento do cartorio. "
    "Nao e tabeliao. Nao emite certidao sozinho. "
    "DPO: dpo@2notasudi.com.br"
)


def main() -> int:
    if not TOKEN or "COLOQUE" in TOKEN:
        print("Defina TELEGRAM_BOT_TOKEN no ambiente.", file=sys.stderr)
        return 1
    base = f"{API.rstrip('/')}/bot{TOKEN}"
    with httpx.Client(timeout=20.0) as client:
        steps = [
            ("setMyDescription", {"description": DESC}),
            ("setMyShortDescription", {"short_description": SHORT}),
            ("setMyName", {"name": "Cartorio 2o Oficio — Udi"}),
            (
                "setMyCommands",
                {
                    "commands": [
                        {"command": "start", "description": "Aviso LGPD e inicio"},
                        {"command": "menu", "description": "Atalhos opcionais"},
                        {"command": "humano", "description": "Atendimento humano"},
                        {"command": "lgpd", "description": "Privacidade LGPD"},
                        {"command": "cancelar", "description": "Limpar conversa"},
                    ]
                },
            ),
        ]
        for method, payload in steps:
            r = client.post(f"{base}/{method}", json=payload)
            print(method, r.status_code, r.text[:200])
        # verify
        for method in ("getMyDescription", "getMyShortDescription", "getMe"):
            r = client.get(f"{base}/{method}")
            print(method, r.status_code, r.text[:300])
    print("OK — confira no app Telegram o perfil do bot (sem links porn).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
