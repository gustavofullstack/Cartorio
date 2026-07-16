"""Testes unitários de prevenção de vazamento de PII no Sentry (Wave 4 S4.T3).

Modified by Gustavo Almeida.
"""

from __future__ import annotations



from app.services.sentry import _before_send
from app.services.metrics import store


def test_before_send_detects_and_prevents_pii_leak() -> None:
    """Valida se o before_send mascara PIIs cruas e incrementa a métrica de leak contido."""
    event = {
        "message": "Erro processando CPF 111.222.333-44 e email dpo@2notasudi.com.br",
        "exception": {
            "values": [
                {"value": "Falhou no CPF 99988877766"}
            ]
        },
        "tags": {"user_email": "vazamento@gmail.com"}
    }

    # Zera contador da métrica antes do teste
    store.counters["cartorio_pii_leak_prevented_total"] = {"": 0}

    processed = _before_send(event, {})

    # 1. Verifica se os valores foram devidamente scrubbed
    assert "[MASKED:cpf]" in processed["message"]
    assert "[MASKED:email]" in processed["message"]
    assert "[MASKED:cpf]" in processed["exception"]["values"][0]["value"]
    assert "[MASKED:email]" in processed["tags"]["user_email"]

    # 2. Verifica se a métrica de prevenção de vazamento foi incrementada
    assert store.counters["cartorio_pii_leak_prevented_total"][""] == 1


def test_before_send_allows_generic_error_without_increment() -> None:
    """Valida se erros genéricos sem PII passam sem alteração e sem incrementar o contador."""
    event = {
        "message": "Erro de timeout na conexao com a Evolution API",
        "exception": {
            "values": [
                {"value": "TimeoutError: connection refused"}
            ]
        },
        "tags": {"component": "whatsapp_adapter"}
    }

    # Zera contador da métrica antes do teste
    store.counters["cartorio_pii_leak_prevented_total"] = {"": 0}

    processed = _before_send(event, {})

    # Verifica integridade
    assert processed["message"] == "Erro de timeout na conexao com a Evolution API"
    assert processed["exception"]["values"][0]["value"] == "TimeoutError: connection refused"
    assert processed["tags"]["component"] == "whatsapp_adapter"

    # Métrica de prevenção de vazamento deve continuar zerada
    assert store.counters["cartorio_pii_leak_prevented_total"][""] == 0
