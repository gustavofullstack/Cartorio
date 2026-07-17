"""G7 Wave 22 — coverage gap tooling + canned v4 + WA emolumento synthetic.

Modified by Gustavo Almeida — G7 Wave 22.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.api.v1.whatsapp import parse_evolution_payload
from app.services.chatwoot_canned_responses_v4 import (
    V4_CANNED_RESPONSES,
    count_all_canned_v2_v3_v4,
    get_v4_short_codes,
)
from app.services.dead_mans_switch import check_audit_log_alive, send_alert
from app.services.emolumento import calcular
from app.services.evolution_ingest import validate_evolution_signature

ROOT = Path(__file__).resolve().parents[2]


def test_coverage_gap_report_script_exists() -> None:
    assert (ROOT / "scripts" / "coverage_gap_report.py").is_file()


def test_canned_v4_has_ten_and_hitl_tags() -> None:
    assert len(V4_CANNED_RESPONSES) == 10
    codes = get_v4_short_codes()
    assert "isencao_hitl" in codes
    assert "urgencia_hitl" in codes
    counts = count_all_canned_v2_v3_v4()
    assert counts["v4"] == 10
    assert counts["v3"] == 10
    # meta 20+ no codigo v3+v4 sozinho
    assert counts["v3"] + counts["v4"] >= 20


def test_wa_emolumento_synthetic_flow() -> None:
    """G7.04.T4 synthetic: Evolution dual payload → intent emolumento → calcular.

    Nao chama WhatsApp real; valida pipeline de negocio.
    """
    nested = {
        "event": "messages.upsert",
        "instance": "cartorio-2notas",
        "data": {
            "key": {
                "remoteJid": "5534999999999@s.whatsapp.net",
                "fromMe": False,
                "id": "SYNTH_EMOL_1",
            },
            "message": {"conversation": "quanto custa procuracao"},
            "pushName": "Cliente Teste",
        },
    }
    msg = parse_evolution_payload(nested)
    assert msg is not None
    assert "procuracao" in msg.text.lower() or "procuração" in msg.text.lower()

    calc = calcular("procuracao", folhas=1, urgencia=False)
    assert calc.total == Decimal("156.40")
    assert calc.tipo == "procuracao"
    # HITL: isencao nao automatica
    calc_u = calcular("procuracao", folhas=1, urgencia=True)
    assert calc_u.total > calc.total


def test_wa_emolumento_certidao_casamento() -> None:
    calc = calcular("certidao_casamento")
    assert calc.total == Decimal("105.40")


def test_dead_mans_switch_empty_table() -> None:
    db = MagicMock()
    db.execute.return_value.scalar.return_value = None
    result = check_audit_log_alive(db)
    assert result["alive"] is False
    assert result["cold_start"] is True
    assert result["last_seen"] is None


def test_send_alert_fail_open_without_telegram() -> None:
    with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "", "TELEGRAM_CHAT_ID": ""}, clear=False):
        assert send_alert("drill") is False


def test_evolution_signature_rotation_prev_still_works(monkeypatch: pytest.MonkeyPatch) -> None:
    import hashlib
    import hmac

    monkeypatch.setenv("EVOLUTION_WEBHOOK_SECRET", "new")
    monkeypatch.setenv("EVOLUTION_WEBHOOK_SECRET_PREV", "old")
    body = b'{"event":"messages.upsert"}'
    sig = hmac.new(b"old", body, hashlib.sha256).hexdigest()
    assert validate_evolution_signature(body, sig) is True


def test_dns_sui_pack_exists() -> None:
    assert (ROOT / "docs" / "DNS_TRAEFIK_SUI_PACK_G7.md").is_file()
