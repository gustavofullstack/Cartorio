# Contributing — Cartório Chatbot

> Guia para todos os reins (cartorio-dev, cartorio-n8n, cartorio-lgpd, Mavis orquestrador).
> Última atualização: 2026-06-24.

## TL;DR

1. **Master only** — NUNCA criar branch temporária
2. **TDD quando possível** — teste falhou → implementa → passa → refactor
3. **Conventional Commits** — `feat:` / `fix:` / `docs:` / `test:` / `refactor:` / `chore:` / `perf:`
4. **Mensagem termina com `Modified by Gustavo Almeida`**
5. **Cada commit = pytest + ruff + mypy verde** + coverage >= 90%
6. **Mudança em `audit` ou `pii`** exige review do `cartorio-lgpd` antes de merge
7. **Workflow obrigatório**: analisar → testar → corrigir → melhorar → otimizar → documentar → comentar → salvar na memória

## Workflow completo (8 etapas)

### 1. Analisar
Antes de mexer em qualquer código:
- Ler `.harness/AGENTS.md` (98 linhas) — regras do projeto
- Ler `.harness/STANDARDS.md` (262 linhas) — Clean Code + SOLID + DDD
- Ler `.harness/TASKS.md` — task tree com owner + critérios de done
- Ler agent.md do seu rein — scope próprio
- Ler `.harness/memory/MEMORY.md` — lições anteriores (não duplicar erros)

### 2. Testar
Baseline antes de mudar nada:
- `cd backend && uv run pytest tests/ --cov=app --cov-fail-under=90 -q` → ver count atual + coverage
- `cd backend && uv run ruff check .` → 0 erros
- `cd backend && uv run mypy app/` → 0 erros
- `git log --oneline -5` → ver commits recentes (estilo + escopo)
- `git status -sb` → working tree clean

### 3. Corrigir
Implementação mínima:
- TDD: teste falhou → implementar → passa → refactor
- NUNCA agrupar lógica em try/except genérico
- NUNCA logar PII puro (LGPD art. 50)
- Toda mutação grava `audit_log` (hash chain + HMAC)
- Toda saída LLM passa por `pii.scrub()`

### 4. Melhorar
Refactor mantendo testes verdes:
- Extrair lógica em service próprio (SRP)
- DRY: se copy/paste em 3+ lugares, extrair
- Magic numbers → constantes
- Comentários TODO com link pra issue

### 5. Otimizar
Performance:
- Latência P95 < 200ms (exceto LLM call até 3s)
- Cache Redis onde aplicável (TTL explícito)
- Selectinload para evitar N+1
- httpx async pra I/O não-bloqueante

### 6. Documentar
Atualizar docstrings + AGENTS.md se mudou convenção:
- Endpoint: docstring explica caso de uso + exemplo
- Service: docstring explica responsabilidade + dependencies
- Constants: docstring explica origem
- ADR novo se decisão arquitetural

### 7. Comentar
Conventional Commits + trailer:

```bash
git commit -m "feat(pii): add CNS check-digit Modulo 11

- Pattern CNS 15/17dig com algoritmo Modulo 11
- Pesos 15..1 decrescentes
- Overflow DV >= 10 → DV = 0
- Classificacao provisorio (1o digito 8/9) vs definitivo (1-6)

LGPD art. 11 (CNS = dado sensivel saude).

Modified by Gustavo Almeida"
```

Tipos:
- `feat:` nova feature
- `fix:` bug fix
- `docs:` só documentação
- `test:` só testes
- `refactor:` nem feature nem fix
- `chore:` manutenção (deps, configs)
- `perf:` performance

Scopes comuns:
- `(pii)` — PII scrubber
- `(audit)` — audit log
- `(router)` — API endpoints
- `(models)` — SQLAlchemy models
- `(services)` — services
- `(integrations)` — opencode_go, evolution, chatwoot
- `(n8n)` — workflows
- `(lgpd)` — compliance
- `(infra)` — deployment, Easypanel
- `(docs)` — documentation

### 8. Salvar na memória
Critério: passa no "vale pra outro projeto?"

Se SIM → escrever em:
- `.harness/memory/MEMORY.md` (cross-rein do projeto)
- `~/.mavis/agents/mavis/memory/MEMORY.md` (cross-project)

Se NÃO → fica só no PR description / commit message.

## Pre-flight gates (cross-rein)

### Antes de mexer em `audit.py` ou `pii.py`
Notificar `cartorio-lgpd` no canal. Mudança em segurança/regulatório exige review antes de merge.

### Antes de mexer em output scrub (LGPD-015 pattern)
1. `grep -n scrub backend/app/services/pii.py` — listar TODOS os patterns atuais
2. Listar TODOS os PII relevantes do domínio cartorário
3. **patterns do detector >= set de PII?** Se NÃO = BLOQUEIO pré-fix
4. Add pattern primeiro, DEPOIS aplica fix de output

### Antes de mexer em N8N workflow
1. `grep -r apiKey infra/n8n-workflows/*.json` — 0 hits hardcoded
2. SEMPRE usar `$env.NOME_DA_VARIAVEL` (workaround feat:variables não licenciado)
3. Workflows SEMPRE chamam API backend (nunca Postgres direto)
4. Toda saída de mensagem passa por PII scrubber
5. Webhook idempotente (`message_id` dedup)

### Antes de mexer em DB schema
1. Migration Alembic (autogenerate)
2. Review `cartorio-lgpd` se envolve PII ou retenção
3. RLS policies em todas tabelas (Sprint 3 M4.9)
4. Backup pre-migration: `pg_dump > /tmp/pre-migration-$(date +%s).sql`

## Stop when (critérios de done)

A task só está pronta quando TODOS os pontos forem verdade:

### Backend (cartorio-dev)
- [ ] Build verde (`cd backend && uv sync`)
- [ ] `pytest --cov=app --cov-fail-under=90 -q` passa (coverage >= 90%)
- [ ] `ruff check .` + `ruff format --check .` limpos
- [ ] `mypy app/` 0 errors
- [ ] Toda mutação nova gravou entrada no `audit_log`
- [ ] Toda saída para LLM tem scrubber
- [ ] Endpoint documentado no OpenAPI (FastAPI gera, mas docstring explica caso de uso)
- [ ] Commit segue Conventional Commits + `Modified by Gustavo Almeida`
- [ ] Mudança em `audit` ou `pii` tem review do `cartorio-lgpd` registrado
- [ ] Lição reutilizável salva em `.harness/memory/MEMORY.md`

### N8N (cartorio-n8n)
- [ ] Workflow exportado para `infra/n8n-workflows/<name>.json`
- [ ] Workflow testado em sandbox com payload real (não só happy path — testar 5+ cenários incluindo erro)
- [ ] Toda chamada externa passa pelo backend (zero acesso direto a DB/secret)
- [ ] Toda mensagem de saída passa por PII scrubber
- [ ] Webhook handler idempotente (`message_id` dedup)
- [ ] Latência webhook -> resposta < 2s
- [ ] Commit segue Conventional Commits + `Modified by Gustavo Almeida`
- [ ] Workflow que toca PII tem review do `cartorio-lgpd`
- [ ] Deploy em Easypanel documentado em `infra/README.md`

### LGPD (cartorio-lgpd)
- [ ] Toda PR que mexe em `audit.py`, `pii.py`, `consentimento`, `retencao` revisada e aprovada
- [ ] Mudança documentada em `.harness/memory/MEMORY.md` ou `docs/LGPD.md`
- [ ] Se copy jurídica: revisada + datada + armazenada com fonte legal (lei/artigo)
- [ ] Se política: publicada em local acessível ao escrevente E ao cliente final
- [ ] Se pen-test: relatório gerado + ações corretivas priorizadas + prazo definido
- [ ] Se incidente: resposta documentada (timeline, dados afetados, titulares notificados, mitigação)
- [ ] Commit segue Conventional Commits + `Modified by Gustavo Almeida`

## Conventional Commits — exemplos

```bash
# Feature
git commit -m "feat(pii): add CNS check-digit Modulo 11

[body]

Modified by Gustavo Almeida"

# Bug fix
git commit -m "fix(router): apply output scrub PII in 3 sites

[body]

Modified by Gustavo Almeida"

# Docs
git commit -m "docs(adr): add ADR-022 rate limit DDoS by IP

[body]

Modified by Gustavo Almeida"

# Chore
git commit -m "chore(deps): bump n8n to v1.50.0

[body]

Modified by Gustavo Almeida"
```

## Report binário (Lesson 25 cross-project)

Padrão obrigatório pra QUALQUER report de worker:

```
[WORK] task=<X>, files=<Y>, pytest=<N passed>, ruff=<clean>, mypy=<clean>, commit=<hash>, branch=master
[HOLD] 0 modificações em <N> min, branch master, hash <Y>, pytest <pass/fail>
[BLOCKED] task=<X>, reason=<Y>, action_needed=<Z>
```

Report vago ("tudo ok", "mantive hold") sem evidência = kick + reabrir sessão.

## Comunicação cross-rein

Use `mavis communication send --to <session_id> --command prompt --content "..."`

- Session IDs em `.harness/memory/MEMORY.md` ou `mavis session list`
- Report binário ao final de cada task
- NÃO agrupar múltiplas tasks num report só (1 task = 1 report)
- Mavis orquestrador é root — todos os reins filhos reportam pra root

## Cron self-reminder

Pra esperar CI/jobs async, use:

```bash
mavis cron self <name> --every 5m --prompt "..."
```

Auto-deleta após TTL (default 7d).

## Hard limits (NÃO PODE)

- ❌ Criar branch != master
- ❌ Commitar `.env`, secrets, tokens em chat/log/scratchpad
- ❌ Rotacionar chaves/credenciais sem autorização Gustavo explícita
- ❌ Pular pytest, ruff ou mypy antes de commit
- ❌ Agrupar múltiplas tasks num commit só (cada task = 1 commit)
- ❌ Modificar `audit.py` ou `pii.py` sem review cartorio-lgpd
- ❌ Workflow N8N acessando Postgres direto (sempre API)
- ❌ Logar PII puro (LGPD art. 50)
- ❌ Echo credenciais em chat (mesmo em reler relatório)
- ❌ Mandar 3+ agents em paralelo (regra quota 5h/sem — 1-2 max)

## Onde pedir ajuda

| Tema | Pedir pra |
|------|-----------|
| Mudança em `audit.py` / `pii.py` | `cartorio-lgpd` antes de começar |
| Nova integração externa (LiteLLM, gov.br) | `cartorio-lgpd` (LGPD) + `Mavis` (decisão arquitetura) |
| Mudança em modelo que quebra contrato | abrir thread no relatório, NÃO PR silencioso |
| Performance ruim | instrumentar primeiro (logging + tempo), depois otimizar |
| Bug em Evolution API | verificar workarounds conhecidos no canal |
| Decisão arquitetural grande | `Mavis` orquestrador escala pra Gustavo |
| Workflow N8N falhando em runtime | `cartorio-n8n` com stack trace + executionId |

## Resources

- [docs/ARCHITECTURE.md](ARCHITECTURE.md) — diagrama arquitetural
- [docs/ROADMAP.md](ROADMAP.md) — 12 semanas
- [docs/API.md](API.md) — 31 endpoints documentados
- [.harness/AGENTS.md](../.harness/AGENTS.md) — regras do projeto
- [.harness/STANDARDS.md](../.harness/STANDARDS.md) — Clean Code + SOLID + DDD
- [.harness/TASKS.md](../.harness/TASKS.md) — task tree com owner

Modified by Mavis (Pietra root mvs_410a1b1266d64830b9dfa31973fdd9fe — 2026-06-24 10:40 BRT)