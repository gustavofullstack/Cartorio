"""seed_vault_secrets.py - popula Supabase Vault com 11 secrets do projeto.

SQUAD S0 S08 - operador roda este script APOS a migration 0008.

Le /Users/gustavoalmeida/projetos/Cartorio/.secrets/{cartorio,backend,
chatwoot,evolution,n8n,telegram,jules,render,linear}.env e cria
cada chave no vault via RPC vault.create_secret() (ou INSERT direto
em vault.secrets para self-hosted).

IDEMPOTENTE: deleta secret existente antes de criar (mesmo nome).
LGPD-safe: nao imprime os valores, apenas sucesso/falha.

Uso:
  cd backend
  uv run python scripts/seed_vault_secrets.py --dry-run
  uv run python scripts/seed_vault_secrets.py

Pre-requisitos:
  pgsodium + vault ja habilitados (migration 0008)
  DATABASE_URL aponta para o db do Supabase
  service_role key para autenticar (ou rodar dentro do container)
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import psycopg
from dotenv import dotenv_values

# Mapeamento: env_var_name -> (vault_secret_name, secrets_file_basename)
SECRETS_MAP = [
    ("CARTORIO_API_KEY", "cartorio_api_key", "cartorio"),
    ("AUDIT_HMAC_KEY", "audit_hmac_key", "cartorio"),
    ("OPENCODE_GO_API_KEY", "opencode_go_api_key", "opencode-go"),
    ("CHATWOOT_API_KEY", "chatwoot_api_key", "chatwoot"),
    ("EVOLUTION_API_KEY", "evolution_api_key", "evolution"),
    ("N8N_API_KEY", "n8n_api_key", "n8n"),
    ("N8N_WEBHOOK_SECRET", "n8n_webhook_secret", "n8n"),
    ("TELEGRAM_BOT_TOKEN", "telegram_bot_token", "telegram"),
    ("JULES_API_KEY", "jules_api", "jules"),
    ("RENDER_API_KEY", "render_api", "render"),
    ("LINEAR_API_KEY", "linear_api", "linear"),
]


def load_secrets_from_files(secrets_dir: Path) -> dict[str, str]:
    """Le todos os .env em secrets_dir + backend/.env e retorna dict {VAR_NAME: value}."""
    merged: dict[str, str] = {}
    # 1. backend/.env (fonte canonica para cartorio_api_key, audit_hmac_key, n8n_webhook_secret)
    local_env = Path(__file__).parent.parent / ".env"
    if local_env.exists():
        merged.update({k: v for k, v in dotenv_values(local_env).items() if v is not None})
    # 2. diretorio de secrets
    if secrets_dir.exists():
        for env_file in secrets_dir.glob("*.env"):
            vals = dotenv_values(env_file)
            for k, v in vals.items():
                if v is not None and k not in merged:
                    merged[k] = v
    return merged


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="apenas mostra o que faria")
    parser.add_argument("--secrets-dir", default=str(Path.home() / ".mavis/secrets"),
                        help="diretorio com .env files")
    args = parser.parse_args()

    secrets_dir = Path(args.secrets_dir)
    project_secrets = Path("/Users/gustavoalmeida/projetos/Cartorio/.secrets")
    secrets = load_secrets_from_files(secrets_dir) or load_secrets_from_files(project_secrets)
    if not secrets:
        print("ERRO: nenhum .env encontrado em", secrets_dir, "ou", project_secrets, file=sys.stderr)
        return 1

    print(f"Encontradas {len(secrets)} env vars em {secrets_dir} + {project_secrets}")

    database_url = os.environ.get("DATABASE_URL") or secrets.get("DATABASE_URL")
    if not database_url:
        print("ERRO: DATABASE_URL nao definida", file=sys.stderr)
        return 1

    # Mostra mapeamento (com fallback para variantes _TEST_CARTORIO)
    FALLBACKS = {
        "TELEGRAM_BOT_TOKEN": ["TELEGRAM_BOT_TOKEN_TEST_CARTORIO"],
    }
    print("\nMapeamento vault:")
    for env_var, vault_name, source in SECRETS_MAP:
        actual = env_var
        value = secrets.get(env_var)
        if not value and env_var in FALLBACKS:
            for fb in FALLBACKS[env_var]:
                if fb in secrets:
                    actual = fb
                    value = secrets[fb]
                    break
        if value:
            masked = value[:4] + "***" + value[-4:]
            print(f"  {actual:30s} -> vault.secrets.{vault_name:30s} ({source}.env)  {masked}")
        else:
            print(f"  {env_var:30s} -> FALTA (esperado em {source}.env)")

    if args.dry_run:
        print("\nDRY-RUN: nada foi escrito")
        return 0

    # Conecta e popula
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            ok = 0
            skip = 0
            for env_var, vault_name, _source in SECRETS_MAP:
                if env_var not in secrets:
                    skip += 1
                    continue
                value = secrets[env_var]
                if not value or value.startswith("SUI_GUSTAVO"):
                    print(f"  SKIP {vault_name}: valor placeholder/invalido")
                    skip += 1
                    continue
                # Idempotente: delete + insert
                cur.execute("DELETE FROM vault.secrets WHERE name = %s", (vault_name,))
                # vault.create_secret eh funcao SECURITY DEFINER (pgsodium)
                try:
                    cur.execute(
                        "SELECT vault.create_secret(%s, %s, %s)",
                        (value, vault_name, f"Cartorio 2o Notas - {vault_name} (seed 2026-06-25)"),
                    )
                    print(f"  OK   {vault_name}")
                    ok += 1
                except Exception as e:
                    print(f"  FAIL {vault_name}: {e}")
                    skip += 1
            conn.commit()
    print(f"\nResultado: {ok} criados, {skip} skipped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
