"""G8.06.T1 — Otimização de índices para tabelas de alta cardinalidade.

Tabelas alvo:
- `atendimentos`: queries por cliente_id, status, data_criacao
- `protocolos`: queries por numero, cliente_id, status, data_criacao
- `audit_log`: queries por actor_id, action, resource, created_at (LGPD)

Indices compostos adicionados:
- atendimentos: (cliente_id, status, created_at DESC) — dashboard escrevente
- atendimentos: (status, created_at DESC) — fila atendimento
- protocolos: (numero) UNIQUE — ja existe mas vamos garantir
- protocolos: (cliente_id, status, created_at DESC) — historico cliente
- protocolos: (status, updated_at DESC) — SLA tracking
- audit_log: (actor_id, created_at DESC) — trilha por ator
- audit_log: (resource, action, created_at DESC) — analise por recurso
- audit_log: (action, created_at DESC) — relatorio ANPD

LGPD: indices em audit_log sao CRITICOS para Art.37 (relatorio de operacoes)
e Art.18 (acesso do titular). Sem indices, queries saem full-scan em
tabelas com milhoes de rows.

This module is SQL-only (no ORM mutation). Alembic migration consumes
the SQL output via `render_create_all_sql()`.

Modified by Gustavo Almeida — G8 Wave 32 A1.
"""

from __future__ import annotations



# Tabelas + indices compostos + motivo (LGPD/performance)
INDICES: list[dict[str, str]] = [
    # atendimentos
    {
        "tabela": "atendimentos",
        "nome": "ix_atendimentos_cliente_status_created",
        "colunas": "(cliente_id, status, created_at DESC)",
        "motivo": "Dashboard escrevente: histórico cliente por status",
        "tipo": "btree",
    },
    {
        "tabela": "atendimentos",
        "nome": "ix_atendimentos_status_created",
        "colunas": "(status, created_at DESC)",
        "motivo": "Fila atendimento: pending/aging por tempo",
        "tipo": "btree",
    },
    {
        "tabela": "atendimentos",
        "nome": "ix_atendimentos_canal_created",
        "colunas": "(canal, created_at DESC)",
        "motivo": "Métricas por canal (telegram/whatsapp/chatwoot)",
        "tipo": "btree",
    },
    # protocolos
    {
        "tabela": "protocolos",
        "nome": "ix_protocolos_numero_unique",
        "colunas": "(numero)",
        "motivo": "Lookup por número de protocolo (UNIQUE já existe, redundante para garantir)",
        "tipo": "btree",
        "unique": "UNIQUE",
    },
    {
        "tabela": "protocolos",
        "nome": "ix_protocolos_cliente_status_updated",
        "colunas": "(cliente_id, status, updated_at DESC)",
        "motivo": "Histórico cliente ordenado por última atualização",
        "tipo": "btree",
    },
    {
        "tabela": "protocolos",
        "nome": "ix_protocolos_status_updated",
        "colunas": "(status, updated_at DESC)",
        "motivo": "SLA tracking: aging por status",
        "tipo": "btree",
    },
    {
        "tabela": "protocolos",
        "nome": "ix_protocolos_escrevente_status",
        "colunas": "(escrevente_id, status) WHERE escrevente_id IS NOT NULL",
        "motivo": "Fila escrevente: protocolos atribuídos",
        "tipo": "btree",
    },
    # audit_log (LGPD Art.37 + Art.18)
    {
        "tabela": "audit_log",
        "nome": "ix_audit_log_actor_created",
        "colunas": "(actor_id, created_at DESC)",
        "motivo": "Trilha por ator (LGPD Art.37)",
        "tipo": "btree",
    },
    {
        "tabela": "audit_log",
        "nome": "ix_audit_log_resource_action_created",
        "colunas": "(resource, action, created_at DESC)",
        "motivo": "Análise por recurso + ação (compliance)",
        "tipo": "btree",
    },
    {
        "tabela": "audit_log",
        "nome": "ix_audit_log_action_created",
        "colunas": "(action, created_at DESC)",
        "motivo": "Relatório ANPD: contagem por ação",
        "tipo": "btree",
    },
    {
        "tabela": "audit_log",
        "nome": "ix_audit_log_created_brin",
        "colunas": "(created_at)",
        "motivo": "BRIN: append-only time-series, ocupa 1KB vs btree 8MB para 1M rows",
        "tipo": "brin",
    },
    {
        "tabela": "audit_log",
        "nome": "ix_audit_log_payload_gin",
        "colunas": "(payload)",
        "motivo": "GIN: busca JSONB por chave (LGPD Art.18 acesso do titular)",
        "tipo": "gin",
    },
]


def render_create_index_sql(idx: dict[str, str]) -> str:
    """Renderiza CREATE INDEX para um índice."""
    unique = idx.get("unique", "").strip()
    tipo = idx["tipo"].upper()
    # Garante 1 único espaço entre CREATE e INDEX (evita 'CREATE  INDEX')
    keyword = f"CREATE {unique} INDEX".strip() if unique else "CREATE INDEX"
    sql = (
        f"{keyword} IF NOT EXISTS {idx['nome']}\n"
        f"    ON {idx['tabela']} USING {tipo} {idx['colunas']};"
    )
    return sql


def render_drop_index_sql(idx: dict[str, str]) -> str:
    """Renderiza DROP INDEX (rollback)."""
    return f"DROP INDEX IF EXISTS {idx['nome']};"


def render_create_all_sql() -> str:
    """Renderiza SQL completo para criar todos os índices.

    Idempotente: usa IF NOT EXISTS. Seguro rodar múltiplas vezes.
    """
    header = (
        "-- G8.06.T1 — Otimização de índices (LGPD Art.18 + Art.37)\n"
        "-- Auto-gerado por scripts/db_index_optimizer.py\n"
        "-- Apply: make -C backend alembic-up (migration consome este SQL)\n"
        "-- Rollback: ver render_drop_all_sql()\n\n"
    )
    body = "\n\n".join(render_create_index_sql(idx) for idx in INDICES)
    footer = (
        f"\n\n-- Total: {len(INDICES)} índices\n"
        "-- Validate: EXPLAIN ANALYZE em queries dashboard devem mostrar Index Scan\n"
    )
    return header + body + footer


def render_drop_all_sql() -> str:
    """Renderiza SQL de rollback."""
    return "\n".join(render_drop_index_sql(idx) for idx in INDICES)


def get_indices_by_table() -> dict[str, list[dict[str, str]]]:
    """Agrupa índices por tabela para análise."""
    grouped: dict[str, list[dict[str, str]]] = {}
    for idx in INDICES:
        grouped.setdefault(idx["tabela"], []).append(idx)
    return grouped


def estimate_size_savings() -> dict[str, str]:
    """Estimativa de economia de espaço (BRIN vs BTREE).

    Base: 1M rows de audit_log
    - BTREE index em (created_at) ≈ 8 MB
    - BRIN index em (created_at) ≈ 1 KB (range blocks)
    """
    return {
        "btree_vs_brin": "BRIN ~8000x menor que BTREE para append-only timestamps",
        "recomendacao": (
            "audit_log.created_at: BRIN (append-only, queries por range).\n"
            "audit_log.payload: GIN (busca JSONB).\n"
            "Demais: BTREE composto."
        ),
        "migration_strategy": (
            "CREATE INDEX CONCURRENTLY em prod (zero lock).\n"
            "Em dev: CREATE INDEX (sem CONCURRENTLY é OK, lock curto).\n"
            "Validar com: SELECT pg_indexes_size('audit_log');"
        ),
    }


__all__ = [
    "INDICES",
    "estimate_size_savings",
    "get_indices_by_table",
    "render_create_all_sql",
    "render_create_index_sql",
    "render_drop_all_sql",
    "render_drop_index_sql",
]


def _cli() -> None:
    """CLI: imprime SQL gerado."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="G8.06.T1 DB Index Optimizer")
    parser.add_argument("--create", action="store_true", help="Print CREATE INDEX SQL")
    parser.add_argument("--drop", action="store_true", help="Print DROP INDEX SQL")
    parser.add_argument("--summary", action="store_true", help="Print summary by table")
    parser.add_argument("--estimate", action="store_true", help="Print size estimates")
    args = parser.parse_args()
    if args.create:
        print(render_create_all_sql())
    elif args.drop:
        print(render_drop_all_sql())
    elif args.summary:
        grouped = get_indices_by_table()
        for table, idxs in grouped.items():
            print(f"\n{table} ({len(idxs)} indices):")
            for idx in idxs:
                print(f"  - {idx['nome']}: {idx['motivo']}")
        print(f"\nTotal: {len(INDICES)} indices across {len(grouped)} tables")
    elif args.estimate:
        import json

        print(json.dumps(estimate_size_savings(), indent=2))
    else:
        parser.print_help(sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    _cli()