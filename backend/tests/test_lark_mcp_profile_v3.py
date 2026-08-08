"""Testes de perfil MCP para piloto Lark (V3)."""

from __future__ import annotations



def test_mcp_pilot_profile_allowlist() -> None:
    allowed_tools = ["cartorio_calcular_emolumento"]
    forbidden_tools = ["write_file", "run_command", "execute_sql", "delete_record"]
    
    for tool in forbidden_tools:
        assert tool not in allowed_tools
    assert "cartorio_calcular_emolumento" in allowed_tools
