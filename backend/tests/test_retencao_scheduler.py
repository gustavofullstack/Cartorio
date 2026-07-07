"""Testes para app/jobs/retencao_scheduler.py - compute_next_run + should_run (cobertura).

Cobre:
1. compute_next_run_utc happy path
2. compute_next_run_utc valida hora invalida
3. should_run_retencao_now retorna False se desabilitado
4. should_run_retencao_now retorna True na hora exata BRT
5. should_run_retencao_now retorna False fora da hora

Sobe cobertura retencao_scheduler.py 70% -> >=85%.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.jobs.retencao_scheduler import (
    compute_next_run_utc,
    should_run_retencao_now,
)


# =============================================================================
# compute_next_run_utc
# =============================================================================


def test_compute_next_run_utc_quando_ja_passou_amanha() -> None:
    """Se hour_brazil ja passou hoje, retorna amanha no mesmo slot."""
    # 10:00 UTC = 07:00 BRT 2026-06-29 (slot 03:00 BRT ja passou)
    now = datetime(2026, 6, 29, 10, 0, tzinfo=timezone.utc)
    next_run = compute_next_run_utc(now, retencao_hour_brazil=3)
    # 03:00 BRT ja passou, entao amanha 03:00 BRT = 06:00 UTC
    assert next_run.day == 30
    assert next_run.hour == 6


def test_compute_next_run_utc_quando_ainda_nao_chegou_hoje() -> None:
    """Se hour_brazil ainda nao chegou hoje, retorna hoje no mesmo slot."""
    # 23:00 UTC = 20:00 BRT 2026-06-29
    now = datetime(2026, 6, 29, 23, 0, tzinfo=timezone.utc)
    compute_next_run_utc(now, retencao_hour_brazil=22)
    # 22:00 BRT = 01:00 UTC do dia seguinte
    # Mas em 2026-06-29 23:00 UTC (20:00 BRT), o slot 22:00 BRT ja passou
    # Entao retorna amanha 22:00 BRT
    # Por isso eh importante verificar logica com hora futura
    # 04:00 UTC = 01:00 BRT 2026-06-29
    now2 = datetime(2026, 6, 29, 4, 0, tzinfo=timezone.utc)
    next_run2 = compute_next_run_utc(now2, retencao_hour_brazil=22)
    # 22:00 BRT ainda nao chegou (01:00 BRT), entao hoje 22:00 BRT = 01:00 UTC do dia seguinte
    # Mas como agora eh 01:00 BRT, slot 22:00 eh hoje
    # 22:00 BRT = 01:00 UTC do dia SEGUINTE (2026-06-30)
    assert next_run2.day == 30  # dia seguinte
    assert next_run2.hour == 1


def test_compute_next_run_utc_levanta_ValueError_para_hora_invalida() -> None:
    """compute_next_run_utc levanta ValueError para hora fora de [0, 23]."""
    now = datetime(2026, 6, 29, 5, 0, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="retencao_hour_brazil"):
        compute_next_run_utc(now, retencao_hour_brazil=24)
    with pytest.raises(ValueError, match="retencao_hour_brazil"):
        compute_next_run_utc(now, retencao_hour_brazil=-1)


def test_compute_next_run_utc_default_hora_3() -> None:
    """compute_next_run_utc default retencao_hour_brazil=3 (03:00 BRT)."""
    # 00:00 UTC = 21:00 BRT do dia anterior
    now = datetime(2026, 6, 29, 0, 0, tzinfo=timezone.utc)
    next_run = compute_next_run_utc(now)
    # 03:00 BRT = 06:00 UTC (ainda no dia 29)
    assert next_run.hour == 6
    assert next_run.day == 29


# =============================================================================
# should_run_retencao_now
# =============================================================================


def test_should_run_retencao_now_false_se_desabilitado() -> None:
    """should_run_retencao_now retorna False se retencao_enabled=False."""
    now = datetime(2026, 6, 29, 6, 0, tzinfo=timezone.utc)  # 03:00 BRT exato
    assert should_run_retencao_now(now, retencao_enabled=False, retencao_hour_brazil=3) is False


def test_should_run_retencao_now_true_na_hora_exata_BRT() -> None:
    """should_run_retencao_now retorna True na hora exata (minuto 0) BRT."""
    # 06:00 UTC = 03:00 BRT
    now = datetime(2026, 6, 29, 6, 0, tzinfo=timezone.utc)
    assert should_run_retencao_now(now, retencao_enabled=True, retencao_hour_brazil=3) is True


def test_should_run_retencao_now_false_fora_da_hora() -> None:
    """should_run_retencao_now retorna False fora da hora alvo."""
    # 10:00 UTC = 07:00 BRT (slot 03 ja passou)
    now = datetime(2026, 6, 29, 10, 0, tzinfo=timezone.utc)
    assert should_run_retencao_now(now, retencao_enabled=True, retencao_hour_brazil=3) is False


def test_should_run_retencao_now_false_com_minuto_diferente() -> None:
    """should_run_retencao_now retorna False se minuto != 0."""
    # 06:01 UTC = 03:01 BRT (hora certa mas minuto 1)
    now = datetime(2026, 6, 29, 6, 1, tzinfo=timezone.utc)
    assert should_run_retencao_now(now, retencao_enabled=True, retencao_hour_brazil=3) is False


def test_should_run_retencao_now_hora_zero_meia_noite() -> None:
    """should_run_retencao_now com retencao_hour_brazil=0 (00:00 BRT)."""
    # 03:00 UTC = 00:00 BRT
    now = datetime(2026, 6, 29, 3, 0, tzinfo=timezone.utc)
    assert should_run_retencao_now(now, retencao_enabled=True, retencao_hour_brazil=0) is True


def test_should_run_retencao_now_hora_23_fim_dia() -> None:
    """should_run_retencao_now com retencao_hour_brazil=23 (23:00 BRT)."""
    # 02:00 UTC (29-jun) = 23:00 BRT (28-jun)
    now = datetime(2026, 6, 29, 2, 0, tzinfo=timezone.utc)
    assert should_run_retencao_now(now, retencao_enabled=True, retencao_hour_brazil=23) is True
