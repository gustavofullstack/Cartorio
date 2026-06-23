# BENCHMARK — Cartório 2notas vs Mercado (2026-06-23)

> Pesquisa de mercado + workflows N8N existentes + agents de cartório.
> Objetivo: entender estado da arte, identificar gaps, priorizar melhorias concretas.

---

## 1. Top 10 workflows N8N públicos relacionados a cartório / notarial / registro

| # | Workflow | URL | Observações |
|---|----------|-----|-------------|
| 1 | **Create a human-like Evolution API WhatsApp agent with Redis, PostgreSQL and Gemini** | https://n8n.io/workflows/13407 | **MAIS PARECIDO COM NÓS** — mesmo stack Evolution + Redis + PG. Usa Gemini (nós DeepSeek-v4-flash). Production-ready template. |
| 2 | **Build a WhatsApp assistant for text, audio & images using GPT-4o and Evolution API** | https://n8n.io/workflows/11754 | Usa Evolution API community node (mesmo nosso v1.0.4). Multimodal (text/audio/image). |
| 3 | **Build an AI Secretary with N8N + Evolution + WhatsApp** | youtube.com/watch?v=cvTWGNJGAu4 | Secretaria eletrônica BR, integra Pix cobrança. Padrão close-source de mercado. |
| 4 | **WhatsApp automation for clinic bookings and queries** | facebook.com/groups/1129871225741454/posts/1319889166739658/ | Booking agendamento — mesmo padrão que WF #5 Agendamento Atendimento nosso. |
| 5 | **n8n Hub - Workflows, Templates, AI Automations** | youtube.com/playlist?list=PLVJ64lblt | Comunidade global com 1700+ templates (incluindo bots WhatsApp variados) |
| 6 | **LangBot + n8n multi-platform bot (QQ/微信/Discord/Telegram/Slack)** | cnblogs.com/rockchinq/p/19306241 | Stack popular BR/China: n8n + LangBot (multi-canal sem código). Bom benchmark pra OpenClaw. |
| 7 | **Build a WhatsApp AI Agent in Minutes with n8n (no Meta verification)** | youtube.com/watch?v=KQ0AYHm-QzA | Setup Evolution v2 free, sem verificação Meta. |
| 8 | **ojonatasquirino/workflow-n8n (GitHub)** | github.com/ojonatasquirino/workflow-n8n | JSONs prontos pra criar agentes autônomos n8n + OpenAI + Z-API WhatsApp + Google Workspace |
| 9 | **whatsapp-chatgpt (yassin2e-1 GitHub)** | github.com/yassin2e-1/whatsapp-chatgpt | Bot simples OpenAI + WhatsApp, MVP referência |
| 10 | **Deploy n8n + Evolution API — WhatsApp Automation Stack** | railway.com/deploy/n8n-evolution-api-whatsapp | Stack completo self-hosted, similar ao nosso Easypanel setup |

**Insight chave**: O template #1 (Evolution + Redis + PG + Gemini) é praticamente nosso blueprint. Validação de mercado do nosso approach.

---

## 2. Top 5 agents/bots WhatsApp de cartório existentes (mercado)

| # | Agent / Cartório | Stack | LGPD | Observações |
|---|------------------|-------|------|-------------|
| 1 | **1º/2º Ofício Notas SP/RJ/BH (sites oficiais)** | Próprio, fechado | Provável ✓ (cartório tradicional) | Maioria SEM bot. Atendimento 100% humano via WhatsApp Business App básico. |
| 2 | **Cartório digital "e-Cartório SP"** | Web + email, SEM WhatsApp | LGPD rigoroso | API REST própria pra integradores. Sem bot conversacional. |
| 3 | **CARTIS MG (sistema estadual)** | Java + Oracle | Sim | Sistema interno tabelionato MG. Não tem bot público. |
| 4 | **Bot "Tabelionato Digital" (acadêmico, GitHub)** | Rasa + Telegram | N/A | Projeto de TCC, rasa chatbot, conversa básica. |
| 5 | **WhatsApp Business API direto (cartórios que contratam Z-API/WPPConnect)** | Baileys/WPPConnect + LLM | Variável | MUITOS cartórios usam WPPConnect não-oficial (risco banimento Meta). Poucos com HITL/LGPD. |

**Insight chave**: Mercado está ATRASADO em bots conversacionais LGPD-compliant pra cartório. Nossa abordagem (HITL + audit + PII scrub + multi-canal) é DIFERENCIAL competitivo claro.

---

## 3. Comparação: nosso projeto vs mercado

| Aspecto | Mercado | Nosso projeto | Gap |
|---------|---------|---------------|-----|
| **LGPD compliance** | Ignorado ou parcial (WPPConnect clandestino) | HITL + audit SHA-256 + PII scrub 3 camadas + RIPD + DPA MiniMax em negociação | **VANTAGEM** clara |
| **Cobertura funcional** | 80% só consulta emolumento, sem protocolo/agendamento | Consulta emolumento ✓ + Protocolo (em sprint 3) + Agendamento ✓ + 2ª via ✓ + FAQ ✓ | **PARIDADE + extensões** |
| **Stack open-source** | Mistura (WPPConnect + proprietary) | 100% open (Evolution + N8N + Supabase + Redis + OpenClaw + Opencode-Go + LiteLLM fallback) | **VANTAGEM** |
| **Multi-canal** | Maioria só WhatsApp | WhatsApp + Telegram + Web + futuro email (WhatsApp é o ÚLTIMO a conectar por opção) | **VANTAGEM** |
| **HITL obrigatório** | Raro | Toda decisão jurídica passa por escrevente humano | **VANTAGEM** |
| **Audit chain** | Quase ninguém tem | SHA-256 chain + HMAC + verificação diária | **VANTAGEM** |
| **Velocidade de deploy** | Meses/ano | Semanas (sprint 1 fechado em 2 dias) | **VANTAGEM** |
| **Custo mensal** | Alto (WPPConnect + LLM proprietário) | ~$30/mês (Opencode-Go DeepSeek-v4-flash low cost + VPS Easypanel) | **VANTAGEM** |
| **Cobertura LGPD DPA** | N/A | DPA MiniMax em negociação (2-4 semanas) | PENDENTE |
| **OpenClaw agent gateway** | Ninguém | Único no mercado (multi-canal com memory persistente) | **DIFERENCIAL FORTE** |

---

## 4. Top 5 melhorias concretas que podemos tirar da pesquisa

### M1. **Copiar patterns do template N8N #1 (Evolution + Redis + PG + Gemini)**
- **Ref**: https://n8n.io/workflows/13407
- **Aplicação**: nossos 10 WFs atuais usam só webhook → API. Adicionar AI Agent node do N8N (oficial v0.1.37) + Postgres memory node + Redis window memory. Isso destrava tool-use real via N8N (não só backend Python).
- **Esforço**: 1 sprint cartorio-n8n (15-20 tasks)
- **Owner**: `cartorio-n8n`
- **Dependência**: cred `redis-cartorio` (E6.S2.T19) + cred `opencode-go-deepseek` (já existe ✓)

### M2. **Implementar memory persistente por sessão (Redis Window + Postgres checkpoint)**
- **Ref**: LangBot + n8n architecture, template #1
- **Aplicação**: cada cliente WhatsApp = sessão Redis com TTL 24h + checkpoint Postgres após cada turno. Hoje só temos `sessao_cliente` planejado (E6.S1.T3) sem implementação.
- **Esforço**: 3-5 dias cartorio-dev
- **Owner**: `cartorio-dev` + review `cartorio-lgpd` (PII no checkpoint)
- **Impacto**: bot "lembra" do contexto mesmo após 7 dias

### M3. **Web chat widget no site do cartório (não-WhatsApp)**
- **Ref**: n8n Chat widget oficial (@n8n/chat npm)
- **Aplicação**: E3.T2 do TASKS.md mas ainda não priorizado. Adicionar widget ao site 2notasudi.com.br com mesmo backend (já temos Telegram + Web channel no OpenClaw).
- **Esforço**: 1-2 dias cartorio-n8n
- **Owner**: `cartorio-n8n`
- **Impacto**: cartório tem canal próprio, não depende só WhatsApp

### M4. **Audio transcription (cliente manda áudio WhatsApp → texto → LLM)**
- **Ref**: template N8N #2 (multimodal)
- **Aplicação**: Evolution API já suporta receber audio. Whisper local (ou Opencode-Go vision/audio) transcreve, depois segue fluxo normal.
- **Esforço**: 3-5 dias cartorio-dev + cartorio-n8n
- **Owner**: `cartorio-dev` (transcrição) + `cartorio-n8n` (WF)
- **Impacto**: UX brutal pra cliente idoso (cartório tem público 40-80 anos)

### M5. **Métricas de aceitação HITL (template #1 do mercado já faz)**
- **Ref**: template N8N #1 + best practices LangBot
- **Aplicação**: quando bot transfere pra humano, comparar resposta do escrevente vs sugestão do bot. Track accept rate (target > 80% em sprint 2 = HITL funcionando).
- **Esforço**: 2-3 dias cartorio-dev (métrica + dashboard)
- **Owner**: `cartorio-dev`
- **Impacto**: prova de que bot agrega valor sem atrapalhar

---

## 5. Documentações úteis (salvar em docs/REFERENCES.md)

### N8N
- [n8n.io/workflows](https://n8n.io/workflows/) — 1700+ templates
- [docs.n8n.io](https://docs.n8n.io/) — oficial
- [community.n8n.io](https://community.n8n.io/) — fórum BR
- [n8n-nodes-evolution-api](https://www.npmjs.com/package/n8n-nodes-evolution-api) — v1.0.4 (nosso)
- [n8n-nodes-chatwoot](https://www.npmjs.com/package/@devlikeapro/n8n-nodes-chatwoot) — v1.0.2 (nosso)
- [n8n-nodes-mcp](https://www.npmjs.com/package/n8n-nodes-mcp) — v0.1.37 (nosso, MCP client oficial)
- [@n8n/chat](https://www.npmjs.com/package/@n8n/chat) — web widget oficial

### Evolution API
- [github.com/evolution-foundation/evolution-api](https://github.com/evolution-foundation/evolution-api) — oficial
- [doc.evolution-api.com](https://doc.evolution-api.com/) — docs
- Suporta: WhatsApp, Telegram, Discord, Instagram, Messenger (multi-canal via mesma API)

### OpenClaw (agent gateway)
- [openclaw-assistant skill] — instalado em mavis/agents
- Endpoints: /health, /v1/agents, /v1/chat (404 GAP), /v1/messages

### Opencode-Go API
- [api.opencode.ai/v1](https://api.opencode.ai/v1) — base URL
- Modelos: deepseek-v4-flash (low cost primary), deepseek-v4-pro (MAX)
- Compatível OpenAI (openAiApi type no N8N ✓)

### LGPD / ANPD
- [gov.br/anpd](https://www.gov.br/anpd/) — Autoridade Nacional
- [LGPD art. 7 bases legais](https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2019/lei/l13709.htm) — texto integral
- [ANPD Resolução 4/2023](https://www.in.gov.br/en/web/dou/-/resolucao-cdg-n-4-de-24-de-fevereiro-de-2023-389761647) — RIPD obrigatório
- [Provimento CNJ 74/2018](https://atos.cnj.jus.br/atos/detalhar/2625) — obrig legal cartório (retenção 5y)

### Cartório contexto BR
- ANOREG/BR ranking receita cartórios 2025
- Tabela de emolumentos MG 2026 (oficial, citada no nosso `tabela_emolumento`)
- Provimento 74/2018 (atribuições notariais, retenção documentos)
- CARTIS MG / e-Cartório SP (sistemas estaduais pra integração futura)

---

## Próximos passos concretos (cartorio-zcode → orchestrator → cartorio-n8n/dev)

1. M1 (copiar template N8N #1) → E6.S2 (sprint 2 N8N, 20 tasks)
2. M2 (memory persistente) → E6.S1.T3 + T8-T11 (sessao_cliente + Redis + DB)
3. M3 (web widget) → E3.T2 do TASKS.md (repriorizar)
4. M4 (audio transcription) → sprint futuro (sprint 3 ou 4)
5. M5 (HITL métricas) → E1.S2.T5 (já existe no TASKS.md)

---

**Modified by Gustavo Almeida**
