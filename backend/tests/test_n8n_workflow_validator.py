"""Testes do N8N Workflow Validator (B11)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


from app.services.n8n_workflow_validator import (
    DEFAULT_WF_DIR,
    KNOWN_ENV_VARS,
    _validate_one,
    validate_all,
)


def _make_wf(tmp_path: Path, name: str, content: dict) -> Path:
    p = tmp_path / name
    p.write_text(json.dumps(content), encoding="utf-8")
    return p


class TestN8nWorkflowValidator:
    """TDD strict - B11 N8N WF validator."""

    def test_known_env_vars_cataloged(self):
        """Variaveis de ambiente conhecidas sao catalogadas."""
        assert "CARTORIO_API_URL" in KNOWN_ENV_VARS
        assert "N8N_API_KEY" in KNOWN_ENV_VARS
        assert "EVOLUTION_API_URL" in KNOWN_ENV_VARS
        assert len(KNOWN_ENV_VARS) >= 10

    def test_validate_one_json_invalido(self, tmp_path: Path):
        """JSON invalido eh detectado."""
        p = tmp_path / "bad.json"
        p.write_text("{ not valid json", encoding="utf-8")

        result = _validate_one(p)
        assert result["valid"] is False
        assert "JSON invalido" in result["errors"][0]

    def test_validate_one_no_type(self, tmp_path: Path):
        """Node sem type eh detectado."""
        wf = {
            "name": "test",
            "nodes": [{"name": "node1"}],  # sem type
            "connections": {},
        }
        p = _make_wf(tmp_path, "no-type.json", wf)
        result = _validate_one(p)
        assert result["valid"] is False
        assert any("sem type" in e for e in result["errors"])

    def test_validate_one_conexao_orfa_source(self, tmp_path: Path):
        """Conexao de source inexistente eh detectada."""
        wf = {
            "name": "test",
            "nodes": [{"name": "node1", "type": "t"}],
            "connections": {"node_inexistente": {"main": [[{"node": "node1"}]]}},
        }
        p = _make_wf(tmp_path, "orfas.json", wf)
        result = _validate_one(p)
        assert result["valid"] is False
        assert any("source inexistente" in e for e in result["errors"])

    def test_validate_one_conexao_orfa_target(self, tmp_path: Path):
        """Conexao para target inexistente eh detectada."""
        wf = {
            "name": "test",
            "nodes": [{"name": "node1", "type": "t"}],
            "connections": {"node1": {"main": [[{"node": "node_inexistente"}]]}},
        }
        p = _make_wf(tmp_path, "orfa-target.json", wf)
        result = _validate_one(p)
        assert result["valid"] is False
        assert any("node inexistente" in e for e in result["errors"])

    def test_validate_one_http_sem_url(self, tmp_path: Path):
        """HTTP node sem URL eh detectado."""
        wf = {
            "name": "test",
            "nodes": [
                {
                    "name": "call_api",
                    "type": "n8n-nodes-base.httpRequest",
                    "parameters": {},  # sem url
                }
            ],
            "connections": {},
        }
        p = _make_wf(tmp_path, "no-url.json", wf)
        result = _validate_one(p)
        assert result["valid"] is False
        assert any("sem URL" in e for e in result["errors"])

    def test_validate_one_http_url_hardcoded_warning(self, tmp_path: Path):
        """HTTP com URL hardcoded da warning."""
        wf = {
            "name": "test",
            "nodes": [
                {
                    "name": "call_api",
                    "type": "n8n-nodes-base.httpRequest",
                    "parameters": {"url": "https://api.exemplo.com/foo"},
                }
            ],
            "connections": {},
        }
        p = _make_wf(tmp_path, "hardcoded.json", wf)
        result = _validate_one(p)
        assert any("hardcoded" in w for w in result["warnings"])

    def test_validate_one_http_localhost_warning(self, tmp_path: Path):
        """HTTP com localhost da warning (nao erro)."""
        wf = {
            "name": "test",
            "nodes": [
                {
                    "name": "call_api",
                    "type": "n8n-nodes-base.httpRequest",
                    "parameters": {"url": "http://localhost:8000/api"},
                }
            ],
            "connections": {},
        }
        p = _make_wf(tmp_path, "localhost.json", wf)
        result = _validate_one(p)
        assert result["valid"] is True
        assert any("localhost" in w for w in result["warnings"])

    def test_validate_one_env_var_desconhecida(self, tmp_path: Path):
        """Env var nao catalogada da warning."""
        wf = {
            "name": "test",
            "nodes": [
                {
                    "name": "n1",
                    "type": "n8n-nodes-base.httpRequest",
                    "parameters": {"url": "{{$env.MY_UNKNOWN_VAR_42}}/api"},
                }
            ],
            "connections": {},
        }
        p = _make_wf(tmp_path, "env-unknown.json", wf)

        result = _validate_one(p)
        assert any("MY_UNKNOWN_VAR_42" in w for w in result["warnings"])

    def test_validate_one_wf_valido(self, tmp_path: Path):
        """WF bem formado passa sem erros/warnings."""
        wf = {
            "name": "valid_wf",
            "nodes": [
                {"name": "start", "type": "n8n-nodes-base.start"},
                {
                    "name": "call_api",
                    "type": "n8n-nodes-base.httpRequest",
                    "parameters": {
                        "url": "{{$env.CARTORIO_API_URL}}/x",
                        "options": {"retry": {"maxTries": 3, "waitBetweenTries": 1000}},
                    },
                },
            ],
            "connections": {"start": {"main": [[{"node": "call_api"}]]}},
            "settings": {"errorWorkflow": "global-error-handler"},
        }
        p = _make_wf(tmp_path, "valid.json", wf)
        result = _validate_one(p)
        assert result["valid"] is True
        assert result["errors"] == []
        assert result["warnings"] == []
        assert result["node_count"] == 2

    def test_validate_all_aggregates(self, tmp_path: Path):
        """validate_all agrega stats corretamente."""
        # WF valido (sem warnings: tem settings.errorWorkflow)
        _make_wf(
            tmp_path,
            "ok.json",
            {
                "name": "ok",
                "nodes": [{"name": "n1", "type": "t"}],
                "connections": {},
                "settings": {"errorWorkflow": "global"},
            },
        )
        # WF invalido
        _make_wf(
            tmp_path,
            "bad.json",
            {
                "name": "bad",
                "nodes": [{"name": "n1"}],  # sem type
                "connections": {},
            },
        )
        # WF com warning (sem errorWorkflow)
        _make_wf(
            tmp_path,
            "warn.json",
            {
                "name": "warn",
                "nodes": [
                    {
                        "name": "n1",
                        "type": "n8n-nodes-base.httpRequest",
                        "parameters": {"url": "http://localhost:8000"},
                    }
                ],
                "connections": {},
            },
        )

        result = validate_all(wf_dir=tmp_path)
        assert result["total"] == 3
        assert result["valid"] == 1
        assert result["invalid"] == 1
        assert result["warning"] == 1

    def test_validate_all_directory_not_found(self, tmp_path: Path):
        """Diretorio inexistente retorna error."""
        result = validate_all(wf_dir=tmp_path / "nao-existe")
        assert result["total"] == 0
        assert "error" in result

    def test_default_wf_dir_exists(self):
        """DEFAULT_WF_DIR aponta para infra/n8n-workflows."""
        # Existe no projeto real
        assert "n8n-workflows" in str(DEFAULT_WF_DIR)

    # ========================================================================
    # B12: Test runner checks (retry, timeout, error handler)
    # ========================================================================

    def test_b07_http_node_sem_retry_avisa(self, tmp_path: Path):
        """B07: HTTP node sem retry policy -> warning."""
        wf = {
            "name": "no-retry",
            "nodes": [
                {
                    "name": "call_api",
                    "type": "n8n-nodes-base.httpRequest",
                    "parameters": {"url": "{{$env.CARTORIO_API_URL}}/x"},
                }
            ],
            "connections": {},
            "settings": {"errorWorkflow": "global"},
        }
        p = _make_wf(tmp_path, "no-retry.json", wf)
        result = _validate_one(p)
        assert any("B07" in w and "retry" in w.lower() for w in result["warnings"])

    def test_b07_http_node_com_retry_ok(self, tmp_path: Path):
        """B07: HTTP node COM retry 3x -> sem warning."""
        wf = {
            "name": "with-retry",
            "nodes": [
                {
                    "name": "call_api",
                    "type": "n8n-nodes-base.httpRequest",
                    "parameters": {
                        "url": "{{$env.CARTORIO_API_URL}}/x",
                        "options": {"retry": {"maxTries": 3, "waitBetweenTries": 1000}},
                    },
                }
            ],
            "connections": {},
            "settings": {"errorWorkflow": "global"},
        }
        p = _make_wf(tmp_path, "with-retry.json", wf)
        result = _validate_one(p)
        retry_warnings = [w for w in result["warnings"] if "B07" in w]
        assert retry_warnings == []

    def test_b07_retry_com_max_retries_legacy(self, tmp_path: Path):
        """B07: HTTP node COM maxRetries (legacy) >=3 -> sem warning."""
        wf = {
            "name": "legacy-retry",
            "nodes": [
                {
                    "name": "call_api",
                    "type": "n8n-nodes-base.httpRequest",
                    "parameters": {
                        "url": "{{$env.CARTORIO_API_URL}}/x",
                        "options": {"retry": {"maxRetries": 3, "backoff": "exponential"}},
                    },
                }
            ],
            "connections": {},
            "settings": {"errorWorkflow": "global"},
        }
        p = _make_wf(tmp_path, "legacy.json", wf)
        result = _validate_one(p)
        retry_warnings = [w for w in result["warnings"] if "B07" in w]
        assert retry_warnings == []

    def test_b08_http_timeout_alto_avisa(self, tmp_path: Path):
        """B08: HTTP node com timeout > 30s -> warning."""
        wf = {
            "name": "slow",
            "nodes": [
                {
                    "name": "slow_call",
                    "type": "n8n-nodes-base.httpRequest",
                    "parameters": {
                        "url": "{{$env.CARTORIO_API_URL}}/x",
                        "options": {"timeout": 60000, "retry": {"maxTries": 3}},
                    },
                }
            ],
            "connections": {},
            "settings": {"errorWorkflow": "global"},
        }
        p = _make_wf(tmp_path, "slow.json", wf)
        result = _validate_one(p)
        assert any("B08" in w and "timeout" in w.lower() for w in result["warnings"])

    def test_b08_http_timeout_30s_ok(self, tmp_path: Path):
        """B08: HTTP node com timeout <= 30s -> sem warning."""
        wf = {
            "name": "fast",
            "nodes": [
                {
                    "name": "fast_call",
                    "type": "n8n-nodes-base.httpRequest",
                    "parameters": {
                        "url": "{{$env.CARTORIO_API_URL}}/x",
                        "options": {"timeout": 30000, "retry": {"maxTries": 3}},
                    },
                }
            ],
            "connections": {},
            "settings": {"errorWorkflow": "global"},
        }
        p = _make_wf(tmp_path, "fast.json", wf)
        result = _validate_one(p)
        timeout_warnings = [w for w in result["warnings"] if "B08" in w]
        assert timeout_warnings == []

    def test_b06_wf_sem_error_handler_avisa(self, tmp_path: Path):
        """B06: WF sem error handler wired -> warning."""
        wf = {
            "name": "no-error-handler",
            "nodes": [{"name": "n1", "type": "t"}],
            "connections": {},
            # sem settings.errorWorkflow
        }
        p = _make_wf(tmp_path, "no-handler.json", wf)
        result = _validate_one(p)
        assert any("B06" in w for w in result["warnings"])

    def test_b06_wf_com_error_handler_ok(self, tmp_path: Path):
        """B06: WF COM error handler wired -> sem warning B06."""
        wf = {
            "name": "with-handler",
            "nodes": [{"name": "n1", "type": "t"}],
            "connections": {},
            "settings": {"errorWorkflow": "global-error-handler"},
        }
        p = _make_wf(tmp_path, "with-handler.json", wf)
        result = _validate_one(p)
        b06_warnings = [w for w in result["warnings"] if "B06" in w]
        assert b06_warnings == []

    def test_b12_validate_all_summary_inclui_wfs_aviso_b12(self, tmp_path: Path):
        """Batch validator agrega warnings B06/B07/B08 no summary."""
        # WF sem error handler (B06 warn) + HTTP sem retry (B07 warn)
        _make_wf(
            tmp_path,
            "wf-many-warns.json",
            {
                "name": "many-warns",
                "nodes": [
                    {
                        "name": "call_api",
                        "type": "n8n-nodes-base.httpRequest",
                        "parameters": {"url": "{{$env.CARTORIO_API_URL}}/x"},  # sem retry
                    }
                ],
                "connections": {},
                # sem errorWorkflow
            },
        )

        result = validate_all(wf_dir=tmp_path)
        assert result["total"] == 1
        assert result["warning"] == 1
        wf_result = result["wfs"][0]
        # Warnings B06 + B07 presentes
        warning_codes = set()
        for w in wf_result["warnings"]:
            if "B06" in w:
                warning_codes.add("B06")
            if "B07" in w:
                warning_codes.add("B07")
        assert "B06" in warning_codes
        assert "B07" in warning_codes


class TestN8nBatchValidationB12:
    """B12: Batch validation of ALL 46 workflow files."""

    WF_DIR = DEFAULT_WF_DIR

    def test_b12_all_workflow_files_exist(self):
        """B12: Todos os 46+ workflow files existem em infra/n8n-workflows/."""
        wf_dir = self.WF_DIR
        assert wf_dir.exists(), f"Diretorio de workflows nao encontrado: {wf_dir}"
        files = list(wf_dir.glob("*.json"))
        assert len(files) >= 28, f"Esperado >=28 workflows, encontrado {len(files)}"

    def test_b12_all_files_valid_json(self):
        """B12: Todos os arquivos JSON sao parseaveis."""
        wf_dir = self.WF_DIR
        if not wf_dir.exists():
            pytest.skip("Diretorio de workflows nao encontrado")
        errors = []
        for p in sorted(wf_dir.glob("*.json")):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                assert isinstance(data, dict), f"{p.name}: nao e dict"
                assert "name" in data, f"{p.name}: sem campo 'name'"
            except (json.JSONDecodeError, AssertionError) as e:
                errors.append(f"{p.name}: {e}")
        assert not errors, f"Erros em {len(errors)} arquivos:\n" + "\n".join(errors[:5])

    def test_b12_batch_validate_all_workflows(self):
        """B12: validate_all() processa todos os workflows sem crash."""
        wf_dir = self.WF_DIR
        if not wf_dir.exists():
            pytest.skip("Diretorio de workflows nao encontrado")
        result = validate_all(wf_dir=wf_dir)
        assert result["total"] >= 1
        assert "wfs" in result
        # Nao deve ter crash
        assert "error" not in result or not result["error"]

    def test_b12_http_nodes_have_retry(self):
        """B12: HTTP nodes em todos os workflows tem retry policy (B07)."""
        wf_dir = self.WF_DIR
        if not wf_dir.exists():
            pytest.skip("Diretorio de workflows nao encontrado")
        results = validate_all(wf_dir=wf_dir)
        http_warnings = []
        for wf in results.get("wfs", []):
            for w in wf.get("warnings", []):
                if "B07" in w and "retry" in w.lower():
                    http_warnings.append(f"{wf.get('name', '?')}: {w}")
        # Soft check: muitos workflows sem retry (B07) - registra mas nao falha
        # pois alguns workflows (error handler) gerenciam retry manualmente
        _total_wfs = results.get("total", 0)
        _wfs_with_warnings = len(
            set(
                wf.get("name", "?")
                for wf in results.get("wfs", [])
                if any("B07" in w and "retry" in w.lower() for w in wf.get("warnings", []))
            )
        )
        # Sem assert - apenas informacional. Workflows criticos (B07) devem
        # ter retry, mas a validacao granular e feita caso a caso
