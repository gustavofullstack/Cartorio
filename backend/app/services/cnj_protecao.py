"""G9.S4.T9 (E3.08) — Relatório de proteção de dados a partir do audit log.

Serviço PURO (sem DB, sem I/O): recebe uma lista de audit entries (dicts,
no shape do AuditLog serializado — ex.: saída do massive-dump CNJ ou de um
SELECT read-only) e agrega um relatório de proteção de dados no formato
CNJ-shaped (dict JSON-serializável) + renderização markdown.

Agregações:
  - total de acessos e quebra por `action`;
  - exportações (ações de export/dump/download CNJ/LGPD);
  - mascaramentos PII (heurística documentada: action de scrub/mask ou
    payload contendo marcadores `[*_REDACTED]` / `redaction_count`);
  - falhas de autenticação/autorização (action auth.* fail/deny ou
    payload com status 401/403);
  - janela temporal (min/max de `timestamp`).

Entradas malformadas (não-dict, action ausente/não-string, timestamp
inválido) são TOLERADAS: contabilizadas em `entradas_malformadas` e
ignoradas das agregações — relatório de proteção não pode derrubar o
pipeline por causa de uma linha ruim.

Classificação do artefato: RESTRICTED_AGGREGATED — somente contagens e
janelas; NUNCA serializa actor_id, payload bruto, IP ou qualquer dado
pessoal das entradas de origem.
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import UTC, datetime
from typing import Any

SCHEMA_VERSION = "cnj.protecao_dados/v1"
DATA_CLASSIFICATION = "RESTRICTED_AGGREGATED"

# Ações que caracterizam exportação de dados (pacote CNJ, dump, download).
_EXPORT_ACTION_RE = re.compile(
    r"(^|\.)(export|exportacao|dump|download)(\.|$)|massive_dump|cnj\.export",
    re.IGNORECASE,
)

# Ações que caracterizam mascaramento/scrub de PII.
_MASK_ACTION_RE = re.compile(r"(pii|scrub|mask|redact|anonimiz)", re.IGNORECASE)

# Marcador de redaction dentro de payload serializado (ex.: [CPF_REDACTED]).
_REDACTED_MARKER_RE = re.compile(r"\[[A-Z0-9_]+_REDACTED\]")

# Ações que caracterizam falha de autenticação/autorização.
_AUTH_FAIL_ACTION_RE = re.compile(
    r"auth\w*[._-]?(fail|denied|deny|reject|unauthorized|forbidden)|"
    r"(fail|denied|reject)\w*[._-]?auth",
    re.IGNORECASE,
)


def _parse_timestamp(value: Any) -> datetime | None:
    """Tolera datetime, str ISO-8601 (com/sem 'Z') e None. Inválido -> None."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return None


def _is_export(action: str) -> bool:
    return bool(_EXPORT_ACTION_RE.search(action))


def _is_masking(action: str, payload: Any) -> bool:
    if _MASK_ACTION_RE.search(action):
        return True
    if isinstance(payload, dict):
        if "redaction_count" in payload or "pii_scrubbed" in payload:
            return True
        try:
            blob = repr(payload)
        except Exception:  # noqa: BLE001 — payload exótico não derruba
            return False
        return bool(_REDACTED_MARKER_RE.search(blob))
    return False


def _is_auth_failure(action: str, payload: Any) -> bool:
    if _AUTH_FAIL_ACTION_RE.search(action):
        return True
    if isinstance(payload, dict):
        status = payload.get("status") or payload.get("status_code")
        if status in (401, 403):
            return True
    return False


def build_protecao_report(
    entries: list[dict[str, Any]],
    *,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    """Agrega audit entries em relatório CNJ-shaped de proteção de dados.

    Args:
        entries: lista de dicts no shape AuditLog serializado. Malformadas
                 são toleradas e contabilizadas à parte.
        generated_at: carimbo de geração (default: agora, UTC).

    Returns:
        Dict JSON-serializável, somente com agregados (minimização LGPD).
    """
    gerado_em = generated_at or datetime.now(UTC)
    if gerado_em.tzinfo is None:
        gerado_em = gerado_em.replace(tzinfo=UTC)

    por_acao: Counter[str] = Counter()
    exportacoes_por_acao: Counter[str] = Counter()
    total = 0
    exportacoes = 0
    mascaramentos = 0
    falhas_auth = 0
    malformadas = 0
    inicio: datetime | None = None
    fim: datetime | None = None

    for entry in entries:
        if not isinstance(entry, dict):
            malformadas += 1
            continue
        action = entry.get("action")
        if not isinstance(action, str) or not action:
            malformadas += 1
            continue

        total += 1
        por_acao[action] += 1
        payload = entry.get("payload")

        if _is_export(action):
            exportacoes += 1
            exportacoes_por_acao[action] += 1
        if _is_masking(action, payload):
            mascaramentos += 1
        if _is_auth_failure(action, payload):
            falhas_auth += 1

        ts = _parse_timestamp(entry.get("timestamp"))
        if ts is not None:
            inicio = ts if inicio is None else min(inicio, ts)
            fim = ts if fim is None else max(fim, ts)

    return {
        "schema": SCHEMA_VERSION,
        "data_classification": DATA_CLASSIFICATION,
        "gerado_em": gerado_em.isoformat(),
        "fonte": "audit_log_read_only",
        "totais": {
            "acessos": total,
            "exportacoes": exportacoes,
            "mascaramentos": mascaramentos,
            "falhas_auth": falhas_auth,
            "entradas_malformadas": malformadas,
        },
        "acessos_por_acao": dict(sorted(por_acao.items(), key=lambda kv: (-kv[1], kv[0]))),
        "exportacoes_por_acao": dict(
            sorted(exportacoes_por_acao.items(), key=lambda kv: (-kv[1], kv[0]))
        ),
        "janela_temporal": {
            "inicio": inicio.isoformat() if inicio else None,
            "fim": fim.isoformat() if fim else None,
        },
        "minimizacao": {
            "contem_dados_pessoais": False,
            "somente_agregados": True,
        },
    }


def render_protecao_markdown(report: dict[str, Any]) -> str:
    """Renderiza o relatório CNJ-shaped em markdown legível para o DPO."""
    totais = report["totais"]
    janela = report["janela_temporal"]
    linhas = [
        "# Relatório de Proteção de Dados — Audit Log (CNJ)",
        "",
        f"- Schema: `{report['schema']}`",
        f"- Classificação: **{report['data_classification']}**",
        f"- Gerado em: {report['gerado_em']}",
        f"- Fonte: {report['fonte']}",
        "",
        "## Janela temporal",
        "",
        f"- Início: {janela['inicio'] or '—'}",
        f"- Fim: {janela['fim'] or '—'}",
        "",
        "## Totais",
        "",
        "| Métrica | Valor |",
        "| --- | ---: |",
        f"| Acessos registrados | {totais['acessos']} |",
        f"| Exportações | {totais['exportacoes']} |",
        f"| Mascaramentos PII | {totais['mascaramentos']} |",
        f"| Falhas de autenticação/autorização | {totais['falhas_auth']} |",
        f"| Entradas malformadas toleradas | {totais['entradas_malformadas']} |",
        "",
        "## Acessos por ação",
        "",
        "| Ação | Total |",
        "| --- | ---: |",
    ]
    for acao, qtd in report["acessos_por_acao"].items():
        linhas.append(f"| `{acao}` | {qtd} |")
    if not report["acessos_por_acao"]:
        linhas.append("| _(nenhuma entrada válida)_ | 0 |")
    linhas += [
        "",
        "## Exportações por ação",
        "",
        "| Ação | Total |",
        "| --- | ---: |",
    ]
    for acao, qtd in report["exportacoes_por_acao"].items():
        linhas.append(f"| `{acao}` | {qtd} |")
    if not report["exportacoes_por_acao"]:
        linhas.append("| _(nenhuma exportação no período)_ | 0 |")
    linhas += [
        "",
        "---",
        "Relatório agregado, sem dados pessoais (LGPD art. 6º, XI — minimização).",
    ]
    return "\n".join(linhas) + "\n"


__all__ = [
    "DATA_CLASSIFICATION",
    "SCHEMA_VERSION",
    "build_protecao_report",
    "render_protecao_markdown",
]
