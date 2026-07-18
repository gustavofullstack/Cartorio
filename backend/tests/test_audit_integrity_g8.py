"""G8.19.T1 — testes do verificador de integridade da blockchain de auditoria.

Cobre:
- chain intacta (5 entries canonicas) -> []
- tamper mid-chain (modifica entry 3) -> indices quebrados >= [3]
- HMAC forjado (assinatura invalida, hash OK) -> [indice]
- chain head (entry 0 sem prev_hash) -> OK
- edicao retroativa no meio -> quebra chain subsequente
- cadeia vazia -> []
- CLI exit code 0 quando intacto
- CLI exit code 1 quando quebrado

Regressao t024 (retro-edit mid-chain) e t025 (HMAC key rotation).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.services.audit import AuditService
from app.services.audit_integrity import (
    from_db,
    verify_full_chain,
    verify_hash_sequence,
)


def _seed_chain(db: Session, n: int = 5) -> list[dict[str, Any]]:
    """Insere N entries canonicas e retorna a lista serializada."""
    for i in range(n):
        AuditService.log(
            db,
            actor_id=f"user:{i}",
            action="protocolo.create",
            resource=f"protocolo:{i}",
            payload={"i": i, "valor": 100 + i},
        )
    db.commit()
    return list(from_db(db))


def test_chain_intact_returns_empty(db_session):
    """5 entries canonicas devem produzir lista vazia de breaks."""
    entries = _seed_chain(db_session, n=5)
    assert len(entries) == 5
    broken = verify_hash_sequence(entries)
    assert broken == [], f"Cadeia intacta nao deveria ter breaks, achou {broken}"


def test_chain_break_detected_after_payload_edit(db_session):
    """Modificar payload de entry 3 deve quebrar todos os entries >= 3."""
    entries = _seed_chain(db_session, n=5)

    # Tamper: altera payload do entry 3 (mas NAO mexe no hash armazenado).
    # Isso quebra a regra 2 (hash recomputado != stored).
    entries[3]["payload"] = {"i": 999, "valor": 99999}

    broken = verify_hash_sequence(entries)
    # Index 3 quebra por hash mismatch; indices 4+ quebram por chain (prev_hash
    # do entry 4 != hash do entry 3 recalculado). Por isso esperamos >= [3, 4].
    assert 3 in broken, f"Esperava quebra no indice 3, achou {broken}"
    assert 4 in broken, f"Esperava quebra no indice 4 (chain subsequente), achou {broken}"
    assert broken[0] == 3, f"Primeira quebra deveria ser 3, achou {broken[0]}"


def test_hmac_break_detected_with_valid_hash(db_session):
    """Forjar HMAC (mantendo hash consistente) deve quebrar chain pela regra 3."""
    entries = _seed_chain(db_session, n=5)

    # Substitui HMAC do entry 3 por um valor fake de 64 chars hex.
    # O hash chain permanece correto, mas a regra HMAC falha.
    entries[3]["hmac_signature"] = "f" * 64

    broken = verify_hash_sequence(entries)
    assert 3 in broken, f"Esperava quebra HMAC no indice 3, achou {broken}"


def test_first_entry_no_prev_hash_is_ok(db_session):
    """Index 0 com prev_hash=None (chain head) deve ser aceito."""
    entries = _seed_chain(db_session, n=3)
    # Entrada 0 do banco tem prev_hash=None por design (chain head).
    assert entries[0]["prev_hash"] is None
    broken = verify_hash_sequence(entries)
    assert broken == [], f"Chain head nao deveria quebrar, achou {broken}"


def test_modify_in_middle_breaks_remaining(db_session):
    """Editar entry 2 -> quebra indices 2..N-1 (regra t024 retro-edit mid-chain)."""
    entries = _seed_chain(db_session, n=6)

    # Altera payload do entry 2 — rompe a chain a partir dele.
    entries[2]["payload"]["tampered"] = True

    broken = verify_hash_sequence(entries)
    # Indices quebrados: 2 (hash recomputado != stored) + 3, 4, 5 (chain).
    assert broken == [2, 3, 4, 5], f"Esperava [2, 3, 4, 5], achou {broken}"


def test_empty_chain_returns_empty(db_session):
    """Tabela vazia -> lista vazia de breaks, score=1.0 (vacuously true)."""
    broken = verify_hash_sequence([])
    assert broken == []

    result = verify_full_chain(db_session)
    assert result["total_entries"] == 0
    assert result["broken_indices"] == []
    assert result["integrity_score"] == 1.0
    assert result["chain_intact"] is True
    assert result["first_break_id"] is None
    assert result["error"] is None


def test_verify_full_chain_intact(db_session):
    """verify_full_chain em cadeia integra deve retornar summary OK."""
    _seed_chain(db_session, n=7)

    result = verify_full_chain(db_session)
    assert result["total_entries"] == 7
    assert result["broken_indices"] == []
    assert result["integrity_score"] == 1.0
    assert result["chain_intact"] is True
    assert result["first_break_id"] is None
    assert result["error"] is None


def test_verify_full_chain_detects_tamper(db_session):
    """verify_full_chain deve detectar tamper mid-chain e popular summary."""
    _seed_chain(db_session, n=4)

    # Tamper direto no banco: edita payload do entry com id 2 (0-indexed = 1).
    from app.models.audit_log import AuditLog

    target = db_session.query(AuditLog).order_by(AuditLog.id.asc()).offset(1).first()
    target.payload = {"hacked": True}
    db_session.commit()

    result = verify_full_chain(db_session)
    assert result["total_entries"] == 4
    assert result["chain_intact"] is False
    assert len(result["broken_indices"]) >= 2  # entry editado + chain subsequente
    assert result["broken_indices"][0] == 1
    assert result["first_break_id"] == target.id
    assert 0.0 < result["integrity_score"] < 1.0


def _patch_cli_session(monkeypatch, db_session):
    """Redireciona o SessionLocal do CLI script para a engine do teste.

    O CLI faz `from app.db import SessionLocal` que snapshotou a referencia
    original (Postgres de prod). O autouse conftest rebinds `app.db.SessionLocal`
    para SQLite in-memory, mas o modulo `scripts.*` nao eh afetado pelo loop
    de rebind. Entao patchamos o atributo `SessionLocal` no modulo do CLI
    diretamente.
    """
    from sqlalchemy.orm import sessionmaker
    from scripts import audit_integrity_check as cli_mod

    TestSessionLocal = sessionmaker(
        bind=db_session.get_bind(),
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    monkeypatch.setattr(cli_mod, "SessionLocal", TestSessionLocal)


def test_cli_exit_code_zero_when_intact(db_session, monkeypatch, capsys):
    """CLI deve sair 0 quando a cadeia esta integra."""
    _seed_chain(db_session, n=3)
    _patch_cli_session(monkeypatch, db_session)

    from scripts.audit_integrity_check import main

    rc = main([])
    captured = capsys.readouterr()
    assert rc == 0, f"Esperava exit 0, achou {rc}. stdout={captured.out!r}"
    assert "OK" in captured.out or "verified" in captured.out.lower()


def test_cli_exit_code_one_when_broken(db_session, monkeypatch, capsys):
    """CLI deve sair 1 quando a cadeia esta quebrada."""
    from app.models.audit_log import AuditLog

    _seed_chain(db_session, n=3)
    target = db_session.query(AuditLog).order_by(AuditLog.id.asc()).first()
    target.payload = {"hacked": True}
    db_session.commit()

    _patch_cli_session(monkeypatch, db_session)

    from scripts.audit_integrity_check import main

    rc = main([])
    captured = capsys.readouterr()
    assert rc == 1, f"Esperava exit 1, achou {rc}. stdout={captured.out!r}"
    assert "BROKEN" in captured.out or "broken" in captured.out.lower()


def test_cli_json_output_format(db_session, monkeypatch, capsys):
    """CLI com --json deve emitir JSON parseavel com chaves canonicas."""
    _seed_chain(db_session, n=2)
    _patch_cli_session(monkeypatch, db_session)

    from scripts.audit_integrity_check import main

    rc = main(["--json"])
    captured = capsys.readouterr()
    assert rc == 0
    parsed = __import__("json").loads(captured.out)
    assert "total_entries" in parsed
    assert "broken_indices" in parsed
    assert "integrity_score" in parsed
    assert "chain_intact" in parsed
    assert parsed["total_entries"] == 2
    assert parsed["chain_intact"] is True


def test_large_chain_streams_correctly(db_session):
    """100 entries: integridade deve permanecer 1.0 via streaming de from_db."""
    _seed_chain(db_session, n=100)

    result = verify_full_chain(db_session)
    assert result["total_entries"] == 100
    assert result["chain_intact"] is True
    assert result["integrity_score"] == 1.0
