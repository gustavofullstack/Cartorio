"""G8.06.T4 — testes parse_notify_payload + estrutura SQL cartorio_meta.

Sem live DB. Cobertura:

- expected_channel / constantes
- parse_notify_payload (dict, str, bytes, erros)
- validate_sql_file_exists
- sql_structure_ok (markers pg_notify / triggers / tabelas)

Modified by Gustavo Almeida — G8.06.T4.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.n8n_meta_triggers import (
    CRITICAL_TABLES,
    EXPECTED_CHANNEL,
    REQUIRED_PAYLOAD_KEYS,
    SQL_REL_PATH,
    MetaNotifyPayload,
    expected_channel,
    parse_notify_payload,
    read_sql,
    repo_root,
    sql_file_path,
    sql_structure_ok,
    validate_sql_file_exists,
)


def _sample_payload(**overrides: object) -> dict:
    base: dict = {
        "channel": "cartorio_meta",
        "table": "protocolos",
        "op": "UPDATE",
        "id": 42,
        "status": "em_andamento",
        "old_status": "aberto",
        "protocolo_id": None,
        "numero": "2026-00042",
        "ts": "2026-07-17T12:00:00.000Z",
    }
    base.update(overrides)
    return base


class TestExpectedChannel:
    def test_constant(self) -> None:
        assert EXPECTED_CHANNEL == "cartorio_meta"

    def test_function(self) -> None:
        assert expected_channel() == "cartorio_meta"
        assert expected_channel() == EXPECTED_CHANNEL

    def test_critical_tables(self) -> None:
        assert CRITICAL_TABLES == frozenset({"protocolos", "atendimentos"})


class TestParseNotifyPayload:
    def test_parse_dict(self) -> None:
        p = parse_notify_payload(_sample_payload())
        assert isinstance(p, MetaNotifyPayload)
        assert p.channel == "cartorio_meta"
        assert p.table == "protocolos"
        assert p.op == "UPDATE"
        assert p.id == 42
        assert p.status == "em_andamento"
        assert p.old_status == "aberto"
        assert p.numero == "2026-00042"
        assert p.to_dict()["id"] == 42

    def test_parse_json_string(self) -> None:
        raw = json.dumps(_sample_payload(table="atendimentos", op="INSERT", old_status=None))
        p = parse_notify_payload(raw)
        assert p.table == "atendimentos"
        assert p.op == "INSERT"
        assert p.old_status is None

    def test_parse_bytes(self) -> None:
        raw = json.dumps(_sample_payload(id=7)).encode("utf-8")
        p = parse_notify_payload(raw)
        assert p.id == 7

    def test_op_normalized_upper(self) -> None:
        p = parse_notify_payload(_sample_payload(op="update"))
        assert p.op == "UPDATE"

    def test_atendimento_with_protocolo_id(self) -> None:
        p = parse_notify_payload(
            _sample_payload(
                table="atendimentos",
                protocolo_id=99,
                numero=None,
            )
        )
        assert p.protocolo_id == 99
        assert p.numero is None

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            parse_notify_payload(None)
        with pytest.raises(ValueError, match="empty"):
            parse_notify_payload("")
        with pytest.raises(ValueError, match="empty"):
            parse_notify_payload(b"")

    def test_invalid_json(self) -> None:
        with pytest.raises(ValueError, match="invalid notify JSON"):
            parse_notify_payload("{not-json")

    def test_wrong_type(self) -> None:
        with pytest.raises(TypeError):
            parse_notify_payload(12345)  # type: ignore[arg-type]

    def test_missing_keys(self) -> None:
        with pytest.raises(ValueError, match="missing keys"):
            parse_notify_payload({"channel": "cartorio_meta"})

    def test_bad_channel_strict(self) -> None:
        with pytest.raises(ValueError, match="unexpected channel"):
            parse_notify_payload(_sample_payload(channel="other"))

    def test_bad_channel_relaxed(self) -> None:
        p = parse_notify_payload(_sample_payload(channel="other"), strict_channel=False)
        assert p.channel == "other"

    def test_bad_table(self) -> None:
        with pytest.raises(ValueError, match="unexpected table"):
            parse_notify_payload(_sample_payload(table="clientes"))

    def test_bad_op(self) -> None:
        with pytest.raises(ValueError, match="unexpected op"):
            parse_notify_payload(_sample_payload(op="DELETE"))

    def test_bad_id(self) -> None:
        with pytest.raises(ValueError, match="invalid id"):
            parse_notify_payload(_sample_payload(id="x"))

    def test_empty_status(self) -> None:
        with pytest.raises(ValueError, match="status is required"):
            parse_notify_payload(_sample_payload(status=""))

    def test_required_keys_cover_sample(self) -> None:
        sample = _sample_payload()
        for k in REQUIRED_PAYLOAD_KEYS:
            assert k in sample


class TestSqlFile:
    def test_validate_sql_file_exists(self) -> None:
        path = validate_sql_file_exists()
        assert path.is_file()
        assert path.name == "triggers_n8n_notify_g8.sql"
        assert SQL_REL_PATH in str(path).replace("\\", "/")

    def test_sql_file_path_under_repo(self) -> None:
        root = repo_root()
        assert (root / "backend" / "app").is_dir()
        assert sql_file_path(root) == root / SQL_REL_PATH

    def test_validate_missing_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="G8.06.T4 SQL missing"):
            validate_sql_file_exists(tmp_path)

    def test_sql_structure_ok(self) -> None:
        ok, missing = sql_structure_ok()
        assert ok is True, f"missing SQL markers: {missing}"
        assert missing == []

    def test_sql_content_markers(self) -> None:
        sql = read_sql()
        assert "G8.06.T4" in sql
        assert "pg_notify('cartorio_meta'" in sql
        assert "CREATE OR REPLACE FUNCTION" in sql
        assert "notify_cartorio_meta" in sql
        assert "trg_cartorio_meta_protocolos" in sql
        assert "trg_cartorio_meta_atendimentos" in sql
        assert "AFTER INSERT OR UPDATE" in sql
        assert "public.protocolos" in sql
        assert "public.atendimentos" in sql
        assert "DROP TRIGGER IF EXISTS" in sql
        # status-only update filter
        assert "IS NOT DISTINCT FROM" in sql
        assert "OF status" in sql
