import psycopg

conn = psycopg.connect("host=127.0.0.1 port=5432 user=gustavoalmeida dbname=postgres")
conn.autocommit = True
with conn.cursor() as cur:
    try:
        cur.execute("CREATE ROLE supabase_admin WITH LOGIN SUPERUSER PASSWORD 'KqJ2kWjkYwZxKpLnBMVbtA';")
    except psycopg.errors.DuplicateObject:
        pass
    try:
        cur.execute("CREATE DATABASE cartorio;")
    except psycopg.errors.DuplicateDatabase:
        pass
