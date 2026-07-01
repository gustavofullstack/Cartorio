#!/usr/bin/env python3
"""Gera SQL para resetar/criar credenciais N8N via DB.

Uso: python3 scripts/reset_n8n_password.py
Imprime os comandos SQL para colar no psql.
"""

import sys

try:
    import bcrypt
except ImportError:
    print("Installing bcrypt...")
    import subprocess

    subprocess.run([sys.executable, "-m", "pip", "install", "bcrypt", "-q"], check=True)
    import bcrypt

PW = "@Techno832466"
PW_HASH = bcrypt.hashpw(PW.encode(), bcrypt.gensalt(rounds=10)).decode()

# Para o user já existente admin@cartorio.local
ADMIN_ID = "a65815fb-a12a-4bc8-a3eb-293f22c50a4b"

print(f"-- Hash bcrypt para senha '{PW}': {PW_HASH[:30]}...\n")
print(f"-- 1) auth_identity para admin@cartorio.local (já existente):")
print(f"""INSERT INTO auth_identity ("userId", "providerId", "providerType", "createdAt", "updatedAt")
VALUES ('{ADMIN_ID}', 'admin@cartorio.local', 'email', NOW(), NOW())
ON CONFLICT ("providerId", "providerType")
DO UPDATE SET "userId" = '{ADMIN_ID}';""")

print()
print(f"-- 2) criar user gustavomar.fullstack@gmail.com com role global:owner:")
print(f"""INSERT INTO "user" (id, email, "firstName", "lastName", "password", "roleSlug", "createdAt", "updatedAt")
VALUES (
    'b0000001-0000-0000-0000-000000000001',
    'gustavomar.fullstack@gmail.com',
    'Gustavo',
    'Almeida',
    'PLACEHOLDER_HASH',
    'global:owner',
    NOW(),
    NOW()
) ON CONFLICT (email) DO NOTHING;""")

print(f"""
-- 3) auth_identity para gustavomar.fullstack@gmail.com:
INSERT INTO auth_identity ("userId", "providerId", "providerType", "createdAt", "updatedAt")
VALUES (
    'b0000001-0000-0000-0000-000000000001',
    'gustavomar.fullstack@gmail.com',
    'email',
    NOW(),
    NOW()
) ON CONFLICT ("providerId", "providerType") DO NOTHING;""")
