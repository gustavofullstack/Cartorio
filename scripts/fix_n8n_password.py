#!/usr/bin/env python3
"""Atualiza senha dos usuários N8N diretamente no Postgres via SSH.

Uso: python3 scripts/fix_n8n_password.py
"""

import os
import shlex
import subprocess

import bcrypt

EMAIL_LOCAL = "admin@cartorio.local"
EMAIL_GUSTAVO = "gustavomar.fullstack@gmail.com"
PASSWORD = os.environ.get("N8N_ADMIN_PASSWORD", "")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_ADMIN_PASSWORD", "")

if not PASSWORD or not POSTGRES_PASSWORD:
    raise SystemExit(
        "N8N_ADMIN_PASSWORD e POSTGRES_ADMIN_PASSWORD devem ser injetadas pelo secret manager"
    )

# bcryptjs compatível ($2b$)
NEW_HASH = bcrypt.hashpw(PASSWORD.encode(), bcrypt.gensalt(rounds=10)).decode()
print(f"Novo hash (60 chars): {NEW_HASH} len={len(NEW_HASH)}")

# Pre-sql com placeholder
sql = f"""
UPDATE "user" SET password = '{NEW_HASH}' WHERE email IN ('{EMAIL_LOCAL}', '{EMAIL_GUSTAVO}');
SELECT email, length(password) AS len_pwd, substring(password, 1, 15) AS prefix FROM "user";
"""

cmd = f"""ssh -i ~/.ssh/id_ed25519_cartorio -o ConnectTimeout=10 root@100.99.172.84 <<'SSH_END'
SID=$(docker ps -q --filter name=cartorio_supabase | head -1)
docker exec -i $SID sh <<'PSQL_END'
PGPASSWORD={shlex.quote(POSTGRES_PASSWORD)} psql -U admin -d supabase <<SQL_END
{sql}
SQL_END
PSQL_END
SSH_END
"""

r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
print("STDOUT:", r.stdout[-2000:])
print("STDERR:", r.stderr[-500:])
print("RETURN:", r.returncode)
