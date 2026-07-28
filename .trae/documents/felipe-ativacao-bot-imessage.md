# Plano — Felipe Pizarro: Ativação Bot iMessage (+1 628 289-3877) + Super Agent Resolutivo

> **Para agentes executores:** implementar task a task. Steps com checkbox (`- [ ]`).
> Orquestrador: Pietra (TRAE). Execução 100% via subagents sequenciais (regra Gustavo).
> **NUNCA derrubar/reiniciar/desativar nada** — rolling update apenas. Stack vive na VPS: cartorio_hermes, API, Postgres, Redis, MCP, N8N.
> **NÃO** usar /init nem plugin Lark (workspace já scaffoldado).

**Goal:** Ativar 100% o bot do Cartório para o Felipe Pizarro (número do agent: +1 628 289-3877) — bot independente, inteligente, resolutivo, sem mandar para telefone/email/endereço, com testes manuais por subagents, memória salva, e validação de todos os modelos MiniMax Coding Plan.

**Architecture:** Photon sidecar (Mac local) → Hermes gateway → VPS API `/api/v1/pietra/chat/completions` → MiniMax-M3 → tools MCP. O número +1 628 289-3877 é o número do AGENT (Hermes cartorio), não do Felipe. O Felipe é +55 34 99880-7228. O erro "number didn't recognize yours" = Felipe não está no allowlist do projeto Photon.

**Tech Stack:** Photon/Spectrum, Hermes gateway, FastAPI, MiniMax Coding Plan, Docker Swarm, subagents TRAE.

**Decisões travadas (Gustavo, 2026-07-28):**
- Foco 100% no problema do Felipe AGORA
- Bot resolve TUDO (atendimento, coleta, documentos, soluções) — só HITL para: pix/pagamento, assinatura/carimbo, integração gov (não temos ainda)
- NÃO mandar para telefone/email/endereço como resposta final
- Testar todos os modelos MiniMax Coding Plan (OAuth Hermes VPS)
- Usar subagents sequenciais, teste manual, não pytest-padrão
- Organizar ambiente local (pastas/arquivos soltos)

---

## Estado Atual (ground truth da exploração)

### Confirmado
- Screenshot WhatsApp: Felipe mandou msg para +1 628 289-3877 e recebeu "This number didn't recognize yours, so the message couldn't be delivered to a project" + link https://app.photon.codes
- Screenshot iPhone: mesma mensagem de erro do Photon
- `~/.hermes/profiles/cartorio/channel_directory.json` = `{"platforms": {"photon": []}}` (vazio)
- `~/.hermes/profiles/cartorio/config.yaml` NÃO EXISTE (profile tem apenas: cache, channel_directory.json, cron, logs, skills, state, state.db)
- Photon app.photon.codes responde "Not authenticated" (precisa auth)
- Número do agent: +1 628 289-3877 (Hermes cartorio) · Número do Felipe: +55 34 99880-7228
- Runner 10K pausado (checkpoint 50/10.000, 100% PASS)
- 15 tools MCP ativas em `backend/mcp_server.py`

### Gaps confirmados
1. **Felipe não está no allowlist do projeto Photon** — o erro é claro: "add your number under Project → Users at https://app.photon.codes"
2. **channel_directory.json vazio** — gateway não tem rota para o número do Felipe
3. **config.yaml ausente** — profile sem configuração de modelo/agent explícita
4. **Bot deflete demais** — baseline mostra "ligue pro cartório" repetidamente
5. **Modelos MiniMax não testados** — falta benchmark de todos os modelos do Coding Plan

---

## Task 1: Adicionar Felipe ao projeto Photon (subagent, manual/UI)

**Files:** nenhum (ação externa)

- [ ] **Step 1:** Subagent orienta Gustavo a acessar https://app.photon.codes → Project → Users → Add User → número `+55 34 99880-7228` (Felipe). Se precisar de auth: Gustavo faz login (é a conta dele).
- [ ] **Step 2:** Confirmar que o número foi adicionado (screenshot ou confirmação do Gustavo).
- [ ] **Step 3:** Subagent envia mensagem de teste do Mac para +1 628 289-3877 via osascript: "Teste de ativação — bot do cartório". Verificar se o Photon aceita (não retorna mais "didn't recognize").

## Task 2: Configurar gateway Hermes para o Felipe (subagent)

**Files:**
- Create/Modify: `~/.hermes/profiles/cartorio/config.yaml` (fora do workspace — via shell)
- Modify: `~/.hermes/profiles/cartorio/channel_directory.json`

- [ ] **Step 1:** Subagent cria `config.yaml` mínimo com: modelo MiniMax-M3, system prompt canônico (referência ao PIETRA_SYSTEM_PROMPT da VPS), max_tokens 4096, temperature 0.7, thinking adaptive OFF para chat simples.
- [ ] **Step 2:** Atualizar `channel_directory.json` para incluir rota photon → VPS API:
```json
{
  "updated_at": "2026-07-28T14:00:00",
  "platforms": {
    "photon": [
      {
        "chat_id": "+16282893877",
        "target": "https://api.2notasudi.com.br/api/v1/pietra/chat/completions",
        "model": "MiniMax-M3",
        "active": true
      }
    ]
  }
}
```
- [ ] **Step 3:** Kickstart gateway local (`launchctl kickstart -k gui/$(id -u)/ai.hermes.gateway-cartorio`) — é restart de processo local, permitido. Confirmar UP via `launchctl list | grep cartorio`.

## Task 3: Teste manual completo com Felipe (subagent, iMessage real)

**Files:** `artifacts/felipe/ativacao_2026-07-28.jsonl`

- [ ] **Step 1:** Subagent envia 5 mensagens de teste do Mac para +1 628 289-3877 (simulando o Felipe): saudação, pergunta sobre endereço, pergunta sobre emolumento, pergunta sobre agendamento, pergunta sobre documentos.
- [ ] **Step 2:** Capturar respostas via state.db (mesmo transport TCC-free). Verificar: (a) respondeu? (b) sem erro "didn't recognize"? (c) sem chinês? (d) sem deflection ("ligue", "mande email")? (e) resolutiva?
- [ ] **Step 3:** Documentar cada resposta em `artifacts/felipe/ativacao_2026-07-28.jsonl` com PASS/FAIL por critério.

## Task 4: Benchmark modelos MiniMax Coding Plan (subagent)

**Files:** `artifacts/models/benchmark_minimax_2026-07-28.md`

- [ ] **Step 1:** Subagent lista modelos disponíveis via `curl https://api.minimax.io/v1/models -H "Authorization: Bearer $MINIMAX_API_KEY"` (ou via OAuth Hermes VPS).
- [ ] **Step 2:** Para cada modelo: medir latência (3 requests), verificar se fala chinês (procurar CJK), verificar context window, custo estimado.
- [ ] **Step 3:** Documentar em `artifacts/models/benchmark_minimax_2026-07-28.md` com tabela: modelo, latência média, chinês?, context, custo, recomendação.

## Task 5: Bot resolutivo — eliminar deflection (subagent)

**Files:**
- Modify: `backend/app/api/v1/pietra.py` (PIETRA_SYSTEM_PROMPT)
- Modify: `~/.hermes/profiles/cartorio/SOUL.md`
- Test: `backend/tests/test_pietra_resolutiva.py`

- [ ] **Step 1:** Atualizar prompt para regra P0: "NUNCA responda apenas 'ligue para o cartorio', 'va ao cartorio', 'fale com o escrevente' ou 'mande um email' para algo que voce mesma pode informar — isso e falha de atendimento. So encaminhe ao escrevente humano para: isencao de custas, urgencia, decisao juridica, validacao, emissao e assinatura de atos — e, nesses casos, explique com carinho que a decisao final e humana por lei (CNS/CNJ), oferecendo o canal humano como complemento, nao como resposta."
- [ ] **Step 2:** Testes: 3 cenários que antes defletiam (agendamento, documentos, emolumento complexo) → agora devem responder diretamente.
- [ ] **Step 3:** Commit + push + deploy rolling (rsync+build+service update --force).

## Task 6: Organização ambiente local (subagent)

**Files:** `scripts/lark/`, `scripts/ops/`, `docs/sessions/`, `artifacts/lark/`

- [ ] **Step 1:** Mover arquivos soltos da raiz: `lark-auth-qr.png`→`artifacts/lark/`, `lark_bot*.py`+`test_lark_bot*.py`+`LARK_BOT*.md`→`scripts/lark/`, `CHECKLIST_VOLTA_MAC_2026-07-28.md`+`SESSION_2026-07-28_INDEX.md`→`docs/sessions/2026-07-28/`, `run_campaign_when_quiet.sh`+`vps_fix_cartorio_hermes_F3.sh`→`scripts/ops/`.
- [ ] **Step 2:** `git status` limpo. Commit `chore(org): consolida scripts lark/ops, sessões docs/, artifacts por campanha`. Push.

## Task 7: Memória + relatório final (orquestrador)

- [ ] **Step 1:** Lesson 295 em `.harness/memory/lesson-295-felipe-ativacao-bot-2026-07-28.md` (problema, solução, config, testes, benchmark modelos).
- [ ] **Step 2:** Atualizar `.brain/memory/2026-07-28.md`.
- [ ] **Step 3:** Relatório final ao Gustavo: status ativação, evidências, próximos passos.

---

## Assumptions & Decisions
- O erro do Felipe é 100% allowlist do Photon (não é bug nosso código)
- O número +1 628 289-3877 é o agent (Hermes cartorio), não o Felipe
- O Felipe é +55 34 99880-7228 (precisa estar no allowlist do projeto Photon)
- Ação no app.photon.codes é manual do Gustavo (auth dele)
- Gateway local pode ser kickstarted (restart de processo local, não é derrubar serviço)
- Deploy VPS é rolling update (nunca scale 0)
- Modelos MiniMax: benchmark read-only, decisão de troca só com evidência

## Verification (aceite global)
1. Felipe consegue enviar msg para +1 628 289-3877 e recebe resposta (sem "didn't recognize")
2. Respostas são resolutivas (sem deflection para telefone/email/endereço)
3. Sem chinês, sem artifact, sem contaminação de contexto
4. Benchmark de modelos documentado
5. Repo organizado, git status limpo
6. Memória salva (Lesson 295 + brain)
7. Nada derrubado em nenhum momento
