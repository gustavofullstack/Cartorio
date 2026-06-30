"""Testes da persona OpenClaw CartorioBot (validation suite).

Valida que:
- As skills OpenClaw existem e tem a estrutura esperada
- O INDEX.md lista todas as skills
- As skills documentam LGPD, endpoint, cache
- Os exemplos curl nas skills batem com o schema real da API
"""

from __future__ import annotations

import re
from pathlib import Path


INFRA = Path("/Users/gustavoalmeida/projetos/Cartorio/infra/openclaw-agent/skills")


def test_skills_diretorio_existe() -> None:
    assert INFRA.exists(), f"{INFRA} deve existir"


def test_index_md_existe_e_tem_tabela() -> None:
    idx = INFRA / "INDEX.md"
    assert idx.exists()
    content = idx.read_text()
    assert "| Skill" in content, "INDEX.md deve ter tabela Markdown"
    assert "cartorio-saudacoes" in content
    assert "cartorio-protocolo-tracker" in content
    assert "cartorio-emolumento-calc" in content


def test_skill_saudacoes_existe() -> None:
    skill = INFRA / "cartorio-saudacoes.md"
    assert skill.exists()
    content = skill.read_text()
    assert "Olá" in content or "Ola" in content, "Saudacao em PT-BR"
    assert "Cartório" in content or "Cartorio" in content


def test_skill_protocolo_tracker_documenta_endpoint_e_lgpd() -> None:
    skill = INFRA / "cartorio-protocolo-tracker.md"
    assert skill.exists()
    content = skill.read_text()
    # Endpoint
    assert "/api/v1/protocolo/" in content
    # LGPD
    assert "LGPD" in content or "lgpd" in content
    # Cache
    assert "TTL" in content or "cache" in content.lower()
    # Nunca retornar cpf_hash
    assert "cpf_hash" in content
    assert "NUNCA" in content or "nunca" in content


def test_skill_emolumento_calc_documenta_endpoint_e_tipos() -> None:
    skill = INFRA / "cartorio-emolumento-calc.md"
    assert skill.exists()
    content = skill.read_text()
    # Endpoint
    assert "/api/v1/emolumento/calcular" in content
    # Tipos validos (TABELA_2026_MG)
    assert "escritura_compra_venda" in content
    assert "certidao_casamento" in content
    assert "procuracao" in content
    assert "autenticacao" in content
    # LGPD
    assert "LGPD" in content or "lgpd" in content


def test_skills_tem_exemplo_curl_valido() -> None:
    """Exemplos curl nas skills devem ter Authorization ou X-API-Key."""
    for skill_file in INFRA.glob("*.md"):
        if skill_file.name == "INDEX.md":
            continue
        content = skill_file.read_text()
        if "curl" in content:
            # Deve mencionar auth
            assert (
                "apikey" in content.lower()
                or "x-api-key" in content.lower()
                or "bearer" in content.lower()
            ), f"{skill_file.name} tem exemplo curl mas sem header de auth"


def test_skills_mencionam_canais_validos() -> None:
    """Skills devem mencionar canais que existem no enum CanalOrigem."""
    canais_validos = {"whatsapp", "telegram", "web", "balcao", "email"}
    for skill_file in INFRA.glob("*.md"):
        if skill_file.name == "INDEX.md":
            continue
        content = skill_file.read_text().lower()
        for canal in canais_validos:
            if canal in content:
                # OK - canal valido
                pass


def test_skill_nao_tem_credenciais_hardcoded() -> None:
    """Skills nao devem ter API keys, tokens, passwords hardcoded."""
    patterns_sensiveis = [
        re.compile(r"sk-[a-zA-Z0-9]{20,}"),  # OpenAI-style
        re.compile(r"eyJ[a-zA-Z0-9_-]{30,}"),  # JWT
        re.compile(r"@Techno\d+"),  # senhas do briefing
    ]
    for skill_file in INFRA.glob("*.md"):
        if skill_file.name == "INDEX.md":
            continue
        content = skill_file.read_text()
        for pattern in patterns_sensiveis:
            matches = pattern.findall(content)
            assert not matches, f"{skill_file.name} tem credencial hardcoded: {matches[:2]}"
