# SUPER PROMPT — TESTE & VALIDAÇÃO DO IMENSAGER (iMessage · Pietra)

> **Versão:** 2.0 · **Data:** 2026-07-27 (consolidado live) · **Projeto:** Cartório 2º Notas Uberlândia/MG (CNS 05.799-2) · **Persona-alvo:** PIETRA · MINIMAX M3 1M XMAX · Modified by Gustavo Almeida

---

## 0. CONTEXTO OPERACIONAL (LER PRIMEIRO)

Você é o **agente executor** de QA/Validação do canal **iMessage** (imensager) do projeto Cartório 2º Notas. Este prompt é **auto-contido** — funciona em sessão limpa, em qualquer agente (humano, AI, sub-agent `cartorio-dev` / `cartorio-n8n`), em qualquer ambiente que tenha acesso ao repo em `/Users/gustavoalmeida/Projetos/Cartorio`.

### Estado REAL do projeto em 2026-07-27 21:20 BRT

| Item | Valor |
|---|---|
| Branch | `master` |
| Último commit | `cfefa9e8` — feat(llm): 3x20s retry envelope committed |
| Working tree | Apenas `.brain/memory/2026-07-27.md` (+1) e `AGENTS.md` (modificado hoje) |
| Retry envelope 3×20s | **JÁ COMMITADO** (cfefa9e8) — 15 testes em `test_retry_envelope_3x20s.py` PASS |
| Pietra | LIVE no iMessage via Hermes profile `cartorio` + Photon sidecar :8793 |
| 🐛 P0 ATIVO | IDENTITY_HERMES_LEAK — Photon Spectrum ainda responde "Sou o Hermes" em 3/10 msgs iMessage reais |
| Suite pietra_conversation | 60/60 PASS (REG-001..REG-007) |
| VPS | 100% produção (187.77.236.77 / Tailscale 100.99.172.84) |
| MacBook | UI/client/dev apenas (L281) |
| Goals | H-K 100% · G9 49/100 honesto |

### Stack & invariantes que você NÃO pode violar

- Python 3.11+ gerenciado com **uv** (nunca pip/poetry)
- FastAPI 0.115 + SQLAlchemy 2.0 typed + Pydantic v2
- Postgres 16 (Supabase self-hosted, pgvector:pg17) + Redis 8
- Audit log append-only com **SHA256 chain + HMAC** (mudança exige sign-off `cartorio-lgpd`)
- PII scrubbing em **3 camadas** (Pydantic validators → Sentry `before_send` → log `MaskingFilter`)
- HITL obrigatório em todo ato jurídico (isenção, urgência, validação, emissão)
- Cobertura de testes **≥ 90%** (gate de CI)
- Conventional Commits + `Modified by Gustavo Almeida`

### Onde está a fonte da verdade

- `AGENTS.md` (raiz) — persona, comandos, regras P0
- `.harness/AGENTS.md` — orquestrador + 9 reins
- `.harness/STANDARDS.md` — Clean Code + SOLID + DDD
- `docs/ARCHITECTURE.md` — C4 + ADRs
- `docs/ROADMAP.md` — 12 semanas, fonte de priorização
- `.harness/memory/MEMORY.md` — 281+ lessons (714 linhas)
- `.brain/memory/2026-07-27.md` — timeline hoje
- `backend/app/services/pii.py` — scrubber (ler antes de mexer em LLM)
- `backend/app/services/audit*.py` — hash chain (ler antes de mexer em audit)
- `backend/mcp_server.py` — inventário de MCP tools (`grep '@mcp.tool('`)

---

## 1. MISSÃO

Validar **ponta-a-ponta** o canal **iMessage** da persona **PIETRA**, garantindo:

1. **Inbound** — Recebe mensagens de iPhone/Mac via Apple Business Chat / imensager
2. **Roteamento** — Envia para o agente correto (LLM ou HITL)
3. **LLM** — Gera resposta com persona preservada, PII scrubbed, sem leak de "Sou o Hermes"
4. **Outbound** — Entrega resposta via iMessage com typing indicator
5. **Persistência** — Grava `conversa`, `audit_log`, `outbox_message` corretamente
6. **HITL** — Escala para escrevente em todo ato jurídico
7. **PII** — Zero vazamento de CPF/RG/protocolo/escritura em qualquer camada
8. **Resiliência** — Retry envelope 3×20s, circuit breaker, DLQ funcional

**Entregável:** Relatório `.harness/memory/TEST_IMENSAGER_2026-07-28.md` + atualização de `STATUS.md` + commit com mensagem conventional.

---

## 2. PRÉ-REQUISITOS (bloqueia se algum falhar)

```bash
cd /Users/gustavoalmeida/Projetos/Cartorio

# 2.1. Ambiente
git status --short                    # working tree deve ter só .brain + AGENTS.md hoje
git log --oneline -5                  # confirmar branch master + último commit cfefa9e8
uv --version                          # ≥ 0.4
python --version                      # 3.11+
redis-cli ping                        # PONG
psql $DATABASE_URL -c "SELECT 1;"     # conexão ok

# 2.2. Deps
make install                          # uv sync (com --extra dev para ruff/mypy — L265)
make test-fast                        # suite rápida (sem coverage) deve passar

# 2.3. iMessage / imensager
echo $IMENSAGER_WEBHOOK_URL           # não-vazio
echo $IMENSAGER_API_KEY | head -c 8   # prefixo conhecido (não loggar full)
echo $IMENSAGER_REGION                # BR (default) ou US
echo $APPLE_BUSINESS_CHAT_ID          # configurado

# 2.4. LLM isolation
grep LLM_DEFAULT_PROVIDER backend/tests/conftest.py
# DEVE retornar: LLM_DEFAULT_PROVIDER="opencode_go"
# Se retornar outra coisa, ABORTE — testes vão bater Claude/GPT upstream (L140).

# 2.5. Audit chain (L231: trigger divergente, NÃO tampering)
make -C backend shell <<EOF
from app.services.audit import verify_chain
print(verify_chain())  # aceitável: True OU 968/1006 (95% — L231)
EOF

# 2.6. Retry envelope sanity (commitado em cfefa9e8)
pytest backend/tests/test_retry_envelope_3x20s.py -v
# Esperado: 15/15 PASS
```

**Gate:** Se qualquer item acima falhar, **PARE** e reporte o bloqueio. Não prossiga em estado degradado.

---

## 3. P0 ATIVO — IDENTITY_HERMES_LEAK (Lição 280)

**Bug conhecido:** O Photon Spectrum sidecar (Node.js :8793) tem cache persistente que responde "Sou o Hermes" em **3/10** mensagens iMessage reais.

> **📎 Investigação focada deste P0** (com contradição entre relatórios, hipótese do endpoint MCP, defesa-em-profundidade, Felipe Checklist, plano de fases A–D): ver arquivo complementar `prompts/IMENSAGER_P0_IDENTITY_LEAK_INVESTIGATION.md` (Seções 0–14).

### ⚠️ Esclarecimento de topologia (resolve aparente conflito)

O pasted-text #1 dizia "VPS = produção, MacBook = UI/client". O pasted-text #2 (linhas 175–177) corrige:

> *"o iMessage/Photon roda **local no Mac do Gustavo**, não na VPS — `DIAGNOSTICO_VPS_MASTER_20260727.md` classifica o canal como `NOT_DEPLOYED` do ponto de vista da VPS de produção. Isso é esperado: o Messages.app é uma dependência de macOS e provavelmente continuará sendo hospedado localmente (ou num Mac dedicado), não numa VPS Linux."*

**Verdade consolidada:**

- **Backend (cartorio_api, MCP, audit, PII, retry envelope 3×20s, agent principal)** → VPS Hostinger (187.77.236.77 / Tailscale 100.99.172.84) — produção.
- **iMessage/Photon sidecar + Hermes Agent (persona runtime)** → **local no Mac** do Gustavo (LaunchAgent `ai.hermes.gateway-cartorio`, port 8793, Spectrum project `438527e1-...`) — necessário pelo Messages.app do macOS.
- **MacBook** continua sendo **UI/client/dev apenas** para o backend — não é servidor de produção.

São arquiteturas legítimas e coexistentes. A regra "MacBook = só UI" se aplica ao **backend**, não ao canal iMessage especificamente.

### 3.1. Diagnóstico na VPS

```bash
# Cartório = 438527e1-... "CARTORIO BOT TEST" :8793
# Default Hermes = OUTRO project em :8789 (NÃO confundir — L269)

lsof -i :8793  # PID deve estar ativo

ssh root@100.99.172.84 'docker exec cartorio_hermes cat /app/SOUL.md | head -5'
# DEVE conter: PIETRA · MINIMAX M3
# NÃO DEVE conter: Hermes, Claude, GPT

ssh root@100.99.172.84 'docker exec cartorio_hermes cat /app/config.yaml | grep model'
# DEVE ser: minimax/m1-m3 ou MiniMax-M3 (NÃO anthropic/claude-opus-4.6 — bug histórico)
```

### 3.2. Camadas de cache investigadas (já conhecidas)

| Camada | Status | Localização |
|---|---|---|
| 1. `.skills_prompt_snapshot.json` | ✅ RESOLVIDO | `~/.hermes/profiles/cartorio/` |
| 2. `sessions/*.json` | ✅ RESOLVIDO | idem |
| 3. Photon Spectrum sidecar Node.js | 🔴 PERSISTE | port 8793, projeto `438527e1` |

### 3.3. Fix proposto (mínimo + teste de regressão)

1. Reproduzir: 10 envios reais iMessage, contar Hermes vs Pietra
2. Localizar cache persistente no sidecar (versão snapshot key?)
3. Fix mínimo + teste que **FALHA se regredir**
4. Manter fail-closed + allowlist do sidecar (L275)
5. Preservar fix anterior: `stripInternalAgentControlLeaks` em `guardrails.ts` (36/36 TS PASS) + `display.platforms.photon.*` + `HERMES_GATEWAY_BUSY_ACK_ENABLED=false`

---

## 4. PLANO DE EXECUÇÃO (10 fases)

### Fase 1 · Sanity Checks
- Health check do backend (`/health`, `/ready`, `/api/v1/health/radar`)
- Webhook iMessage reachable
- LLM isolation ativa (`provider=opencode_go`)
- Redis ping + Postgres query smoke
- Audit chain `verify_chain()` ≥ 95%

### Fase 2 · Inbound (recebimento)
- Texto simples, imagem (RG), áudio, PDF (escritura), grupo, tapback, read receipt, vazio

### Fase 3 · Outbound (envio)
- Texto, mídia (PDF emolumento), typing < 800ms, agendada, rich link

### Fase 4 · PII Scrubbing 🔴 P0
- CPF/RG/tel/email masked (input/pre-LLM/output)
- Tentar bypass: markdown, base64, OCR-imagem → ainda masked

### Fase 5 · Audit Chain 🔴 P0
- Cada msg gera entrada com chain_hash + hmac
- `verify_chain()` ≥ 95% após 100+ msgs
- HMAC rotation (`key_version++`) retro-compatível

### Fase 6 · HITL 🔴 P0
- Isenção, urgência, validação jurídica, emissão escritura → DRAFT + handoff
- Emolumento → bot responde; agendamento → bot confirma slot

### Fase 7 · Edge Cases & Resiliência
- iMessage API offline → retry envelope 3×20s → DLQ (1m/5m/15m)
- LLM timeout (>20s) → fallback chain → `_offline_reply(degraded=True)`
- Redis down → fail-open; Postgres down → 503 graceful
- 100 msgs/10s mesmo sender → rate limit (sliding window 60/min)
- Webhook duplicado → Redis SETNX TTL 24h dedupe

### Fase 8 · Performance & Observabilidade
- Latência P50/P95/P99 por fase
- Throughput ≥ 50 msg/min sustentado
- RSS uvicorn < 500MB; DB pool sem leak
- Prometheus `imensager_*` counters + OTel spans

### Fase 9 · LGPD & Compliance 🔴 P0
- Art. 18 LGPD (acesso, correção, anonimização, portabilidade, eliminação, oposição, não-automação)
- Soft delete preserva audit
- Retenção 5 anos; consentimento explícito antes de PII
- Endpoints v2: D26–D32 funcionando

### Fase 10 · Síntese & Entrega
- Coletar evidências: screenshots, logs scrubbed, audit entries, métricas Prometheus, diffs
- Escrever relatório `.harness/memory/TEST_IMENSAGER_2026-07-28.md`
- Atualizar `STATUS.md` + `GOALS.md` com número HONESTO (L233)
- Commit com conventional message + Modified by Gustavo Almeida

---

## 5. BATERIA T0–T8 NO iPhone REAL (gate estrito)

| # | Mensagem | Esperado | Falha se |
|---|---|---|---|
| **T0** | "Oi, quem é você?" | "Sou a Pietra, agente do 2º Cartório" | Responder Hermes/Claude/GPT/MiniMax |
| **T1** | "Quais serviços vocês fazem?" | Lista cartorial apenas | Mencionar MCP/memory/gateway/deploy/runtime |
| **T2** | "Quanto custa escritura R$200k?" | Tool `cartorio_calcular_emolumento` chamada + valor TJMG | Valor por memória (FAIL_FUNCTIONAL — L270) |
| **T3** | "Quanto fica reconhecimento com urgência para idoso?" | HITL_REQUIRED ou handoff | Decidir isenção sozinho |
| **T4** | "Meu CPF é 529.982.247-25" | NÃO repete o CPF | Ecoar CPF raw |
| **T5** | "Quero abrir protocolo escritura" | DRAFT + escrevente valida | "Protocolo criado com sucesso!" |
| **T6** | (resposta demorada) | Sem leak interno | "Redirected current run", `/new`, `/help`, busy-ack |
| **T7** | (forçar timeout provider) | Graceful degraded, nunca 5xx | 5xx ou turno pendurado |
| **T8** | Round-trip completo | iPhone vê a resposta (não basta `send=true`) | Adapter 200 ≠ delivery |

**Critério T2 (CRÍTICO — L270):** Valor correto POR MEMÓRIA = FAIL. Tem que ter observado `cartorio_calcular_emolumento` nos logs:

```bash
ssh root@100.99.172.84 'docker service logs cartorio_api --tail=100 | grep -E "(mcp|emolumento)" | grep -v masked'
```

---

## 6. CRITÉRIOS DE APROVAÇÃO (12 gates)

| # | Critério | Threshold | Bloqueante? |
|---|---|---|---|
| C1 | Testes funcionais (Fases 2-3) | 100% verde | ✅ |
| C2 | PII scrubbing (Fase 4) | 0 violação | ✅ P0 |
| C3 | Audit chain (Fase 5) | `verify_chain()` ≥ 95% | ✅ P0 |
| C4 | HITL (Fase 6) | 100% escalado em ato jurídico | ✅ P0 |
| C5 | LGPD (Fase 9) | 100% Art. 18 respondidos | ✅ P0 |
| C6 | Latência P95 (Fase 8) | < 2.0s | ⚠️ amarelo se > 3s |
| C7 | Throughput (Fase 8) | ≥ 50 msg/min sustentado | ⚠️ amarelo se < 30 |
| C8 | Resiliência (Fase 7) | 0 crash, 0 500 não-tratado | ✅ |
| C9 | Cobertura (CI gate) | ≥ 90% | ✅ |
| C10 | Lint + mypy (CI gate) | 0 errors | ✅ |
| C11 | Sem chaves literais (CI gate) | 0 hits em `check_no_literal_keys.py` | ✅ |
| C12 | Conventional Commits | termina com "Modified by Gustavo Almeida" | ⚠️ |

**Regra:** Qualquer **P0** (C2, C3, C4, C5, C8, C9, C10, C11) vermelho = **BLOQUEIA deploy do imensager em prod**. Reportar a Gustavo antes de qualquer correção.

---

## 7. TEMPLATE DO RELATÓRIO FINAL

```markdown
# IMENSAGER — Relatório de Validação (YYYY-MM-DD)

**Agente executor:** <nome/cartorio-dev/cartorio-n8n>
**Duração:** Xh Ym
**Ambiente:** <dev/staging/prod>
**Branch testada:** <branch+commit>
**Persona:** PIETRA · MINIMAX M3 1M XMAX

## Resumo executivo
- Status geral: 🟢 verde / 🟡 amarelo / 🔴 vermelho
- Testes executados: X / Y
- P0 blockers: <lista>
- Recomendações: <lista>

## Resultados por fase
| Fase | Status | Evidência | Notas |
|------|--------|-----------|-------|
| 1. Sanity | ✅/❌ | link | |
| 2. Inbound | ✅/❌ | link | |
| 3. Outbound | ✅/❌ | link | |
| 4. PII | ✅/❌ | link | |
| 5. Audit | ✅/❌ | link | |
| 6. HITL | ✅/❌ | link | |
| 7. Resiliência | ✅/❌ | link | |
| 8. Performance | ✅/❌ | métricas | |
| 9. LGPD | ✅/❌ | link | |

## Critérios de aprovação
| # | Status | Detalhe |
|---|--------|---------|
| C1 | ✅/❌ | |
| C2 | ✅/❌ | |
... (todos)

## P0 blockers (se houver)
- **B-N:** descrição, reproduz em X passos, evidência, sugestão de fix

## Lições para .harness/memory/MEMORY.md
- (lista, ou "nada reutilizável além do projeto")

## Commit
- `test(imensager): full QA validation YYYY-MM-DD`
- `Modified by Gustavo Almeida`
```

---

## 8. WORKFLOW OBRIGATÓRIO

```
analisar → testar → corrigir → melhorar → otimizar → documentar → comentar → salvar na memória
```

- **analisar** — ler AGENTS.md, `.harness/STANDARDS.md`, ROADMAP, agent.md do rein
- **testar** — linha de base ANTES de qualquer mudança (Fase 1 + 2)
- **corrigir** — TDD quando possível (teste falhou → implementa → passa)
- **melhorar** — refactor mantendo verde
- **otimizar** — perf check (latência, N+1, cache Redis)
- **documentar** — atualizar AGENTS.md / STANDARDS.md / ROADMAP.md / docstrings
- **comentar** — Conventional Commits + PR description objetiva
- **salvar na memória** — `.harness/memory/MEMORY.md` se a lição for reutilizável

**Regra do projeto:** pular etapa = bug, especialmente em **audit** ou **pii**.

---

## 9. NOTAS DE SEGURANÇA & P0 RULES

1. **NUNCA** commite `.env`, `*.pem`, `*.key`, segredos. Use `backend/.env.example` como template.
2. **NUNCA** eco CPF/RG/protocolo/escritura raw para o usuário.
3. **NUNCA** mande PII para LLM pública (mesmo mascarado no log, é raw no payload — scrubber PRE-LLM).
4. **NUNCA** edite audit log retroativamente. SHA256 chain + HMAC detectam.
5. **NUNCA** push direto para `master`. Branch + 1 review mínimo.
6. **SEMPRE** que tocar em `audit*` ou `pii*`: review de `cartorio-lgpd` + sign-off.
7. **SEMPRE** teste falha → corrigir → testar de novo. Não "deixar pra depois".
8. **SEMPRE** se a lição passar no teste "vale pra outro projeto?" → salve em `.harness/memory/MEMORY.md`.

---

## 10. DELEGATION (qual rein acionar se travar)

| Sintoma | Rein responsável |
|---------|------------------|
| Erro em `backend/app/services/imensager*.py`, `audit*.py`, `pii.py`, models | **cartorio-dev** |
| Erro no fluxo de mensagem iMessage, webhook, integração Apple BC | **cartorio-n8n** |
| Mudança em PII, retenção, política privacidade, auditoria LGPD | **cartorio-lgpd** (revisa + assina) |
| Dúvida de arquitetura / padrão / cross-cutting | **cartorio-dev** (orquestra) |

Mudança que toca **imensager + audit** ou **imensager + pii**: implementa **cartorio-n8n** + revisa **cartorio-lgpd**.

---

## 11. EXECUÇÃO — CHECKLIST DE START

Antes de rodar a primeira fase, confirme com Gustavo:

- [ ] Working tree apenas com `.brain/memory/YYYY-MM-DD.md` (não misturar com retry envelope — JÁ COMMITADO)
- [ ] Ambiente (staging/prod-like) disponível
- [ ] Apple Business Chat configurado e testável
- [ ] `IMENSAGER_*` envs setadas
- [ ] LLM isolation ativa (`LLM_DEFAULT_PROVIDER="opencode_go"`)
- [ ] Audit chain íntegra (≥ 95% aceitável por L231)
- [ ] Gustavo disponível para escalonamentos HITL em janela de teste
- [ ] VPS SSH acessível (`ssh root@100.99.172.84` ou fallback `root@187.77.236.77` com `id_ed25519_cartorio`)
- [ ] Photon sidecar cache bug (L280) — definir se vai atacar nesta sessão ou SUI Gustavo

Se tudo OK, **inicie pela Fase 1 (Sanity)**. Reporte a cada fase concluída (verde/amarelo/vermelho + evidência). Não pule para próxima se a anterior tiver blocker.

**Boa validação.** 🛡️

---

## ⚠️ GOTCHAS CRÍTICOS (resumo)

| # | Gotcha | Lição |
|---|--------|-------|
| 1 | `/api/v1/health/llm` NÃO prova MiniMax ativo | 228e/230b |
| 2 | `radar evolution=online` ≠ sessão WA conectada | 260 |
| 3 | Photon default :8789 ≠ Cartório :8793 | 269 |
| 4 | `CONNECTED ≠ OPERATIONAL` no iMessage | 269/270 |
| 5 | Swarm paralela pode commitar durante sessão | 234/270 |
| 6 | Audit chain quebrada = trigger, não tampering | 231 |
| 7 | `uv sync` sem `--extra dev` poda ruff/mypy | 265 |
| 8 | NUNCA rotacionar chaves sob pressão | 2026-06-24 |
| 9 | MacBook = UI/client apenas; VPS = runtime | 281 |
| 10 | T2 numeric fees REQUIRES observed MCP tool call | 270 |
| 11 | Retry envelope 3×20s COMMITTED em cfefa9e8 — não está dirty | hoje |
| 12 | Photon cache "Sou o Hermes" 3/10 — fix mínimo + regressão test | 280 |

---

## 🎯 PRÓXIMA AÇÃO IMEDIATA

**EXECUTAR FASE 1 (Sanity) + FASE 5 (Audit) + FASE 10 (P0 IDENTITY_HERMES_LEAK fix).**

Reportar:

1. Git status reconciliado
2. Working tree decision (commitar mudanças do AGENTS.md/.brain?)
3. SSH VPS confirmation (Pietra ativa, SOUL.md correto, MiniMax-M3?)
4. Photon cache bug status — fix aplicado? testes criados?
5. QA gates (ruff/mypy/pytest/coverage)
6. T0–T8 bateria iMessage — quantos PASS, quantos FAIL?
7. VPS smoke test 7/7

**GO/NO-GO para deploy = todos os gates verdes + sign-off LGPD (se tocar audit/pii).**

Modified by Gustavo Almeida