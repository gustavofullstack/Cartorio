"""T024 / T025 — Audit chain regression tests (v22 plan).

T024 — Retro-edit em entry mid-chain invalida VERIFY a partir desse ponto.
T025 — Rotacao de HMAC key mid-chain deve ser GRACEFUL (overlap handling).
"""

from __future__ import annotations

import pytest

from app.models.audit_log import AuditLog
from app.services.audit import AuditService


@pytest.mark.t024
def test_retro_edit_in_mid_chain_invalidates_chain(db_session):
    """T024: edit em entry no MEIO da chain quebra verify com last_valid < total."""
    # Setup: cria 5 entries
    for i in range(5):
        AuditService.log(
            db_session,
            actor_id=f"u{i}",
            action="retro_test",
            resource=f"r:{i}",
            payload={"i": i, "valor": i * 100},
        )
    db_session.commit()

    # Verify pre-tamper (deve passar)
    ok_before, count_before = AuditService.verify_chain(db_session)
    assert ok_before is True, "Chain deve estar integra apos setup"
    assert count_before == 5

    # Tampering: edita entry do meio (id=3, no index 2 de 5)
    entries = db_session.query(AuditLog).order_by(AuditLog.id.asc()).all()
    midpoint = entries[2]
    midpoint.payload = {"i": 999, "valor": 99999}  # attacker modifica
    db_session.commit()

    # Verify pos-tamper
    ok_after, last_valid_after = AuditService.verify_chain(db_session)
    assert ok_after is False, "Verify DEVE detectar tampering"
    assert last_valid_after == 2, (
        f"last_valid esperado=2 (entries 0 e 1 intactas); obtido={last_valid_after}"
    )


@pytest.mark.t025
def test_hmac_key_rotation_does_not_break_old_verifications(db_session):
    """T025: entries ANTIGAS (assinadas com key antiga) ainda devem validar
    via fallback chain (primary key + N historical keys).

    Setup:
    1. Loga 3 entries (assinadas com key atual)
    2. Simula rotacao de key
    3. Loga 2 entries (nova key)
    4. verify_chain() deve passar TUDO (assume multi-key support).

    NOTA: se o projeto ainda for single-key-only, este teste valida que
    a transicao e' detectavel e que ha plano de migracao.
    """
    from app.config import settings

    # Captura key atual
    original_key = settings.audit_hmac_key

    # 3 entries com key A
    for i in range(3):
        AuditService.log(
            db_session,
            actor_id="keyA",
            action="rotation_test",
            resource=f"a:{i}",
            payload={"i": i, "key": "A"},
        )
    db_session.commit()

    # Rotaciona key
    settings.audit_hmac_key = "ROTATED_KEY_B_FOR_T025_TEST"

    # 2 entries com key B
    for i in range(2):
        AuditService.log(
            db_session,
            actor_id="keyB",
            action="rotation_test",
            resource=f"b:{i}",
            payload={"i": i, "key": "B"},
        )
    db_session.commit()

    # Verify chain: ainda deve passar pois cada entry' signature e' armazenada
    # no momento do log (nao recalculada na verificacao)
    ok, count = AuditService.verify_chain(db_session)
    assert ok is True, f"Chain deve validar mesmo apos rotacao de key (got ok={ok})"
    assert count == 5

    # Restaura key original (cleanup)
    settings.audit_hmac_key = original_key


def test_retro_edit_with_hmac_chain_consistency(db_session):
    """T024b: validacao dupla — tampering do payload (campo hasheado) invalida
    entries subsequentes; hash chain permanece conectado entre entry 0 e 1."""
    # 3 entries
    for i in range(3):
        AuditService.log(
            db_session,
            actor_id="u",
            action="double_check",
            resource=f"x:{i}",
            payload={"v": i},
        )
    db_session.commit()

    # Edit PAYLOAD (campo hasheado) na entry 2 (do meio)
    entries = db_session.query(AuditLog).order_by(AuditLog.id.asc()).all()
    entries[1].payload = {"v": 9999}
    db_session.commit()

    ok, last_valid = AuditService.verify_chain(db_session)
    assert ok is False
    # Entry 0 deve estar OK; entry 1 (tampered) quebra chain; entries 1 e 2 invalidos
    assert last_valid == 1
