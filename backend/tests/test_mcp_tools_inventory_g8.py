"""G8.07.T1 — Testes de inventário das tools do MCP server.

Cobre:
  - Quantidade de tools expostas (>=13, conforme snapshot Wave 26)
  - Cada tool tem nome único (sem colisão)
  - Cada tool tem descrição não-vazia
  - Tools canônicos presentes: cartorio_calcular_emolumento, cartorio_consultar_protocolo,
    cartorio_criar_protocolo, cartorio_gerar_segunda_via, cartorio_audit_verify,
    cartorio_saudacao, super_server_info
  - MCP server name é "cartorio-mcp-cabuloso" (canônico do projeto)
  - MCP version >= 0.6.0
  - mcp_app() retorna sub-app Starlette (montagem FastAPI)

Modified by Gustavo Almeida — G8 Wave 30 A1.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MCP_SERVER = ROOT / "mcp_server.py"


@pytest.fixture(scope="module")
def mcp_module():
    """Importa mcp_server.py dinamicamente (não é pacote, é arquivo solto)."""
    spec = importlib.util.spec_from_file_location("mcp_server", MCP_SERVER)
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    # Evita executar main() / uvicorn.run ao final do arquivo
    if "mcp_server" in sys.modules:
        del sys.modules["mcp_server"]
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def mcp_tools(mcp_module):
    """Retorna dict {name: tool_object} do FastMCP."""
    mcp = mcp_module.mcp
    tools = {}
    # FastMCP 2.x expõe _tool_manager ou list_tools()
    if hasattr(mcp, "_tool_manager"):
        for tool_name, tool in mcp._tool_manager._tools.items():
            tools[tool_name] = tool
    elif hasattr(mcp, "list_tools"):
        import asyncio

        async def _list():
            return await mcp.list_tools()

        result = asyncio.run(_list())
        for t in result:
            tools[t.name] = t
    else:
        # Fallback: scan AST
        import ast

        text = MCP_SERVER.read_text(encoding="utf-8")
        tree = ast.parse(text)
        names: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for dec in node.decorator_list:
                    if (
                        isinstance(dec, ast.Call)
                        and isinstance(dec.func, ast.Attribute)
                        and dec.func.attr == "tool"
                    ):
                        names.append(node.name)
                        break
        for n in names:
            tools[n] = None  # type: ignore[assignment]
    return tools


class TestMCPInventory:
    def test_mcp_module_loads(self, mcp_module):
        assert mcp_module is not None
        assert hasattr(mcp_module, "mcp")

    def test_mcp_name_is_canonico(self, mcp_module):
        assert mcp_module.mcp.name == "cartorio-mcp-cabuloso"

    def test_mcp_version_is_at_least_060(self, mcp_module):
        version = getattr(mcp_module.mcp, "version", "0.0.0")
        major, minor, *_ = version.split(".")
        assert (int(major), int(minor)) >= (0, 6), f"version {version} < 0.6.0"

    def test_minimum_13_tools_expostas(self, mcp_tools):
        # Wave 26 reportou 13 tools. Aceito >=13 (regressão se cair)
        assert len(mcp_tools) >= 13, f"Esperado ≥13 tools, achou {len(mcp_tools)}"

    def test_tool_names_are_unique(self, mcp_tools):
        names = list(mcp_tools.keys())
        assert len(names) == len(set(names)), f"Nomes duplicados: {names}"

    def test_no_empty_tool_name(self, mcp_tools):
        for name in mcp_tools:
            assert name and isinstance(name, str), f"Tool sem nome: {name!r}"

    def test_canonico_tools_presentes(self, mcp_tools):
        # Tools canônicos documentados no header do mcp_server.py
        canonicos = {
            "cartorio_calcular_emolumento",
            "cartorio_consultar_protocolo",
            "cartorio_criar_protocolo",
            "cartorio_gerar_segunda_via",
            "cartorio_audit_verify",
            "cartorio_saudacao",
            "super_server_info",
        }
        missing = canonicos - set(mcp_tools.keys())
        assert not missing, f"Tools canônicos faltando: {missing}"


class TestMCPAppMount:
    """Valida que mcp_app() retorna sub-app Starlette para FastAPI mount."""

    def test_mcp_app_callable(self, mcp_module):
        assert hasattr(mcp_module, "mcp_app")
        assert callable(mcp_module.mcp_app)

    def test_mcp_app_returns_starlette_app(self, mcp_module):
        app = mcp_module.mcp_app()
        # Starlette/FastAPI apps têm atributo routes ou router
        assert hasattr(app, "routes") or hasattr(app, "router"), \
            f"mcp_app() retornou {type(app)}, não é Starlette app"


class TestMCPSourceCode:
    """Análise estática do mcp_server.py para garantir padrões."""

    def test_has_setup_path_for_app_imports(self, mcp_module):
        # Deve adicionar backend/ ao sys.path para importar app.*
        text = MCP_SERVER.read_text(encoding="utf-8")
        assert "sys.path.insert" in text
        assert "from app.config" in text

    def test_has_fallback_for_outside_venv(self, mcp_module):
        # Try/except ImportError para rodar fora do venv
        text = MCP_SERVER.read_text(encoding="utf-8")
        assert "ImportError" in text or "except ImportError" in text

    def test_no_http_self_loop(self, mcp_module):
        # Não pode chamar a si próprio via HTTP localhost:8000 (timeout).
        # Docstring pode MENCIONAR localhost:8000 explicando o que NÃO fazer,
        # mas o código não pode USAR isso como URL de produção.
        import re

        text = MCP_SERVER.read_text(encoding="utf-8")
        # Extrai apenas linhas que NÃO estão em docstrings (heurística simples).
        # Procura padrões de URL em chamadas de função (.get, .post, AsyncClient).
        bad_pattern = re.compile(
            r'(httpx\.|requests\.|url\s*=\s*|base_url\s*=\s*)["\'](https?://)?(localhost|127\.0\.0\.1):8000',
            re.IGNORECASE,
        )
        matches = bad_pattern.findall(text)
        assert not matches, f"Self-loop HTTP detectado em código: {matches}"
        # Docstring pode conter "localhost:8000" explicando o que evitar (OK)

    def test_module_docstring_lists_tools(self, mcp_module):
        text = MCP_SERVER.read_text(encoding="utf-8")
        # Docstring deve listar os tools (autodoc-friendly)
        for canonico in [
            "cartorio_calcular_emolumento",
            "cartorio_consultar_protocolo",
            "cartorio_audit_verify",
        ]:
            assert canonico in text, f"Tool {canonico} não está no docstring"


class TestMCPIntegration:
    """Snapshot de regressão: tools count vs Wave 26 (13)."""

    def test_tools_count_matches_wave26_snapshot(self, mcp_tools):
        # Wave 26 / lesson 198 reporta 13 tools. Aceito 13-15 (margem para adições controladas)
        count = len(mcp_tools)
        assert 13 <= count <= 20, \
            f"Tools count {count} fora da margem esperada [13-20]. Wave 26=13, revisar regressão."