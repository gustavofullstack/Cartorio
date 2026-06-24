# ADRs - Architectural Decision Records

> **Decisoes arquiteturais do projeto Cartorio Chatbot, em ordem cronologica.**
> Total: 23 ADRs (2026-06-23 ao 2026-06-24).
> Formato: [MADR](https://adr.github.io/madr/) simplificado (Contexto, Decisao, Consequencias, Alternativas).

## Indice por data

| # | Data | Titulo | Status |
|---|---|---|---|
| 013 | 2026-06-22 | [Supabase password mismatch](./013-backup-mount-watchdog.md) | Aceito |
| 015 | 2026-06-23 | [Chatwoot restart loop](./015-chatwoot-restart-loop.md) | Aceito |
| 016 | 2026-06-23 | [OpenClaw context overflow](./016-openclaw-context-overflow.md) | Aceito |
| 017 | 2026-06-23 | [Credential rotation policy](./017-credential-rotation.md) | Aceito |
| 018 | 2026-06-23 | [Delete cliente LGPD](./018-delete-cliente-lgpd.md) | Aceito |
| 019 | 2026-06-23 | [Retencao 5 anos](./019-retencao-5y.md) | Aceito |
| 020 | 2026-06-23 | [N8N official nodes](./020-n8n-official-nodes.md) | Aceito |
| 021 | 2026-06-24 | [Pre-deploy config validation](./021-pre-deploy-config-validation.md) | Aceito |
| 022 | 2026-06-24 | [Rate limit DDoS por IP](./022-rate-limit-ddos-by-ip.md) | Aceito |
| 023 | 2026-06-24 | [CNS/CNH check-digit](./023-cns-cnh-check-digit.md) | Aceito |

## Indice por tema

### LGPD / Compliance
- **018** Delete cliente LGPD (soft delete + audit)
- **019** Retencao 5 anos (tabela_emolumento + audit_log)
- **023** CNS/CNH check-digit (LGPD art. 11 - dado sensivel)

### Seguranca
- **017** Credential rotation policy (sem rotacao forcada)
- **022** Rate limit DDoS por IP (defesa 100 req/min)

### Operacional
- **013** Supabase password mismatch (SUI)
- **015** Chatwoot restart loop (SUI, B1)
- **016** OpenClaw context overflow (SUI, B2)

### Workflow / Integracao
- **020** N8N official nodes (substituir nodes custom)

### Deploy / Validation
- **021** Pre-deploy config validation (env check antes de subir)

## Indice por status

### Aceitos
Todos os 10 ADRs acima estao aceitos e em producao.

### Drafts / Em discussao
Nenhum no momento.

### Superseded
Nenhum no momento.

## Template para novos ADRs

```markdown
# ADR-NNN: Titulo curto da decisao

> **Status**: Aceito | Draft | Superseded
> **Data**: YYYY-MM-DD
> **Decisor**: Nome (sessao X)
> **Contexto**: ID do task/issue

## Contexto

Qual problema estamos resolvendo? Por que agora?

## Decisao

O que decidimos fazer. Seja ESPECIFICO (nao "usar Redis", mas "usar Redis 7 com TTL 60s").

## Consequencias

### Positivas
- ...

### Negativas
- ...

## Alternativas consideradas

### A) Nome
- Pro: ...
- Contra: ...

## Validacao

- pytest: X passed (era Y)
- Coverage: X% (gate Y% OK)
- Ruff: 0 erros
- Mypy: 0 erros

## Referencias

- Task/Issue: ...
- Codigo: `path/file.py`
- Tests: `path/test_file.py`
- Commit: <hash>
```

## Como usar

1. **Antes de tomar decisao tecnica grande**: leia ADRs relacionados
2. **Apos implementar**: escreva o ADR documentando a decisao
3. **Em code review**: ADRs sao a FONTE DA VERDADE para o "por que" de cada decisao
4. **ADRs NAO sao para refactor** - use o CHANGELOG para isso

Modified by ZCode/Mavis - 2026-06-24
