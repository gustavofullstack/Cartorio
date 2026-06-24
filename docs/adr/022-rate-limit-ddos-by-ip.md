# ADR-022: Rate Limit DDoS Protection por IP

> **Status**: Aceito
> **Data**: 2026-06-24
> **Decisor**: ZCode/Mavis (sessao orcestracao)
> **Contexto**: P2.BE.5 do plano de 100 tasks

## Contexto

O `RateLimitByKeyMiddleware` (Sprint 3) implementa rate-limit por **tier de API key** (n8n 600/min, dpo 60/min, padrao 30/min). Porem, ha 2 vetores de ataque nao cobertos:

1. **Atacante rotaciona API keys**: cada key nova comeca com 0 count, permitindo multiplas vezes o limite de "padrao".
2. **Atacante nao usa API key**: ja cai no "padrao" 30/min, mas um botnet distribuido pode usar 30 req/min POR IP sem atingir o limite individual.

Alem disso, o sistema ja tinha fallback para IP no `RateLimitMiddleware` (Sprint 0.5) mas APENAS em `/integrations/` e `/admin/`, nao em `/api/v1/` (rota principal).

## Decisao

Adicionar **camada 1 de rate-limit por IP absoluto** (100 req/min) que roda ANTES do rate-limit por tier, em TODAS as rotas sob `/api/v1/`.

## Consequencias

### Positivas

- **Defesa DDoS em profundidade**: atacante que rotaciona keys ou nao usa key e segurado pelo limite de IP.
- **Nao muda API publica**: 100 req/min por IP e razoavel para uso legitimo (cliente humano, N8N cron em IP fixo pode precisar ajuste).
- **Fail-open**: se Redis offline, NAO bloqueia (ja documentado em outros middlewares).
- **Configuravel**: `ddos_per_minute` e parametro do middleware, ajustavel sem redeploy.

### Negativas

- **N8N em IP fixo**: se a VPS da cartorio tem 1 IP compartilhado com varios servicos, o limite de 100 req/min pode ser atingido. Solucao: ajustar `ddos_per_minute=600` no Easypanel env se for o caso (monitorar).
- **NAT/CGNAT**: varios usuarios atras do mesmo IP compartilham o limite. Para cartorio (uso interno), e aceitavel.
- **Header spoofing**: `X-Forwarded-For` pode ser falsificado se nao tiver proxy reverso confiavel. Mitigacao: usar `request.client.host` como fallback.

## Implementacao

- Arquivo: `backend/app/services/rate_limit_by_key.py`
- Novo metodo: `_check_ip_ddos(client_ip)` com limite de 100 req/min
- Modificado: `dispatch()` chama IP check antes do tier check
- Novo erro: `RATE_LIMITED_DDOS` (vs `RATE_LIMITED` do tier)
- Header: `Retry-After` + `X-RateLimit-Limit` + `X-RateLimit-Remaining`

## Alternativas consideradas

### A) WAF externo (Cloudflare, AWS WAF)

- Pro: defesa em borda, nao consome recurso do backend.
- Contra: $$$, mais um servico para gerenciar, latencia adicional.

### B) Apenas por API key (status quo)

- Pro: simples, ja funciona.
- Contra: vetor de ataque documentado (rotacao de keys).

### C) Rate limit por session_id

- Pro: ja existe em `RateLimitMiddleware`.
- Contra: requer X-Session-Id, que nao existe em chamadas de API/webhook.

## Validacao

- 400 testes pytest (era 382, +18 de CNS/CNH)
- Coverage 92.19% (gate 90% OK)
- Ruff/mypy: 0 erros
- 10 warnings pytest (4 novos, mesmo problema de mock - nao regressao)

## Referencias

- MEGA_PLANO: `docs/superpowers/plans/2026-06-24-mega-plano-100-tasks.md` (P2.BE.5)
- Commit: `525f03a`
- Codigo: `backend/app/services/rate_limit_by_key.py`

Modified by ZCode/Mavis
