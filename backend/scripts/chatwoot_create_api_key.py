"""chatwoot_create_api_key.py - gera API key do Chatwoot via Rails console.

SQUAD H H8 - resolver H8 Chatwoot API key placeholder.

O Gustavo colocou 'SUI_GUSTAVO_GERAR_VIA_RAILS_CONSOLE_OU_CHATWOOT_UI' no
backend/.env como placeholder. Este script:
1. Conecta no container cartorio_chatwoot-1
2. Executa Rails runner que cria access_token para User.first.accounts.first
3. Imprime o token para Gustavo copiar e colar no .env

Pre-requisito: docker exec no host
Uso:
  cd backend
  uv run python scripts/chatwoot_create_api_key.py
"""

from __future__ import annotations

import argparse
import subprocess
import sys


CHATWOOT_CONTAINER = "cartorio_chatwoot-1"

RAILS_CMD = """
user = User.find_by(email: 'admin@2notasudi.com.br') || User.first
account = user.accounts.first
existing = account.access_tokens.find_by(name: 'cartorio-api')
if existing
  puts 'Token existente (revogando para criar novo):'
  existing.destroy
end
token = account.access_tokens.create!(name: 'cartorio-api', scope: 'administrator')
puts 'TOKEN_NOVO=' + token.token
puts 'ACCOUNT_ID=' + account.id.to_s
puts 'USER_ID=' + user.id.to_s
puts 'USER_EMAIL=' + user.email
""".strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--container",
        default=CHATWOOT_CONTAINER,
        help="nome do container Chatwoot",
    )
    args = parser.parse_args()

    print(f"=== Gerar API key do Chatwoot via Rails console ({args.container}) ===\n")

    cmd = [
        "docker",
        "exec",
        args.container,
        "bash",
        "-c",
        f"bundle exec rails runner '{RAILS_CMD.replace(chr(39), chr(34) + chr(34))}'",
    ]
    print(f"Comando: {' '.join(cmd[:6])}...\n")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        print("ERRO: timeout 60s no docker exec", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 1

    print("--- STDOUT ---")
    print(result.stdout)
    if result.stderr:
        print("--- STDERR ---")
        print(result.stderr[-1000:])

    if "TOKEN_NOVO=" in result.stdout:
        # Extrair o token
        for line in result.stdout.splitlines():
            if line.startswith("TOKEN_NOVO="):
                token = line.split("=", 1)[1]
                print("\n=== ACAO PARA GUSTAVO ===")
                print(f"1. Copie o token: {token}")
                print(
                    "2. Edite backend/.env e troque CHATWOOT_API_KEY=SUI_GUSTAVO_GERAR_VIA_RAILS_CONSOLE_OU_CHATWOOT_UI"
                )
                print(f"   por: CHATWOOT_API_KEY={token}")
                print("3. Restart API: docker service update --force cartorio_api")
                print(
                    f"4. Validar: curl -H 'api_access_token: {token}' https://chat.2notasudi.com.br/api/v1/accounts"
                )
                return 0
    print("\nERRO: Rails runner nao retornou TOKEN_NOVO=", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
