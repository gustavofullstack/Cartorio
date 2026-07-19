"""G8.10.T3 tests.

Modified by Gustavo Almeida — Wave 42.
"""

from __future__ import annotations

from app.services.traefik_log_masker import mask_access_log_line, mask_query_string


def test_mask_cpf() -> None:
    line = "GET /x?cpf=529.982.247-25 HTTP/1.1"
    out = mask_access_log_line(line)
    assert "529" not in out
    assert "***" in out


def test_mask_email() -> None:
    assert "@" not in mask_query_string("user=a@b.com") or "***" in mask_query_string(
        "user=a@b.com"
    )


def test_mask_token() -> None:
    out = mask_query_string("authorization=Bearer_secret_value_here")
    assert "secret" not in out
    assert "***" in out


def test_empty() -> None:
    assert mask_access_log_line("") == ""


def test_clean_line_unchanged_structure() -> None:
    line = "GET /health 200"
    assert "health" in mask_access_log_line(line)
