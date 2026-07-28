# Plano — Pietra Super Versão: Aprofundamento de Fixes + Validação 15 Personas + Audit Full + Organização

> **Para agentes executores:** implementar task a task. Steps com checkbox (`- [ ]`).
> Orquestrador: Pietra (TRAE). Execução 100% via subagents sequenciais (regra Gustavo).
> **NUNCA derrubar/reiniciar/desativar nada** — rolling update apenas. Stack vive na VPS: cartorio_hermes, API, Postgres, Redis, MCP, N8N.

**Goal:** Levar a Pietra de baseline humanidade 4.3/10 para ≥8/10 com zero falha P0 em 15 personas (10 originais + 5 novas), com repo/VPS auditados e organizados.

**Architecture:** Canal iMessage (Photon→Hermes gateway Mac) → POST `/api/v1/pietra/chat/completions` (VPS) → sanitize+prompt canônico → MiniMax-M3 → tools MCP. Fixes em 3 camadas: backend (sanitizer/prompt/tools), gateway Hermes (correlation/turn-lock, modelo), operação (audit/organização).

**Tech Stack:** FastAPI, SQLAlchemy 2.0, FastMCP, pytest, Docker Swarm (Easypanel), imsg CLI/osascript, state.db sqlite, subagents TRAE.

**Decisões travadas (Gustavo, 2026-07-28):**
- Modelo: **manter MiniMax-M3** (K3 fora; sanitizer resolve o chinês na saída)
- Validação: **10 personas originais + 5 novas** (teste manual agent-por-agente, SEM pytest-padrão na validação de persona)
- Escopo: **aprofundar fixes** antes do re-teste (agendamento tool loop, dessincronia de turnos, typos PT-BR)
- **NÃO** usar /init nem plugin Lark (workspace já scaffoldado)

---

## Estado Atual (ground truth da exploração)

### Já feito (sessões anteriores desta data)
- 10 personas originais executadas (59 turnos, baseline em `artifacts/personas/*.json` + `RELATORIO_HUMANIDADE_2026-07-28.md`)
- Sanitizador determinístico round 2 em `backend/app/api/v1/pietra.py:495-660` (artifact strip, Photon strip, non-latin retry, anglicismo/PT-PT strip, anti-glitch, contadores `_SANITIZER_STATS`)
- Prompt humanizado + POSTURA RESOLUTIVA + notas técnicas notariais em `PIETRA_SYSTEM_PROMPT` (linhas 470-492)
- Deploy VPS converged; 4/4 validações manuais (condolências, 850, sem artifact, carinho sem nome errado); pytest 39/39; commits até `f9a303c2` pushed
- 15 tools MCP em `backend/mcp_server.py` (emolumento×2, protocolo consultar/criar, segunda via, audit×2, saudação, whatsapp reaction/poll…)
- Runner 10K pausado no checkpoint (50/10.000, 100% PASS)
- Working tree com modificações NÃO commitadas do swarm paralelo (models atendimento/audit_log/base, .brain/memory) — respeitar, não varrer

### Gaps confirmados (evidência do baseline + exploração)
1. **Dessincronia de turnos + artifact na fonte** — sanitizer mitiga na saída, mas raiz está no gateway Hermes (streaming perde pareamento pergunta↔resposta)
2. **Typos PT-BR persistentes** ("quedesignar", "tranqulão", "escribente") — sanitizer cobre idioma/glitch, não ortografia
3. **Agendamento não resolutivo** — tool `agendamento` citada no prompt mas tool loop não cobre criação real de slot; bot deflete p/ telefone
4. **Deflection residual** — baseline mostra "ligue pro cartório" 4x (Seu Jorge); POSTURA RESOLUTIVA deployada precisa de re-validação
5. **Audit full-stack** (VPS/Easypanel/Docker/Traefik/Tailscale/endpoints/logs/lint/pytest/warnings) — pendente
6. **Organização** — arquivos soltos na raiz (lark_bot v1-v6, CHECKLIST, SESSION_INDEX, PNG) e pastas locais
7. **Memória** — Lesson do upgrade + índice MEMORY.md + brain + harness + retomada 10K

---

## Task 1: Re-validação rápida da fonte do chinês (read-only)

**Files:** nenhum (diagnóstico)

- [ ] **Step 1:** Subagent testa 3 mensagens diretas no endpoint prod e loga se alguma volta com não-latino APÓS sanitizer (evidência de que o sanitizer basta):
```bash
for m in "oi, me conta sobre testamento" "meu pai faleceu, e agora?" "quanto custa uma procuracao?"; do
  curl -sk -m 40 -X POST "https://api.2notasudi.com.br/api/v1/pietra/chat/completions" \
    -H "Content-Type: application/json" \
    -d "{\"messages\":[{\"role\":\"user\",\"content\":\"$m\"}]}" | python3 -c "
import sys, json, re
c = json.load(sys.stdin)['choices'][0]['message']['content']
bad = re.findall(r'[Ͱ-ϿЀ-ӿ؀-ۿ぀-ヿ一-鿿가-힯]', c)
print('NON-LATIN' if bad else 'CLEAN', '::', c[:120])"
done
```
Esperado: 3× CLEAN. Se alguma NON-LATIN → abrir bug no sanitizer (adicionar range faltante).
- [ ] **Step 2:** Verificar contadores do sanitizer no log do container: `ssh root@100.99.172.84 "docker service logs cartorio_system-api --tail 200 2>&1 | grep -i sanitizer | tail -5"` — esperado: linhas de retry/fallback = sanitizer ATUANDO em prod.

## Task 2: Fix dessincronia de turnos no gateway Hermes (subagent)

**Files:**
- Modify: `~/.hermes/profiles/cartorio/config.yaml` (fora do workspace — via shell)
- Diagnose: `~/.hermes/profiles/cartorio/logs/agent.log`, `gateway.log`

- [ ] **Step 1:** Subagent lê os últimos 200 lines de gateway.log procurando o padrão "Queued follow-up ... final stream delivery not confirmed" (evidência de race confirmada no baseline). Documentar frequência.
- [ ] **Step 2:** Verificar se config.yaml expõe knob de entrega (ex.: `stream_delivery`, `final_only`, `wait_stream_complete`, `turn_lock`). Se existir: ajustar para enviar SOMENTE a resposta final confirmada do turno (nunca parcial/interrompida). Se NÃO existir: documentar como limitação upstream Hermes + abrir nota no `.harness/memory` (não hackear o venv).
- [ ] **Step 3:** Validar com 1 conversa real de 3 turnos rápidos (fire 3 msgs seguidas sem esperar): contar artifacts/dessincronias ANTES vs DEPOIS do ajuste (se knob existir).

## Task 3: Typos PT-BR — regra determinística leve (subagent)

**Files:**
- Modify: `backend/app/api/v1/pietra.py` (adicionar ao sanitizer)
- Test: `backend/tests/test_pietra_output_sanitizer.py`

- [ ] **Step 1:** Adicionar `_TYPO_MAP` pequeno (só os typos observados no baseline — YAGNI):
```python
_TYPO_MAP: Final[dict[str, str]] = {
    "escribente": "escrevente",
    "tranqulão": "tranquilo",
    "acostumbrado": "acostumado",
    "vizigo": "vizinho",
    "compararse": "comparecer",
    "au caso": "no caso",
    "quedesignar": "que designar",
    "lucinda": "",  # glitch: remover
    "ellos": "eles",
    "se.programando": "se programando",
    "diferentão": "diferente",
}
```
Aplicar após o retry/fallback (última etapa do sanitizer), case-insensitive, com boundary de palavra; remover palavra quando valor vazio. Contador `_SANITIZER_STATS["typo_fix"]`.
- [ ] **Step 2:** Testes: cada entrada do mapa corrige; texto correto intocado; "escritura" NÃO vira "escreventura" (boundary).
- [ ] **Step 3:** `uv run pytest tests/test_pietra_output_sanitizer.py --no-cov -q` 100% + ruff. Commit `fix(pietra): typo map deterministico PT-BR (10 entradas do baseline personas)`. Push.

## Task 4: Agendamento resolutivo (subagent)

**Files:**
- Modify: `backend/app/api/v1/pietra.py` (prompt) + avaliar tool existente
- Read: `backend/app/api/v1/pietra.py:298-310` (endpoint `/agendamento`), `backend/app/models/agendamento.py`

- [ ] **Step 1:** Verificar se o endpoint `criar_agendamento` é funcional (cria slot em DB com status DRAFT/pendente). Teste manual via curl prod com telefone de teste +5534999990001 → esperado 200 com id.
- [ ] **Step 2:** Se funcional: atualizar `PIETRA_SYSTEM_PROMPT` regra de agendamento: quando cliente pedir para agendar, oferecer janela ("manhã/tarde, dia útil") e CONFIRMAR o pré-agendamento via tool/endpoint (nascendo pendente de validação do escrevente), em vez de defletir ao telefone. Se NÃO funcional: documentar gap + manter deflection com justificativa carinhosa (decisão documentada, não omissão).
- [ ] **Step 3:** Teste manual endpoint (2 cenários) + commit `feat(pietra): agendamento resolutivo via pre-booking DRAFT` + push + deploy rolling (rsync+build+service update --force; aguardar "converged").

## Task 5: 5 personas novas (cenários inéditos) — criar fixtures (orquestrador, rápido)

**Files:** Create: `scripts/personas/{mateo-45,ana-38,dona-rosa-72,marcos-29,paulo-60}.json`

- [ ] **Step 1:** Mateo 45 (argentino, RNE, quer autenticar docs): testa nota técnica (d) RNE válido / não exigir CRM.
- [ ] **Step 2:** Ana 38 (vai casar na Itália, apostilamento): testa nota (b) Haia + tradução juramentada.
- [ ] **Step 3:** Dona Rosa 72 (filho no Canadá precisa de procuração): testa nota (c) consulado/apostila/e-Notariado, NUNCA "via Teams".
- [ ] **Step 4:** Marcos 29 (quer agendar escritura pra amanhã de manhã): testa Task 4 (agendamento resolutivo).
- [ ] **Step 5:** Paulo 60 (reclama que cobraram errado, irritado): testa acolhimento de conflito + HITL sem deflection fria.

## Task 6: Deploy rolling + Validação 15 personas (10+5) SEQUENCIAL via subagents

**Files:** `artifacts/personas/*.json` (novos runs sobrescrevem; baseline preservado em git)

- [ ] **Step 1:** Deploy do acumulado (Tasks 3+4) via rsync+docker build+`service update --force` → aguardar "converged". NUNCA scale 0.
- [ ] **Step 2:** Snapshot USER.md/MEMORY.md; gateway kickstart (é restart de processo LOCAL do gateway, permitido — não é derrubar serviço; confirmar UP depois).
- [ ] **Step 3:** 15 subagents SEQUENCIAIS, cada um roda `uv run python ../scripts/imessage_persona_sim.py --persona <slug>` e reporta ok/fail/timeout/warm + 3 observações (mesmo protocolo dos 10 primeiros). Ordem: 10 originais (maria-24 … seu-jorge-67) depois 5 novas.
- [ ] **Step 4:** Subagent analista regenera `RELATORIO_HUMANIDADE_2026-07-28.md` → `..._POS_UPGRADE.md` com tabela comparativa baseline vs pós (humanidade/formalidade/carinho/warm por persona + P0 counts). **Gate:** 0 vazamento multilíngue, 0 artifact, 0 contaminação, 0 nome errado entregues; humanidade média ≥8.

## Task 7: Audit full-stack (subagent auditor, read-only)

**Sem editar nada.** Checklist (cada item: status + evidência 1 linha):
- [ ] VPS: `docker service ls` (todos replicas x/x), `docker ps` sem Restarting, `docker stats --no-stream` mem <85%, disco `df -h` <80%
- [ ] Easypanel: 12 serviços UP; Traefik: routers 6 domínios respondem status esperado (api 200, flow 200, whatsapp 200, supbase 401, easypanel 200, agent 200)
- [ ] Tailscale: `tailscale status` conectado
- [ ] Endpoints API: /health /ready /api/v1/health/radar /api/v1/pietra/health /metrics
- [ ] Logs: system-api sem ERROR/CRITICAL novos (últimas 200 linhas); gateway local sem ERROR não-explicado
- [ ] Repo: `ruff check .` 0, `mypy app/` 0, secret-scan 0 violações, pytest **fast** (`make test-fast` ou lote focado) sem failures; warnings/deprecations catalogados (não precisa zerar DeprecationWarning de deps — catalogar)
- [ ] Produção: radar + `audit/verify` com key (chain_ok) — reportar valor
- [ ] Saída: `docs/AUDIT_FULLSTACK_2026-07-28.md` + 1 parágrafo de GO/NO-GO

## Task 8: Organização (subagent organizer)

- [ ] **Step 1:** Raiz do repo: mover `lark-auth-qr.png`→`artifacts/lark/`, `lark_bot*.py`+`test_lark_bot*.py`+`LARK_BOT*.md`→`scripts/lark/`, `CHECKLIST_VOLTA_MAC_2026-07-28.md`+`SESSION_2026-07-28_INDEX.md`→`docs/sessions/2026-07-28/`, `run_campaign_when_quiet.sh`+`vps_fix_cartorio_hermes_F3.sh`→`scripts/ops/`. Atualizar referências (grep por paths antigos). NÃO mover nada do swarm paralelo em modificação ativa (models, .brain).
- [ ] **Step 2:** `artifacts/imessage/` — consolidar failures/test_results antigos em `artifacts/imessage/campaigns-2026-07-27/` (subpasta). Manter `10k/` e `history/` no topo.
- [ ] **Step 3:** `git status` limpo de untracked restante (commitar ou .gitignore com justificativa). Commit `chore(org): consolida scripts lark/ops, sessões docs/, artifacts por campanha`. Push.

## Task 9: Memória + retomada (orquestrador)

- [ ] **Step 1:** Lesson 294 em `.harness/memory/lesson-294-pietra-super-versao-pipeline-completo-2026-07-28.md` (pipeline: 10 personas → análise → sanitizer → humanização → re-teste 15 → audit → org) + índice MEMORY.md (Etapa 11) + 1 memória de sessão nova (`pietra-resolutiva-vs-deflection`).
- [ ] **Step 2:** Atualizar `.brain/memory/2026-07-28.md` (append, respeitando formato existente do swarm).
- [ ] **Step 3:** Retomar campanha 10K: `nohup backend/.venv/bin/python scripts/imessage_10k_runner.py --all >> artifacts/imessage/10k/campaign.log 2>&1 &` (checkpoint retoma do índice 50).
- [ ] **Step 4:** Commit final `docs(memory): Lesson 294 + sessão personas/audit/org` + push. Relatório final ao Gustavo com scores antes/depois.

---

## Assumptions & Decisions
- Typos: mapa determinístico pequeno (10 entradas observadas), NÃO spell-checker completo (YAGNI, risco de falsos positivos jurídicos)
- Dessincronia: se gateway não expuser knob, documentar como limitação upstream (não hackear venv Hermes)
- Agendamento: se endpoint não for funcional, deflection justificada documentada (não quebrar promessa ao cliente)
- Personas novas rolam DEPOIS do deploy para validar o pacote completo
- Warnings de deps (DeprecationWarning) são catalogados, não zerados (fora do nosso controle)
- Audit é read-only; qualquer fix encontrado vira task nova aprovada antes

## Verification (aceite global)
1. Gate personas: 0 P0 (multilíngue/artifact/contaminação/nome errado) + humanidade ≥8/10 média
2. `pytest tests/test_pietra*` 100% + ruff 0 + mypy 0
3. Audit GO com evidências em `docs/AUDIT_FULLSTACK_2026-07-28.md`
4. Repo organizado: raiz sem arquivos soltos, `git status` limpo
5. 10K rodando em background (checkpoint > 50)
6. Commits pushed; deploy converged; nada derrubado em nenhum momento
