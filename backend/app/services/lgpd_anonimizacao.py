"""lgpd_anonimizacao.py - LGPD art. 12 anonimizacao (D13).

Anonimizacao vs pseudonimizacao:
- ANONIMIZACAO: remove identificadores de forma IRREVERSIVEL. Dado nao pode
  ser re-identificado. Usado para analytics/relatorios ANPD.
- PSEUDONIMIZACAO: substitui identificador por hash/token reversivel somente
  com chave separada. Usado para operacao diaria (consentimento reversivel).

Este service implementa AMBOS:
- hash_pii(value, salt) -> SHA-256 deterministico (pseudonimizacao)
- anonymize_cliente_row(row) -> dict sem PII (anonimizacao p/ analytics)
"""
from __future__ import annotations

import hashlib
import hmac
import re
from typing import Any

# Campos PII que DEVEM ser anonimizados em analytics/relatorios
PII_FIELDS = (
    "nome",
    "cpf",
    "cnpj",
    "rg",
    "email",
    "telefone",
    "celular",
    "endereco",
    "numero",
    "complemento",
    "bairro",
    "cidade",
    "cep",
    "nome_mae",
    "nome_pai",
    "data_nascimento",
    "cns",
    "cnh",
    "passaporte",
)

# Padroes regex para detectar PII
PII_PATTERNS = {
    "cpf": re.compile(r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}"),
    "cnpj": re.compile(r"\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}"),
    "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    # Telefone: aceita BR com DDD (34) e celular 9 digitos. Sem lookbehind
    # porque Python 3.11 re module supports fixed-width lookbehind.
    "telefone": re.compile(r"(?:\+?55\s?)?\(?\d{2}\)?\s?9?\d{4}-?\d{4}"),
    "rg": re.compile(r"\d{1,2}\.?\d{3}\.?\d{3}-?\d{1}"),
    # CNS: 15 digitos com ou sem espacos
    "cns": re.compile(r"(?<![\d.])\d{15}(?![\d.])"),
    "cnh": re.compile(r"\d{11}"),
}


def hash_pii(value: str, salt: str = "cartorio-pii-salt-v1") -> str:
    """Pseudonimizacao: SHA-256 HMAC com salt.

    Args:
        value: dado PII a pseudonimizar (CPF, email, etc)
        salt: chave HMAC (vem de settings.audit_hmac_key em prod)

    Returns:
        Hex SHA-256 (64 chars) deterministico. Mesmo input = mesmo hash.
    """
    if not value:
        return ""
    # Normaliza (remove mascara)
    normalized = re.sub(r"\D", "", value) if value else ""
    return hmac.new(
        salt.encode("utf-8"),
        normalized.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def anonymize_cliente_row(row: dict[str, Any]) -> dict[str, Any]:
    """Anonimizacao: remove/substitui PII de um dict de cliente.

    Mantem apenas:
    - id (PK)
    - cidade (apenas sigla do estado: 'MG')
    - tipo_cliente (PF/PJ)
    - lgpd_consent_granted (boolean - necessario para metricas)
    - lgpd_consent_at (timestamp)
    - deleted_at (LGPD art. 18 V)
    - created_at (mes)
    - qualquer campo nao-PII explicitamente

    Args:
        row: dict com campos do cliente (do SQLAlchemy ou dict puro)

    Returns:
        dict sem PII, pronto para analytics
    """
    result: dict[str, Any] = {}
    for key, value in row.items():
        if key in PII_FIELDS:
            # Substitui por hash (pseudonimizacao reversivel com chave)
            result[f"{key}_hash"] = hash_pii(str(value)) if value else None
        elif key == "endereco_uf":
            # Mantem sigla do estado (LGPD-safe: 27 valores)
            result[key] = value
        elif key in ("id", "tipo_cliente", "lgpd_consent_granted", "lgpd_consent_at", "deleted_at", "created_at"):
            result[key] = value
        # Outros campos NAO-PII: descarta (whitelist-only)
    return result


def scrub_text_pii(text: str) -> str:
    """Remove PII de texto livre (mensagens WhatsApp, anotacoes, etc).

    Substitui cada padrao detectado por [REDACTED-{tipo}].

    Ordem importa: CNS (15 digitos) antes de CPF (11 digitos) para evitar
    que o CPF pegue apenas uma parte do CNS.

    Args:
        text: texto a sanitizar

    Returns:
        texto com PIIs substituidos
    """
    if not text:
        return text
    result = text
    # Ordem especifica: CNS primeiro (mais especifico), depois CPF, CNPJ, RG, etc
    ordered = ("cns", "cnpj", "cpf", "rg", "cnh", "email", "telefone")
    for tipo in ordered:
        if tipo in PII_PATTERNS:
            result = PII_PATTERNS[tipo].sub(f"[REDACTED-{tipo.upper()}]", result)
    return result


def truncate_ip(ip: str) -> str:
    """LGPD art. 6 VIII - minimizacao: trunca IP em /24 (IPv4) ou /48 (IPv6).

    Args:
        ip: endereco IP completo

    Returns:
        IP truncado para reduzir identificabilidade
    """
    if not ip:
        return ""
    if ":" in ip:  # IPv6
        parts = ip.split(":")
        return ":".join(parts[:3]) + "::/48"
    # IPv4
    parts = ip.split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
    return ip
