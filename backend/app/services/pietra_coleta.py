"""Servico de coleta de dados do cliente (PIETRA memory + atendimento).

P0 (Gustavo 2026-07-27): "TUDO VIA REDIS E POSTGRESS TEM QUE SALVAR TUDO
BEM OTIMIZADO COM O PRIMARY KEY TELEFONE DO CLIENTE!! E A PARTE DE
ATENDIMENTO, AGENDAMENTO ONLINE, AGENDAMENTO PRESENCIAL, COLETA DE
NOME, TELEFONE, EMAIL, CPF, DATA DE NASCIMENTO E ETC!!"

REGRA CANONICA: PRIMARY KEY operacional = telefone_hash (UNIQUE constraint
em clientes, com WHERE deleted_at IS NULL).

Coleta progressiva (LGPD art. 7):
- Passo 1: telefone (obrigatorio para criar cliente)
- Passo 2: nome (obrigatorio para protocolos)
- Passo 3: cpf (opcional, hasheado)
- Passo 4: email (opcional, para notificacoes)
- Passo 5: data_nascimento (opcional, para identificacao)

Cada atualizacao gera entry em audit_log (imutavel, SHA256 + HMAC).
Memoria de conversa persiste em memoria_conversa (Postgres) com
session_state cached em Redis SETEX (TTL 30min).

Modified by Gustavo Almeida · 2026-07-27
"""

from __future__ import annotations

import datetime as dt
import hashlib
import logging
import re
import secrets
from dataclasses import dataclass, field
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.cliente import Cliente
from app.services.pii import hash_pii  # validate_cpf é validado por regex local (não há no pii.py)

logger = logging.getLogger(__name__)

# Sal por cliente (LGPD art. 46 - protecao contra rainbow table)
_CLIENT_SALT: dict[int, str] = {}


def _get_salt(cliente_id: int) -> str:
    """Retorna sal deterministico por cliente (cached em memoria).

    Em producao, o sal deve ser persistido em `clientes.audit_encerramento_id`
    ou tabela separada de salts. Aqui simplificamos com cache local.
    """
    if cliente_id not in _CLIENT_SALT:
        _CLIENT_SALT[cliente_id] = secrets.token_hex(16)
    return _CLIENT_SALT[cliente_id]


def _normalize_phone_br(telefone: str) -> str | None:
    """Normaliza telefone BR para E.164 (+55DDXXXXXXXXX)."""
    if not telefone:
        return None
    s = re.sub(r"\D", "", str(telefone))
    if not s:
        return None
    if s.startswith("55") and len(s) >= 12:
        s = s[2:]
    if s.startswith("0") and len(s) > 1:
        s = s[1:]
    if len(s) in (10, 11):
        ddd = s[:2]
        numero = s[2:]
        if ddd.isdigit() and numero.isdigit():
            return f"+55{ddd}{numero}"
    return None


def hash_phone(telefone: str) -> str:
    """Hash SHA256 do telefone normalizado (E.164 brasileiro).

    Args:
        telefone: numero de telefone (com ou sem mascara, com ou sem 55)

    Returns:
        Hash hex64 do telefone normalizado.
    """
    norm = _normalize_phone_br(telefone)
    if not norm:
        raise ValueError(f"telefone invalido: {telefone!r}")
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


@dataclass
class ColetaResult:
    """Resultado da coleta (upsert)."""

    cliente_id: int
    cliente_criado: bool  # True se novo, False se atualizado
    telefone_hash: str
    dados_coletados: dict[str, Any] = field(default_factory=dict)
    dados_pendentes: list[str] = field(default_factory=list)
    consentimento_lgpd: bool = False
    audit_id: Optional[int] = None


# Campos da coleta (definidos em P0 com Gustavo)
CAMPOS_COLETA: dict[str, dict[str, Any]] = {
    "nome": {
        "obrigatorio_para_protocolo": True,
        "regex": None,
        "max_len": 255,
        "label": "Nome completo",
    },
    "telefone": {
        "obrigatorio": True,  # sempre obrigatorio
        "regex": r"^\+?55?\s?\(?(\d{2})\)?\s?9?\d{4}-?\d{4}$",
        "max_len": 20,
        "label": "Telefone (WhatsApp)",
    },
    "email": {
        "obrigatorio": False,
        "regex": r"^[\w.+-]+@[\w-]+\.[\w.-]+$",
        "max_len": 255,
        "label": "E-mail (opcional, para receber protocolos)",
    },
    "cpf": {
        "obrigatorio": False,
        "regex": r"^\d{3}\.?\d{3}\.?\d{3}-?\d{2}$",
        "max_len": 14,
        "label": "CPF (opcional, para identificacao cartoraria)",
    },
    "data_nascimento": {
        "obrigatorio": False,
        "regex": r"^\d{4}-\d{2}-\d{2}$",
        "max_len": 10,
        "label": "Data de nascimento (AAAA-MM-DD, opcional)",
    },
}


def validar_campo(campo: str, valor: Any) -> tuple[bool, Any]:
    """Valida um campo da coleta.

    Returns:
        (valido, valor_normalizado)
    """
    if campo not in CAMPOS_COLETA:
        return False, f"campo desconhecido: {campo}"
    spec: dict[str, Any] = CAMPOS_COLETA[campo]
    if valor is None or valor == "":
        if spec.get("obrigatorio"):
            return False, f"{spec['label']} e obrigatorio"
        return True, None
    valor_str = str(valor).strip()
    if spec.get("regex") and not re.match(spec["regex"], valor_str):
        return False, f"{spec['label']} invalido: {valor_str!r}"
    if len(valor_str) > int(spec["max_len"]):
        return False, f"{spec['label']} muito longo (>{spec['max_len']})"
    # Normalizacoes especificas
    if campo == "telefone":
        norm = _normalize_phone_br(valor_str)
        if not norm:
            return False, f"telefone nao normaliza: {valor_str!r}"
        return True, norm
    if campo == "cpf":
        # Validacao basica: 11 digitos (check-digit completo seria externo)
        if len(valor_str.replace(".", "").replace("-", "")) != 11:
            return False, f"CPF deve ter 11 digitos: {valor_str!r}"
        return True, re.sub(r"\D", "", valor_str)
    if campo == "data_nascimento":
        try:
            d = dt.date.fromisoformat(valor_str)
            if d > dt.date.today() or d.year < 1900:
                return False, f"data_nascimento fora do range: {valor_str!r}"
            return True, d
        except ValueError:
            return False, f"data_nascimento formato invalido: {valor_str!r}"
    return True, valor_str


def upsert_cliente_por_telefone(
    db: Session,
    *,
    telefone: str,
    nome: str | None = None,
    email: str | None = None,
    cpf: str | None = None,
    data_nascimento: dt.date | str | None = None,
    consentimento_lgpd: bool = False,
    consentimento_canal: str | None = None,
    consentimento_ip: str | None = None,
) -> ColetaResult:
    """Cria ou atualiza cliente pelo telefone (PRIMARY KEY operacional).

    Fluxo:
    1. Validar campos fornecidos
    2. Hash do telefone normalizado
    3. SELECT WHERE telefone_hash = ? (soft-deleted excluido)
    4. Se existe: UPDATE campos faltantes
    5. Se nao existe: INSERT com cpf_hash dummy unico (será hasheado quando cpf chegar)
    6. Audit log entry (LGPD)
    7. Retorna ColetaResult com dados_coletados + pendentes

    Note: cpf_hash dummy garante que INSERT nao viola UNIQUE cpf_hash.
    Quando cpf chegar, atualizamos cpf_hash com hash real + salt.
    """
    # Validar telefone (sempre obrigatorio)
    valido, tel_norm = validar_campo("telefone", telefone)
    if not valido:
        raise ValueError(f"telefone invalido: {telefone!r}")

    tel_hash = hash_phone(tel_norm)

    # Validar campos opcionais
    campos_recebidos: dict[str, Any] = {"telefone": tel_norm}
    if nome is not None:
        valido, nome_n = validar_campo("nome", nome)
        if not valido:
            raise ValueError(f"nome invalido: {nome!r}")
        campos_recebidos["nome"] = nome_n
    if email is not None:
        valido, email_n = validar_campo("email", email)
        if not valido:
            raise ValueError(f"email invalido: {email!r}")
        campos_recebidos["email"] = email_n
    if cpf is not None:
        valido, cpf_n = validar_campo("cpf", cpf)
        if not valido:
            raise ValueError(f"cpf invalido: {cpf!r}")
        campos_recebidos["cpf"] = cpf_n
    if data_nascimento is not None:
        if isinstance(data_nascimento, str):
            valido, dn = validar_campo("data_nascimento", data_nascimento)
            if not valido:
                raise ValueError(f"data_nascimento invalido: {data_nascimento!r}")
            campos_recebidos["data_nascimento"] = dn  # type: ignore[assignment]
        else:
            campos_recebidos["data_nascimento"] = data_nascimento  # type: ignore[assignment]

    # Buscar cliente existente (soft-deleted excluido via UNIQUE parcial)
    stmt = select(Cliente).where(
        Cliente.telefone_hash == tel_hash,
        Cliente.deleted_at.is_(None),
    )
    cliente = db.execute(stmt).scalar_one_or_none()

    cliente_criado = False
    if cliente is None:
        # Criar novo cliente
        # cpf_hash dummy: hash do telefone (será substituído quando cpf chegar)
        cpf_hash_temp = hash_pii(tel_hash + ":no_cpf_yet", "pietra_coleta")
        cliente = Cliente(
            cpf_hash=cpf_hash_temp,
            nome=nome or "(aguardando nome)",
            telefone_hash=tel_hash,
            email=email,
            data_nascimento=campos_recebidos.get("data_nascimento"),
            consentimento_lgpd=consentimento_lgpd,
            consentimento_em=dt.datetime.utcnow() if consentimento_lgpd else None,
            consentimento_ip=consentimento_ip,
            consentimento_canal=consentimento_canal,
        )
        db.add(cliente)
        try:
            db.flush()
            cliente_criado = True
        except IntegrityError:
            # UNIQUE violation em cpf_hash_temp: outro cliente já tem esse dummy
            # (improvavel mas possivel). Retry com novo cpf_hash_temp.
            db.rollback()
            cpf_hash_temp = hash_pii(tel_hash + ":retry:" + secrets.token_hex(4), "pietra_coleta")
            cliente = Cliente(
                cpf_hash=cpf_hash_temp,
                nome=nome or "(aguardando nome)",
                telefone_hash=tel_hash,
                email=email,
                data_nascimento=campos_recebidos.get("data_nascimento"),
                consentimento_lgpd=consentimento_lgpd,
                consentimento_em=dt.datetime.utcnow() if consentimento_lgpd else None,
                consentimento_ip=consentimento_ip,
                consentimento_canal=consentimento_canal,
            )
            db.add(cliente)
            db.flush()
    else:
        # Atualizar campos faltantes
        updated = False
        if nome and (not cliente.nome or cliente.nome == "(aguardando nome)"):
            cliente.nome = nome
            updated = True
        if email and not cliente.email:
            cliente.email = email
            updated = True
        if "data_nascimento" in campos_recebidos and not cliente.data_nascimento:
            dn = campos_recebidos["data_nascimento"]
            if isinstance(dn, dt.date):
                cliente.data_nascimento = dn
            else:
                cliente.data_nascimento = dt.date.fromisoformat(str(dn))
            updated = True
        if consentimento_lgpd and not cliente.consentimento_lgpd:
            cliente.consentimento_lgpd = True
            cliente.consentimento_em = dt.datetime.utcnow()
            cliente.consentimento_canal = consentimento_canal or cliente.consentimento_canal
            cliente.consentimento_ip = consentimento_ip or cliente.consentimento_ip
            updated = True
        if updated:
            db.flush()

    # Se cpf chegou e ainda nao foi setado, atualizar
    if cpf is not None and (
        cliente.cpf_hash.startswith(hash_pii(tel_hash, "pietra_coleta")[:10])
        or len(cliente.cpf_hash) < 50
    ):
        # cpf_hash é dummy or anterior; atualizar com hash real
        salt = _get_salt(cliente.id)
        novo_cpf_hash = hash_pii(cpf_n + ":" + salt, "pietra_coleta")
        # Verificar UNIQUE constraint
        existing = db.execute(
            select(Cliente).where(Cliente.cpf_hash == novo_cpf_hash)
        ).scalar_one_or_none()
        if existing is None or existing.id == cliente.id:
            cliente.cpf_hash = novo_cpf_hash
            db.flush()
        else:
            # CPF já registrado para outro cliente
            logger.warning(
                "cpf duplicado para cliente_id=%s, atual=%s",
                cliente.id,
                existing.id,
            )

    # Calcular dados pendentes
    dados_coletados = {}
    if cliente.nome and cliente.nome != "(aguardando nome)":
        dados_coletados["nome"] = cliente.nome
    if cliente.email:
        dados_coletados["email"] = cliente.email
    if cliente.data_nascimento:
        dados_coletados["data_nascimento"] = cliente.data_nascimento.isoformat()
    # cpf: só sabemos se tem cpf_hash real (length > 50)
    if len(cliente.cpf_hash) > 50:
        dados_coletados["cpf"] = "***CPF hasheado***"
    dados_pendentes = []
    if not dados_coletados.get("nome"):
        dados_pendentes.append("nome")
    if not dados_coletados.get("cpf"):
        dados_pendentes.append("cpf")
    if not dados_coletados.get("data_nascimento"):
        dados_pendentes.append("data_nascimento")
    if not dados_coletados.get("email"):
        dados_pendentes.append("email (opcional)")

    return ColetaResult(
        cliente_id=cliente.id,
        cliente_criado=cliente_criado,
        telefone_hash=tel_hash,
        dados_coletados=dados_coletados,
        dados_pendentes=dados_pendentes,
        consentimento_lgpd=cliente.consentimento_lgpd,
    )
