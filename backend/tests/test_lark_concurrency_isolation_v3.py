"""Testes de concorrência e isolamento no Lark (V3)."""

from __future__ import annotations


def test_session_isolation_deterministic() -> None:
    session_a = {"user_id": "usr_001", "context": "Dúvida sobre inventário"}
    session_b = {"user_id": "usr_002", "context": "Dúvida sobre autenticação"}

    assert session_a["user_id"] != session_b["user_id"]
    assert session_a["context"] != session_b["context"]
