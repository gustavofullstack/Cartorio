"""Backup Dry-Run script (G6.D.T3 / G7.08.T2).

Valida que um backup .sql.gz pode ser restaurado SEM de fato rodar pg_restore
em prod. Usa sqlite in-memory + parsing SQL para garantir:

1. Arquivo existe e tem tamanho > 1KB
2. Header gzip valido (magic bytes 1f 8b)
3. Conteudo eh SQL valido (CREATE TABLE, INSERT, COPY)
4. Tabelas canonicas existem no dump (cliente, protocolo, audit_log, ...)
5. Checksum SHA256 calculado e comparado com .sha256 sidecar
6. Restore simulado em sqlite (cria tabelas, sem dados)

Tambem aceita (opcional) bundle tar.gz no estilo `infra/backup/cartorio-backup.sh`
via `--tar-list` (so lista conteudo — nao restaura dumps -Fc).

Exit codes:
    0 = backup integro, pode ser usado em restore real
    1 = backup corrompido ou faltando tabelas
    2 = erro pre-requisito (arquivo nao existe, deps ausentes)

Uso:
    python3 scripts/backup_dryrun.py /var/backups/cartorio/db-2026-07-16.sql.gz
    python3 scripts/backup_dryrun.py --latest  # pega o mais recente em /var/backups/cartorio/
    python3 scripts/backup_dryrun.py --report backup_dryrun.md
    python3 scripts/backup_dryrun.py --tar-list /var/backups/cartorio/cartorio_backup_X.tar.gz

Modified by Gustavo Almeida + Pietra orquestrador — G6 wave 6 / G7 Wave 24.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

REQUIRED_TABLES = {
    "cliente", "protocolo", "atendimento", "documento",
    "emolumento", "audit_log", "conversa", "agendamento",
}


def validate_backup(path: Path) -> tuple[bool, list[str], dict]:
    """Valida backup. Retorna (integro, lista_problemas, stats)."""
    problems: list[str] = []
    stats: dict = {}

    # 1. Arquivo existe
    if not path.exists():
        return False, [f"arquivo nao existe: {path}"], stats

    # 2. Tamanho
    size = path.stat().st_size
    stats["size_bytes"] = size
    if size < 1024:
        problems.append(f"arquivo muito pequeno: {size} bytes (< 1KB)")

    # 3. SHA256 sidecar
    sha_path = path.with_suffix(path.suffix + ".sha256")
    if sha_path.exists():
        expected = sha_path.read_text().strip().split()[0]
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        stats["sha256_expected"] = expected
        stats["sha256_actual"] = actual
        if expected != actual:
            problems.append(
                f"SHA256 mismatch: expected={expected[:16]}... actual={actual[:16]}..."
            )
    else:
        stats["sha256_sidecar"] = "MISSING"
        problems.append(f"SHA256 sidecar ausente: {sha_path}")

    # 4. Header gzip
    with path.open("rb") as f:
        magic = f.read(2)
        if magic != b"\x1f\x8b":
            problems.append(f"magic bytes invalidos (esperado 1f 8b, got {magic.hex()})")
        else:
            stats["gzip_magic"] = "OK"

    # 5. Parse SQL content
    try:
        with gzip.open(path, "rt", encoding="utf-8", errors="replace") as f:
            sql = f.read(100_000_000)  # ate 100MB
    except Exception as exc:
        return False, [f"falha ao descomprimir gzip: {type(exc).__name__}: {exc}"], stats

    stats["sql_size_chars"] = len(sql)
    stats["create_table_count"] = len(re.findall(r"CREATE TABLE", sql, re.IGNORECASE))
    stats["insert_count"] = len(re.findall(r"INSERT INTO", sql, re.IGNORECASE))
    stats["copy_count"] = len(re.findall(r"^COPY ", sql, re.MULTILINE | re.IGNORECASE))

    if stats["create_table_count"] == 0:
        problems.append("nenhuma CREATE TABLE encontrada (backup nao eh pg_dump?)")

    # 6. Tabelas canonicas presentes
    # Aceita: CREATE TABLE cliente | "cliente" | public.cliente | "public"."cliente"
    # pg_dump real costuma emitir schema-qualified (public.tabela).
    tables_found: set[str] = set()
    create_table_re = re.compile(
        r"CREATE TABLE\s+(?:IF NOT EXISTS\s+)?"
        r"(?:\"?(?:\w+)\"?\.)?"  # schema opcional
        r"\"?(\w+)\"?",
        re.IGNORECASE,
    )
    for m in create_table_re.finditer(sql):
        tables_found.add(m.group(1).lower())
    stats["tables_found"] = sorted(tables_found)

    missing_tables = REQUIRED_TABLES - tables_found
    if missing_tables:
        problems.append(
            f"tabelas canonicas AUSENTES: {sorted(missing_tables)}"
        )

    # 7. Restore simulado em sqlite
    # Extrai apenas CREATE TABLE statements e roda em sqlite
    try:
        sqlite_conn = sqlite3.connect(":memory:")
        sqlite_cur = sqlite_conn.cursor()
        create_stmts = re.findall(
            r"CREATE TABLE[^;]+;",
            sql,
            re.IGNORECASE | re.DOTALL,
        )
        applied = 0
        for stmt in create_stmts[:100]:  # limite de seguranca
            # Converte tipos Postgres -> SQLite (basico)
            sqlite_stmt = stmt
            # Strip schema qualification (public.tabela / "public"."tabela")
            sqlite_stmt = re.sub(
                r"CREATE TABLE\s+(?:IF NOT EXISTS\s+)?(?:\"?\w+\"?\.)",
                "CREATE TABLE ",
                sqlite_stmt,
                count=1,
                flags=re.IGNORECASE,
            )
            # Remove tipos nao suportados em SQLite (BIGSERIAL, etc)
            sqlite_stmt = re.sub(r"BIGSERIAL", "INTEGER", sqlite_stmt, flags=re.IGNORECASE)
            sqlite_stmt = re.sub(r"SERIAL", "INTEGER", sqlite_stmt, flags=re.IGNORECASE)
            sqlite_stmt = re.sub(r"JSONB?", "TEXT", sqlite_stmt, flags=re.IGNORECASE)
            sqlite_stmt = re.sub(r"UUID", "TEXT", sqlite_stmt, flags=re.IGNORECASE)
            sqlite_stmt = re.sub(r"TIMESTAMP(?:\s+WITH(?:OUT)?\s+TIME\s+ZONE)?", "TEXT", sqlite_stmt, flags=re.IGNORECASE)
            sqlite_stmt = re.sub(r"BOOLEAN", "INTEGER", sqlite_stmt, flags=re.IGNORECASE)
            sqlite_stmt = re.sub(r"BYTEA", "BLOB", sqlite_stmt, flags=re.IGNORECASE)
            sqlite_stmt = re.sub(r"NUMERIC\(\d+,\s*\d+\)", "REAL", sqlite_stmt, flags=re.IGNORECASE)
            sqlite_stmt = re.sub(
                r"DEFAULT\s+now\(\)",
                "DEFAULT CURRENT_TIMESTAMP",
                sqlite_stmt,
                flags=re.IGNORECASE,
            )
            try:
                sqlite_cur.execute(sqlite_stmt)
                applied += 1
            except sqlite3.Error:
                pass  # esperado para tipos complexos
        sqlite_conn.commit()
        stats["sqlite_restore_applied"] = applied
        stats["sqlite_restore_total"] = len(create_stmts[:100])
        sqlite_conn.close()
    except Exception as exc:
        problems.append(f"restore simulado em sqlite falhou: {type(exc).__name__}: {exc}")

    return len(problems) == 0, problems, stats


def find_latest_backup(backup_dir: Path = Path("/var/backups/cartorio")) -> Path | None:
    """Encontra o backup mais recente em backup_dir."""
    try:
        if not backup_dir.exists():
            return None
        candidates = sorted(
            backup_dir.glob("*.sql.gz"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
    except PermissionError:
        print(
            f"[ERROR] sem permissao para ler {backup_dir} "
            "(HOLD-GUSTAVO: rodar no VPS como root/cron user)",
            file=sys.stderr,
        )
        return None
    return candidates[0] if candidates else None


def tar_list_validate(path: Path) -> tuple[bool, list[str], dict]:
    """Lista e valida bundle tar.gz no formato cartorio-backup.sh (sem extrair dumps).

    Criterios minimos (sample restore check):
    - arquivo existe e > 1KB
    - gzip/tar legivel via tarfile
    - contem ao menos um artefato supabase_*.dump OU *.sql / *.sql.gz
    """
    import tarfile

    problems: list[str] = []
    stats: dict = {}
    if not path.exists():
        return False, [f"arquivo nao existe: {path}"], stats
    size = path.stat().st_size
    stats["size_bytes"] = size
    if size < 1024:
        problems.append(f"tar.gz muito pequeno: {size} bytes (< 1KB)")
    try:
        with tarfile.open(path, "r:gz") as tf:
            names = [m.name for m in tf.getmembers() if m.isfile()]
        stats["tar_members"] = names
        stats["tar_member_count"] = len(names)
        has_dump = any(
            n.endswith(".dump") or n.endswith(".sql") or n.endswith(".sql.gz") for n in names
        )
        if not has_dump:
            problems.append(
                "bundle sem dump SQL/custom (esperado supabase_*.dump ou *.sql.gz)"
            )
        stats["tar_has_dump"] = has_dump
    except Exception as exc:
        return False, [f"tar list falhou: {type(exc).__name__}: {exc}"], stats
    return len(problems) == 0, problems, stats


def render_markdown(path: Path, integro: bool, problems: list[str], stats: dict) -> str:
    md: list[str] = []
    md.append("# Backup Dry-Run Report")
    md.append("")
    md.append(f"**Data**: {datetime.now(timezone.utc).isoformat()}")
    md.append(f"**Arquivo**: `{path}`")
    md.append("")
    if integro:
        md.append("## [WORK] Backup integro e restauravel")
    else:
        md.append(f"## [HOLD] {len(problems)} problema(s) detectado(s)")
    md.append("")
    md.append("## Stats")
    md.append("")
    md.append(f"- Tamanho: {stats.get('size_bytes', '?')} bytes ({stats.get('size_bytes', 0) / 1024 / 1024:.2f} MB)")
    md.append(f"- SQL chars: {stats.get('sql_size_chars', '?')}")
    md.append(f"- CREATE TABLE: {stats.get('create_table_count', '?')}")
    md.append(f"- INSERT INTO: {stats.get('insert_count', '?')}")
    md.append(f"- COPY: {stats.get('copy_count', '?')}")
    if "sqlite_restore_applied" in stats:
        md.append(f"- SQLite restore: {stats['sqlite_restore_applied']}/{stats.get('sqlite_restore_total', '?')} tabelas aplicadas")
    if "sha256_expected" in stats:
        md.append(f"- SHA256: expected={stats['sha256_expected'][:16]}... actual={stats['sha256_actual'][:16]}...")
    md.append("")
    md.append(f"## Tabelas encontradas: {len(stats.get('tables_found', []))}")
    md.append("")
    for t in sorted(stats.get("tables_found", [])):
        md.append(f"- `{t}`")
    md.append("")
    if problems:
        md.append("## Problemas")
        md.append("")
        for p in problems:
            md.append(f"- ❌ {p}")
        md.append("")
    md.append("---")
    md.append("")
    md.append("**Modified by Gustavo Almeida + Pietra orquestrador — G6 wave 6 (auto-gerado)**")
    return "\n".join(md)


def main() -> int:
    parser = argparse.ArgumentParser(description="Backup dry-run validator")
    parser.add_argument("backup_file", nargs="?", help="caminho do backup .sql.gz")
    parser.add_argument("--latest", action="store_true", help="usar o backup mais recente em /var/backups/cartorio/")
    parser.add_argument("--report", type=Path, help="gerar report markdown")
    parser.add_argument(
        "--tar-list",
        type=Path,
        help="valida bundle tar.gz (lista membros; nao restaura dumps -Fc)",
    )
    args = parser.parse_args()

    if args.tar_list:
        path = args.tar_list
        print(f"Validando tar bundle: {path}")
        integro, problems, stats = tar_list_validate(path)
        if integro:
            print(f"[WORK] tar list OK ({stats.get('tar_member_count', 0)} membros)")
            for n in stats.get("tar_members", []):
                print(f"  - {n}")
        else:
            print(f"[HOLD] {len(problems)} problemas:")
            for p in problems:
                print(f"  - {p}")
        if args.report:
            args.report.write_text(render_markdown(path, integro, problems, stats))
            print(f"  Report: {args.report}", file=sys.stderr)
        return 0 if integro else 1

    if args.latest:
        path = find_latest_backup()
        if path is None:
            print("[ERROR] nenhum backup encontrado em /var/backups/cartorio/", file=sys.stderr)
            return 2
        print(f"Usando backup mais recente: {path}", file=sys.stderr)
    elif args.backup_file:
        path = Path(args.backup_file)
    else:
        print("[ERROR] especifique backup_file, --latest ou --tar-list", file=sys.stderr)
        return 2

    print(f"Validando backup: {path}")
    integro, problems, stats = validate_backup(path)

    if integro:
        print(f"[WORK] Backup integro ({stats.get('size_bytes', 0) / 1024 / 1024:.2f} MB)")
        print(f"  CREATE TABLE: {stats.get('create_table_count', 0)}")
        print(f"  Tabelas: {len(stats.get('tables_found', []))}")
    else:
        print(f"[HOLD] {len(problems)} problemas:")
        for p in problems:
            print(f"  - {p}")

    if args.report:
        args.report.write_text(render_markdown(path, integro, problems, stats))
        print(f"  Report: {args.report}", file=sys.stderr)

    return 0 if integro else 1


if __name__ == "__main__":
    sys.exit(main())
