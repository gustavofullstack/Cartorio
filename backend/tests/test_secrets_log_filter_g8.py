"""Testes de regressão do filtro de segredos G8.23.T1."""

from __future__ import annotations

import ast
import logging
from pathlib import Path

from app.core.secrets_log_filter import REDACTION, SecretScrubLogFilter


def _make_record(message: str, args: tuple[object, ...] = ()) -> logging.LogRecord:
    return logging.LogRecord(
        name="test.secrets",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=args,
        exc_info=None,
    )


def _filtered_message(message: str, args: tuple[object, ...] = ()) -> str:
    record = _make_record(message, args)
    assert SecretScrubLogFilter().filter(record) is True
    return record.getMessage()


def test_filter_redacts_api_key() -> None:
    secret = "super-sensitive-value"
    message = _filtered_message(f"API_KEY={secret}")
    assert message == REDACTION
    assert secret not in message


def test_filter_redacts_jwt() -> None:
    jwt = ".".join(
        (
            "eyJhbGciOiJIUzI1NiJ9",
            "eyJzdWIiOiIxMjM0NTY3ODkwIn0",
            "signature_value",
        )
    )
    message = _filtered_message(f"authorization={jwt}")
    assert REDACTION in message
    assert jwt not in message


def test_filter_redacts_openai_key() -> None:
    secret = "sk-" + ("OpenAISecretPart" * 2)
    message = _filtered_message(f"provider credential {secret}")
    assert REDACTION in message
    assert secret not in message


def test_filter_redacts_anthropic_key() -> None:
    secret = "sk-ant-" + ("AnthropicSecretPart" * 2)
    message = _filtered_message(f"provider credential {secret}")
    assert REDACTION in message
    assert secret not in message


def test_filter_redacts_aws_key() -> None:
    secret = "AKIA" + ("A1" * 8)
    message = _filtered_message(f"aws_access_key_id={secret}")
    assert REDACTION in message
    assert secret not in message


def test_filter_passes_clean_message() -> None:
    message = "startup concluído sem credenciais"
    assert _filtered_message(message) == message


def test_log_record_args_handled() -> None:
    secret = "argument-sensitive-value"
    record = _make_record("token=%s", (secret,))
    assert SecretScrubLogFilter().filter(record) is True
    assert record.args == ()
    assert record.getMessage() == REDACTION
    assert secret not in record.getMessage()


def test_filter_handles_unicode_safely() -> None:
    secret = "segredo-çã-安全"
    message = _filtered_message(f"password={secret} operação iniciada")
    assert message == f"{REDACTION} operação iniciada"
    assert secret not in message


def test_main_startup_does_not_print_env() -> None:
    main_path = Path(__file__).parents[1] / "app" / "main.py"
    tree = ast.parse(main_path.read_text(encoding="utf-8"))
    forbidden_names = {"environ", "getenv"}

    for statement in tree.body:
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        for node in ast.walk(statement):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Name) or node.func.id != "print":
                continue
            referenced_names = {child.id for child in ast.walk(node) if isinstance(child, ast.Name)}
            referenced_attributes = {
                child.attr for child in ast.walk(node) if isinstance(child, ast.Attribute)
            }
            assert forbidden_names.isdisjoint(referenced_names | referenced_attributes)


def test_main_lifespan_registers_secret_filter() -> None:
    main_path = Path(__file__).parents[1] / "app" / "main.py"
    tree = ast.parse(main_path.read_text(encoding="utf-8"))
    lifespan = next(
        node
        for node in tree.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "lifespan"
    )
    calls = [node for node in ast.walk(lifespan) if isinstance(node, ast.Call)]

    assert any(
        isinstance(call.func, ast.Name) and call.func.id == "SecretScrubLogFilter" for call in calls
    )
    assert any(
        isinstance(call.func, ast.Attribute) and call.func.attr == "addFilter" for call in calls
    )
