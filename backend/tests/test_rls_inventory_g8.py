"""G8.06.T3 — Testes inventário/validador de políticas RLS (cliente PII).

Cobre:
  - EXPECTED_RLS_POLICIES: 12 policies (4 tabelas × 3)
  - name, table, cmd, roles presentes e estáveis
  - validate_rls_inventory: missing / extra / ok / red_flags
  - normalize_policy_row: aliases pg_policies + roles {array}
  - red flags: anon_*, auth_all_*
  - render SQL / report / CLI smoke
  - self-validate inventory is ok

Modified by Gustavo Almeida — G8.06.T3.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RLS_MODULE = ROOT / "app" / "services" / "rls_inventory.py"


@pytest.fixture(scope="module")
def rls():
    spec = importlib.util.spec_from_file_location("rls_inventory", RLS_MODULE)
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _as_db_rows(policies: list[dict]) -> list[dict]:
    return [
        {
            "policyname": p["name"],
            "tablename": p["table"],
            "cmd": p["cmd"],
            "roles": list(p["roles"]),
        }
        for p in policies
    ]


class TestExpectedInventory:
    def test_four_pii_tables(self, rls):
        assert set(rls.PII_CLIENTE_TABLES) == {
            "clientes",
            "conversas",
            "protocolos",
            "atendimentos",
        }

    def test_twelve_expected_policies(self, rls):
        assert len(rls.EXPECTED_RLS_POLICIES) == 12

    def test_three_policies_per_table(self, rls):
        for table in rls.PII_CLIENTE_TABLES:
            rows = rls.list_expected_policies([table])
            assert len(rows) == 3
            names = {p["name"] for p in rows}
            assert names == {
                "service_role_full_access",
                "dpo_read_access",
                "authenticated_read_own",
            }

    def test_policy_shape(self, rls):
        for p in rls.EXPECTED_RLS_POLICIES:
            assert p["name"]
            assert p["table"] in rls.PII_CLIENTE_TABLES
            assert p["cmd"] in {"ALL", "SELECT", "INSERT", "UPDATE", "DELETE"}
            assert isinstance(p["roles"], tuple)
            assert len(p["roles"]) >= 1

    def test_service_role_is_all(self, rls):
        for p in rls.EXPECTED_RLS_POLICIES:
            if p["name"] == "service_role_full_access":
                assert p["cmd"] == "ALL"
                assert p["roles"] == ("service_role",)

    def test_dpo_is_select(self, rls):
        for p in rls.EXPECTED_RLS_POLICIES:
            if p["name"] == "dpo_read_access":
                assert p["cmd"] == "SELECT"
                assert p["roles"] == ("dpo",)

    def test_auth_own_join_cols(self, rls):
        assert rls.AUTH_OWN_JOIN_COL["clientes"] == "id"
        assert rls.AUTH_OWN_JOIN_COL["conversas"] == "cliente_id"
        assert rls.AUTH_OWN_JOIN_COL["protocolos"] == "cliente_id"
        assert rls.AUTH_OWN_JOIN_COL["atendimentos"] == "cliente_id"

    def test_expected_keys_unique(self, rls):
        keys = rls.expected_policy_keys()
        assert len(keys) == 12


class TestNormalizePolicyRow:
    def test_pg_policies_aliases(self, rls):
        key = rls.normalize_policy_row(
            {
                "policyname": "dpo_read_access",
                "tablename": "Clientes",
                "cmd": "select",
                "roles": "{dpo}",
            }
        )
        assert key == ("dpo_read_access", "clientes", "SELECT", ("dpo",))

    def test_list_roles_sorted(self, rls):
        key = rls.normalize_policy_row(
            {
                "name": "x",
                "table": "protocolos",
                "command": "ALL",
                "roles": ["service_role", "dpo"],
            }
        )
        assert key[3] == ("dpo", "service_role")

    def test_name_table_aliases(self, rls):
        key = rls.normalize_policy_row(
            {
                "policy_name": "authenticated_read_own",
                "table_name": "atendimentos",
                "cmd_type": "SELECT",
                "grantee": "authenticated",
            }
        )
        assert key[0] == "authenticated_read_own"
        assert key[1] == "atendimentos"
        assert key[2] == "SELECT"
        assert key[3] == ("authenticated",)


class TestValidateRlsInventory:
    def test_perfect_match_ok(self, rls):
        rows = _as_db_rows(rls.EXPECTED_RLS_POLICIES)
        report = rls.validate_rls_inventory(rows)
        assert report["ok"] is True
        assert report["missing"] == []
        assert report["extra"] == []
        assert report["red_flags"] == []
        assert report["expected_count"] == 12
        assert report["observed_count"] == 12
        assert len(report["matched"]) == 12

    def test_missing_policy_detected(self, rls):
        rows = _as_db_rows(rls.EXPECTED_RLS_POLICIES)
        # drop one
        rows = [r for r in rows if not (
            r["policyname"] == "dpo_read_access" and r["tablename"] == "clientes"
        )]
        report = rls.validate_rls_inventory(rows)
        assert report["ok"] is False
        assert len(report["missing"]) == 1
        assert report["missing"][0]["name"] == "dpo_read_access"
        assert report["missing"][0]["table"] == "clientes"

    def test_extra_policy_detected(self, rls):
        rows = _as_db_rows(rls.EXPECTED_RLS_POLICIES)
        rows.append(
            {
                "policyname": "custom_write",
                "tablename": "clientes",
                "cmd": "UPDATE",
                "roles": ["authenticated"],
            }
        )
        report = rls.validate_rls_inventory(rows)
        assert len(report["extra"]) == 1
        assert report["extra"][0]["name"] == "custom_write"
        # custom is not red-flag prefix → ok still True if no missing
        assert report["ok"] is True
        assert report["red_flags"] == []

    def test_red_flag_anon_breaks_ok(self, rls):
        rows = _as_db_rows(rls.EXPECTED_RLS_POLICIES)
        rows.append(
            {
                "policyname": "anon_select_own_clientes",
                "tablename": "clientes",
                "cmd": "SELECT",
                "roles": ["anon"],
            }
        )
        report = rls.validate_rls_inventory(rows)
        assert report["ok"] is False
        assert len(report["red_flags"]) == 1
        assert report["red_flags"][0]["name"] == "anon_select_own_clientes"

    def test_red_flag_auth_all(self, rls):
        rows = _as_db_rows(rls.EXPECTED_RLS_POLICIES)
        rows.append(
            {
                "policyname": "auth_all_conversas",
                "tablename": "conversas",
                "cmd": "ALL",
                "roles": ["authenticated"],
            }
        )
        report = rls.validate_rls_inventory(rows)
        assert report["ok"] is False
        assert any(r["name"] == "auth_all_conversas" for r in report["red_flags"])

    def test_empty_db_all_missing(self, rls):
        report = rls.validate_rls_inventory([])
        assert report["ok"] is False
        assert len(report["missing"]) == 12
        assert report["observed_count"] == 0

    def test_out_of_scope_ignored_for_extra(self, rls):
        rows = _as_db_rows(rls.EXPECTED_RLS_POLICIES)
        rows.append(
            {
                "policyname": "service_role_full_access",
                "tablename": "documentos",
                "cmd": "ALL",
                "roles": ["service_role"],
            }
        )
        report = rls.validate_rls_inventory(rows)
        assert report["ok"] is True
        assert report["extra"] == []
        assert any(r["table"] == "documentos" for r in report["out_of_scope"])

    def test_subset_tables(self, rls):
        only = [p for p in rls.EXPECTED_RLS_POLICIES if p["table"] == "protocolos"]
        report = rls.validate_rls_inventory(
            _as_db_rows(only),
            tables=["protocolos"],
        )
        assert report["ok"] is True
        assert report["expected_count"] == 3
        assert report["tables"] == ["protocolos"]

    def test_strict_roles_false_matches_without_role(self, rls):
        rows = [
            {
                "policyname": p["name"],
                "tablename": p["table"],
                "cmd": p["cmd"],
                "roles": [],  # empty roles still match name+table+cmd
            }
            for p in rls.EXPECTED_RLS_POLICIES
        ]
        report = rls.validate_rls_inventory(rows, strict_roles=False)
        assert report["ok"] is True
        assert len(report["matched"]) == 12

    def test_summary_string(self, rls):
        report = rls.validate_rls_inventory(_as_db_rows(rls.EXPECTED_RLS_POLICIES))
        assert "matched=12/12" in report["summary"]
        assert "ok=True" in report["summary"]


class TestRedFlagHelper:
    def test_prefixes(self, rls):
        assert rls.is_red_flag_policy("anon_insert_own_clientes") is True
        assert rls.is_red_flag_policy("auth_all_atendimentos") is True
        assert rls.is_red_flag_policy("service_all_mensagens") is True
        assert rls.is_red_flag_policy("service_role_full_access") is False
        assert rls.is_red_flag_policy("dpo_read_access") is False


class TestRenderers:
    def test_inventory_report_markdown(self, rls):
        report = rls.render_inventory_report()
        assert "# RLS Inventory G8.06.T3" in report
        assert "| Policy |" in report
        for table in rls.PII_CLIENTE_TABLES:
            assert f"`{table}`" in report

    def test_pg_policies_query(self, rls):
        sql = rls.render_pg_policies_query()
        assert "FROM pg_policies" in sql
        assert "clientes" in sql
        assert "atendimentos" in sql

    def test_create_sql_has_drop_create(self, rls):
        sql = rls.render_expected_create_sql()
        assert "DROP POLICY IF EXISTS service_role_full_access" in sql
        assert "CREATE POLICY service_role_full_access" in sql
        assert "ENABLE ROW LEVEL SECURITY" in sql
        for table in rls.PII_CLIENTE_TABLES:
            assert f"ON public.{table}" in sql


class TestCLI:
    def test_help(self):
        result = subprocess.run(
            [sys.executable, str(RLS_MODULE), "--help"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert result.returncode in (0, 1, 2)

    def test_validate_self(self):
        result = subprocess.run(
            [sys.executable, str(RLS_MODULE), "--validate-self"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["ok"] is True
        assert data["expected_count"] == 12

    def test_inventory_cli(self):
        result = subprocess.run(
            [sys.executable, str(RLS_MODULE), "--inventory"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert result.returncode == 0
        assert "RLS Inventory" in result.stdout

    def test_sql_cli(self):
        result = subprocess.run(
            [sys.executable, str(RLS_MODULE), "--sql"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert result.returncode == 0
        assert "CREATE POLICY" in result.stdout
