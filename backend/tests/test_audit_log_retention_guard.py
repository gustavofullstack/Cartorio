"""Regression checks for the append-only audit-log retention boundary."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RETENTION_SCRIPT = ROOT / "scripts" / "lgpd_retention_job.py"
CRON_MIGRATION = (
    ROOT / "infra" / "supabase" / "migrations" / "2026_06_24_0002-supabase-cron-vault-final.sql"
)
GUARD_MIGRATION = (
    ROOT / "infra" / "supabase" / "migrations" / "2026_07_19_0001-audit-log-retention-guard.sql"
)


def test_retention_script_never_offers_audit_log_as_a_deletion_target() -> None:
    """A CLI retention invocation must not be able to select audit_log."""
    source = RETENTION_SCRIPT.read_text(encoding="utf-8")

    rules_source = source.split("RETENTION_RULES =", maxsplit=1)[1].split(
        "\n\n\ndef get_db_config", 1
    )[0]
    assert '"audit_log"' not in rules_source


def test_supabase_cron_never_schedules_audit_log_delete() -> None:
    """Fresh Supabase installs schedule verification, not a chain-breaking purge."""
    source = CRON_MIGRATION.read_text(encoding="utf-8")

    assert "DELETE FROM public.audit_log" not in source
    assert "audit-chain-verify-daily-03h" in source


def test_retention_guard_cancels_legacy_job_and_rejects_mutations() -> None:
    """Existing installations remove the legacy job and receive a DB-level guard."""
    source = GUARD_MIGRATION.read_text(encoding="utf-8")

    assert "cron.unschedule" in source
    assert "retention-daily-03h" in source
    assert "BEFORE UPDATE OR DELETE ON public.audit_log" in source
    assert "RAISE EXCEPTION" in source
