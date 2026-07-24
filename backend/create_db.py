"""Bootstrap local Postgres role/db for dev only.

NUNCA hardcode senha. Use env SUPABASE_ADMIN_PASSWORD (ou skip role create).
Script ad-hoc — nao usar em producao.

Modified by Gustavo Almeida
"""

from __future__ import annotations

import os
import sys

import psycopg

password = os.environ.get("SUPABASE_ADMIN_PASSWORD", "").strip()
dsn = os.environ.get(
    "POSTGRES_SUPERUSER_DSN",
    "host=127.0.0.1 port=5432 user=gustavoalmeida dbname=postgres",
)

conn = psycopg.connect(dsn)
conn.autocommit = True
with conn.cursor() as cur:
    if password:
        try:
            # password via psycopg param — never interpolate into SQL string
            cur.execute(
                "CREATE ROLE supabase_admin WITH LOGIN SUPERUSER PASSWORD %s",
                (password,),
            )
        except psycopg.errors.DuplicateObject:
            pass
    else:
        print(
            "SUPABASE_ADMIN_PASSWORD ausente — pulando CREATE ROLE "
            "(defina a env para criar o role).",
            file=sys.stderr,
        )
    try:
        cur.execute("CREATE DATABASE cartorio;")
    except psycopg.errors.DuplicateDatabase:
        pass
