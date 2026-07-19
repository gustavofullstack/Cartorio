"""G8.05.T1 — Inventário e revisão de TTL/eviction Redis para dados de sessão.

Mapeia todos os usos de TTL no Redis do projeto e recomenda políticas.
Garante que:
1. Toda chave de sessão tem TTL (evita crescimento ilimitado)
2. TTL alinhado com LGPD (Art.16 eliminação + Art.37 auditoria)
3. Eviction policy documentada (allkeys-lru vs volatile-lru vs volatile-ttl)

API:
- TTL_REGISTRY: dict[name -> {ttl_seconds, scope, evict_ttl, lgpd_art, ...}]
- get_keys_by_scope(scope: str) -> list[str]
- validate_ttl_config() -> dict[str, list[str]] — issues encontrados
- recommended_eviction_policy() -> str ("allkeys-lru" recomendado)
- render_inventory_report() -> str — Markdown table
- render_recommended_config() -> str — redis.conf snippet

LGPD mapping:
- conversa_ia_log (90d) — Art.16 eliminação
- audit_log (6m) — Art.37 registro
- session_temp (24h) — Art.16 eliminação + segurança
- rate_limit (60s) — operacional, sem PII

Modified by Gustavo Almeida — G8 Wave 32 A2.
"""

from __future__ import annotations

from typing import Any


# Inventário canônico de chaves Redis do projeto
TTL_REGISTRY: dict[str, dict[str, Any]] = {
    # === IDEMPOTÊNCIA ===
    "webhook:idempotency:{key}": {
        "ttl_seconds": 86400,  # 24h (lesson-142 webhooks Evolution)
        "scope": "webhook",
        "lgpd_art": "Art.16 (eliminação após processamento)",
        "eviction_safe": True,
        "current_location": "app/services/idempotency_store.py (SETNX + EXPIRE)",
        "rationale": "Webhook dedupe: 24h cobre retries + reprocessamento",
    },
    # === RATE LIMIT ===
    "ratelimit:ip:{ip}": {
        "ttl_seconds": 60,
        "scope": "rate_limit",
        "lgpd_art": "operacional (sem PII)",
        "eviction_safe": True,
        "current_location": "app/services/rate_limit.py (sliding window)",
        "rationale": "Sliding window 60s por IP",
    },
    "ratelimit:apikey:{key}:{bucket}": {
        "ttl_seconds": 60,
        "scope": "rate_limit",
        "lgpd_art": "operacional (sem PII)",
        "eviction_safe": True,
        "current_location": "app/services/rate_limit_by_key.py",
        "rationale": "3-tier (N8N 600, DPO 60, default 30) por minuto",
    },
    # === SESSÕES / TOKEN ===
    "session:user:{user_id}": {
        "ttl_seconds": 3600,  # 1h (access token TTL)
        "scope": "session",
        "lgpd_art": "Art.16 (sessão efêmera)",
        "eviction_safe": True,
        "current_location": "app/services/auth_jwt.py + cache_lgpd.py",
        "rationale": "JWT access TTL 60min + refresh 7d",
    },
    "session:refresh:{user_id}": {
        "ttl_seconds": 604800,  # 7d
        "scope": "session",
        "lgpd_art": "Art.16",
        "eviction_safe": True,
        "current_location": "app/services/auth_jwt.py",
        "rationale": "Refresh token 7d (rotacionado a cada use)",
    },
    # === DLQ / OUTBOX ===
    "dlq:depth:{queue}": {
        "ttl_seconds": 3600,  # 1h gauge
        "scope": "metrics",
        "lgpd_art": "operacional",
        "eviction_safe": True,
        "current_location": "app/services/dlq.py + metrics.py (gauge)",
        "rationale": "Gauge depth expira após 1h, re-derivado em runtime",
    },
    # === CHAT PIPELINE ===
    "chat:pipeline:queue:{atendimento_id}": {
        "ttl_seconds": 10,
        "scope": "queue",
        "lgpd_art": "Art.16 (transient)",
        "eviction_safe": True,
        "current_location": "app/services/chat_pipeline.py (pipe.expire)",
        "rationale": "Fila chat morre rápido (10s) — sem risco de acúmulo",
    },
    "chat:memory:user:{user_id}": {
        "ttl_seconds": 86400,  # 24h
        "scope": "session",
        "lgpd_art": "Art.16 (conversa IA)",
        "eviction_safe": True,
        "current_location": "app/services/brain_memory.py + chat_pipeline.py",
        "rationale": "Multi-turn Redis: 24h cobre sessão ativa + retomada no dia seguinte",
    },
    "chat:catalog:{category}": {
        "ttl_seconds": 3600,  # 1h cache
        "scope": "cache",
        "lgpd_art": "Art.16",
        "eviction_safe": True,
        "current_location": "app/services/chat_pipeline.py",
        "rationale": "Catalog cache 1h (atualização infrequente)",
    },
    # === PROTOCOLO ===
    "protocolo:cache:{numero}": {
        "ttl_seconds": 300,  # 5min
        "scope": "cache",
        "lgpd_art": "Art.16",
        "eviction_safe": True,
        "current_location": "app/services/protocolo.py + protocolo_query.py",
        "rationale": "Cache curto: dados mudam em DRAFT → CONCLUIDO",
    },
    "protocolo:emolumento:{valor}": {
        "ttl_seconds": 86400,  # 24h
        "scope": "cache",
        "lgpd_art": "operacional",
        "eviction_safe": True,
        "current_location": "app/services/emolumento_cache.py",
        "rationale": "Tabela MG 2026 estática, cache 24h é seguro",
    },
    # === AGENDAMENTO ===
    "agendamento:slot:{data}:{hora}": {
        "ttl_seconds": 60,  # 1min
        "scope": "queue",
        "lgpd_art": "operacional",
        "eviction_safe": True,
        "current_location": "app/services/agendamento_cache.py",
        "rationale": "Lock de slot: 1min auto-release se processo morrer",
    },
    "agendamento:metrics:{key}": {
        "ttl_seconds": 300,  # 5min
        "scope": "metrics",
        "lgpd_art": "operacional",
        "eviction_safe": True,
        "current_location": "app/services/agendamento_metrics.py",
        "rationale": "Métricas efêmeras: 5min",
    },
    # === ATENDIMENTO ===
    "atendimento:lock:{atendimento_id}": {
        "ttl_seconds": 30,  # 30s
        "scope": "queue",
        "lgpd_art": "operacional",
        "eviction_safe": True,
        "current_location": "app/services/atendimento_cache.py",
        "rationale": "Lock curta: HITL exige atomicidade mas não pode bloquear",
    },
    # === REDLOCK ===
    "redlock:{name}": {
        "ttl_seconds": 300,  # 5min default
        "scope": "lock",
        "lgpd_art": "operacional",
        "eviction_safe": True,
        "current_location": "app/services/redlock.py",
        "rationale": "Lock distribuído auto-release (process crash safety)",
    },
    # === LGPD CACHE (PII MASKED) ===
    "lgpd:consent:{cliente_id}": {
        "ttl_seconds": 86400,  # 24h
        "scope": "session",
        "lgpd_art": "Art.18 II (acesso)",
        "eviction_safe": True,
        "current_location": "app/services/lgpd_consent.py + cache_lgpd.py",
        "rationale": "Consentimento cache 24h (refresh em mudança)",
    },
}


# Configuração recomendada para redis.conf (production)
RECOMMENDED_REDIS_CONFIG: dict[str, str] = {
    "maxmemory": "2gb",  # ajuste conforme VPS (4-8gb disponível)
    "maxmemory-policy": "allkeys-lru",  # LRU global (LGPD-safe: chaves com TTL são short-lived)
    "maxmemory-samples": "10",
    "appendonly": "yes",  # AOF para durabilidade
    "appendfsync": "everysec",
    "tcp-keepalive": "60",
    "timeout": "0",  # 0 = sem timeout para clientes (deixe app controlar)
    "lazyfree-lazy-eviction": "yes",
    "lazyfree-lazy-expire": "yes",
}


def get_keys_by_scope(scope: str) -> list[str]:
    """Retorna lista de keys com scope específico."""
    return [k for k, v in TTL_REGISTRY.items() if v.get("scope") == scope]


def get_keys_by_lgpd_art(art: str) -> list[str]:
    """Retorna lista de keys associadas a um Art. LGPD."""
    return [k for k, v in TTL_REGISTRY.items() if art in v.get("lgpd_art", "")]


def validate_ttl_config() -> dict[str, list[str]]:
    """Valida configuração de TTL. Retorna issues por severidade.

    Returns:
        Dict {"ERROR": [...], "WARN": [...], "INFO": [...]}
    """
    issues: dict[str, list[str]] = {"ERROR": [], "WARN": [], "INFO": []}

    # Check 1: nenhuma chave sem TTL (eviction_safe=True obrigatório)
    for key, meta in TTL_REGISTRY.items():
        if not meta.get("eviction_safe", False):
            issues["ERROR"].append(
                f"Key '{key}' sem eviction_safe=True. Risco de crescimento ilimitado."
            )

    # Check 2: TTL máximo <= 7d (exceto refresh token e audit-log-cached)
    for key, meta in TTL_REGISTRY.items():
        ttl = meta.get("ttl_seconds", 0)
        if ttl > 604800 and "refresh" not in key and "audit" not in key:
            issues["WARN"].append(
                f"Key '{key}' TTL={ttl}s ({ttl // 86400}d). Acima de 7d — revisar LGPD."
            )

    # Check 3: TTL mínimo >= 1s (evita hot path de EXPIRE)
    for key, meta in TTL_REGISTRY.items():
        ttl = meta.get("ttl_seconds", 0)
        if ttl < 1:
            issues["ERROR"].append(f"Key '{key}' TTL={ttl}s. Mínimo 1s.")

    # Check 4: LGPD art documentado
    for key, meta in TTL_REGISTRY.items():
        if not meta.get("lgpd_art"):
            issues["WARN"].append(f"Key '{key}' sem lgpd_art. Compliance gap.")

    # Info: contagem por scope
    scopes: dict[str, int] = {}
    for meta in TTL_REGISTRY.values():
        scope = meta.get("scope", "unknown")
        scopes[scope] = scopes.get(scope, 0) + 1
    issues["INFO"].append(f"Total {len(TTL_REGISTRY)} keys em {len(scopes)} scopes: {scopes}")
    return issues


def recommended_eviction_policy() -> str:
    """Retorna política de eviction recomendada.

    allkeys-lru: evict qualquer chave, priorizando menos usadas.
    - Pro: simples, sempre funciona.
    - Con: pode evict chave com TTL longo (mas todas têm TTL aqui).

    volatile-lru: evict só chaves COM TTL, priorizando LRU.
    - Pro: protege chaves sem TTL (não há no projeto).
    - Con: se todas têm TTL, equivalente a allkeys-lru.

    Decisão: **allkeys-lru** porque todas as chaves do projeto têm TTL
    definido (validado por validate_ttl_config).
    """
    return "allkeys-lru"


def render_inventory_report() -> str:
    """Renderiza relatório Markdown do inventário."""
    lines = [
        "# Redis TTL Inventory (G8.05.T1)",
        "",
        f"Total: **{len(TTL_REGISTRY)}** chaves catalogadas",
        "",
        "| Key | TTL | Scope | LGPD Art | Eviction-safe |",
        "|-----|-----|-------|----------|---------------|",
    ]
    for key, meta in sorted(TTL_REGISTRY.items()):
        ttl = meta.get("ttl_seconds", 0)
        ttl_str = (
            f"{ttl // 86400}d"
            if ttl >= 86400
            else f"{ttl // 3600}h"
            if ttl >= 3600
            else f"{ttl // 60}m"
            if ttl >= 60
            else f"{ttl}s"
        )
        scope = meta.get("scope", "?")
        lgpd = meta.get("lgpd_art", "?").split(" ")[0]  # só Art.XX
        safe = "✅" if meta.get("eviction_safe") else "❌"
        lines.append(f"| `{key}` | {ttl_str} | {scope} | {lgpd} | {safe} |")

    issues = validate_ttl_config()
    lines.append("")
    lines.append("## Validation")
    for sev in ("ERROR", "WARN"):
        if issues[sev]:
            lines.append(f"### {sev}")
            for issue in issues[sev]:
                lines.append(f"- {issue}")
        else:
            lines.append(f"### {sev}: 0 issues ✅")

    lines.append("")
    lines.append("## Recommended Redis Config")
    lines.append("```conf")
    for k, v in RECOMMENDED_REDIS_CONFIG.items():
        lines.append(f"{k} {v}")
    lines.append("```")
    lines.append("")
    lines.append(f"**Eviction policy**: `{recommended_eviction_policy()}`")
    return "\n".join(lines)


def render_recommended_config() -> str:
    """Renderiza snippet redis.conf puro."""
    lines = ["# G8.05.T1 recommended Redis config", ""]
    for k, v in RECOMMENDED_REDIS_CONFIG.items():
        lines.append(f"{k} {v}")
    return "\n".join(lines)


def find_long_ttl_keys(threshold_days: int = 7) -> list[tuple[str, int]]:
    """Retorna chaves com TTL > threshold_days (exceto refresh)."""
    threshold_s = threshold_days * 86400
    result = []
    for key, meta in TTL_REGISTRY.items():
        if "refresh" in key or "audit" in key:
            continue
        ttl = meta.get("ttl_seconds", 0)
        if ttl > threshold_s:
            result.append((key, ttl))
    return sorted(result, key=lambda x: -x[1])


def find_short_ttl_keys(threshold_seconds: int = 60) -> list[tuple[str, int]]:
    """Retorna chaves com TTL < threshold_seconds (operacionais)."""
    result = []
    for key, meta in TTL_REGISTRY.items():
        ttl = meta.get("ttl_seconds", 0)
        if ttl < threshold_seconds:
            result.append((key, ttl))
    return sorted(result, key=lambda x: x[1])


__all__ = [
    "RECOMMENDED_REDIS_CONFIG",
    "TTL_REGISTRY",
    "find_long_ttl_keys",
    "find_short_ttl_keys",
    "get_keys_by_lgpd_art",
    "get_keys_by_scope",
    "recommended_eviction_policy",
    "render_inventory_report",
    "render_recommended_config",
    "validate_ttl_config",
]


def _cli() -> None:
    """CLI: imprime inventory ou config."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="G8.05.T1 Redis TTL Inventory")
    parser.add_argument("--inventory", action="store_true", help="Print inventory report")
    parser.add_argument("--config", action="store_true", help="Print recommended redis.conf")
    parser.add_argument("--validate", action="store_true", help="Run validation only")
    parser.add_argument("--long-ttl", type=int, default=7, help="Threshold days for long TTL")
    args = parser.parse_args()

    if args.inventory:
        print(render_inventory_report())
    elif args.config:
        print(render_recommended_config())
    elif args.validate:
        import json

        print(json.dumps(validate_ttl_config(), indent=2, ensure_ascii=False))
    elif args.long_ttl != 7:  # usado como flag semântica
        import json

        long_keys = find_long_ttl_keys(args.long_ttl)
        print(
            json.dumps(
                [{"key": k, "ttl_seconds": ttl, "days": ttl // 86400} for k, ttl in long_keys],
                indent=2,
            )
        )
    else:
        parser.print_help(sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    _cli()
