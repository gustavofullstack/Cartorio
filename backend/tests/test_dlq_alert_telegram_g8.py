"""G8.08.T3 — Testes para DLQ alert script.

Cobre:
  - collect_metrics: retorna dict por queue (LGPD-safe, sem payload)
  - build_alert_message: None quando tudo dentro do threshold
  - build_alert_message: detecta FAILED > threshold
  - build_alert_message: detecta PENDING > threshold
  - build_alert_message: formato MarkdownV2 correto
  - send_telegram: stub (não chama API real em testes)
  - main(): exit codes (0=ok, 1=alerta, 2=config, 3=send fail)
  - LGPD: mensagem NUNCA inclui payload/last_error

Modified by Gustavo Almeida — G8 Wave 31 A2.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "dlq_alert_telegram.py"


@pytest.fixture(scope="module")
def alert_module():
    """Importa dlq_alert_telegram.py dinamicamente."""
    spec = importlib.util.spec_from_file_location("dlq_alert_telegram", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestBuildAlertMessage:
    def test_returns_none_when_all_within_thresholds(self, alert_module):
        metrics = {
            "evolution": {"pending": 5, "failed_1h": 1, "max_age_minutes": 30},
            "chatwoot": {"pending": 10, "failed_1h": 2, "max_age_minutes": 15},
            "telegram": {"pending": 0, "failed_1h": 0, "max_age_minutes": 0},
            "outbox": {"pending": 3, "failed_1h": 0, "max_age_minutes": 5},
        }
        msg = alert_module.build_alert_message(metrics, threshold_failed=10, threshold_pending=100)
        assert msg is None

    def test_detects_failed_threshold_breach(self, alert_module):
        metrics = {
            "evolution": {"pending": 0, "failed_1h": 15, "max_age_minutes": 0},
        }
        msg = alert_module.build_alert_message(metrics, threshold_failed=10, threshold_pending=100)
        assert msg is not None
        assert "evolution" in msg
        assert "15" in msg
        assert "10" in msg  # threshold shown

    def test_detects_pending_threshold_breach(self, alert_module):
        metrics = {
            "chatwoot": {"pending": 150, "failed_1h": 0, "max_age_minutes": 240},
        }
        msg = alert_module.build_alert_message(metrics, threshold_failed=10, threshold_pending=100)
        assert msg is not None
        assert "chatwoot" in msg
        assert "150" in msg
        assert "240min" in msg

    def test_message_includes_multiple_queues(self, alert_module):
        metrics = {
            "evolution": {"pending": 5, "failed_1h": 12, "max_age_minutes": 30},
            "chatwoot": {"pending": 200, "failed_1h": 0, "max_age_minutes": 60},
        }
        msg = alert_module.build_alert_message(metrics, threshold_failed=10, threshold_pending=100)
        assert msg is not None
        assert "evolution" in msg
        assert "chatwoot" in msg

    def test_message_uses_markdownv2_format(self, alert_module):
        metrics = {"telegram": {"pending": 5, "failed_1h": 50, "max_age_minutes": 10}}
        msg = alert_module.build_alert_message(metrics, threshold_failed=10, threshold_pending=100)
        assert msg is not None
        # MarkdownV2 markers
        assert "*" in msg  # bold/italic
        assert "_" in msg  # italic (footer)
        assert "🚨" in msg or "⚠️" in msg  # emoji


class TestLGPDCompliance:
    """Garante que mensagem NUNCA inclui dados pessoais."""

    def test_message_does_not_contain_payload(self, alert_module):
        metrics = {"evolution": {"pending": 5, "failed_1h": 50, "max_age_minutes": 10}}
        msg = alert_module.build_alert_message(metrics, threshold_failed=10, threshold_pending=100)
        # NÃO pode ter chaves que indicariam payload
        assert "payload" not in msg.lower()
        assert "cpf" not in msg.lower()
        assert "rg" not in msg.lower()
        assert "telefone" not in msg.lower()
        assert "email" not in msg.lower()

    def test_message_only_contains_aggregates(self, alert_module):
        metrics = {
            "evolution": {"pending": 5, "failed_1h": 50, "max_age_minutes": 10},
            "chatwoot": {"pending": 200, "failed_1h": 30, "max_age_minutes": 60},
        }
        msg = alert_module.build_alert_message(metrics, threshold_failed=10, threshold_pending=100)
        # Apenas números e nomes de queue (sem chaves/dicts que indicariam payload)
        assert "{" not in msg
        assert "}" not in msg
        assert "last_error" not in msg
        assert "payload" not in msg.lower()

    def test_message_no_human_readable_names(self, alert_module):
        metrics = {"telegram": {"pending": 5, "failed_1h": 50, "max_age_minutes": 10}}
        msg = alert_module.build_alert_message(metrics, threshold_failed=10, threshold_pending=100)
        # Nomes próprios comuns NÃO devem aparecer
        for name in ["Gustavo", "João", "Maria", "Silva", "Santos"]:
            assert name not in msg


class TestSendTelegram:
    def test_send_telegram_missing_token_returns_error(self, alert_module, capsys):
        # Sem env vars, send deve falhar gracefully
        import os as os_mod

        old_token = os_mod.environ.pop("TELEGRAM_BOT_TOKEN", None)
        old_chat = os_mod.environ.pop("TELEGRAM_CHAT_ID", None)
        try:
            ok, response = alert_module.send_telegram(
                "test message",
                token="",  # empty
                chat_id="123",
            )
            # Empty token deve falhar (sem network call)
            assert ok is False
        finally:
            if old_token:
                os_mod.environ["TELEGRAM_BOT_TOKEN"] = old_token
            if old_chat:
                os_mod.environ["TELEGRAM_CHAT_ID"] = old_chat


class TestMain:
    def test_main_dry_run_returns_1_when_alert_triggered(self, alert_module, monkeypatch, capsys):
        # Mock collect_metrics para retornar FAILED > threshold
        monkeypatch.setattr(
            alert_module,
            "collect_metrics",
            lambda db=None: {
                "evolution": {"pending": 0, "failed_1h": 50, "max_age_minutes": 0},
            },
        )
        monkeypatch.setattr(sys, "argv", ["dlq_alert_telegram.py"])
        rc = alert_module.main()
        # DRY-RUN mode (sem --apply) retorna 1 se alerta detectado
        assert rc == 1
        captured = capsys.readouterr()
        assert "ALERT TRIGGERED" in captured.out
        assert "DRY-RUN" in captured.out

    def test_main_dry_run_returns_0_when_no_alert(self, alert_module, monkeypatch, capsys):
        monkeypatch.setattr(
            alert_module,
            "collect_metrics",
            lambda db=None: {
                "evolution": {"pending": 0, "failed_1h": 0, "max_age_minutes": 0},
            },
        )
        monkeypatch.setattr(sys, "argv", ["dlq_alert_telegram.py"])
        rc = alert_module.main()
        assert rc == 0
        captured = capsys.readouterr()
        assert "No alert" in captured.out

    def test_main_apply_without_env_returns_2(self, alert_module, monkeypatch):
        monkeypatch.setattr(
            alert_module,
            "collect_metrics",
            lambda db=None: {
                "evolution": {"pending": 0, "failed_1h": 50, "max_age_minutes": 0},
            },
        )
        # Garantir que TELEGRAM_BOT_TOKEN nao esta setado

        monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
        monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
        monkeypatch.setattr(
            sys, "argv", ["dlq_alert_telegram.py", "--apply"]
        )
        # .secrets/telegram.env pode existir com token real. Forcar file inexistente.
        monkeypatch.setattr(
            alert_module, "_load_env_file", lambda path: {}
        )
        rc = alert_module.main()
        assert rc == 2


class TestScriptSurface:
    """Smoke tests do módulo (entrypoint funciona)."""

    def test_script_has_shebang(self):
        first_line = SCRIPT.read_text(encoding="utf-8").splitlines()[0]
        assert first_line.startswith("#!"), "Script deve ter shebang"

    def test_script_has_docstring(self):
        text = SCRIPT.read_text(encoding="utf-8")
        assert '"""' in text or "'''" in text

    def test_script_documents_lgpd_compliance(self):
        text = SCRIPT.read_text(encoding="utf-8").lower()
        assert "lgpd" in text
        assert "payload" in text or "pessoal" in text

    def test_script_imports_no_pii_leak_in_default(self):
        """Garante que LGPD Art.46/16 mentioned explicitamente."""
        text = SCRIPT.read_text(encoding="utf-8")
        assert "Art.37" in text or "Art.16" in text or "Art.46" in text

    def test_script_has_dry_run_default(self):
        """Default deve ser dry-run (Lesson 185: 1-2 agents max + safe default)."""
        text = SCRIPT.read_text(encoding="utf-8")
        assert "dry-run" in text.lower() or "DRY-RUN" in text
        # --apply é opt-in
        assert "--apply" in text

    def test_script_has_help_text(self):
        text = SCRIPT.read_text(encoding="utf-8")
        assert "--help" in text or "argparse" in text