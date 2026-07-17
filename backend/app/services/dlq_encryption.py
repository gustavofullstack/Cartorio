"""G8.08.T2 — Encryption-at-rest para DLQ payload (LGPD Art.46).

Camada adicional sobre `app.services.dlq` que criptografa o payload antes de
persistir no DB e descriptografa ao ler. Usa `app.services.crypto.encrypt_pii`
(Fernet AES-128-CBC + HMAC, chave derivada de AUDIT_HMAC_KEY).

API:
- encrypt_dlq_payload(payload: dict, key: str) -> dict
    Retorna dict pronto para DB com payload criptografado:
    {"_encrypted": True, "ciphertext": "...", "v": 1}
- decrypt_dlq_payload(stored: dict, key: str) -> dict
    Inverso. Levanta ValueError se payload nao esta criptografado
    ou ciphertext invalido.
- is_encrypted_payload(stored: dict) -> bool
    Helper para checar se um payload ja foi criptografado.

Decisao:
- Mantemos `dlq.enqueue()` original sem criptografia (retrocompat).
- `dlq_enqueue_encrypted()` eh a versao LGPD-secure.
- Wrapper em `dlq_crypto.py` decide automaticamente se payload precisa
  ser criptografado (heuristica: dict com campos PII provaveis).

LGPD Art. 46: "medidas tecnicas e administrativas aptas a proteger os dados
pessoais de acessos nao autorizados e de situacoes acidentais ou ilicitas
de destruicao, perda, alteracao, comunicacao ou qualquer forma de tratamento
inadequado ou excessivo".

Modified by Gustavo Almeida — G8 Wave 30 A2.
"""

from __future__ import annotations

import json
from typing import Any

from app.services.crypto import decrypt_pii, encrypt_pii

# Marker interno para detectar payloads criptografados.
_ENCRYPTED_MARKER = "_encrypted"
_VERSION_KEY = "v"
_VERSION = 1

# Campos provaveis de conter PII (LGPD). Se payload tiver qualquer um,
# criptografa automaticamente.
_PII_HEURISTIC_FIELDS = frozenset(
    {
        "cpf",
        "rg",
        "cnpj",
        "nome",
        "name",
        "email",
        "telefone",
        "phone",
        "endereco",
        "address",
        "data_nascimento",
        "birth_date",
        "passaporte",
        "passport",
        "cnh",
    }
)


def is_encrypted_payload(stored: dict[str, Any]) -> bool:
    """Checa se dict já é um envelope criptografado."""
    return (
        isinstance(stored, dict)
        and stored.get(_ENCRYPTED_MARKER) is True
        and "ciphertext" in stored
        and _VERSION_KEY in stored
    )


def encrypt_dlq_payload(payload: dict[str, Any], key: str) -> dict[str, Any]:
    """Criptografa payload dict e retorna envelope.

    Args:
        payload: dict JSON-serializável (deve estar scrubbed de segredos,
            mas pode conter PII que será protegida por criptografia).
        key: chave mestra (em prod: AUDIT_HMAC_KEY).

    Returns:
        Envelope dict com marker + ciphertext + versão.
        Pronto para ser passado a `dlq.enqueue()`.
    """
    if is_encrypted_payload(payload):
        # Idempotência: já criptografado
        return payload
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    ciphertext = encrypt_pii(serialized, key)
    return {
        _ENCRYPTED_MARKER: True,
        _VERSION_KEY: _VERSION,
        "ciphertext": ciphertext,
    }


def decrypt_dlq_payload(stored: dict[str, Any], key: str) -> dict[str, Any]:
    """Descriptografa envelope e retorna payload original.

    Args:
        stored: dict envelope (output de encrypt_dlq_payload) ou payload raw.
        key: chave mestra (mesma usada em encrypt).

    Returns:
        Payload original descriptografado.

    Raises:
        ValueError: se envelope inválido ou descriptografia falha.
    """
    if not is_encrypted_payload(stored):
        # Backward compat: payload raw (não criptografado)
        if isinstance(stored, dict):
            return stored
        raise ValueError(f"Invalid DLQ payload envelope: {type(stored).__name__}")
    try:
        plaintext = decrypt_pii(stored["ciphertext"], key)
        return json.loads(plaintext)
    except Exception as exc:
        raise ValueError(f"Failed to decrypt DLQ payload: {exc}") from exc


def should_encrypt_payload(payload: dict[str, Any]) -> bool:
    """Heurística: True se payload provavelmente contém PII.

    Usado por wrappers que decidem automaticamente se devem criptografar
    antes de chamar `dlq.enqueue()`.
    """
    if not isinstance(payload, dict):
        return False
    if is_encrypted_payload(payload):
        return False  # já criptografado, não duplicar
    # Checagem superficial: intersect keys
    payload_keys_lower = {str(k).lower() for k in payload.keys()}
    # Tenta também nested dict (1 nível)
    nested_keys: set[str] = set()
    for v in payload.values():
        if isinstance(v, dict):
            nested_keys.update(str(k).lower() for k in v.keys())
    all_keys = payload_keys_lower | nested_keys
    return bool(all_keys & _PII_HEURISTIC_FIELDS)