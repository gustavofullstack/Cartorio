# Plano — Progresso VPS Cartório + Recovery de Serviços + Finalização Hermes/Lark MiniMax

Data: 2026-07-28 · Autor: Orquestrador (Pietra Ops) · Modo: delegar → testar → validar (1-2 agents em paralelo, regra prompt-cartorio)

---

## 1. Summary

Este plano consolida o **progresso real atual** da stack VPS Cartório (Hostinger/Easypanel/Docker Swarm) capturado ao vivo em 2026-07-28, e define as ondas de execução para:

1. **W1** — Recuperar serviços degradados: `cartorio_n8n` (0/1 crash-loop), `cartorio_n8n-runner` (0/1), `cartorio_supabase_realtime` (0/1).
2. **W2** — Investigar o desaparecimento de **Chatwoot** e **OpenClaw** do Swarm e levar a decisão ao Gustavo (restore vs decomissionar).
3. **W3** — Finalizar a branch `agent/fix-hermes-swarm-lifecycle` (Hermes + Lark + MiniMax-M3): testes, lint, commit das mudanças pendentes, merge em `master`.
4. **W4** — Validação E2E do canal Lark conforme runbook (só o passo 5 do runbook — mensagem real — declara o canal operacional).
5. **W5** — Atualizar fontes de verdade (task-bank.json está stale desde 2026-06-24, loop-state.json desde 2026-07-17) e registrar lessons em MEMORY.md.

---

## 2. Current State Analysis (evidência viva 2026-07-28)

### 2.1 Health check externo (curl, Mac → internet)

| Domínio | HTTP | Interpretação |
|---|---|---|
| api.2notasudi.com.br | **200** (96ms) | OK — servido por `cartorio_system-api` (Lesson 283) |
| flow.2notasudi.com.br | **502** | n8n DOWN (crash-loop) |
| whatsapp.2notasudi.com.br | **200** | OK — `cartorio_whatsapp-api` 1/1 |
| chat.2notasudi.com.br | **404** | Traefik default — router sem match (Lesson 176: ≠ app down necessariamente) |
| agent.2notasudi.com.br | **404** | OpenClaw ausente do Swarm |
| supbase.2notasudi.com.br | **503** | Supabase kong/realtime degradado |
| easypanel.2notasudi.com.br | **200** | OK |
| cartorio-chatwoot.dfgdxq.easypanel.host | **404** | Chatwoot fora do ar |

Radar interno (`/api/v1/health/radar`): `status=yellow` — database online, redis online, **n8n offline, openclaw offline, evolution offline, chatwoot offline, supabase degraded**.

### 2.2 Swarm real (`docker service ls` via SSH root@100.99.172.84)

| Serviço | Réplicas | Nota |
|---|---|---|
| cartorio_system-api | **1/1** | Backend principal (api.2notasudi) |
| cartorio_api | 0/0 | Legado — substituído por system-api |
| **cartorio_hermes** | **1/1** | Running há ~4 min (restart recente — trabalho Lark ativo) |
| cartorio_whatsapp-api | 1/1 | Evolution (novo nome; `cartorio_evolution-api` está 0/0 legado) |
| cartorio_banco_de_dados | 1/1 | pgvector/pgvector:pg17 |
| cartorio_memory-cache | 1/1 | redis:8.8 (substitui `cartorio_redis` 0/0) |
| **cartorio_n8n** | **0/1** | CRASH-LOOP: `task: non-zero exit (1)` repetido |
| **cartorio_n8n-runner** | **0/1** | DOWN |
| cartorio_n8n-db / dbgate / pgweb | 1/1 | OK |
| **cartorio_supabase_realtime** | **0/1** | CRASH-LOOP: `non-zero exit (1)` |
| cartorio_supabase_auth / storage / dbgate / pgweb | 1/1 | OK |
| cartorio_supabase | 0/0 | Legado |
| **Chatwoot / OpenClaw / LobeChat** | **—** | **NÃO EXISTEM no Swarm** (grep vazio) |
| vps_whoami | 0/1 | DOWN (baixa prioridade) |

Recursos VPS: disco 20% usado (156G livre), RAM 2.7G/16G usada — **não é OOM nem disco**.

### 2.3 Git (repo local)

- Branch ativa: **`agent/fix-hermes-swarm-lifecycle`** (1 commit à frente de master: `a3337d1b fix(hermes): evita gateway duplicado no Swarm`).
- **Mudanças NÃO commitadas** (working tree):
  - `backend/tests/test_hermes_vps_stack_contract.py` (+32/-X)
  - `infra/hermes/.env.example`, `config.cartorio.yaml`, `docker-stack.yml`, `lark-entrypoint.sh`, `preflight-vps.sh`
  - `docs/HERMES_LARK_MINIMAX_RUNBOOK.md` (untracked, novo — contrato de produção Lark)
- Commits recentes relevantes: `fd8fb2c6` (gateway Lark persistente Swarm), `e94d2fd8` (perfil institucional Pietra + guards), `f9a303c2` (purge OPENCODE_GO_API_KEY), Lessons 292/293 (outbound guard, anti-glitch, language guard latino).
- Branch paralela existente: `agent/restore-lark-hermes-vps` (avaliar se mergeável/obsoleta).

### 2.4 Fontes de verdade — frescor

| Fonte | Última atualização | Estado |
|---|---|---|
| `.harness/memory/MEMORY.md` | 2026-07-28 (Lesson 293) | **FRESCO** — fonte primária |
| `.harness/task-bank.json` | **2026-06-24** | **STALE** — P0.7/P0.8/P0.9 constam "pending" mas muito já foi entregue (outbound guard, pii scrub, etc.) |
| `.brain/loop-state.json` | **2026-07-17** | **STALE** — fala em G7 W29, mundo já mudou (Etapa 10 iMessage, Lark) |
| `~/.zcode/goals/*.md` | — | **NÃO EXISTE** (comando /goal sem fonte) |
| `GOALS.md` (raiz) | — | vazio/ausente |

### 2.5 Últimas lessons críticas (MEMORY.md)

- **Lesson 287 addendum**: deploy path manual EasyPanel validado (`git archive | ssh tar -x` → rsync → docker build → service update). M2.7-HighSpeed + thinking medium live em prod via env no service spec.
- **Lesson 290**: aceite iMessage/canal exige round-trip real autorizado — CONNECTED ≠ OPERATIONAL. Mesmo critério se aplica ao Lark.
- **Lesson 283**: `api.2notasudi.com.br` é servido por `cartorio_system-api`, não `cartorio_api`. MCP público funcional (16 tools).
- **Lesson 284**: `EMOLUMENTOS_2026` placeholder corrigido; tool de preço exige diff contra fonte TJMG (já validado 120/120 pós-fix).
- **Runbook Lark** (`docs/HERMES_LARK_MINIMAX_RUNBOOK.md`): provider `minimax` nativo, modelo M3 + contingência M2.7-highspeed, secret `hermes_minimax_api_key`, validação em 5 camadas — só passo 5 (mensagem real Lark→Hermes→MiniMax→Lark) declara canal operacional.

---

## 3. Proposed Changes (ondas de execução)

### W1 — Recovery n8n + supabase_realtime (P0) · owner: cartorio-sre + cartorio-n8n

**Arquivos/alvos**: VPS (somente operação, sem código inicialmente)

1. `ssh root@100.99.172.84 "docker service logs cartorio_n8n --tail 80"` — capturar causa do `exit(1)` (suspeitas por ordem: env `DATABASE_URL` errada — Lesson 176 mostrou Easypanel sobrescrevendo credenciais; encryption key ausente; permissão de volume).
2. Idem `cartorio_supabase_realtime` (suspeita: `DATABASE_URL`/JWT secret do cluster supabase).
3. Corrigir via `docker service update --env-add ...` (padrão Lesson 228/287 — persiste no service spec, sem rebuild). **Nunca imprimir valores de secret; só fingerprint SHA256[:12]**.
4. Validar: `flow.2notasudi.com.br` → 200; radar `n8n: online`; `supbase` → 401/200 (não 503).
5. Se a causa for config Easypanel (UI-only), registrar como **HOLD-GUSTAVO** com runbook copy-pasteable (padrão Lesson 172).

**Critério de saída**: radar `n8n=online`, `supabase` não-degraded; `docker service ps` sem `Failed` recente.

### W2 — Chatwoot + OpenClaw: investigação → decisão (P0) · owner: cartorio-sre

1. Investigar: `docker service ls -a`, `docker ps -a | grep -iE 'chatwoot|openclaw'`, histórico Easypanel (`easypanel` API/UI), Traefik `main.yaml`/`custom.yaml` em `/etc/easypanel/traefik/`.
2. Verificar se routers Traefik para `chat.` e `agent.` ainda existem (404 = router sem match — podem ter sido removidos juntos ou não).
3. Produzir relatório curto: quando sumiram, por quê (se rastreável), custo de restore (backups em `/var/backups/cartorio/` e `infra/backup/`).
4. **Ponto de decisão Gustavo (SUI)**: restaurar Chatwoot (necessário p/ HITL humano omnichannel) e OpenClaw, ou decomissionar e ajustar radar (`/api/v1/health/radar` remove os 2 checks) + docs. Até a decisão: **não restaurar nem apagar nada**.

**Critério de saída**: relatório + decisão registrada em MEMORY.md; se restore aprovado → plano de restore separado.

### W3 — Finalizar branch hermes-swarm-lifecycle (P1) · owner: cartorio-dev

**Arquivos**: `infra/hermes/*`, `backend/tests/test_hermes_vps_stack_contract.py`, `docs/HERMES_LARK_MINIMAX_RUNBOOK.md`

1. Re-ler os 6 arquivos modificados + runbook (Lesson 234/270: reconciliar antes — swarm paralela pode ter escrito).
2. Rodar contrato: `cd backend && uv run pytest tests/test_hermes_vps_stack_contract.py -v --no-cov`.
3. Gates: `make format` → `make lint` (ruff 0 + mypy 0) → `make test-fast` (suíte completa sem coverage para garantir não-regressão).
4. Commit das mudanças pendentes em commits atômicos por tema (entrypoint/preflight vs stack yaml vs testes vs runbook), Conventional Commits terminando com `Modified by Gustavo Almeida`.
5. Avaliar branch `agent/restore-lark-hermes-vps`: mergear, reabsorver ou deletar (listar diff antes).
6. Merge `agent/fix-hermes-swarm-lifecycle` → `master` (fast-forward ou PR com checklist `.github/pull_request_template.md`); push.

**Critério de saída**: master verde (ruff/mypy 0, pytest pass), branch mergeada, working tree limpa.

### W4 — Validação E2E Lark (P1) · owner: cartorio-n8n + Gustavo (passo 5)

Seguir `docs/HERMES_LARK_MINIMAX_RUNBOOK.md` camadas 1-5:

1. `docker service ls` → `cartorio_hermes 1/1` ✔ (já observado, re-validar estabilidade — restart há 4min; checar `docker service ps` por churn).
2. Logs: uma única conexão WS Lark, zero `Another gateway instance` (commit a3337d1b trata exatamente disso — confirmar eficácia).
3. `hermes auth status minimax` reconhecido (sem imprimir chave).
4. Prompt sintético sem PII em M3 e M2.7-highspeed (fallback).
5. **Mensagem real no Lark (SUI Gustavo)** — round-trip `Lark → Hermes → MiniMax → Hermes → mesmo chat`. Sem passo 5: canal = `NOT_E2E_VALIDATED` (Lesson 290).

**Critério de saída**: passos 1-4 PASS + passo 5 PASS (ou registro honesto `LARK_NOT_E2E_VALIDATED`).

### W5 — Fontes de verdade + memória (P2) · owner: cartorio-dev

1. Atualizar `.harness/task-bank.json`: marcar entregas reais desde 2026-06-24 (P0.7/P0.8/P0.9 outbound guard + pii scrub entregues nas Lessons 286-293; P0.3/P0.4 Chatwoot/OpenClaw aguardam decisão W2).
2. Atualizar `.brain/loop-state.json` para estado real (Etapa 10 → Hermes/Lark).
3. Recriar `GOALS.md` raiz ou apontar `/goal` para fonte existente (hoje `~/.zcode/goals/` não existe).
4. Lesson nova em `.harness/memory/MEMORY.md`: diagnóstico 2026-07-28 (n8n crash-loop, supabase realtime, chatwoot/openclaw ausentes, radar yellow) + outcomes das waves.

---

## 4. Assumptions & Decisions

- **Escopo assumido**: diagnóstico + recovery + finalização Hermes/Lark (usuário pulou a pergunta de escopo — default = plano completo).
- **Chatwoot/OpenClaw**: NÃO restaurar sem decisão do Gustavo (W2 produz relatório primeiro). Pode ter sido remoção intencional.
- **`cartorio_api`, `cartorio_evolution-api`, `cartorio_redis`, `cartorio_supabase` em 0/0** são tratados como **legados intencionais** (substituídos por system-api / whatsapp-api / memory-cache / cluster supabase) — não "subir" cegamente.
- **Regra 1-2 agents paralelos** respeitada; waves sequenciais W1→W5, dentro de cada wave no máx 2 lanes.
- **Secrets**: nunca imprimir valores; fingerprint SHA256[:12] apenas. Nenhuma rotação de chave (regra Gustavo).
- **Deploy VPS** usa o path manual validado (Lesson 287 addendum) se rebuild for necessário.
- Nada de push direto em `master` sem gates verdes locais; mudança em `audit*`/`pii*` exigiria sign-off cartorio-lgpd (não previsto neste plano).

## 5. Verification (final)

1. `curl` 7 domínios: api 200, flow 200, whatsapp 200, easypanel 200; chat/agent/supbase conforme decisão W2.
2. Radar: `status=green` (ou yellow justificado com decisão registrada).
3. `docker service ls`: n8n 1/1, n8n-runner 1/1, supabase_realtime 1/1, hermes 1/1 estável (sem restart < 15min).
4. Local: `make qa` verde (ruff 0, mypy 0, pytest pass, coverage ≥90%).
5. Git: master contém branch hermes; `git status` limpo; push feito.
6. Lark: round-trip real confirmado (ou `LARK_NOT_E2E_VALIDATED` registrado).
7. task-bank.json + loop-state.json + MEMORY.md atualizados com data 2026-07-28.
