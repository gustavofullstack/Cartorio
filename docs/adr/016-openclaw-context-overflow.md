# ADR-016: OpenClaw context overflow (sessão agente:cartorio:main)

**Data:** 2026-06-23
**Status:** RESOLVIDA 2026-06-24 03:15 BRT (schema legado substituído por ADR-021)
**Sprint:** Sprint 2, task 9

> **ATUALIZAÇÃO 2026-06-24:** schema proposto nesta ADR é PRÉ-2026.6.x e
> não existe no OpenClaw 2026.6.10 rodando na VPS. Mapeamento para o
> schema moderno + lições aprendidas + pipeline de validação pré-deploy:
> ver **ADR-021**. Aplicação concreta foi feita via `openclaw config
> patch --stdin --dry-run` (3 iterações incrementais) durante cron
> `reapply-b2-openclaw` 24/06 00:00 BRT. Container UP, HTTP 200, sem
> context overflow.

## Contexto

Sessão `agent:main:main` do OpenClaw acumulou 142 mensagens. Provider
`openai/deepseek-v4-flash` retornou "Context overflow: prompt too large"
(131073 tokens > budget 111072). Auto-compactação ativou (attempt 1/3)
mas `compactionAttempts=0` mostra que falhou.

**Achado da sessão 18:50 (vide `docs/SESSION_SUMMARY_2026-06-23.md`):**
- Sessão `agent:main:main` com 142 msgs acumuladas
- Auto-compact falhou em 1/3 attempts
- Tokens observados: 131073 (acima do budget de 111072)

## Causa raiz

1. **Threshold de compactação muito alto.** OpenClaw compacta após overflow,
   não antes. Sessões longas (>100 msgs) batem o teto antes da compactação
   automática.
2. **`compactionAttempts=0` apesar de attempt 1/3.** Bug ou config do provider
   `deepseek-v4-flash` que não suporta compactação transparente.
3. **Session não tem TTL.** Sem `session_ttl` configurado, mensagens
   continuam acumulando indefinidamente.

## Decisão proposta

Configurar compactação automática mais agressiva e adicionar TTL.

### Configuração nova (SUI - aplicar via UI OpenClaw ou config YAML)

```yaml
openclaw:
  context:
    auto_compact:
      enabled: true
      threshold_messages: 50        # era ~120 (overflow)
      strategy: compact_then_truncate
    session_ttl_minutes: 1440       # 24h
    max_context_tokens: 100000      # margem de seguranca (budget = 111072)
```

### Mitigação imediata (1-liner via Tailscale)

Forçar compactação manual da sessão atual:

```bash
curl -X POST http://100.99.172.84:18790/v1/sessions/agent:main:main/compact \
  -H "Authorization: Bearer $OPENCLAW_GATEWAY_TOKEN"
```

## Consequências

- Compactação automática **antes** do overflow (em 50 msgs)
- Sessões longas continuam funcionando
- TTL de 24h evita acúmulo indefinido
- Audit log da compactação (próprio do OpenClaw)

## Follow-up

- [ ] Gustavo aplica config no OpenClaw (SUI - via UI ou YAML)
- [ ] Validar: 0 overflows em 24h após threshold aplicado
- [ ] Sprint 2.1: workflow N8N #24 que detecta sessões >40 msgs e força compact preventivamente
- [ ] Considerar session summarization LLM-side (chamar OpenCode-Go pra resumir antes de armazenar)

## Referências

- `docs/PENDENCIAS_SUI_2026-06-23.md` (bug B2)
- `docs/SESSION_SUMMARY_2026-06-23.md` (achado 18:50 BRT)
- `infra/openclaw-agent/RELOAD_PERSONA.md` (procedimento reload OpenClaw)
