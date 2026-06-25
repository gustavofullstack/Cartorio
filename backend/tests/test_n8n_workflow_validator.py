"""Testes do N8N Workflow Validator (B11)."""
from __future__ import annotations

import json
from pathlib import Path


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
            "connections": {
                "node_inexistente": {"main": [[{"node": "node1"}]]}
            },
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
            "connections": {
                "node1": {"main": [[{"node": "node_inexistente"}]]}
            },
        }
        p = _make_wf(tmp_path, "orfa-target.json", wf)
        result = _validate_one(p)
        assert result["valid"] is False
        assert any("node inexistente" in e for e in result["errors"])

    def test_validate_one_http_sem_url(self, tmp_path: Path):
        """HTTP node sem URL eh detectado."""
        wf = {
            "name": "test",
            "nodes": [{
                "name": "call_api",
                "type": "n8n-nodes-base.httpRequest",
                "parameters": {},  # sem url
            }],
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
            "nodes": [{
                "name": "call_api",
                "type": "n8n-nodes-base.httpRequest",
                "parameters": {"url": "https://api.exemplo.com/foo"},
            }],
            "connections": {},
        }
        p = _make_wf(tmp_path, "hardcoded.json", wf)
        result = _validate_one(p)
        assert any("hardcoded" in w for w in result["warnings"])

    def test_validate_one_http_localhost_warning(self, tmp_path: Path):
        """HTTP com localhost da warning (nao erro)."""
        wf = {
            "name": "test",
            "nodes": [{
                "name": "call_api",
                "type": "n8n-nodes-base.httpRequest",
                "parameters": {"url": "http://localhost:8000/api"},
            }],
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
            "nodes": [{
                "name": "n1",
                "type": "n8n-nodes-base.httpRequest",
                "parameters": {"url": "{{$env.MY_UNKNOWN_VAR_42}}/api"},
            }],
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
                    "parameters": {"url": "{{$env.CARTORIO_API_URL}}/x"},
                },
            ],
            "connections": {
                "start": {"main": [[{"node": "call_api"}]]}
            },
        }
        p = _make_wf(tmp_path, "valid.json", wf)
        result = _validate_one(p)
        assert result["valid"] is True
        assert result["errors"] == []
        assert result["warnings"] == []
        assert result["node_count"] == 2

    def test_validate_all_aggregates(self, tmp_path: Path):
        """validate_all agrega stats corretamente."""
        # WF valido
        _make_wf(tmp_path, "ok.json", {
            "name": "ok",
            "nodes": [{"name": "n1", "type": "t"}],
            "connections": {},
        })
        # WF invalido
        _make_wf(tmp_path, "bad.json", {
            "name": "bad",
            "nodes": [{"name": "n1"}],  # sem type
            "connections": {},
        })
        # WF com warning
        _make_wf(tmp_path, "warn.json", {
            "name": "warn",
            "nodes": [{
                "name": "n1",
                "type": "n8n-nodes-base.httpRequest",
                "parameters": {"url": "http://localhost:8000"},
            }],
            "connections": {},
        })

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
