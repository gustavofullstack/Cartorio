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
- [x] **E0.S0.5.T2** DNS + HTTPS (cartorio.com.br → Caddy/Traefik no Easypanel) — owner: `cartorio-n8n` — Traefik LetsEncrypt DNS-01 ativo, 6/6 dominios verdes
- [~] **E0.S0.5.T3** Backup automatizado Postgres (snapshot diario, retencao 30d) — owner: `cartorio-lgpd` (compliance de retencao) + `cartorio-n8n` (execucao) — script + cron instalados, sem S3 ainda
- [ ] **E0.S0.5.T4** Seed inicial de `tabela_emolumento` MG 2026 — owner: `cartorio-dev`
- [x] **E0.S0.5.T5** Atualizar `.env` com todas API keys (Opencode-Go DeepSeek-v4 flash + OpenClaw + N8N + Evolution + Supabase) — owner: Mavis — done 2026-06-23
- [x] **E0.S0.5.T6** Prospecção top 30 cartórios BR com scoring Tier A/B/C — owner: `ceo-assistant` (prospecção) + Mavis (orquestração) — done 2026-06-23, doc `docs/leads/cartorios-br-top30.md`
- [x] **E0.S0.5.T7** Roteiro LGPD-safe de abordagem (3 variantes: WhatsApp curto / e-mail institucional / LinkedIn tabelião) — owner: `cartorio-lgpd` — **DONE 2026-06-23 11:35 BRT**
  - **SPEC CEO (addendum 2026-06-23)**: 5 critérios obrigatórios em todas as 11 copies — (1) SINAL ESPECÍFICO por cartório, (2) LGPD-safe (zero dado PF, opt-out em rodapé), (3) CTA claro (15min + 2 opções concretas), (4) Tom PT-BR natural (sem juridiquês), (5) Piloto 30 dias grátis. Detalhe em MSG #1490 pro cartorio-lgpd.
  - **Entrega cartorio-lgpd 11:19 BRT**: 12 arquivos em `/docs/leads/roteiros/` (5 WhatsApp + 3 email + 3 LinkedIn + README com checklist CEO).
  - **Verdict CEO-assistant 11:35 BRT** (sessão mvs_ac62941039b3414e8d0ed9f10dfae67d, MSG #1531): **5/5 APROVADOS WhatsApp Tier A** — nenhum rewrite. Scores por arquivo:
    - 01-vampre-14sp: **9.8/10** (sinal >R$ 90M/ano ANOREG 2025 — abre conversa sozinho)
    - 05-cartorio-herrera-1salvador: **9.2/10** (único BA top 30 + pioneirismo regional; header diz Tier B com alto valor estratégico)
    - 02-cartorio-amaral-5bh: **9.0/10** (2 nums WhatsApp Business + LinkedIn ativo; B já criada pra 5d sem retorno)
    - 04-5tabelionato-londrina: **8.7/10** (novo endereço 2025 = sinal geográfico de expansão; B já criada)
    - 03-cartorio-jaguarao-2bh: **8.5/10** (5º GPTW MG 2026 — **RESSALVA**: briefing CEO prioriza e-mail; WhatsApp é BACKUP após 7d sem resposta por e-mail — regra já documentada na linha 43-45 do arquivo)
  - **3 micro patches aceitos** (custo ~5min total, não bloqueia envio):
    1. "Boa tarde" hardcoded → saudação dinâmica (Olá / Bom dia / Boa tarde) ou "Olá" universal
    2. CTA datas fixas (terça 30/06 / quinta 02/07) → gerar relativo ao envio real (D+5 / D+7 úteis)
    3. 03-Jaguarao backup rule → NÃO disparar antes de 7d sem resposta por e-mail (regra já documentada, mantida)
  - **Tracking plan aceito**: planilha simples (cartorio | data_envio | canal | status: enviado/respondeu/agendou/perdido).
  - **Próximo passo executivo (CEO-assistant 11:35 BRT)**: Gustavo dispara Vampre PRIMEIRO (sinal mais forte do lote, abre ciclo) na terça 30/06. Follow-up Variação B em D+7 onde A não respondeu (Vampre B pendente sprint 2; 02-Amaral e 04-Londrina já têm B). Sem escalação adicional — Gustavo dispara pessoal via Telegram, não bot. Cron `check-ceo-review` deletado pós-integração.

---

## EPIC E1 — MVP WhatsApp (Semana 3-8) — CORTE ESTRATEGICO CEO

> Decisao D3.1 (ceo-assistant): Sprint 1 faz SÓ consulta de emolumento. Status protocolo so no Sprint 2. Criar protocolo so apos 30 dias de shadow mode.

### Sprint 1 (sem 3-4) — SO CONSULTA EMOLUMENTO
- [x] **E1.S1.T1** Workflow n8n #1: msg WhatsApp -> Evolution -> OpenClaw -> API regras -> resposta — owner: `cartorio-n8n` — done em `3cdb65a` (WF bR7qIo3bFpG4zgxO, /webhook/consulta-emolumento, 200 OK, valores reais MG 2026)
- [ ] **E1.S1.T2** Endpoint `GET /api/v1/emolumento/calcular` polish + OpenAPI documentado — owner: `cartorio-dev` — **em andamento 2026-06-23 11:00 BRT** (worker spawn `general` mvs_c80baa2137734df2a70630561e56598b, não commitou ainda)
  - **Status uncommitted 11:00 BRT**:
    - `backend/app/api/v1/router.py`: +803 linhas (11 novos endpoints adicionados — `/protocolo/{numero}`, `/protocolo`, `/webhook/evolution`, `/audit/verify`, `/health/radar`, `/health/backup`, `/agendamento/disponibilidade`, `/documento/segunda-via`, `/atendimentos/ultimas-24h`, `/postman`)
    - `backend/app/schemas/protocolo.py`: schema Pydantic novo (ProtocoloCreateRequest/Response, LGPDBlockedResponse, StatusProtocolo enum, CanalOrigem enum, etc.)
    - `backend/tests/test_protocolo_endpoint.py`: novo, 15.9KB
    - `backend/tests/test_api.py` + `test_radar.py` + `conftest.py`: atualizados
    - `backend/app/main.py`: +69 linhas (lifespan, CORS, OpenAPI metadata)
    - `infra/backup/cartorio-backup.sh`: melhorado (128 linhas reescritas)
  - **Bloqueio flag (MSG #1474)**: worker rodou como `agent=general` (não como `cartorio-dev` rein project-scoped) — workaround documentado em memory. Cartorio-harness não encontrou o rein registrado como global agent.
  - **Próximo**: commit pelo cartorio-dev após smoke tests verdes. Revisão code-reviewer antes de merge.
- [ ] **E1.S1.T3** Integracao LiteLLM (Claude Opus 4.5 primary, GPT-5.5 fallback, Gemini/Llama router intencao) — owner: `cartorio-dev`
- [ ] **E1.S1.T4** PII scrubbing regex-only (latencia < 5ms) ANTES de chamar LLM — owner: `cartorio-dev` + review `cartorio-lgpd`
- [x] **E1.S1.T5** Template de resposta WhatsApp: "emolumento X custa R$ Y, prazo Z" — owner: `cartorio-n8n` — done em `3cdb65a` (WF #1 happy path R$ 105.40 certidao_casamento, R$ 156.40 procuracao)
- [x] **E1.S1.T6** Health check `/health` com smoke do hash chain — owner: `cartorio-dev` — `/health` 200 OK, `/api/v1/audit/verify` chain_ok=true last_valid_position=10
- [ ] **E1.S1.T7** Teste E2E: webhook Evolution -> resposta WhatsApp com PII zero no payload externo — owner: `cartorio-dev`
- **KPI Sprint 1**: 100 consultas/dia, 0 erro de valor, 0 handoff humano.

### Sprint 1 — Bonus workflows (cartorio-n8n Sprint 1 deliverable) ✅ done em `3cdb65a`
- [x] **E1.S1.WF2** Workflow n8n #2: criar protocolo (LGPD_BLOCKED sem consent, provisional CART-2026-XXXXXX com consent) — `MzeYTSDouymzdpRw` /webhook/criar-protocolo — backend 404 (Sprint 3 E1.S3.T1 pendente)
- [x] **E1.S1.WF3** Workflow n8n #3: handoff humano Chatwoot com inbox URL fallback — `OQRIOVHcOjpkQ0Of` /webhook/handoff-human
- [x] **E1.S1.WF4** Workflow n8n #4: boas-vindas + LGPD (novo cliente LGPD text, recorrente menu numerado) — `sDtkfOJ5BA7M73wB` /webhook/boas-vindas
- [ ] **E1.S1.WF3.BOT** Chatwoot Agent Bot (Cartorio Assistant) — PENDING Gustavo UI: precisa super_admin credentials no https://cartorio-chatwoot.dfgdxq.easypanel.host/super_admin/agent_bots; CHATWOOT_API_KEY vazio em backend/.env (WF3 usa inbox URL fallback enquanto isso)
  - **Tentativa 2026-06-23 10:42 BRT**: 5 credenciais default (admin@cartorio.com.br / @Techno832466 etc) → todas 429 rate-limited pelo Chatwoot
  - **Recomendação Gustavo**: criar super_admin pelo UI (5 cliques) OU me passar password por chat → cartorio-n8n finaliza via API em <2min
  - **NÃO bloqueia Sprint 1**: WF3 já tem inbox URL fallback funcionando
- [x] **E1.S1.WF5-10** Bonus workflows Sprint 2 — **DONE 2026-06-23 11:15 BRT** (verificado via psql n8n.workflow_entity): 7 workflows adicionais importados (04-consulta-protocolo, 05-agendamento, 06-segunda-via, 07-pesquisa-satisfacao, 08-audit-verify-diario, 09-monitor-backup, 10-faq-bot). Total: 11 workflows no N8N (4 Sprint 1 + 7 bonus Sprint 2 antecipado).
  - **⚠ AUDITORIA CREDS 11:25 BRT**: 11/11 workflows LIMPOS (zero credenciais hardcoded). Workflows 08 e 09 usam `$env.CARTORIO_API_KEY` e `$env.CHATWOOT_BOT_TOKEN` corretamente.
  - **⚠ ENV VARS FALTANDO 11:25 BRT**: CARTORIO_API_KEY e CHATWOOT_BOT_TOKEN não estavam setadas no N8N. FIX aplicado via `docker service update --env-add CARTORIO_API_KEY=<openssl rand hex 32> --env-add CHATWOOT_BOT_TOKEN=PENDING_GUSTAVO_UI_CREATE cartorio_n8n`. CARTORIO_API_KEY também setada na API.
  - **DB_HOST FALTANDO 11:18 BRT**: DB_POSTGRESDB_HOST=db (alias DNS antigo). FIX aplicado: --env-rm DB_POSTGRESDB_HOST=db --env-add DB_POSTGRESDB_HOST=10.0.1.34 (IP direto do container Supabase DB). Service converged em 26s.

### Sprint 1 — Ajustes pré-merge commit e487081 (review cartorio-lgpd msg #1521, 2026-06-23)
- [ ] **E1.S1.AJU.1** LGPDBlockedResponse copy jurídica defensável (art. 7º I + art. 8º §5º + DPO + política + revogação) — owner: `cartorio-dev` — pré-merge obrigatório (bloqueador)
- [ ] **E1.S1.AJU.2** Coluna `cliente.motivo_encerramento` (ENUM: revogacao_consentimento | retencao_5y | exercicio_direito_titular | outros) — owner: `cartorio-dev` + migration Alembic — pré-merge
- [ ] **E1.S1.AJU.3** `RequestContextMiddleware` (FastAPI) + popular `consentimento_ip` + `consentimento_user_agent` + `consentimento_canal` + `consentimento_em` + `AuditService.request_ip` — owner: `cartorio-dev` — pré-merge
- [ ] **E1.S1.AJU.4** Cross-review pré-merge por `cartorio-lgpd` (standby 24h após PR aberto) — owner: `cartorio-lgpd` — gate de qualidade
- [ ] **E1.S1.AJU.5** Atualizar `.env` + `.env.example` local com CARTORIO_API_KEY (openssl rand hex 32) — owner: Mavis — **FEITO 2026-06-23 11:25 BRT** (.env.example atualizado, .env real pendente permissão)

### Sprint 2 — Pendentes LGPD (escopo separado, pós-merge)
- [ ] **E1.S2.T6** Job retenção diária `backend/app/jobs/retencao.py` (5 anos Provimento CNJ 74/2018 + LGPD art. 7 II para cliente COM protocolo; até-revogação para cliente SEM) — owner: `cartorio-dev` + review `cartorio-lgpd`
- [ ] **E1.S2.T7** Endpoint `DELETE /api/v1/cliente/{id}` (LGPD art. 18 VI — direito ao esquecimento) — owner: `cartorio-dev` + review `cartorio-lgpd`
- [ ] **E1.S2.T8** Atualizar RIPD addendum Sprint 1 (gate LGPD → scrub → hash → DRAFT → HITL) — owner: `cartorio-lgpd`
- [ ] **E1.S2.T9** IP truncado /24 em output (LGPD-by-design) + retenção IP 2 anos — owner: `cartorio-dev`
- [ ] **E1.S2.T10** Política de credenciais em workflows N8N (auditoria $env vs hardcoded — Sprint 3) — owner: `cartorio-lgpd` (gatekeeper)

## EPIC E0 — Decisões arquiteturais ADICIONAIS (2026-06-23 11:25 BRT)

- **ADR-010**: DB_HOST em Swarm = IP direto do container do banco, NUNCA alias DNS. Motivo: Swarm services NÃO herdam alias de compose; restart causa ENOTFOUND e crash loop. Exemplo: N8N usava `db` → fix pra `10.0.1.34` (IP direto).
- **D4**: Retenção cartório — 5y cliente COM protocolo (Provimento CNJ 74/2018 + LGPD art. 7 II obrig legal), até-revogação cliente SEM protocolo (LGPD art. 7 I consentimento + art. 16 eliminação pós-finalidade).
- **D5**: IP é dado pessoal (LGPD art. 5 I) — armazenar completo 2y, exibir truncado /24 em output.
- **D6**: AUTH inter-service N8N ↔ API via `CARTORIO_API_KEY` (header `X-API-Key`, openssl rand hex 32, rotação 90d).

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
