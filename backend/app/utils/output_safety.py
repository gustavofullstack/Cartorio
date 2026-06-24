"""Output safety utilities (LGPD-016 #13 — output scrub FULL COVERAGE).

Wrapper UNICO para aplicar PII scrubbing em QUALQUER payload de saida
(responses HTTP, error messages, audit payloads, webhook returns, etc).

LGPD art. 46: dados pessoais nao podem sair do backend em texto puro.
Defense-in-depth: mesmo que o caller ja tenha feito scrub, eh idempotente
(re-roda eh no-op em texto ja scrubbed).

NAO mexer em audit/pii.py diretamente — apenas USAR `scrub()` daqui.
"""

from __future__ import annotations

from typing import Any

from app.services.pii import scrub


def scrub_response(payload: Any) -> tuple[Any, int]:
    """Aplica PII scrubbing recursivo em QUALQUER payload de saida.

    Args:
        payload: dict, list, str, int, float, bool, ou None. Aceita qualquer
                 estrutura JSON-like (response Pydantic serializada, dict, etc).

    Returns:
        Tuple (payload_scrubbed, total_pii_redacted_count).
        - payload_scrubbed: mesma estrutura do input, mas strings com PII
          tem CPF/RG/phone/CNS/CNH/etc substituidos por marcadores [TIPO_REDACTED].
        - total_pii_redacted_count: soma de PII removidas em TODAS as strings
          processadas recursivamente.

    Examples:
        >>> scrub_response("meu cpf é 123.456.789-09")
        ('meu cpf é [CPF_REDACTED]', 1)
        >>> scrub_response({"nome": "João", "cpf": "123.456.789-09"})
        ({'nome': 'João', 'cpf': '[CPF_REDACTED]'}, 1)
        >>> scrub_response({"cliente": {"cns": "898 0007 6473 5600"}})
        ({'cliente': {'cns': '[CNS_REDACTED]'}}, 1)
        >>> scrub_response(123)  # numero nao precisa scrub
        (123, 0)
        >>> scrub_response(None)  # None eh passado direto
        (None, 0)

    Idempotencia:
        >>> payload = {"cpf": "123.456.789-09"}
        >>> scrubbed, n1 = scrub_response(payload)
        >>> scrubbed2, n2 = scrub_response(scrubbed)
        >>> scrubbed == scrubbed2  # True
        True
        >>> n2 == 0  # segunda passada nao detecta mais PII
        True

    LGPD: use em TODA resposta HTTP, error message, audit payload, webhook
    return, etc. Nunca confie que caller ja fez scrub — wrapper eh
    idempotente e barato.
    """
    if payload is None:
        return None, 0

    # String: aplica scrub() e retorna count
    if isinstance(payload, str):
        result = scrub(payload)
        if result.redaction_count > 0:
            return result.text, result.redaction_count
        return payload, 0

    # Dict: recursivo em cada valor
    if isinstance(payload, dict):
        total = 0
        scrubbed_dict: dict[str, Any] = {}
        for key, value in payload.items():
            scrubbed_value, count = scrub_response(value)
            scrubbed_dict[key] = scrubbed_value
            total += count
        return scrubbed_dict, total

    # List: recursivo em cada item
    if isinstance(payload, list):
        total = 0
        scrubbed_list: list[Any] = []
        for item in payload:
            scrubbed_item, count = scrub_response(item)
            scrubbed_list.append(scrubbed_item)
            total += count
        return scrubbed_list, total

    # Tipos primitivos (int, float, bool, None): retorna como veio
    return payload, 0


def scrub_response_safe(payload: Any) -> Any:
    """Versao simplificada que retorna apenas o payload scrubbed (sem count).

    Use quando so importa o payload final (e nao o total de PII removidas).
    LGPD-friendly default para wrappers HTTP, error handlers, etc.
    """
    scrubbed, _ = scrub_response(payload)
    return scrubbed


__all__ = ["scrub_response", "scrub_response_safe"]
