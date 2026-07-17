"""G8.06.T1 — Testes para otimização de índices DB.

Cobre:
  - INDICES: 12 índices declarados (atendimentos/protocolos/audit_log)
  - render_create_index_sql: formato PG correto, IF NOT EXISTS
  - render_drop_index_sql: idempotente
  - render_create_all_sql: header + body + footer
  - get_indices_by_table: agrupamento correto
  - estimate_size_savings: retorna dict útil
  - CLI: smoke test argparse
  - LGPD: audit_log tem índices para Art.18 + Art.37

Modified by Gustavo Almeida — G8 Wave 32 A1.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
OPTIMIZER = ROOT / "app" / "services" / "db_index_optimizer.py"


@pytest.fixture(scope="module")
def opt_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location("db_index_optimizer", OPTIMIZER)
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestIndices:
    def test_total_indices_count(self, opt_module):
        # 12 indices declarados: 3 atendimentos + 4 protocolos + 5 audit_log
        assert len(opt_module.INDICES) == 12

    def test_atendimento_indices(self, opt_module):
        atendimento_idxs = [i for i in opt_module.INDICES if i["tabela"] == "atendimentos"]
        assert len(atendimento_idxs) == 3
        # Cada índice tem campos obrigatórios
        for idx in atendimento_idxs:
            assert "nome" in idx
            assert "colunas" in idx
            assert "motivo" in idx
            assert "tipo" in idx

    def test_protocolo_indices(self, opt_module):
        protocolo_idxs = [i for i in opt_module.INDICES if i["tabela"] == "protocolos"]
        assert len(protocolo_idxs) == 4
        # numero deve ser UNIQUE
        numero_idx = next(i for i in protocolo_idxs if "numero" in i["nome"])
        assert numero_idx.get("unique") == "UNIQUE"

    def test_audit_log_indices_lgpd(self, opt_module):
        """LGPD Art.18 (acesso) + Art.37 (relatorio) devem ter indices."""
        audit_idxs = [i for i in opt_module.INDICES if i["tabela"] == "audit_log"]
        assert len(audit_idxs) == 5
        # BRIN para created_at (append-only)
        brin_idx = next(i for i in audit_idxs if i["tipo"] == "brin")
        assert "created_at" in brin_idx["colunas"]
        # GIN para payload (busca JSONB)
        gin_idx = next(i for i in audit_idxs if i["tipo"] == "gin")
        assert "payload" in gin_idx["colunas"]

    def test_all_indices_have_unique_names(self, opt_module):
        names = [i["nome"] for i in opt_module.INDICES]
        assert len(names) == len(set(names)), f"Duplicate index names: {names}"

    def test_no_overlapping_columns_same_table(self, opt_module):
        """Não deve haver 2 índices BTREE idênticos na mesma tabela."""
        from collections import defaultdict

        by_table: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for idx in opt_module.INDICES:
            if idx["tipo"] == "btree":
                by_table[idx["tabela"]].append((idx["nome"], idx["colunas"]))
        for table, idxs in by_table.items():
            cols = [c for _, c in idxs]
            assert len(cols) == len(set(cols)), f"Duplicate columns in {table}: {cols}"


class TestSQLGeneration:
    def test_create_index_sql_format(self, opt_module):
        idx = opt_module.INDICES[0]
        sql = opt_module.render_create_index_sql(idx)
        assert sql.startswith("CREATE")
        assert "INDEX IF NOT EXISTS" in sql
        assert idx["nome"] in sql
        assert idx["tabela"] in sql
        assert idx["tipo"].upper() in sql.upper()

    def test_create_unique_index(self, opt_module):
        unique_idx = next(i for i in opt_module.INDICES if i.get("unique") == "UNIQUE")
        sql = opt_module.render_create_index_sql(unique_idx)
        assert sql.startswith("CREATE UNIQUE INDEX")

    def test_create_brin_index(self, opt_module):
        brin = next(i for i in opt_module.INDICES if i["tipo"] == "brin")
        sql = opt_module.render_create_index_sql(brin)
        assert "USING BRIN" in sql.upper()

    def test_create_gin_index(self, opt_module):
        gin = next(i for i in opt_module.INDICES if i["tipo"] == "gin")
        sql = opt_module.render_create_index_sql(gin)
        assert "USING GIN" in sql.upper()

    def test_drop_index_sql_idempotent(self, opt_module):
        for idx in opt_module.INDICES:
            sql = opt_module.render_drop_index_sql(idx)
            assert sql.startswith("DROP INDEX IF EXISTS")
            assert idx["nome"] in sql

    def test_create_all_sql_has_header(self, opt_module):
        sql = opt_module.render_create_all_sql()
        assert "G8.06.T1" in sql
        assert "LGPD" in sql
        assert "Total:" in sql

    def test_create_all_sql_is_valid_sql(self, opt_module):
        """Sanity check: 12 statements CREATE INDEX, todos terminam com ;"""
        sql = opt_module.render_create_all_sql()
        # Conta CREATE INDEX ou CREATE UNIQUE INDEX
        create_count = len(re.findall(r"^CREATE\s+(?:UNIQUE\s+)?INDEX\b", sql, re.MULTILINE))
        assert create_count == 12, f"Esperado 12 CREATE INDEX, achou {create_count}"
        # Cada linha 'ON tabela USING tipo (...)' deve terminar com ;
        on_lines = [line for line in sql.split("\n") if line.strip().startswith("ON ") and "USING" in line]
        assert len(on_lines) == 12, f"Esperado 12 ON ... USING, achou {len(on_lines)}"
        for line in on_lines:
            assert line.rstrip().endswith(";"), f"Statement sem ;: {line}"

    def test_create_all_sql_has_no_double_space_create(self, opt_module):
        """Semântica: não pode haver 'CREATE  INDEX' (2 espaços = bug)."""
        sql = opt_module.render_create_all_sql()
        assert "CREATE  INDEX" not in sql, "Bug: unique vazio gera espaço duplo"


class TestGroupedByTable:
    def test_groups_correctly(self, opt_module):
        grouped = opt_module.get_indices_by_table()
        assert "atendimentos" in grouped
        assert "protocolos" in grouped
        assert "audit_log" in grouped
        assert len(grouped) == 3

    def test_no_empty_groups(self, opt_module):
        grouped = opt_module.get_indices_by_table()
        for table, idxs in grouped.items():
            assert len(idxs) > 0, f"Grupo vazio: {table}"


class TestSizeEstimate:
    def test_returns_useful_dict(self, opt_module):
        est = opt_module.estimate_size_savings()
        assert "btree_vs_brin" in est
        assert "recomendacao" in est
        assert "migration_strategy" in est

    def test_estimates_mention_concurrently(self, opt_module):
        est = opt_module.estimate_size_savings()
        # CONCURRENTLY é a forma correta de criar índice em prod sem lock
        assert "CONCURRENTLY" in est["migration_strategy"]


class TestLGPDCoverage:
    """Garante que índices cobrem requisitos LGPD Art.18 + Art.37."""

    def test_audit_log_has_index_for_actor(self, opt_module):
        """LGPD Art.18 V (acesso): titular quer ver quem acessou seus dados."""
        actor_idx = next(
            (i for i in opt_module.INDICES if "actor_id" in i["colunas"]),
            None,
        )
        assert actor_idx is not None, "Falta índice em actor_id"

    def test_audit_log_has_index_for_resource_action(self, opt_module):
        """LGPD Art.37 (registro de operações): auditoria por recurso."""
        res_idx = next(
            (i for i in opt_module.INDICES if "resource" in i["colunas"] and "action" in i["colunas"]),
            None,
        )
        assert res_idx is not None, "Falta índice composto resource+action"

    def test_protocolo_has_index_for_cliente_status(self, opt_module):
        """LGPD Art.18 II (acesso): cliente consulta seus protocolos."""
        cliente_idx = next(
            (i for i in opt_module.INDICES if i["tabela"] == "protocolos" and "cliente_id" in i["colunas"]),
            None,
        )
        assert cliente_idx is not None, "Falta índice em protocolo.cliente_id"

    def test_audit_log_has_partial_indices_for_optional(self, opt_module):
        """LGPD: indices devem usar WHERE quando aplicável (partial index)."""
        # escrevente_id IS NOT NULL (partial index para reduzir tamanho)
        partial_idxs = [i for i in opt_module.INDICES if "WHERE" in i["colunas"]]
        assert len(partial_idxs) >= 1, "Esperava pelo menos 1 partial index"


class TestCLI:
    def test_module_runs_help(self):
        """Smoke test: módulo executa sem erro."""
        result = subprocess.run(
            [sys.executable, str(OPTIMIZER), "--help"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        # --help retorna exit 0 ou 1 (argparse default), mas sem crash
        assert result.returncode in (0, 1, 2)
        assert "usage" in result.stdout.lower() or "usage" in result.stderr.lower()

    def test_module_create_outputs_sql(self):
        result = subprocess.run(
            [sys.executable, str(OPTIMIZER), "--create"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert result.returncode == 0
        assert "CREATE INDEX IF NOT EXISTS" in result.stdout

    def test_module_drop_outputs_sql(self):
        result = subprocess.run(
            [sys.executable, str(OPTIMIZER), "--drop"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert result.returncode == 0
        assert "DROP INDEX IF EXISTS" in result.stdout

    def test_module_summary_outputs_table_breakdown(self):
        result = subprocess.run(
            [sys.executable, str(OPTIMIZER), "--summary"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert result.returncode == 0
        assert "atendimentos" in result.stdout
        assert "protocolos" in result.stdout
        assert "audit_log" in result.stdout

    def test_module_estimate_outputs_json(self):
        result = subprocess.run(
            [sys.executable, str(OPTIMIZER), "--estimate"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert result.returncode == 0
        # Deve ser JSON válido
        data = json.loads(result.stdout)
        assert "btree_vs_brin" in data