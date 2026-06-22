# TASKS — Cartorio Chatbot

Task tree em formato Epic / Sprint / Task. Fonte da verdade para priorizacao e sequenciamento. Atualizar quando uma task mudar de status ou descobrir dependencia nova.

> **Legado**: `docs/ROADMAP.md` mantem a visao de 12 semanas (linguagem de negocio). Este arquivo decompoe em unidades executaveis com dono (rein) e criterios de done.

---

## EPIC E0 — Foundation (Semana 1-2)

Status: **em andamento** (sprint 0 commitado em `81b4893`).

### Sprint 0 — Skeleton [DONE]
- [x] **E0.S0.T1** Repo backend skeleton + pyproject + ruff + pytest — owner: `cartorio-dev` — done em `81b4893`
- [x] **E0.S0.T2** 5 modelos SQLAlchemy (cliente, conversa, protocolo, documento, emolumento) + audit_log — owner: `cartorio-dev`
- [x] **E0.S0.T3** Service `audit` com hash chain SHA256 + HMAC — owner: `cartorio-dev` + review `cartorio-lgpd`
- [x] **E0.S0.T4** Service `pii` com scrubber CPF/RG/telefone/email — owner: `cartorio-dev` + review `cartorio-lgpd`
- [x] **E0.S0.T5** Service `emolumento` com calculo de regras basicas — owner: `cartorio-dev`
- [x] **E0.S0.T6** 22 testes pytest (audit + pii + emolumento), coverage >= 90% — owner: `cartorio-dev`

### Sprint 0.5 — Infra base
- [ ] **E0.S0.5.T1** Rodar migrations Alembic em Supabase staging — owner: `cartorio-dev`
  - Done: schema completo no Postgres, tabelas criadas, indices em `cliente.cpf_hash` e `protocolo.numero`
- [ ] **E0.S0.5.T2** DNS + HTTPS (cartorio.com.br → Caddy/Traefik no Easypanel) — owner: `cartorio-n8n`
- [ ] **E0.S0.5.T3** Backup automatizado Postgres (snapshot diario, retencao 30d) — owner: `cartorio-lgpd` (compliance de retencao) + `cartorio-n8n` (execucao)
- [ ] **E0.S0.5.T4** Seed inicial de `tabela_emolumento` MG 2026 — owner: `cartorio-dev`

---

## EPIC E1 — MVP WhatsApp (Semana 3-8) — CORTE ESTRATEGICO CEO

> Decisao D3.1 (ceo-assistant): Sprint 1 faz SÓ consulta de emolumento. Status protocolo so no Sprint 2. Criar protocolo so apos 30 dias de shadow mode.

### Sprint 1 (sem 3-4) — SO CONSULTA EMOLUMENTO
- [ ] **E1.S1.T1** Workflow n8n #1: msg WhatsApp -> Evolution -> OpenClaw -> API regras -> resposta — owner: `cartorio-n8n`
- [ ] **E1.S1.T2** Endpoint `GET /api/v1/emolumento/calcular` polish + OpenAPI documentado — owner: `cartorio-dev`
- [ ] **E1.S1.T3** Integracao LiteLLM (Claude Opus 4.5 primary, GPT-5.5 fallback, Gemini/Llama router intencao) — owner: `cartorio-dev`
- [ ] **E1.S1.T4** PII scrubbing regex-only (latencia < 5ms) ANTES de chamar LLM — owner: `cartorio-dev` + review `cartorio-lgpd`
- [ ] **E1.S1.T5** Template de resposta WhatsApp: "emolumento X custa R$ Y, prazo Z" — owner: `cartorio-n8n`
- [ ] **E1.S1.T6** Health check `/health` com smoke do hash chain — owner: `cartorio-dev`
- [ ] **E1.S1.T7** Teste E2E: webhook Evolution -> resposta WhatsApp com PII zero no payload externo — owner: `cartorio-dev`
- **KPI Sprint 1**: 100 consultas/dia, 0 erro de valor, 0 handoff humano.

### Sprint 2 (sem 5-6) — STATUS PROTOCOLO + SHADOW MODE
- [ ] **E1.S2.T1** Endpoint `GET /api/v1/protocolo/{numero}` — owner: `cartorio-dev`
- [ ] **E1.S2.T2** Workflow n8n #2 (shadow mode): bot sugere resposta, escrevente envia, comparacao automatica — owner: `cartorio-n8n`
- [ ] **E1.S2.T3** HITL escalonado nivel 1 (read_only bot responde sozinho com confidence >= 0.85) — owner: `cartorio-dev`
- [ ] **E1.S2.T4** Dashboard escrevente: msg recebida, intencao detectada, resposta sugerida, quem enviou — owner: `cartorio-n8n` (UI) + `cartorio-dev` (API)
- [ ] **E1.S2.T5** Metrica de aceitacao de sugestao (comparacao automatica) — owner: `cartorio-dev`
- **KPI Sprint 2**: 95% das sugestoes aceitas sem edicao.

### Sprint 3 (sem 7-8) — CRIAR PROTOCOLO (so pos 30d shadow)
- [ ] **E1.S3.T1** Endpoint `POST /api/v1/protocolo` via conversa (HITL nivel 2 - create_draft) — owner: `cartorio-dev`
- [ ] **E1.S3.T2** Endpoint `POST /api/v1/cliente` com consentimento LGPD obrigatorio — owner: `cartorio-dev` + review `cartorio-lgpd`
- [ ] **E1.S3.T3** Upload documento via Supabase Storage com hash SHA256 — owner: `cartorio-dev`
- [ ] **E1.S3.T4** Notificacao proativa: "seu protocolo #X avancou pra em_andamento" — owner: `cartorio-n8n`
- [ ] **E1.S3.T5** Dashboard React basico para escrevente — owner: `cartorio-n8n`
- **KPI Sprint 3**: 50% dos protocolos novos criados via bot (restante via balcao).

---

## EPIC E2 — Compliance + Hardening (Semana 7-8)

> Paralelo ao E1.S3. LGPD nao espera bot ganhar write access.

- [ ] **E2.T1** RIPD (Relatorio de Impacto a Protecao de Dados Pessoais) — owner: `cartorio-lgpd`
- [ ] **E2.T2** DPO designado e contato publicado no site/chat — owner: `cartorio-lgpd` + `cartorio-n8n` (UI)
- [ ] **E2.T3** Politica de privacidade + termo de consentimento no chat — owner: `cartorio-lgpd` (texto) + `cartorio-n8n` (entrega)
- [ ] **E2.T4** Direito ao esquecimento (endpoint `DELETE /cliente/{id}` + cascade) — owner: `cartorio-dev` + review `cartorio-lgpd`
- [ ] **E2.T5** Retencao automatica (job diario apaga conversas > 365d) — owner: `cartorio-lgpd` (politica) + `cartorio-dev` (execucao)
- [ ] **E2.T6** Logs de acesso (LGPD art. 37) — owner: `cartorio-lgpd`
- [ ] **E2.T7** Pen-test basico (Burp Suite + OWASP top 10) — owner: `cartorio-lgpd` (coordena)
- [ ] **E2.T8** Rate limiting (60 req/min/IP) — owner: `cartorio-dev`
- [ ] **E2.T9** WAF Cloudflare — owner: `cartorio-n8n`

---

## EPIC E3 — Multi-canal + Escala (Semana 9-10)

- [ ] **E3.T1** Telegram bot (mesma API, gateway OpenClaw) — owner: `cartorio-n8n`
- [ ] **E3.T2** Web widget no site do cartorio — owner: `cartorio-n8n`
- [ ] **E3.T3** Email integration (Resend ou SES) — confirmacoes, PDFs assinados — owner: `cartorio-n8n`
- [ ] **E3.T4** LiteLLM gateway em HA (2 replicas, fallback automatico) — owner: `cartorio-dev`
- [ ] **E3.T5** LLM local Llama 3.1 8B para PII scrubbing (zero dado vai pra API publica) — owner: `cartorio-dev` + review `cartorio-lgpd`
- [ ] **E3.T6** Cache Redis para tabela de emolumentos (atualizacao diaria) — owner: `cartorio-dev`

---

## EPIC E4 — Premium + Assinatura Digital (Semana 11-12)

- [ ] **E4.T1** Integracao gov.br/ICP-Brasil para assinatura digital — owner: `cartorio-dev` (API) + `cartorio-n8n` (UI)
- [ ] **E4.T2** Geracao de PDF final com carimbo de tempo — owner: `cartorio-dev`
- [ ] **E4.T3** Validacao humana obrigatoria antes de aplicar isencao — owner: `cartorio-dev` + review `cartorio-lgpd`
- [ ] **E4.T4** Relatorio mensal de auditoria (gerado automaticamente do audit_log) — owner: `cartorio-lgpd`
- [ ] **E4.T5** SLA dashboards (tempo medio, fila, gargalos) — owner: `cartorio-n8n`
- [ ] **E4.T6** Documentacao de operacao para o cartorio (runbook) — owner: `cartorio-lgpd` (compliance) + `cartorio-dev` (tecnico)

---

## EPIC E5 — Pos-12 semanas (backlog)

- [ ] **E5.T1** (Q3 2026) Integracao com sistema estadual (CARTIS MG, e-Cartorio SP) — owner: `cartorio-dev`
- [ ] **E5.T2** (Q3 2026) App mobile nativo (React Native) com biometria — owner: `cartorio-n8n`
- [ ] **E5.T3** (Q4 2026) Multi-cartorio (white label, replicacao) — owner: `cartorio-dev`
- [ ] **E5.T4** (Q1 2027) BI dashboard executivo (Looker/Metabase) — owner: `cartorio-n8n`
- [ ] **E5.T5** (Q2 2027) Integracao com Juizado Especial Federal (procuracoes) — owner: `cartorio-dev`

---

## Matriz de dependencia cross-rein

| Task | Requer de outro rein |
|------|----------------------|
| E1.S1.T4 (PII pre-LLM) | review `cartorio-lgpd` |
| E1.S2.T4 (Dashboard) | API do `cartorio-dev` |
| E1.S3.T2 (Cliente com consentimento) | policy texto do `cartorio-lgpd` |
| E2.T4 (Direito esquecimento) | review `cartorio-lgpd` |
| E2.T5 (Retencao) | policy do `cartorio-lgpd` + execucao `cartorio-dev` |
| E3.T5 (LLM local PII) | review `cartorio-lgpd` (zero dado pra API publica) |
| E4.T3 (HITL isencao) | review `cartorio-lgpd` (decisao final sempre humana) |

## Riscos ativos

| Risco | Mitigacao | Dono |
|-------|-----------|------|
| Hallucination LLM em valor juridico | HITL obrigatorio em toda decisao final | `cartorio-dev` |
| LGPD: vazamento de CPF | PII scrubbing em 3 camadas | `cartorio-lgpd` |
| Disponibilidade WhatsApp | Multi-canal (Telegram, Web) como fallback | `cartorio-n8n` |
| Ataque a audit log | HMAC + hash chain + verificacao automatica diaria | `cartorio-dev` |
| Cartorio pequeno: resistencia a mudanca | Treinamento, runbook, dashboard simples | `cartorio-lgpd` (material) + `cartorio-n8n` (UI) |

## Convecoes de status

- `[ ]` pending
- `[~]` em andamento (algum commit, nao fechado)
- `[x]` done (commit reference no PR)
- `[!]` blocked (anotar blocker no comment da task)
- `[?]` precisa discussao (anotar duvida)

Modified by Gustavo Almeida
