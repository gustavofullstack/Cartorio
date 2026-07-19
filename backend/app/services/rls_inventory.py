"""G8.06.T3 — Inventário e validador de políticas RLS em tabelas com PII de cliente.

Fonte canônica: Alembic `2026_06_25_0004` (S02 RLS) — 4 roles:
  anon (sem policy = deny-by-default com RLS ON),
  authenticated (SELECT own),
  service_role (FOR ALL),
  dpo (SELECT).

Escopo G8.06.T3 (tabelas com info de cliente):
  clientes, conversas, protocolos, atendimentos

API:
  - EXPECTED_RLS_POLICIES: list[dict] (name, table, cmd, roles)
  - PII_CLIENTE_TABLES: tuple das tabelas no escopo
  - expected_policy_keys() / list_expected_policies()
  - normalize_policy_row(row) -> key tuple
  - validate_rls_inventory(policies_from_db) -> report missing/extra
  - render_inventory_report() / render_pg_policies_query()
  - RED_FLAG_POLICY_PREFIXES: extras perigosos (anon_*, auth_all_*)

Live check (ops):
  SELECT policyname, tablename, cmd, roles FROM pg_policies
  WHERE schemaname='public' AND tablename = ANY(...)
  → passar rows (como dicts) para validate_rls_inventory().

Modified by Gustavo Almeida — G8.06.T3.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

# Tabelas com PII de cliente (escopo G8.06.T3)
PII_CLIENTE_TABLES: tuple[str, ...] = (
    "clientes",
    "conversas",
    "protocolos",
    "atendimentos",
)

# Roles canônicas da migration 0004
RLS_ROLES: tuple[str, ...] = ("anon", "authenticated", "service_role", "dpo")

# Prefixos / nomes que NÃO devem existir em prod se 0004 for a verdade
# (drift do dump schema.sql — ver docs/RLS_AUDIT_SAMPLE_G7.md)
RED_FLAG_POLICY_PREFIXES: tuple[str, ...] = (
    "anon_",
    "auth_all_",
    "service_all_",
)

# Coluna de filtro authenticated_read_own (documentação / SQL ref)
AUTH_OWN_JOIN_COL: dict[str, str] = {
    "clientes": "id",
    "conversas": "cliente_id",
    "protocolos": "cliente_id",
    "atendimentos": "cliente_id",
}


def _policy(
    name: str,
    table: str,
    cmd: str,
    roles: Sequence[str],
    *,
    using: str = "true",
    with_check: str | None = None,
    source: str = "alembic:2026_06_25_0004",
) -> dict[str, Any]:
    return {
        "name": name,
        "table": table,
        "cmd": cmd.upper(),
        "roles": tuple(sorted(r.lower() for r in roles)),
        "using": using,
        "with_check": with_check,
        "source": source,
    }


def _build_expected() -> list[dict[str, Any]]:
    """Policies esperadas por tabela PII (canônico 0004)."""
    policies: list[dict[str, Any]] = []
    for table in PII_CLIENTE_TABLES:
        policies.append(
            _policy(
                "service_role_full_access",
                table,
                "ALL",
                ("service_role",),
                using="true",
                with_check="true",
            )
        )
        policies.append(
            _policy(
                "dpo_read_access",
                table,
                "SELECT",
                ("dpo",),
                using="true",
                with_check=None,
            )
        )
        join_col = AUTH_OWN_JOIN_COL[table]
        # Placeholder 0004 (inclui OR IS NULL — gap G1 documentado no G7 audit)
        using_own = f"({join_col}::text = auth.uid()::text OR {join_col} IS NULL)"
        policies.append(
            _policy(
                "authenticated_read_own",
                table,
                "SELECT",
                ("authenticated",),
                using=using_own,
                with_check=None,
            )
        )
    return policies


EXPECTED_RLS_POLICIES: list[dict[str, Any]] = _build_expected()


def list_expected_policies(
    tables: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    """Lista policies esperadas (name, table, cmd, roles, ...)."""
    if tables is None:
        return list(EXPECTED_RLS_POLICIES)
    wanted = {t.lower() for t in tables}
    return [p for p in EXPECTED_RLS_POLICIES if p["table"] in wanted]


def expected_policy_keys(
    tables: Iterable[str] | None = None,
) -> set[tuple[str, str, str, tuple[str, ...]]]:
    """Conjunto de chaves canônicas (name, table, cmd, roles)."""
    return {(p["name"], p["table"], p["cmd"], p["roles"]) for p in list_expected_policies(tables)}


def _normalize_roles(raw: Any) -> tuple[str, ...]:
    """Normaliza roles de pg_policies (array/{role}/string/list)."""
    if raw is None:
        return ()
    if isinstance(raw, (list, tuple, set)):
        parts = [str(r).strip().lower() for r in raw if str(r).strip()]
        return tuple(sorted(parts))
    s = str(raw).strip().lower()
    if not s:
        return ()
    # Postgres array text: {authenticated} or {role1,role2}
    if s.startswith("{") and s.endswith("}"):
        s = s[1:-1]
    parts = [p.strip().strip('"').strip("'") for p in s.replace(";", ",").split(",")]
    parts = [p for p in parts if p]
    return tuple(sorted(parts))


def _normalize_cmd(raw: Any) -> str:
    if raw is None:
        return "ALL"
    s = str(raw).strip().upper()
    # pg_policies.cmd uses SELECT/INSERT/UPDATE/DELETE/ALL
    if s in ("*", "ALL COMMANDS"):
        return "ALL"
    return s


def normalize_policy_row(row: Mapping[str, Any]) -> tuple[str, str, str, tuple[str, ...]]:
    """Normaliza um dict de pg_policies (ou similar) para chave de inventário.

    Aceita aliases comuns:
      policyname|name|policy_name
      tablename|table|table_name
      cmd|command|cmd_type
      roles|role|grantee
    """
    name = row.get("policyname") or row.get("name") or row.get("policy_name") or ""
    table = row.get("tablename") or row.get("table") or row.get("table_name") or ""
    cmd = _normalize_cmd(row.get("cmd") or row.get("command") or row.get("cmd_type"))
    roles = _normalize_roles(
        row.get("roles") if "roles" in row else row.get("role") or row.get("grantee")
    )
    return (
        str(name).strip(),
        str(table).strip().lower(),
        cmd,
        roles,
    )


def is_red_flag_policy(name: str, table: str | None = None) -> bool:
    """True se o nome indica drift perigoso (anon_*/auth_all_*/service_all_*)."""
    n = (name or "").lower()
    if any(n.startswith(p) for p in RED_FLAG_POLICY_PREFIXES):
        return True
    # Nome exato problemático em clientes (dump)
    if n in ("anon_select_own_clientes", "anon_insert_own_clientes"):
        return True
    return False


def validate_rls_inventory(
    policies_from_db: list[dict],
    *,
    tables: Iterable[str] | None = None,
    strict_roles: bool = True,
    flag_red_flags: bool = True,
) -> dict[str, Any]:
    """Compara policies do DB com o inventário canônico.

    Args:
        policies_from_db: lista de dicts no formato pg_policies (ou aliases).
        tables: subset de tabelas (default = PII_CLIENTE_TABLES).
        strict_roles: se True, roles entram na chave de match; se False, só name+table+cmd.
        flag_red_flags: se True, marca extras com prefixos perigosos em red_flags.

    Returns:
        {
          "ok": bool,                 # sem missing e sem red_flags
          "tables": list[str],
          "expected_count": int,
          "observed_count": int,
          "missing": list[dict],      # esperadas e ausentes no DB
          "extra": list[dict],        # no DB e não no inventário (mesmo escopo)
          "matched": list[dict],
          "red_flags": list[dict],    # subset de extra com risco LGPD
          "summary": str,
        }
    """
    scope_tables = tuple(t.lower() for t in (tables if tables is not None else PII_CLIENTE_TABLES))
    scope_set = set(scope_tables)

    expected = list_expected_policies(scope_tables)
    if strict_roles:
        expected_keys = {(p["name"], p["table"], p["cmd"], p["roles"]) for p in expected}
    else:
        expected_keys = {(p["name"], p["table"], p["cmd"]) for p in expected}  # type: ignore[misc]

    observed_keys: set[Any] = set()
    observed_rows: dict[Any, dict[str, Any]] = {}
    out_of_scope: list[dict[str, Any]] = []

    for raw in policies_from_db or []:
        if not isinstance(raw, Mapping):
            continue
        name, table, cmd, roles = normalize_policy_row(raw)
        if not name or not table:
            continue
        if table not in scope_set:
            out_of_scope.append({"name": name, "table": table, "cmd": cmd, "roles": list(roles)})
            continue
        key = (name, table, cmd, roles) if strict_roles else (name, table, cmd)
        observed_keys.add(key)
        observed_rows[key] = {
            "name": name,
            "table": table,
            "cmd": cmd,
            "roles": list(roles),
        }

    missing: list[dict[str, Any]] = []
    for p in expected:
        key = (
            (p["name"], p["table"], p["cmd"], p["roles"])
            if strict_roles
            else (p["name"], p["table"], p["cmd"])
        )
        if key not in observed_keys:
            missing.append(
                {
                    "name": p["name"],
                    "table": p["table"],
                    "cmd": p["cmd"],
                    "roles": list(p["roles"]),
                    "reason": "expected_not_in_db",
                }
            )

    extra: list[dict[str, Any]] = []
    red_flags: list[dict[str, Any]] = []
    for key in sorted(observed_keys, key=lambda k: (k[1], k[0], k[2])):
        if key not in expected_keys:
            row = observed_rows[key]
            item = {**row, "reason": "not_in_canonical_inventory"}
            extra.append(item)
            if flag_red_flags and is_red_flag_policy(row["name"], row["table"]):
                red_flags.append({**item, "reason": "red_flag_policy_prefix"})

    matched: list[dict[str, Any]] = []
    for p in expected:
        key = (
            (p["name"], p["table"], p["cmd"], p["roles"])
            if strict_roles
            else (p["name"], p["table"], p["cmd"])
        )
        if key in observed_keys:
            matched.append(
                {
                    "name": p["name"],
                    "table": p["table"],
                    "cmd": p["cmd"],
                    "roles": list(p["roles"]),
                }
            )

    ok = len(missing) == 0 and len(red_flags) == 0
    summary = (
        f"RLS inventory: ok={ok} matched={len(matched)}/{len(expected)} "
        f"missing={len(missing)} extra={len(extra)} red_flags={len(red_flags)} "
        f"tables={list(scope_tables)}"
    )

    return {
        "ok": ok,
        "tables": list(scope_tables),
        "expected_count": len(expected),
        "observed_count": len(observed_keys),
        "missing": missing,
        "extra": extra,
        "matched": matched,
        "red_flags": red_flags,
        "out_of_scope": out_of_scope,
        "summary": summary,
    }


def render_pg_policies_query(tables: Iterable[str] | None = None) -> str:
    """SQL de inventário live (pg_policies) para as tabelas do escopo."""
    tabs = list(tables) if tables is not None else list(PII_CLIENTE_TABLES)
    in_list = ", ".join(f"'{t}'" for t in tabs)
    return f"""-- G8.06.T3 — inventário live de policies (cliente PII)
SELECT
  schemaname,
  tablename,
  policyname,
  permissive,
  roles,
  cmd,
  qual AS using_expr,
  with_check
FROM pg_policies
WHERE schemaname = 'public'
  AND tablename IN ({in_list})
ORDER BY tablename, policyname;
"""


def render_expected_create_sql() -> str:
    """SQL de referência (comentários IF NOT EXISTS style) — não aplica sozinho.

    Postgres não tem CREATE POLICY IF NOT EXISTS nativo em todas as versões;
    o padrão 0004 é DROP POLICY IF EXISTS + CREATE POLICY.
    """
    lines = [
        "-- G8.06.T3 — RLS expected policies (canônico Alembic 2026_06_25_0004)",
        "-- Tabelas: clientes, conversas, protocolos, atendimentos",
        "-- Apply pattern: DROP POLICY IF EXISTS ...; CREATE POLICY ...",
        "-- Roles: service_role (ALL), dpo (SELECT), authenticated (SELECT own)",
        "-- anon: SEM policy (deny-by-default com RLS ENABLE)",
        "",
    ]
    for table in PII_CLIENTE_TABLES:
        join_col = AUTH_OWN_JOIN_COL[table]
        lines.extend(
            [
                f"-- === {table} ===",
                f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY;",
                "-- FORCE opcional (recomendado em prod para owner):",
                f"-- ALTER TABLE public.{table} FORCE ROW LEVEL SECURITY;",
                f"DROP POLICY IF EXISTS service_role_full_access ON public.{table};",
                f"CREATE POLICY service_role_full_access ON public.{table}",
                "  FOR ALL TO service_role",
                "  USING (true) WITH CHECK (true);",
                f"DROP POLICY IF EXISTS dpo_read_access ON public.{table};",
                f"CREATE POLICY dpo_read_access ON public.{table}",
                "  FOR SELECT TO dpo",
                "  USING (true);",
                f"DROP POLICY IF EXISTS authenticated_read_own ON public.{table};",
                f"CREATE POLICY authenticated_read_own ON public.{table}",
                "  FOR SELECT TO authenticated",
                f"  USING ({join_col}::text = auth.uid()::text OR {join_col} IS NULL);",
                "",
            ]
        )
    lines.append(
        "-- Red flags a REMOVER se existirem (drift schema.sql):\n"
        "-- DROP POLICY IF EXISTS anon_select_own_clientes ON public.clientes;\n"
        "-- DROP POLICY IF EXISTS anon_insert_own_clientes ON public.clientes;\n"
        "-- DROP POLICY IF EXISTS auth_all_atendimentos ON public.atendimentos;\n"
        "-- DROP POLICY IF EXISTS auth_all_conversas ON public.conversas;\n"
    )
    return "\n".join(lines)


def render_inventory_report() -> str:
    """Relatório Markdown do inventário esperado."""
    lines = [
        "# RLS Inventory G8.06.T3 (cliente PII)",
        "",
        f"Tabelas: **{', '.join(PII_CLIENTE_TABLES)}**",
        f"Policies esperadas: **{len(EXPECTED_RLS_POLICIES)}** "
        f"(3 por tabela × {len(PII_CLIENTE_TABLES)})",
        "",
        "Fonte canônica: `backend/alembic/versions/2026_06_25_0004-*.py`",
        "",
        "| Policy | Table | CMD | Roles |",
        "|--------|-------|-----|-------|",
    ]
    for p in EXPECTED_RLS_POLICIES:
        roles = ", ".join(p["roles"])
        lines.append(f"| `{p['name']}` | `{p['table']}` | {p['cmd']} | {roles} |")
    lines.extend(
        [
            "",
            "## Red flags (não devem existir se 0004 canônico)",
            "",
            "- `anon_*` em `clientes`",
            "- `auth_all_*` (FOR ALL USING true) — anula filtro own",
            "- `service_all_*` (naming legacy do dump)",
            "",
            "## Live validation",
            "",
            "```sql",
            render_pg_policies_query().rstrip(),
            "```",
            "",
            "Python:",
            "```python",
            "from app.services.rls_inventory import validate_rls_inventory",
            "report = validate_rls_inventory(rows_from_pg_policies)",
            "assert report['ok'], report['summary']",
            "```",
        ]
    )
    return "\n".join(lines)


__all__ = [
    "AUTH_OWN_JOIN_COL",
    "EXPECTED_RLS_POLICIES",
    "PII_CLIENTE_TABLES",
    "RED_FLAG_POLICY_PREFIXES",
    "RLS_ROLES",
    "expected_policy_keys",
    "is_red_flag_policy",
    "list_expected_policies",
    "normalize_policy_row",
    "render_expected_create_sql",
    "render_inventory_report",
    "render_pg_policies_query",
    "validate_rls_inventory",
]


def _cli() -> None:
    import argparse
    import json
    import sys

    parser = argparse.ArgumentParser(description="G8.06.T3 RLS inventory / validator")
    parser.add_argument("--inventory", action="store_true", help="Markdown inventory")
    parser.add_argument("--sql", action="store_true", help="CREATE POLICY reference SQL")
    parser.add_argument("--query", action="store_true", help="pg_policies SELECT")
    parser.add_argument(
        "--validate-self",
        action="store_true",
        help="Validate expected inventory against itself (must be ok)",
    )
    parser.add_argument(
        "--validate-json",
        type=str,
        default="",
        help="Path to JSON list of pg_policies rows",
    )
    args = parser.parse_args()

    if args.inventory:
        print(render_inventory_report())
    elif args.sql:
        print(render_expected_create_sql())
    elif args.query:
        print(render_pg_policies_query())
    elif args.validate_self:
        # Self-check: expected rows as db rows must match 100%
        fake_db = [
            {
                "policyname": p["name"],
                "tablename": p["table"],
                "cmd": p["cmd"],
                "roles": list(p["roles"]),
            }
            for p in EXPECTED_RLS_POLICIES
        ]
        report = validate_rls_inventory(fake_db)
        print(json.dumps(report, indent=2, ensure_ascii=False))
        sys.exit(0 if report["ok"] else 1)
    elif args.validate_json:
        path = args.validate_json
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, list):
            print("JSON must be a list of policy dicts", file=sys.stderr)
            sys.exit(2)
        report = validate_rls_inventory(data)
        print(json.dumps(report, indent=2, ensure_ascii=False))
        sys.exit(0 if report["ok"] else 1)
    else:
        parser.print_help(sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    _cli()
