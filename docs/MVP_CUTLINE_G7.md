# MVP Cut-line — WhatsApp consult only (G7.23.T4)

| Campo | Valor |
|-------|--------|
| **Task** | G7.23.T4 — MVP cut-line WhatsApp consult only |
| **Wave** | G7 Wave 25 |
| **Rein** | cartorio-brain / cartorio-sre (+ n8n/lgpd em go-live) |
| **North star curto** | Cliente no WhatsApp pergunta emolumento → resposta correta **sem** o bot emitir ato jurídico |
| **Fontes** | `docs/G7_DOR_DOD.md`, `SUPER_GOALS_G7.md`, `AGENTS.md`, `.harness/SUI_CHECKLIST.md`, `docs/WHATSAPP_GUIDE.md` |

---

## 0. Frase de corte (uma linha)

> **MVP = consulta de emolumentos (e status de protocolo read-only) via WhatsApp, com LGPD/audit/PII e HITL obrigatório em qualquer rascunho de protocolo. Tudo que emite, cobra ou decide juridicamente sozinho está FORA.**

Se a feature **não** encaixa nessa frase → **pós-MVP** (backlog G7-S3+), não bloqueia go-live do cut-line.

---

## 1. IN scope (MVP)

### 1.1 Canal e jornada

| # | Capacidade | Done when |
|---|------------|-----------|
| 1 | **WhatsApp** via Evolution (`cartorio-2notas`, state=`open`) | QR SUI + 1 msg real |
| 2 | Webhook dual-format Evolution → API/N8N | payload root **e** `data.message` |
| 3 | **Consulta de emolumento** MG 2026 (tabela oficial) | valor/faixa coerente com `emolumento.py` |
| 4 | FAQ operacional leve (horário, endereço, “falar com humano”) | resposta + handoff path |
| 5 | **Status de protocolo (read-only)** se número informado | sem alterar status |
| 6 | Consent LGPD 1ª mensagem (SIM / PARAR) | audit `consent.whatsapp` |
| 7 | PII 3 camadas (input / pre-LLM / output) | CPF nunca raw em log/LLM |
| 8 | Audit append-only (SHA256 + HMAC) nos eventos de conversa/protocolo | chain verify ok |
| 9 | Handoff humano (Chatwoot ou fila escrevente) quando pedido ou low-confidence | humano assume |
| 10 | Idempotência webhook + rate-limit | sem duplicar resposta em retry |

### 1.2 Intents **permitidos** no bot (automáticos)

- Calcular / estimar **emolumento** (consulta informativa).
- Informar que o valor é **estimativa** e pode depender de análise do escrevente.
- Consultar **status** de protocolo já existente (somente leitura).
- Encaminhar para **atendimento humano**.
- Opt-out LGPD (`PARAR` / `SAIR`).

### 1.3 Tools MCP / API alinhados ao MVP

| Tool / endpoint | MVP? | Nota |
|-----------------|------|------|
| `cartorio_calcular_emolumento` | **SIM** | núcleo do MVP |
| `cartorio_consultar_protocolo` | **SIM** | read-only |
| `cartorio_saudacao` / health | **SIM** | ops |
| `cartorio_criar_protocolo` | **só se DRAFT + HITL** | nasce DRAFT; bot **não** processa |
| `cartorio_gerar_segunda_via` | **NÃO** (pós) | HITL + emissão |
| Pagamento / PIX / boleto | **NÃO** | fora |
| Emissão certidão/escritura | **NÃO** | fora |

---

## 2. OUT of MVP (explícito)

Não implementar, não prometer no bot, não bloquear cut-line por ausência:

| Área | Exemplos | Por quê fora |
|------|----------|--------------|
| **Emissão automática** | certidão, escritura, traslado, 2ª via PDF sem humano | ato notarial / responsabilidade legal |
| **Decisão jurídica sozinha** | isenção, urgência, validade de documento, qualificação | HITL obrigatório (AGENTS P0) |
| **Pagamento** | checkout, PIX cartório, conciliação financeira | compliance + reconciliação |
| **Multi-cartório SaaS** | tenant por CNS, white-label | produto futuro |
| **BI full** | dashboards executivos, funil marketing | não é atendimento MVP |
| **Telegram go-live dual** | parity full com WA | Telegram já serve dev/valida; MVP canal = **WA consult** |
| **OpenClaw cartorio-bot “agentic” full** | tools multi-step sem supervisão | pós G7-S4 |
| **LobeChat UI pública** | chat web agent | pós; não bloqueia WA |
| **Multi-idioma / multi-UF** | emolumento fora MG | tabela MG 2026 only |
| **Agendamento com slot binding** | marca horário e confirma sozinho | handoff/agenda manual ok; auto-book fora |
| **Mutação de dados cadastrais** | correção CPF sem fluxo LGPD Art.18 | direitos LGPD têm fluxo próprio, não bot free-form |

**Regra de ouro:** se a ação **altera estado jurídico ou patrimonial** do cliente → **HITL**, e se não há escrevente no loop → **fora do MVP automático**.

---

## 3. Regras HITL (não negociáveis)

Copiadas e materializadas do contrato do projeto (`AGENTS.md` / `.harness`):

1. **Protocolo sempre nasce `DRAFT`.** Escrevente valida antes de processar.
2. **Bot nunca decide sozinho** em:
   - isenção de emolumentos;
   - urgência / prioridade legal;
   - validação jurídica de documento;
   - emissão de certidão ou escritura;
   - qualquer “está pronto / pode retirar” sem status real no sistema.
3. **Estimativa ≠ cobrança.** Texto de resposta de emolumento deve deixar claro que é **consulta/estimativa** sujeita a conferência.
4. **PII nunca raw** em LLM pública, log, Sentry, ou eco ao usuário (máscara).
5. **Audit é append-only.** Não “corrigir” log retroativo.
6. **Handoff:** em dúvida, baixa confiança LLM, pedido de “falar com alguém”, ou intent fora do cut-line → humano (Chatwoot / fila).

### 3.1 Matriz bot vs humano

| Situação | Bot | Humano |
|----------|-----|--------|
| “Quanto custa reconhecimento de firma?” | Responde estimativa tabela | Confere se caso especial |
| “Meu protocolo 123 está pronto?” | Lê status se existir | Atualiza status no sistema |
| “Preciso de certidão de casamento agora” | Explica processo + handoff | Analisa docs / emite |
| “Sou isento?” | **Não decide** — handoff | Aplica regra legal |
| Cliente manda foto de RG/CPF | Scrub/máscara; não armazenar desnecessário | Fluxo presencial/secure se preciso |
| “Quero pagar pelo WhatsApp” | Fora MVP — orientar canal oficial | Financeiro |

---

## 4. Arquitetura mínima do MVP (caminho feliz)

```
Cliente WA
   │  "quanto custa procuração?"
   ▼
Evolution API (instance open)
   │  webhook MESSAGES_UPSERT (dual-format)
   ▼
N8N e/ou API Cartório
   │  idempotency · PII scrub · consent check
   ▼
Serviço emolumento (tabela MG 2026)
   │  audit log append
   ▼
Resposta texto (estimativa) → Evolution → Cliente
   │
   └─ se intent ≠ consult → handoff Chatwoot / escrevente
```

**Dependências de infraestrutura (MVP):**

| Componente | Papel no MVP |
|------------|--------------|
| `cartorio_api` | regras, emolumento, audit, PII, health |
| `cartorio_evolution-api` | gateway WhatsApp |
| Postgres (Supabase) | persistência mínima |
| Redis | idempotency / rate limit |
| Traefik + LE | TLS público |
| N8N | orquestração webhook (se no path prod) |
| Chatwoot | handoff (pode ser degradado se 502, com fila alternativa documentada) |

OpenClaw/LobeChat/Telegram **não** são bloqueantes do cut-line se o caminho WA→emolumento→resposta estiver verde.

---

## 5. Critérios de aceite do MVP (Definition of Done cut-line)

### 5.1 Funcional (1 mensagem real)

- [ ] Instance Evolution `cartorio-2notas` com `state=open`
- [ ] Mensagem real do celular de teste → resposta de **emolumento** em &lt; 30s (meta soft &lt; 10s)
- [ ] Resposta **não** afirma emissão concluída nem isenção automática
- [ ] Segunda mensagem “falar com atendente” → handoff ou instrução clara
- [ ] Opt-out `PARAR` respeitado

### 5.2 Compliance

- [ ] Consent na primeira interação
- [ ] Sem CPF raw em logs da resposta
- [ ] Evento de audit para a consulta / conversa
- [ ] Protocolo, se criado, permanece `DRAFT` até humano

### 5.3 Ops

- [ ] `GET https://api.2notasudi.com.br/health` → 200
- [ ] `GET .../api/v1/health/radar` alcançável; `database` + `redis` + `evolution` online (ou HOLD documentado)
- [ ] Runbook de rollback conhecido (`docs/CD_EASYPANEL_HOOK_G7.md` §6)

---

## 6. Go-live checklist **subset** (só o que o MVP exige)

Subset de `.harness/SUI_CHECKLIST.md` + SUI packs G7 — **não** o plano 100 tasks inteiro.

### 6.1 Bloqueantes (must)

| # | Item | Owner | Evidência |
|---|------|-------|-----------|
| M1 | API healthy (`/health`, `/ready`) | SRE | curl 200 |
| M2 | `DATABASE_URL` / Redis corretos nos services (Lesson 176) | SRE/Gustavo | radar DB+redis online |
| M3 | Evolution UP (não 502) | SRE | `whatsapp.` HTTP≠502 |
| M4 | WhatsApp QR → `state=open` | **Gustavo SUI** | Manager UI |
| M5 | Webhook Evolution apontando path correto + HMAC | n8n/dev | 1 event ingest |
| M6 | Emolumento path (API e/ou N8N WF consulta) ativo | n8n/dev | msg teste |
| M7 | PII + audit ligados em prod | lgpd/dev | flags env |
| M8 | Texto de disclaimers (estimativa / não é emissão) | brain/lgpd | copy aprovada |

### 6.2 Importantes mas **não** bloqueiam cut-line WA consult

| # | Item | Nota |
|---|------|------|
| S1 | DNS aliases `chatwoot` / `n8n` / `supabase` | canônicos `chat`/`flow`/`supbase` bastam se usados |
| S2 | Chatwoot 502 resolvido | handoff degradado; ainda pode ter fila humana offline |
| S3 | Telegram token/webhook | canal paralelo |
| S4 | LobeChat key / OpenClaw agent full | G7-S4 |
| S5 | `/radar/expanded` 200 | nice-to-have ops |
| S6 | Composite gate prod exit 0 | local 0 + prod HOLD ok para agent-side |

### 6.3 Sequência recomendada no dia D

```
1. Radar API + DB + Redis
2. Evolution health + state open
3. Msg teste "quanto custa reconhecimento de firma?"
4. Validar disclaimer + valor
5. Msg "quero falar com alguém" → handoff
6. Msg com CPF fake → confirmar máscara (não eco raw)
7. Registrar evidência em PROGRESS / paperclip
8. Só então comunicar "MVP WhatsApp consult live" ao cartório
```

---

## 7. Fora do discurso comercial (anti-overpromise)

**Pode dizer ao cliente/usuário interno:**

- “O assistente consulta **estimativas de emolumentos** e tira dúvidas básicas 24/7.”
- “Protocolos e atos finais passam pelo **escrevente**.”

**Não dizer:**

- “O bot emite certidão.”
- “O bot aprova isenção.”
- “Pagamento completo pelo WhatsApp” (MVP).
- “Substitui o atendimento do cartório.”

---

## 8. Relação com sprints SUPER_GOALS

| Sprint | vs cut-line MVP |
|--------|-----------------|
| G7-S0 / S1 | Pré-requisito infra (radar, DNS/env) |
| **G7-S2** | **= cut-line** (WA QR + 1 msg real emolumento) |
| G7-S3+ | Telegram dual, Chatwoot full, agent, LGPD DPA sign-off estendido, coverage 96%… |

Fechar **G7.23.T4** documenta o corte; **fechar G7-S2** prova o cut-line em prod.

---

## 9. Referências

- `docs/G7_DOR_DOD.md` — DoR/DoD + rascunho cut-line
- `docs/CD_EASYPANEL_HOOK_G7.md` — deploy / rollback / radar
- `docs/WHATSAPP_GUIDE.md` — operação canal
- `docs/EVOLUTION_DATABASE_URL_QR_CHECKLIST_G7.md` — SUI Evolution
- `docs/CHATWOOT_HANDOFF_G7.md` — handoff
- `.harness/SUI_CHECKLIST.md` — blockers UI
- `SUPER_GOALS_G7.md` — G7-S2

---

**Modified by Gustavo Almeida** — G7 Wave 25 (G7.23.T4)
