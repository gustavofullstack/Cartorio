"""Testes para app/api/v1/brain.py - _read_json_safe helper (cobertura).

Cobre:
1. _read_json_safe com arquivo valido
2. _read_json_safe com arquivo inexistente
3. _read_json_safe com JSON invalido
4. _read_json_safe com arquivo vazio

Sobe cobertura brain.py - os schemas LessonCreate/LessonSummary/LoopState
tem campos obrigatorios especificos (titulo/contexto/solucao, arquivo/id,
current_squad/gates/etc) cobertos pelos testes brain existentes. Aqui focamos
na funcao utilitaria principal.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from app.api.v1.brain import _read_json_safe


def test_read_json_safe_arquivo_valido() -> None:
    """_read_json_safe le arquivo JSON valido e retorna dict."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"key": "value", "items": [1, 2, 3]}, f)
        f.flush()
        path = Path(f.name)

    try:
        result = _read_json_safe(path)
        assert result is not None
        assert result["key"] == "value"
        assert result["items"] == [1, 2, 3]
    finally:
        path.unlink()


def test_read_json_safe_arquivo_inexistente_retorna_none() -> None:
    """_read_json_safe retorna None para arquivo que nao existe."""
    fake_path = Path("/tmp/arquivo_que_nao_existe_xyz_99999.json")
    assert _read_json_safe(fake_path) is None


def test_read_json_safe_json_invalido_retorna_none() -> None:
    """_read_json_safe retorna None quando JSON esta corrompido."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("{invalid json content")
        f.flush()
        path = Path(f.name)

    try:
        result = _read_json_safe(path)
        assert result is None
    finally:
        path.unlink()


def test_read_json_safe_arquivo_vazio_retorna_none() -> None:
    """_read_json_safe retorna None para arquivo vazio (JSON invalido)."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("")
        f.flush()
        path = Path(f.name)

    try:
        result = _read_json_safe(path)
        assert result is None
    finally:
        path.unlink()


def test_read_json_safe_preserva_unicode() -> None:
    """_read_json_safe preserva caracteres unicode em valores."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump({"msg": "Olá mundo 🌍 测试"}, f, ensure_ascii=False)
        f.flush()
        path = Path(f.name)

    try:
        result = _read_json_safe(path)
        assert result is not None
        assert "Olá" in result["msg"]
        assert "🌍" in result["msg"]
        assert "测试" in result["msg"]
    finally:
        path.unlink()
