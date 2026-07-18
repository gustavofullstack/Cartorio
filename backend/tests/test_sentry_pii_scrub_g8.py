"""G8.18.T4 — Sentry before_send PII scrubber (LGPD Art. 46 + Art. 50).

Cobertura:
- message
- exception.values[].value/type
- exception.values[].stacktrace.frames[].filename/function/vars
- breadcrumbs.values[].message + .data (dict recursivo)
- request.{query_string, cookies, headers, data}
- user.id (hash deterministico quando looks_like_pii)
- early return para event None
- backward-compat: alias `_before_send` continua funcional
- LGPD leak metric increment quando PII detectado em payload

LGPD safety:
- Zero PII raw deve chegar ao vendor Sentry (SaaS externo).
- Hash deterministico (`anon-<sha256[:16]>`) substitui user.id quando
  parece ser CPF/CNS/etc — preserva rastreabilidade cruzada sem expor
  o valor bruto.
"""

from __future__ import annotations

from app.services.sentry import (
    _before_send,
    hash_pii_sentry,
    looks_like_pii,
    scrub_dict_inplace,
    scrub_pii_from_event,
)


# ─── 1. message ──────────────────────────────────────────────────────────


def test_scrub_message_removes_cpf() -> None:
    """Message field: CPF raw -> MASKED."""
    event = {"message": "Erro ao processar CPF 123.456.789-00 do cliente"}
    result = scrub_pii_from_event(event, {})
    assert result is not None
    assert "123.456.789-00" not in result["message"]
    assert "[MASKED:cpf]" in result["message"]


def test_scrub_message_removes_email() -> None:
    """Message field: email raw -> MASKED."""
    event = {"message": "Falha no envio para admin@cartorio.com.br"}
    result = scrub_pii_from_event(event, {})
    assert result is not None
    assert "admin@cartorio.com.br" not in result["message"]
    assert "[MASKED:email]" in result["message"]


# ─── 2. exception values + stacktrace frames ─────────────────────────────


def test_scrub_exception_value_removes_cpf() -> None:
    """exception.values[].value: CPF raw -> MASKED."""
    event = {
        "exception": {
            "values": [
                {"type": "ValueError", "value": "CPF 123.456.789-00 invalido"},
                {"type": "RuntimeError", "value": "seguro"},
            ]
        }
    }
    result = scrub_pii_from_event(event, {})
    assert result is not None
    assert "[MASKED:cpf]" in result["exception"]["values"][0]["value"]
    assert result["exception"]["values"][1]["value"] == "seguro"


def test_scrub_exception_type_with_pii() -> None:
    """exception.values[].type (raro mas ocorre): CPF raw -> MASKED."""
    event = {"exception": {"values": [{"type": "MyError-123.456.789-00"}]}}
    result = scrub_pii_from_event(event, {})
    assert result is not None
    assert "123.456.789-00" not in result["exception"]["values"][0]["type"]
    assert "[MASKED:cpf]" in result["exception"]["values"][0]["type"]


def test_scrub_stacktrace_frame_removes_cpf() -> None:
    """exception.stacktrace.frames[].vars (dict): CPF raw -> SCRUBBED."""
    event = {
        "exception": {
            "values": [
                {
                    "stacktrace": {
                        "frames": [
                            {
                                "filename": "app/auth.py",
                                "function": "validate",
                                "vars": {
                                    "cpf": "123.456.789-00",
                                    "safe": "ok",
                                },
                            }
                        ]
                    }
                }
            ]
        }
    }
    result = scrub_pii_from_event(event, {})
    assert result is not None
    frame = result["exception"]["values"][0]["stacktrace"]["frames"][0]
    assert frame["filename"] == "app/auth.py"
    assert frame["function"] == "validate"
    assert frame["vars"]["cpf"] == "[LGPD-SCRUBBED]"
    assert frame["vars"]["safe"] == "ok"


# ─── 3. breadcrumbs ──────────────────────────────────────────────────────


def test_scrub_breadcrumb_message_removes_cpf() -> None:
    """breadcrumbs.values[].message: CPF raw -> MASKED."""
    event = {
        "breadcrumbs": {
            "values": [
                {
                    "type": "http",
                    "message": "POST /api/v1/cliente com doc=123.456.789-00",
                    "data": {"user_id": 42, "method": "POST"},
                },
                {"type": "ui", "message": "clicked save"},
            ]
        }
    }
    result = scrub_pii_from_event(event, {})
    assert result is not None
    bcs = result["breadcrumbs"]["values"]
    assert "123.456.789-00" not in bcs[0]["message"]
    assert "[MASKED:cpf]" in bcs[0]["message"]
    assert bcs[1]["message"] == "clicked save"


def test_scrub_breadcrumb_data_dict_removes_pii() -> None:
    """breadcrumbs.values[].data (dict): PII raw -> SCRUBBED."""
    event = {
        "breadcrumbs": {
            "values": [
                {
                    "type": "ui",
                    "message": "form submitted",
                    "data": {
                        "email": "user@example.com",
                        "items_count": 3,
                        "nested": {"phone": "(34) 99999-8888"},
                    },
                }
            ]
        }
    }
    result = scrub_pii_from_event(event, {})
    assert result is not None
    data = result["breadcrumbs"]["values"][0]["data"]
    assert data["email"] == "[LGPD-SCRUBBED]"
    assert data["items_count"] == 3
    assert data["nested"]["phone"] == "[LGPD-SCRUBBED]"


# ─── 4. request ──────────────────────────────────────────────────────────


def test_scrub_request_query_string_removes_cpf() -> None:
    """request.query_string (string): CPF raw -> MASKED."""
    event = {
        "request": {
            "method": "GET",
            "url": "https://api.cartorio/v1/cliente?doc=123.456.789-00",
            "query_string": "doc=123.456.789-00&tipo=cpf",
        }
    }
    result = scrub_pii_from_event(event, {})
    assert result is not None
    qs = result["request"]["query_string"]
    assert "123.456.789-00" not in qs
    assert "[MASKED:cpf]" in qs


def test_scrub_request_headers_dict_removes_pii() -> None:
    """request.headers (dict): valor com PII -> SCRUBBED, safe preservado."""
    event = {
        "request": {
            "headers": {
                "authorization": "Bearer token-123.456.789-00",
                "content-type": "application/json",
                "x-client-email": "admin@cartorio.com",
            }
        }
    }
    result = scrub_pii_from_event(event, {})
    assert result is not None
    headers = result["request"]["headers"]
    assert "123.456.789-00" not in headers["authorization"]
    assert headers["content-type"] == "application/json"
    assert headers["x-client-email"] == "[LGPD-SCRUBBED]"


def test_scrub_request_body_recursive_removes_pii() -> None:
    """request.data (dict): scrub recursivo remove PII de qualquer nivel."""
    event = {
        "request": {
            "data": {
                "cliente": {
                    "nome": "Joao",
                    "cpf": "123.456.789-00",
                    "contatos": [
                        {"tipo": "email", "valor": "joao@x.com"},
                        {"tipo": "tel", "valor": "(34) 99999-1111"},
                    ],
                },
                "qtd": 5,
            }
        }
    }
    result = scrub_pii_from_event(event, {})
    assert result is not None
    data = result["request"]["data"]
    assert data["cliente"]["nome"] == "Joao"
    assert data["cliente"]["cpf"] == "[LGPD-SCRUBBED]"
    assert data["cliente"]["contatos"][0]["valor"] == "[LGPD-SCRUBBED]"
    assert data["cliente"]["contatos"][1]["valor"] == "[LGPD-SCRUBBED]"
    assert data["qtd"] == 5


def test_scrub_request_cookies_dict_removes_pii() -> None:
    """request.cookies (dict): valor PII -> SCRUBBED."""
    event = {
        "request": {
            "cookies": {"session": "abc", "user_email": "x@y.com"},
        }
    }
    result = scrub_pii_from_event(event, {})
    assert result is not None
    cookies = result["request"]["cookies"]
    assert cookies["session"] == "abc"
    assert cookies["user_email"] == "[LGPD-SCRUBBED]"


# ─── 5. user.id hash ─────────────────────────────────────────────────────


def test_user_id_hashed_when_looks_like_pii() -> None:
    """user.id raw (CPF) -> hash deterministico anon-<sha256[:16]>."""
    event = {"user": {"id": "123.456.789-00", "username": "joao"}}
    result = scrub_pii_from_event(event, {})
    assert result is not None
    assert result["user"]["id"].startswith("anon-")
    assert "123.456.789-00" not in result["user"]["id"]
    assert result["user"]["username"] == "joao"


def test_user_id_preserved_when_safe() -> None:
    """user.id que NAO eh PII -> preservado."""
    event = {"user": {"id": "user-12345", "email": "x@y.com"}}
    result = scrub_pii_from_event(event, {})
    assert result is not None
    assert result["user"]["id"] == "user-12345"
    # email continua scrubbed (camada tags/extra/user aplicada)
    assert result["user"]["email"] == "[MASKED:email]"


def test_user_id_int_converted_to_hash() -> None:
    """user.id numerico (int) -> convertido para hash deterministico."""
    event = {"user": {"id": 12345678900}}
    result = scrub_pii_from_event(event, {})
    assert result is not None
    assert result["user"]["id"].startswith("anon-")


# ─── 6. edge cases / misc ───────────────────────────────────────────────


def test_scrub_pii_from_event_none_returns_none() -> None:
    """Early return: event None -> None (early return optimization)."""
    assert scrub_pii_from_event(None, {}) is None  # type: ignore[arg-type]


def test_returns_event_with_no_pii_unaffected_when_clean() -> None:
    """Evento sem PII: volta identico (sem alteracoes espurias)."""
    event = {
        "message": "operacao normal",
        "tags": {"env": "test", "version": "0.6.0"},
        "extra": {"qtd": 10, "ok": True},
        "user": {"id": "abc-123", "username": "demo"},
    }
    result = scrub_pii_from_event(event, {})
    assert result is not None
    assert result["message"] == "operacao normal"
    assert result["tags"]["env"] == "test"
    assert result["tags"]["version"] == "0.6.0"
    assert result["extra"]["qtd"] == 10
    assert result["user"]["id"] == "abc-123"
    assert result["user"]["username"] == "demo"


def test_scrub_pii_from_event_without_sections() -> None:
    """Evento sem exception/breadcrumbs/request: nao quebra."""
    event = {"message": "clean"}
    result = scrub_pii_from_event(event, {})
    assert result is not None
    assert result["message"] == "clean"


def test_scrub_dict_inplace_modifies_in_place() -> None:
    """scrub_dict_inplace mutates o dict (LGPD-safe side effect)."""
    d = {"cpf": "123.456.789-00", "nested": {"email": "a@b.com"}, "safe": 1}
    scrub_dict_inplace(d)
    assert d["cpf"] == "[LGPD-SCRUBBED]"
    assert d["nested"]["email"] == "[LGPD-SCRUBBED]"
    assert d["safe"] == 1


def test_looks_like_pii_detects_cpf() -> None:
    """looks_like_pii retorna True para CPF formatado."""
    assert looks_like_pii("doc 123.456.789-00") is True


def test_looks_like_pii_returns_false_for_safe_text() -> None:
    """looks_like_pii retorna False para texto sem PII."""
    assert looks_like_pii("operacao normal sem dados sensiveis") is False


def test_looks_like_pii_returns_false_for_empty() -> None:
    """looks_like_pii retorna False para string vazia / None."""
    assert looks_like_pii("") is False
    assert looks_like_pii("   ") is False


def test_hash_pii_sentry_deterministic() -> None:
    """hash_pii_sentry eh deterministico (mesmo input -> mesmo output)."""
    a = hash_pii_sentry("123.456.789-00")
    b = hash_pii_sentry("123.456.789-00")
    assert a == b
    assert a.startswith("anon-")
    # Raw nao vaza
    assert "123.456.789-00" not in a


# ─── 7. backward-compat _before_send alias ───────────────────────────────


def test_before_send_alias_delegates_to_scrub_pii_from_event() -> None:
    """_before_send (legado) delega para scrub_pii_from_event e retorna scrubbed."""
    event = {"message": "ERRO: CPF 123.456.789-00 invalido"}
    result = _before_send(event, {})
    assert result is not None
    assert "123.456.789-00" not in result["message"]
    assert "[MASKED:cpf]" in result["message"]


def test_before_send_alias_handles_none_event() -> None:
    """_before_send retorna None quando event eh None (Sentry DropEvent)."""
    assert _before_send(None, {}) is None  # type: ignore[arg-type]
