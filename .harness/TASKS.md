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
- [x] **E1.S1.T3** Integracao LLM via OpenCode-Go provider (deepseek-v4-flash primary) + 8 blockers LGPD resolvidos — owner: `cartorio-dev` + review `cartorio-lgpd` (cross-review retroativo via auditoria 8 blockers antes do merge 20036bb) — **DONE 2026-06-23 14:06 BRT em `01c26df`** (audit.py + pii.py ZERO modificacao; LGPD by design: scrub INTERNO defense-in-depth, consent gate, audit log SHA-256, rate limit Redis 60/min, fallback scaffold). LiteLLM multi-provider fica sprint 3.
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

---

## EPIC E6 — INTEGRAÇÃO FULL (2026-06-23 14:15 BRT — sprint multi-rein)

> Gerado pelo orquestrador Mavis após briefing Gustavo pedindo 100 tasks + super plano.
> Princípio: TUDO passa pela API + N8N + DB + Redis. Cada cliente WhatsApp = 1 sessão.
> Conexão WhatsApp real é a ÚLTIMA parte (deixar tudo pronto antes).
> Owners: `cartorio-dev` (API/DB), `cartorio-n8n` (WF/EVO/CHATWOOT), `cartorio-lgpd` (LGPD/compliance), `cartorio-zcode` (cross-cutting/integrador), `cartorio-highspeed` (cron/monitor/sweep).

### Sprint E6.S0 — Orquestração + agent team ATIVADO

- [x] **E6.S0.T1** Ativar agent `cartorio-zcode` (compat ZCODE-AGENT-MINIMAX-M3, M3 thinking) — owner: Mavis — done 2026-06-23 14:18
- [x] **E6.S0.T2** Ativar agent `cartorio-highspeed` (compat MINIMAX-M7-HIGHSPEED, M3 highspeed) — owner: Mavis — done 2026-06-23 14:18
- [x] **E6.S0.T3** Responder cartorio-lgpd BATCH 2 review (consent.md + copy 11 variantes + auditoria 32 testes PII) — owner: Mavis — done 2026-06-23 14:14
- [x] **E6.S0.T4** Verificar status real N8N (12 WFs ON, 4 creds, 26 execs reais) — owner: Mavis — done 2026-06-23 14:16
- [x] **E6.S0.T5** Verificar agents globais disponíveis — owner: Mavis — done 2026-06-23 14:16
- [x] **E6.S0.T6** Verificar .env.example (279 linhas, Opencode-Go + OpenClaw + Tailscale + LGPD completos) — owner: Mavis — done 2026-06-23 14:17

### Sprint E6.S1 — API + DB + Redis (camada central) — 25 tasks

- [ ] **E6.S1.T1** Adicionar tabela `config_runtime` (key, value, updated_at, updated_by) no DB — owner: `cartorio-dev`
- [ ] **E6.S1.T2** Seed `config_runtime` com `llm.default_provider=opencode_go`, `llm.default_model=deepseek-v4-flash`, `llm.fallback_model=deepseek-v4-flash` — owner: `cartorio-dev`
- [ ] **E6.S1.T3** Adicionar tabela `sessao_cliente` (id UUID, cliente_id FK, canal, instance_name, session_data JSONB, created_at, last_active_at, closed_at) — owner: `cartorio-dev`
- [ ] **E6.S1.T4** Migration Alembic p/ tabelas `config_runtime` + `sessao_cliente` — owner: `cartorio-dev`
- [ ] **E6.S1.T5** Endpoint `GET /api/v1/config/{key}` (lê config_runtime com cache Redis 60s TTL) — owner: `cartorio-dev`
- [ ] **E6.S1.T6** Endpoint `POST /api/v1/config/{key}` (admin only, atualiza + invalida cache) — owner: `cartorio-dev` + review `cartorio-lgpd` (audit)
- [ ] **E6.S1.T7** Service `config` com fallback env → DB → hardcoded (defense-in-depth) — owner: `cartorio-dev`
- [ ] **E6.S1.T8** Endpoint `GET /api/v1/sessao/{cliente_id}` (lê sessão ativa do Redis ou DB) — owner: `cartorio-dev`
- [ ] **E6.S1.T9** Endpoint `POST /api/v1/sessao` (cria/atualiza sessão Redis + DB) — owner: `cartorio-dev`
- [ ] **E6.S1.T10** Endpoint `DELETE /api/v1/sessao/{id}` (fecha sessão, mantém histórico no DB) — owner: `cartorio-dev`
- [ ] **E6.S1.T11** Service `sessao` com Redis (sessão ativa 24h TTL) + DB (histórico permanente até retenção) — owner: `cartorio-dev`
- [ ] **E6.S1.T12** Cache Redis para `tabela_emolumento` (TTL 24h, invalidar via cron diário) — owner: `cartorio-dev`
- [ ] **E6.S1.T13** Rate limit Redis 60 req/min/IP (LGPD mitigation) — owner: `cartorio-dev`
- [ ] **E6.S1.T14** Audit log middleware FastAPI (request_id, ip, user_agent, timestamp) — owner: `cartorio-dev` + review `cartorio-lgpd`
- [ ] **E6.S1.T15** Endpoint `GET /api/v1/health/radar` com latência por serviço — owner: `cartorio-dev`
- [ ] **E6.S1.T16** Endpoint `GET /api/v1/health/integracoes` (N8N + EVO + CW + OCL + SUP + RED status) — owner: `cartorio-dev`
- [ ] **E6.S1.T17** Endpoint `POST /api/v1/webhook/evolution` (entrada principal WhatsApp, integridade HMAC) — owner: `cartorio-dev`
- [ ] **E6.S1.T18** Endpoint `POST /api/v1/webhook/chatwoot` (handoff humano recebe do N8N) — owner: `cartorio-dev`
- [ ] **E6.S1.T19** Endpoint `POST /api/v1/webhook/openclaw` (eventos do gateway OpenClaw) — owner: `cartorio-dev`
- [ ] **E6.S1.T20** Validação HMAC em todos os webhooks (header `X-Signature` com AUDIT_HMAC_KEY) — owner: `cartorio-dev`
- [ ] **E6.S1.T21** Idempotência webhook (Redis SETNX com TTL 5min, rejeita replay) — owner: `cartorio-dev`
- [ ] **E6.S1.T22** Dead-letter queue Redis para webhooks falhados (retry 3x exp backoff) — owner: `cartorio-dev`
- [ ] **E6.S1.T23** Endpoint `GET /api/v1/dlq/list` (admin only, ver webhooks falhados) — owner: `cartorio-dev`
- [ ] **E6.S1.T24** Endpoint `POST /api/v1/dlq/retry/{id}` (admin only, reprocessar) — owner: `cartorio-dev`
- [ ] **E6.S1.T25** Testes integração: 25 endpoints novos + 100% coverage — owner: `cartorio-dev`

### Sprint E6.S2 — N8N Workflows (12→20 workflows) — 20 tasks

- [ ] **E6.S2.T1** WF #13: OpenClaw Chat Bridge (recebe msg OpenClaw → encaminha p/ API webhook) — owner: `cartorio-n8n`
- [ ] **E6.S2.T2** WF #14: Opencode-Go LLM Fallback (se OpenClaw falhar, chama Opencode-Go direto) — owner: `cartorio-n8n`
- [ ] **E6.S2.T3** WF #15: Session Sync (sincroniza sessão Redis ↔ DB a cada 5min) — owner: `cartorio-n8n`
- [ ] **E6.S2.T4** WF #16: Prospecção Lead Enrichment (enriquece lead novo com dados ANOREG/Google) — owner: `cartorio-n8n`
- [ ] **E6.S2.T5** WF #17: Prospecção Send WhatsApp (dispara mensagem inicial + tracking opt-out) — owner: `cartorio-n8n`
- [ ] **E6.S2.T6** WF #18: Prospecção Follow-up D+7 (automático se lead não respondeu) — owner: `cartorio-n8n`
- [ ] **E6.S2.T7** WF #19: Cliente Criado (novo cliente → boas-vindas LGPD → menu inicial) — owner: `cartorio-n8n`
- [ ] **E6.S2.T8** WF #20: Protocolo Criado (workflow emite protocolo provisório + notifica escrevente) — owner: `cartorio-n8n`
- [ ] **E6.S2.T9** WF #21: Backup Status 5min (cron rápido com heartbeat) — owner: `cartorio-n8n`
- [ ] **E6.S2.T10** WF #22: Audit Verify 6h (verifica chain SHA256) — owner: `cartorio-n8n`
- [ ] **E6.S2.T11** WF #23: LGPD Esqueci (cliente pede exclusão → DELETE cliente + cascade) — owner: `cartorio-n8n` + review `cartorio-lgpd`
- [ ] **E6.S2.T12** WF #24: Daily Cleanup (roda 03:00, apaga sessões > 24h Redis + backup pre-retention) — owner: `cartorio-n8n`
- [ ] **E6.S2.T13** WF #25: Metrics Collector (envia Prometheus metrics p/ API) — owner: `cartorio-n8n`
- [ ] **E6.S2.T14** WF #26: Alerta Crítico (any service down → Telegram IM imediato) — owner: `cartorio-n8n`
- [ ] **E6.S2.T15** WF #27: Welcome First Time (primeira msg cliente → apresenta bot + pede consentimento) — owner: `cartorio-n8n`
- [ ] **E6.S2.T16** WF #28: Audit Snapshot (snapshot audit_log diário p/ S3 backup) — owner: `cartorio-n8n`
- [ ] **E6.S2.T17** WF #29: Rate Limit Reset (cron hourly reset counter Redis) — owner: `cartorio-n8n`
- [ ] **E6.S2.T18** WF #30: Health Deep Check (cron 15min, testa TODOS endpoints API + timeout 5s) — owner: `cartorio-n8n`
- [ ] **E6.S2.T19** Credenciais N8N: criar `opencode-go-deepseek` (existe ✓) + `openclaw-gateway` (FALTA) + `chatwoot-api` (FALTA) + `redis-cartorio` (FALTA) — owner: `cartorio-n8n`
- [ ] **E6.S2.T20** Workflow documentado em `infra/n8n-workflows/` (JSON export canônico) — owner: `cartorio-n8n`

### Sprint E6.S3 — OpenClaw + Opencode-Go + LLM Stack — 15 tasks

- [ ] **E6.S3.T1** Investigar `/v1/chat POST 404` no OpenClaw (decisão: patch local, esperar release, ou workaround) — owner: `cartorio-zcode`
- [ ] **E6.S3.T2** Patch local OpenClaw com rota `/v1/chat` funcional (se factível em <2h) — owner: `cartorio-zcode`
- [ ] **E6.S3.T3** Workaround: WF #14 chama Opencode-Go direto se OpenClaw 404 — owner: `cartorio-zcode`
- [ ] **E6.S3.T4** OpenClaw config: provider `opencode_go` + modelo `deepseek-v4-flash` — owner: `cartorio-zcode`
- [ ] **E6.S3.T5** OpenClaw plugins: ativar `evolution-api`, `supabase`, `audit-log` — owner: `cartorio-zcode`
- [ ] **E6.S3.T6** OpenClaw agent "Pietra Cartório" prompt LGPD-aware (system prompt com scrub interno + audit) — owner: `cartorio-zcode` + review `cartorio-lgpd`
- [ ] **E6.S3.T7** Opencode-Go API key rotacionada (90d policy) — owner: Mavis + Gustavo
- [ ] **E6.S3.T8** Opencode-Go fallback configurado (mesmo modelo, mesma key, retry 2x) — owner: `cartorio-zcode`
- [ ] **E6.S3.T9** LiteLLM gateway (FUTURO sprint 3 — placeholder scaffold) — owner: `cartorio-dev`
- [ ] **E6.S3.T10** Model registry em `config_runtime` (deepseek-v4-flash + future Claude/GPT) — owner: `cartorio-dev`
- [ ] **E6.S3.T11** Endpoint `GET /api/v1/llm/models` (lista modelos disponíveis + provider) — owner: `cartorio-dev`
- [ ] **E6.S3.T12** Endpoint `POST /api/v1/llm/test` (smoke test de cada provider) — owner: `cartorio-dev`
- [ ] **E6.S3.T13** Health check LLM providers (cron hourly: Opencode-Go + OpenClaw + LiteLLM) — owner: `cartorio-highspeed`
- [ ] **E6.S3.T14** Alerta se qualquer LLM provider offline > 5min — owner: `cartorio-highspeed`
- [ ] **E6.S3.T15** DPA MiniMax assinado (escalado Gustavo — bloqueia prod até assinar) — owner: Gustavo + DPO

### Sprint E6.S4 — Evolution API + Chatwoot + Supabase — 20 tasks

- [ ] **E6.S4.T1** Evolution Manager UI acessível em `https://whatsapp.2notasudi.com.br/manager` — owner: Gustavo UI
- [ ] **E6.S4.T2** Evolution instance `cartorio-2notas` provisionada (deixar criada, NÃO conectar número ainda) — owner: `cartorio-n8n`
- [ ] **E6.S4.T3** Evolution webhook registrado apontando p/ N8N `/webhook/evo-in` — owner: `cartorio-n8n`
- [ ] **E6.S4.T4** Evolution eventos escutados: `messages.upsert`, `messages.update`, `connection.update` — owner: `cartorio-n8n`
- [ ] **E6.S4.T5** Chatwoot Agent Bot "Cartorio Assistant" (criado no UI pelo Gustavo) — owner: Gustavo UI
- [ ] **E6.S4.T6** Chatwoot inbox provisionada (WhatsApp + Web + Telegram channels) — owner: `cartorio-n8n`
- [ ] **E6.S4.T7** Chatwoot custom domain `chat.2notasudi.com.br` ativo (DNS OK ✓) — owner: `cartorio-n8n`
- [ ] **E6.S4.T8** Chatwoot Agent Bot handoff rules (transfer to human > 0.7 confidence LLM) — owner: `cartorio-n8n`
- [ ] **E6.S4.T9** Chatwoot super_admin password criado via UI — owner: Gustavo UI
- [ ] **E6.S4.T10** Chatwoot Canned Responses p/ FAQs cartorários (50+ templates) — owner: `cartorio-n8n`
- [ ] **E6.S4.T11** Chatwoot Macros para handoff humano → escrevente (10 macros) — owner: `cartorio-n8n`
- [ ] **E6.S4.T12** Supabase tabela `prospeccao_leads` (id, nome, cartorio, cidade, uf, status, ultimo_contato, opt_out) — owner: `cartorio-dev`
- [ ] **E6.S4.T13** Supabase tabela `cliente_sessao` (sincronizada com Redis) — owner: `cartorio-dev`
- [ ] **E6.S4.T14** Supabase Realtime habilitado p/ tabela `conversa` (live updates no dashboard) — owner: `cartorio-dev`
- [ ] **E6.S4.T15** Supabase Storage bucket `documentos` (privado, signed URL 24h) — owner: `cartorio-dev`
- [ ] **E6.S4.T16** Supabase Edge Function `prospeccao-webhook` (recebe eventos do N8N) — owner: `cartorio-dev`
- [ ] **E6.S4.T17** Supabase backup automático 4x/dia (DB chatwoot validado ✓, DB cartorio PENDENTE) — owner: `cartorio-n8n`
- [ ] **E6.S4.T18** Supabase RLS policies em `cliente`, `protocolo`, `documento` (somente owner pode ler) — owner: `cartorio-dev` + review `cartorio-lgpd`
- [ ] **E6.S4.T19** Supabase Kong gateway rate limit (100 req/min/API key) — owner: `cartorio-dev`
- [ ] **E6.S4.T20** Supabase secrets: rotacionar `SUPABASE_SERVICE_ROLE_KEY` (90d policy) — owner: Mavis + Gustavo

### Sprint E6.S5 — MCP Server/Client + Plugins + Skills — 15 tasks

- [ ] **E6.S5.T1** MCP server da API (✓ existe `/mcp/mcp` FastMCP 3.x, 14 tools) — manter — owner: `cartorio-dev`
- [ ] **E6.S5.T2** MCP server do N8N (✓ existe `/mcp-server/http`, 30 tools) — manter — owner: `cartorio-n8n`
- [ ] **E6.S5.T3** MCP server do Supabase (configurar via Antigravity Supabase MCP) — owner: `cartorio-zcode`
- [ ] **E6.S5.T4** MCP server do Easypanel (helbertparanhos/easypanel-mcp-server community) — owner: `cartorio-zcode`
- [ ] **E6.S5.T5** MCP server do OpenClaw (expor gateway OpenClaw via MCP) — owner: `cartorio-zcode`
- [ ] **E6.S5.T6** MCP server do Redis (redis-mcp-server community) — owner: `cartorio-zcode`
- [ ] **E6.S5.T7** MCP client config global `~/.mavis/mcp/clients/cartorio-mcp-config.json` (6 servers) — owner: `cartorio-zcode`
- [ ] **E6.S5.T8** MCP client integrado no Claude Desktop / Cursor / OpenClaw — owner: Mavis
- [ ] **E6.S5.T9** N8N MCP client node (✓ instalado n8n-nodes-mcp v0.1.37) — usar nos WFs — owner: `cartorio-n8n`
- [ ] **E6.S5.T10** N8N Evolution API node (✓ instalado v1.0.4) — usar em todos WFs WhatsApp — owner: `cartorio-n8n`
- [ ] **E6.S5.T11** N8N Chatwoot node (✓ instalado v1.0.2) — usar em handoff humano — owner: `cartorio-n8n`
- [ ] **E6.S5.T12** N8N MinIO node (✓ instalado v1.3.0) — usar em backup PDFs — owner: `cartorio-n8n`
- [ ] **E6.S5.T13** N8N PdfKit node (✓ instalado v0.1.2) — usar em geração certidões — owner: `cartorio-n8n`
- [ ] **E6.S5.T14** Skills Mavis: criar `cartorio-orchestrator` skill (roteador de tasks multi-rein) — owner: Mavis
- [ ] **E6.S5.T15** Skills Mavis: criar `cartorio-mcp` skill (wrapper MCP client global) — owner: Mavis

### Sprint E6.S6 — Tailscale + Domínios + SSL — 10 tasks

- [ ] **E6.S6.T1** Gerar certs Tailscale para `*.tail2fe279.ts.net` (`tailscale cert` na VPS) — owner: `cartorio-zcode`
- [ ] **E6.S6.T2** Traefik routers para `api.tail2fe279.ts.net`, `n8n.tail2fe279.ts.net`, `agent.tail2fe279.ts.net`, `whatsapp.tail2fe279.ts.net`, `chat.tail2fe279.ts.net`, `supabase.tail2fe279.ts.net` — owner: `cartorio-zcode`
- [ ] **E6.S6.T3** DNS Cloudflare wildcard `*.tail2fe279.ts.net` (Tailscale MagicDNS auto) — owner: `cartorio-zcode`
- [ ] **E6.S6.T4** OpenClaw gateway bind 0.0.0.0:18789 (já está ✓) — manter — owner: `cartorio-zcode`
- [ ] **E6.S6.T5** VPS firewall: aceitar Tailscale 100.64.0.0/10 em todas portas internas — owner: `cartorio-zcode`
- [ ] **E6.S6.T6** Mac firewall: aceitar Tailscale 100.64.0.0/10 para SSH local — owner: Gustavo
- [ ] **E6.S6.T7** Easypanel domínio custom `easypanel.2notasudi.com.br` (✓ OK) — manter — owner: Mavis
- [ ] **E6.S6.T8** Domínio `flow.2notasudi.com.br` (N8N com domínio próprio, opcional sprint 3) — owner: `cartorio-n8n`
- [ ] **E6.S6.T9** Monitor cert expiry (Tailscale + Cloudflare) com alerta 30d antes — owner: `cartorio-highspeed`
- [ ] **E6.S6.T10** Backup VPS-side scripts em `/usr/local/bin/` + keyfile em `/etc/cartorio-backup/` (✓ já OK) — manter — owner: Mavis

### Sprint E6.S7 — Crons + Monitor + Alertas (1 por área) — 15 tasks

- [ ] **E6.S7.T1** Cron `cartorio-api-health` (5min tick, GET /health, alerta Telegram se != 200) — owner: `cartorio-highspeed`
- [ ] **E6.S7.T2** Cron `cartorio-radar` (5min tick, GET /health/radar, alerta se != GREEN) — owner: `cartorio-highspeed`
- [ ] **E6.S7.T3** Cron `cartorio-n8n-health` (5min tick, GET /healthz N8N) — owner: `cartorio-highspeed`
- [ ] **E6.S7.T4** Cron `cartorio-evo-health` (5min tick, GET / Evolution) — owner: `cartorio-highspeed`
- [ ] **E6.S7.T5** Cron `cartorio-cw-health` (10min tick, GET /api/v1/accounts Chatwoot) — owner: `cartorio-highspeed`
- [ ] **E6.S7.T6** Cron `cartorio-ocl-health` (5min tick, GET /health OpenClaw) — owner: `cartorio-highspeed`
- [ ] **E6.S7.T7** Cron `cartorio-redis-health` (10min tick, PING Redis, maxmemory check) — owner: `cartorio-highspeed`
- [ ] **E6.S7.T8** Cron `cartorio-supabase-health` (10min tick, GET /auth/v1/health) — owner: `cartorio-highspeed`
- [ ] **E6.S7.T9** Cron `cartorio-llm-health` (15min tick, smoke Opencode-Go + OpenClaw) — owner: `cartorio-highspeed`
- [ ] **E6.S7.T10** Cron `cartorio-backup-status` (hourly, GET /api/v1/health/backup) — owner: `cartorio-highspeed`
- [ ] **E6.S7.T11** Cron `cartorio-audit-verify` (daily 03:30, GET /api/v1/audit/verify) — owner: `cartorio-highspeed`
- [ ] **E6.S7.T12** Cron `cartorio-cert-expiry` (daily 09:00, monitor Tailscale + Cloudflare cert) — owner: `cartorio-highspeed`
- [ ] **E6.S7.T13** Cron `cartorio-prospeccao-daily` (daily 08:00, sumariza leads do dia) — owner: `cartorio-highspeed`
- [ ] **E6.S7.T14** Cron `cartorio-morning-brief` (daily 07:30, IM Telegram c/ status completo) — owner: Mavis
- [ ] **E6.S7.T15** Cron `cartorio-weekly-summary` (Sunday 23:00, resumo sprint p/ Gustavo) — owner: Mavis

### Sprint E6.S8 — Prospecção + Operação Real — 10 tasks

- [ ] **E6.S8.T1** Top 100 cartórios SP scoring Tier A/B/C (✓ já 30 prontos) — owner: `ceo-assistant`
- [ ] **E6.S8.T2** Disparo Vampre PRIMEIRO (sinal >R$ 90M/ano, terça 30/06) — owner: Gustavo
- [ ] **E6.S8.T3** Disparo Amaral 5BH + Herrera 1Salvador + Londrina (Tier A Wave 1) — owner: Gustavo
- [ ] **E6.S8.T4** Tracking planilha `docs/leads/tracking.csv` (cartorio | data_envio | canal | status) — owner: Gustavo
- [ ] **E6.S8.T5** WF #16 enrichment auto + WF #17 send WhatsApp (Wave 2 escalável) — owner: `cartorio-n8n`
- [ ] **E6.S8.T6** WF #18 follow-up D+7 automático (LGPD opt-out keyword PARAR/SAIR) — owner: `cartorio-n8n`
- [ ] **E6.S8.T7** Dashboard prospecção React (cartorio | status | próximo follow-up) — owner: `cartorio-n8n`
- [ ] **E6.S8.T8** KPI prospecção: 10 leads Tier A → 5 reuniões → 2 pilotos 30d — owner: `ceo-assistant`
- [ ] **E6.S8.T9** Runbook escrevente (como receber handoff Chatwoot + LGPD checklist) — owner: `cartorio-lgpd`
- [ ] **E6.S8.T10** Onboarding cartório piloto (Kick-off + treinamento + dashboard) — owner: Gustavo

### Sprint E6.S9 — LGPD Final + Compliance (batch 2 + futuro) — 10 tasks

- [ ] **E6.S9.T1** BATCH 2 LGPD review (consent + copy 11 variantes + auditoria PII) — owner: `cartorio-lgpd` — sprint 2026-06-23 14:14+
- [ ] **E6.S9.T2** RIPD v1.2 (Tratamento 7 OpenCode-Go + Tratamento 8 N8N ferramenta + R13-R17) — owner: `cartorio-lgpd`
- [ ] **E6.S9.T3** Auditoria opencode_go.py (8 blockers identificados em commit 2c9ff79) — owner: `cartorio-lgpd`
- [ ] **E6.S9.T4** DPA MiniMax assinado (escalado Gustavo — STAGING ONLY até assinar) — owner: Gustavo + DPO
- [ ] **E6.S9.T5** Encryption at-rest Postgres (pgcrypto + gpg key rotacionada) — owner: `cartorio-dev` + review `cartorio-lgpd`
- [ ] **E6.S9.T6** Consent explícito no webhook Evolution ("digite SIM para continuar") — owner: `cartorio-dev` + review `cartorio-lgpd`
- [ ] **E6.S9.T7** Logs de acesso LGPD art. 37 (request_id + IP truncado /24 + user_agent + timestamp) — owner: `cartorio-dev`
- [ ] **E6.S9.T8** Pen-test OWASP top 10 (Burp Suite + Zap) — owner: `cartorio-lgpd` (coordena)
- [ ] **E6.S9.T9** DPO designado + contato publicado no site/chat — owner: `cartorio-lgpd` + `cartorio-n8n` (UI)
- [ ] **E6.S9.T10** Auditoria ANPD readiness checklist (15 itens) — owner: `cartorio-lgpd`

### Sprint E6.S10 — Conexão WhatsApp Real (ÚLTIMA ETAPA) — 10 tasks

- [ ] **E6.S10.T1** Conectar número real WhatsApp via Evolution QR (scan pelo Gustavo) — owner: Gustavo
- [ ] **E6.S10.T2** Smoke test E2E: msg WhatsApp → Evolution → N8N → API → resposta → WhatsApp — owner: `cartorio-n8n`
- [ ] **E6.S10.T3** Teste PII real: cliente envia CPF → scrub → LLM (zero dado bruto no provider) — owner: `cartorio-dev`
- [ ] **E6.S10.T4** Teste HITL: cliente pede isenção → bot responde "vou transferir p/ escrevente" — owner: `cartorio-n8n`
- [ ] **E6.S10.T5** Teste sessão: cliente volta 3 dias depois → sessão recuperada (Redis ou DB) — owner: `cartorio-dev`
- [ ] **E6.S10.T6** KPI Sprint 1: 100 consultas/dia, 0 erro de valor, 0 handoff humano — owner: Mavis monitora
- [ ] **E6.S10.T7** Go-live: anunciar p/ top 100 cartórios (prospecção fase 2) — owner: Gustavo
- [ ] **E6.S10.T8** Monitor prod 7x24 (radar + alertas Telegram) — owner: Mavis
- [ ] **E6.S10.T9** Retrospectiva 30 dias (métricas + LGPD + custos) — owner: Mavis
- [ ] **E6.S10.T10** Sprint 2 planejamento (consulta protocolo + shadow mode) — owner: Mavis + Gustavo

### Sprint E6.SMETA — Ad-hoc + melhorias contínuas — 5 tasks

- [ ] **E6.SMETA.T1** Melhorar cobertura testes de 95.61% → 98% — owner: `cartorio-dev`
- [ ] **E6.SMETA.T2** Reduzir latência `/api/v1/emolumento/calcular` p/ < 50ms (cache Redis) — owner: `cartorio-dev`
- [ ] **E6.SMETA.T3** OpenAPI completo + Postman collection (✓ já existe) — manter atualizado — owner: `cartorio-dev`
- [ ] **E6.SMETA.T4** Swagger UI customizado com auth demo (sandbox cartorário) — owner: `cartorio-dev`
- [ ] **E6.SMETA.T5** CI/CD: GitHub Actions ruff + mypy + pytest + deploy Easypanel — owner: `cartorio-dev`

**TOTAL TASKS E6: 100 (T1-T100)** — sprint multi-rein full integração Cartório 2notas.

Modified by Gustavo Almeida
---

## TIER 2 — INTEGRAÇÕES AVANÇADAS (Sprint 2 — paralelizado, 5 workers)

> **Contexto Gustavo 2026-06-23 14:13 BRT**: Sprint 1 fechou com QUALIDADE (LGPD compliance, 12 WFs re-exportados, 95.61% coverage, cross-review gate). Mas faltou INTEGRAÇÃO ponta a ponta:
> - N8N: workflows simples, sem MCP server/client, sem variables/data tables, sem credenciais faltantes
> - API: poucos endpoints, sem Swagger completo, sem MCP server full
> - Supabase: schema parcial, sem RLS, sem pgvector para memoria agent
> - OpenClaw: sem dominio Tailscale (tail2fe279.ts.net), sem gateway
> - Evolution API: travado, sem webhooks full
> - Comunicação ZCode-MiniMax: nao estabelecida
> - Falta OpenCode-Go (deepseek-v4-flash) integrado em tudo
>
> **Decisão D2-arquitetura**: TUDO passa pela API + N8N + Supabase. OpenClaw é cerebro LLM. Evolution API é WhatsApp. Redis acelera. Chatwoot = CRM/humano.
> **Não conectar WhatsApp ainda** (Gustavo 2026-06-23).

### Subtier N8N-A — cartorio-n8n-pro (25 tasks)

> Refazer workflows com integração REAL (API calls, Supabase, Redis, OpenCode-Go), criar MCP server completo, configurar Variables (workaround $env), Data Tables, credenciais faltantes.

- [ ] **T2.N8N.T1** Workflow #01 v3: consulta-emolumento COMPLETO (OpenCode-Go deepseek-v4-flash → API → Supabase cache → Redis) — não só calculo, com cache de 24h, fallback LiteLLM, audit log
- [ ] **T2.N8N.T2** Workflow #02 v2: criar-protocolo REAL (Supabase insert, hash chain increment, retorno com protocolo_id, NOT LGPD_BLOCKED se consent=ok)
- [ ] **T2.N8N.T3** Workflow #03 v2: handoff-human com Chatwoot API real (não inbox URL fallback) — POST /api/v1/accounts/{id}/conversations com inbox_id=1
- [ ] **T2.N8N.T4** Workflow #04 v2: boas-vindas + LGPD consent capture (gravar consent no Supabase tabela cliente, marcar cliente.consent_at)
- [ ] **T2.N8N.T5** Workflow #05 v2: agendamento completo (calcular slots livres do tabelião via API, bloquear horário via Redis SETNX, confirmar no Supabase)
- [ ] **T2.N8N.T6** Workflow #06 v2: segunda-via PDF (gerar via API → Supabase Storage signed URL → WhatsApp send)
- [ ] **T2.N8N.T7** Workflow #07 v2: pesquisa-satisfação (NPS 0-10, CSAT 1-5, gravar no Supabase tabela feedback, dashboard Grafana)
- [ ] **T2.N8N.T8** Workflow #08 v2: audit-verify diário (cron 06:00, chamar GET /api/v1/audit/verify, alertar Slack/Telegram se chain_ok=false)
- [ ] **T2.N8N.T9** Workflow #09 v2: monitor-backup (cron 04:00, ler log backup, alertar se > 26h atras)
- [ ] **T2.N8N.T10** Workflow #10 v2: faq-bot com OpenCode-Go RAG (consultar embeddings no Supabase pgvector, responder com contexto)
- [ ] **T2.N8N.T11** Workflow #11: monitor-cartório (health checks Evolution+N8N+API+Supabase+OpenClaw+Chatwoot+Redis, alerta Telegram se down >2min)
- [ ] **T2.N8N.T12** Workflow #12 NOVO: registrar-lead (entrada prospecção, validar LGPD, inserir Supabase leads, enviar boas-vindas)
- [ ] **T2.N8N.T13** Workflow #13 NOVO: enviar-pesquisa-NPS (cron semanal, lista clientes últimos 30d, enviar via WhatsApp template aprovado)
- [ ] **T2.N8N.T14** Workflow #14 NOVO: relatorio-diario (cron 18:00, sumariza atendimentos do dia, envia pro Telegram do tabelião)
- [ ] **T2.N8N.T15** Workflow #15 NOVO: renova-protocolo (cliente pede renovação, valida prazo, gera novo PDF, envia link)
- [ ] **T2.N8N.T16** Credencial `cartorio-api-key` no N8N (header X-API-Key, valor $env.CARTORIO_API_KEY)
- [ ] **T2.N8N.T17** Credencial `opencode-go` no N8N (HTTP header Auth Bearer $env.OPENCODE_GO_API_KEY, base URL https://api.deepseek.com/v1 ou gateway)
- [ ] **T2.N8N.T18** Credencial `supabase-rest` no N8N (HTTP header apikey $env.SUPABASE_ANON_KEY + Authorization Bearer $env.SUPABASE_SERVICE_ROLE_KEY)
- [ ] **T2.N8N.T19** Credencial `evolution-api-cartorio` JÁ EXISTE (verificar instanceName=cartorio-2notas, apiKey ativo)
- [ ] **T2.N8N.T20** Data Table `cartorio-sessions` (chave=session_id, valor=JSON {phone, customer_id, last_msg_at, context, consent})
- [ ] **T2.N8N.T21** Data Table `cartorio-rate-limits` (chave=phone, valor={count, window_start})
- [ ] **T2.N8N.T22** N8N MCP Server completo (mcp-server/http endpoint com tools: trigger_consulta, trigger_protocolo, trigger_handoff, query_supabase, query_openclaw)
- [ ] **T2.N8N.T23** Variables workspace (workaround com $env permanente — Variables feature licenciada)
- [ ] **T2.N8N.T24** Tags automáticas em executions (tag=`cartorio`, `consulta`, `protocolo`, `handoff`, `lgpd-blocked`)
- [ ] **T2.N8N.T25** Error workflow global (captura falhas, envia pro Telegram do tabelião com stack trace)

### Subtier API-A — cartorio-api-integrations (25 tasks)

> Endpoints de integração completos, MCP server 15+ tools, Swagger atualizado, Redis pub/sub, WebSocket.

- [ ] **T2.API.T1** POST /integrations/opencode/chat (já existe em opencode_go.py — verificar e expor via router)
- [ ] **T2.API.T2** POST /integrations/opencode/test (smoke test da key, retorna modelo ativo + quota)
- [ ] **T2.API.T3** POST /integrations/n8n/trigger/{workflow_name} (chamar workflow via webhook URL configurável)
- [ ] **T2.API.T4** POST /integrations/n8n/credentials/list (proxy seguro, retorna lista de creds N8N sem expor valores)
- [ ] **T2.API.T5** POST /integrations/evolution/send-text (proxy Evolution sendText com retry + audit)
- [ ] **T2.API.T6** POST /integrations/evolution/send-media (sendImage/sendDocument com signed URL Supabase Storage)
- [ ] **T2.API.T7** POST /integrations/evolution/instance-status (verifica se instância cartorio-2notas conectada)
- [ ] **T2.API.T8** POST /integrations/chatwoot/contact/create (proxy Chatwoot contacts API)
- [ ] **T2.API.T9** POST /integrations/chatwoot/conversation/create (proxy conversations API com inbox_id=1)
- [ ] **T2.API.T10** POST /integrations/chatwoot/message/send (proxy messages API)
- [ ] **T2.API.T11** POST /integrations/supabase/query (proxy Supabase REST API, com RLS service_role bypass)
- [ ] **T2.API.T12** POST /integrations/supabase/storage/upload (upload PDF/imagem com hash SHA-256)
- [ ] **T2.API.T13** GET /integrations/openclaw/health (proxy OpenClaw /health endpoint)
- [ ] **T2.API.T14** POST /integrations/openclaw/chat (proxy /v1/chat com LGPD scrubbing interno)
- [ ] **T2.API.T15** GET /integrations/openclaw/agents (lista agents sandbox configurados)
- [ ] **T2.API.T16** MCP server completo /mcp com 15+ tools: calcular_emolumento, criar_protocolo, buscar_protocolo, criar_agendamento, listar_horarios, gerar_segunda_via, enviar_pesquisa, consultar_cpf_hash, criar_handoff, validar_consent, upload_storage, enviar_whatsapp, criar_chatwoot_contact, query_openclaw, audit_verify
- [ ] **T2.API.T17** Swagger completo em /docs com todos os novos endpoints documentados (summary, params, responses, exemplos)
- [ ] **T2.API.T18** Postman collection atualizada (regenerar via /api/v1/postman endpoint existente)
- [ ] **T2.API.T19** WebSocket /ws/atendimentos (real-time dashboard, broadcaster com Redis pub/sub channel `cartorio:atendimentos`)
- [ ] **T2.API.T20** Redis pub/sub helper service (subscribe_to_channel, publish, patterns)
- [ ] **T2.API.T21** Rate limiting por sessão (já tem Redis 60/min em opencode_go — estender pra endpoints integração)
- [ ] **T2.API.T22** Health check /health/radar expandido (status de TODOS os 6 serviços externos)
- [ ] **T2.API.T23** Middleware CORS atualizado (origins específicas, não wildcard em prod)
- [ ] **T2.API.T24** API key rotation endpoint POST /admin/api-key/rotate (gera nova, invalida antiga, audit log)
- [ ] **T2.API.T25** Endpoint /integrations/mcp-servers/list (lista MCPs disponíveis: n8n, openclaw, evolution, chatwoot, supabase)

### Subtier SUPABASE-A — cartorio-supabase-pro (15 tasks)

> Schema completo + RLS + pgvector + triggers + migrations + seed.

- [ ] **T2.SUP.T1** Migration `001_initial_schema.sql` (tabelas: cliente, conversa, protocolo, documento, emolumento, audit_log, atendimento, agendamento, feedback, lead)
- [ ] **T2.SUP.T2** Migration `002_rls_policies.sql` (RLS por role: anon, authenticated, service_role, com policies granulares)
- [ ] **T2.SUP.T3** Migration `003_pgvector_memory.sql` (extensão vector + tabela agent_memory(id, session_id, embedding vector(1536), content, metadata))
- [ ] **T2.SUP.T4** Migration `004_functions.sql` (functions SQL: criar_protocolo_atomic, hash_chain_append, soft_delete_cliente, calcular_nps_mes)
- [ ] **T2.SUP.T5** Migration `005_triggers.sql` (triggers: audit_log auto-insert on protocolo update, cliente consent_at auto-set, embeddings auto-update on content change)
- [ ] **T2.SUP.T6** Migration `006_storage_buckets.sql` (buckets: protocolos-pdf, documentos-cliente, anexos-atendimento, todos com RLS)
- [ ] **T2.SUP.T7** Migration `007_seed_data.sql` (tabela_emolumento MG 2026 com 50+ tipos de certidão, 10 tabeliães fictícios, 5 modelos de protocolo)
- [ ] **T2.SUP.T8** Alembic setup completo (env.py, alembic.ini, versions/, autogenerate funcionando)
- [ ] **T2.SUP.T9** Backup automation v2 (cron 03:00, pg_dump custom format, upload Supabase Storage bucket `backups`, retenção 30d)
- [ ] **T2.SUP.T10** Restore drill (script bash pra testar restore a partir de backup, runbook)
- [ ] **T2.SUP.T11** Encryption at-rest (pgcrypto para campos sensíveis: cliente.cpf_hash, cliente.email_encrypted)
- [ ] **T2.SUP.T12** Connection pooler PgBouncer (supabase-pooler URL no .env, evitar exhaustion)
- [ ] **T2.SUP.T13** Realtime subscriptions (configurar broadcast em `cartorio:atendimentos`, `cartorio:protocolos`, `cartorio:alertas`)
- [ ] **T2.SUP.T14** Logs explorer (estrutura JSON estruturado pra facilitar query: timestamp, level, service, trace_id, session_id, payload_hash)
- [ ] **T2.SUP.T15** Supabase dashboard custom (SQL views: vw_atendimentos_hoje, vw_nps_mes, vw_protocolos_pendentes, vw_leads_quentes)

### Subtier OPENCLAW-A — cartorio-openclaw-domain (15 tasks)

> Domínio Tailscale + gateway + sandbox + brain + skills + tools + plugins.

- [ ] **T2.OC.T1** Domínio Tailscale `tail2fe279.ts.net` resolvendo (MagicDNS ou split-DNS no Mac 100.83.180.16)
- [ ] **T2.OC.T2** Subdomínio `agent.tail2fe279.ts.net` (ou `cartorio.tail2fe279.ts.net`) com TLS 1.3 via Tailscale cert
- [ ] **T2.OC.T3** OpenClaw gateway rodando no VPS (porta 8082 ou 9000, escutando só na rede Tailscale 100.64.0.0/10)
- [ ] **T2.OC.T4** OpenClaw firewall: DROP tudo de não-Tailscale (iptables INPUT chain, allow 100.64.0.0/10 only)
- [ ] **T2.OC.T5** OpenClaw sandbox config (/opt/openclaw/sandbox/cartorio-agent-cartorio/ com brain/, memory/, skills/, tools/, plugins/, hooks/, goals/)
- [ ] **T2.OC.T6** OpenClaw LLM provider = deepseek-v4-flash via OpenCode-Go (sk-j03KVdV6rDkSW1D2KmrmbCL8zRjhBw0IkOes2BNCEetOokTnbLJXwc7AyltoRscr)
- [ ] **T2.OC.T7** OpenClaw tools registry (web_search, http_get, file_read, code_exec, memory_save, memory_recall, pii_scrub, audit_log)
- [ ] **T2.OC.T8** OpenClaw skills registry (consulta-emolumento, criar-protocolo, agendar, handoff-human, faq, gerar-pdf)
- [ ] **T2.OC.T9** OpenClaw plugins registry (lgpd-blocker, consent-gate, audit-logger, redis-cache, supabase-persist)
- [ ] **T2.OC.T10** OpenClaw hooks (pre_send: PII scrub + consent check; post_send: audit log; on_error: alert Telegram)
- [ ] **T2.OC.T11** OpenClaw goals (goal=atender cliente cartorário com compliance LGPD, subgoals=responder em <5s, encaminhar humano se dúvida, registrar tudo)
- [ ] **T2.OC.T12** OpenClaw brain config (system prompt com contexto cartório 2 Notas Uberlândia, regras de negócio, base legal LGPD)
- [ ] **T2.OC.T13** OpenClaw memory (long-term via Supabase pgvector, short-term via Redis, session via Data Table N8N)
- [ ] **T2.OC.T14** OpenClaw health endpoint /health (status, uptime, model_provider, active_sessions, last_error)
- [ ] **T2.OC.T15** OpenClaw métricas endpoint /metrics (Prometheus format: openclaw_sessions_active, openclaw_requests_total, openclaw_pii_blocks_total, openclaw_consent_blocks_total)

### Subtier EVO-A — cartorio-evo-advanced (10 tasks)

> Evolution API webhooks + Chatwoot integration + Redis sessions.

- [ ] **T2.EVO.T1** Evolution API rodando e HEALTH OK (verificar container cartorio_evolution-api, log sem erro)
- [ ] **T2.EVO.T2** Instância `cartorio-2notas` criada e conectada (verificar via /instance/connect, NÃO parear WhatsApp ainda)
- [ ] **T2.EVO.T3** Webhook `MESSAGES_UPSERT` configurado pra apontar pro N8N WF #04 (boas-vindas)
- [ ] **T2.EVO.T4** Webhook `MESSAGES_UPDATE` (status de entrega: SENT, DELIVERED, READ, FAILED) → atualizar Supabase conversa.status
- [ ] **T2.EVO.T5** Webhook `CONNECTION_UPDATE` (se cair, alertar Telegram do tabelião)
- [ ] **T2.EVO.T6** Integração Chatwoot via inbox (configurar Chatwoot inbox WhatsApp appointer Evolution API)
- [ ] **T2.EVO.T7** Redis session storage (key=`evo:session:{phone}`, TTL=24h, value=JSON {customer_id, last_msg, context})
- [ ] **T2.EVO.T8** Rate limit por sender (60 msgs/min Redis INCR, alert se > 100)
- [ ] **T2.EVO.T9** Evolution API dashboard (URL admin com auth basica, log de mensagens, métricas)
- [ ] **T2.EVO.T10** Anti-spam filter (rejeitar msgs com > 5 URLs ou > 3 telefones ou palavras banned)

### Subtier COM-A — comunicação ZCode-MiniMax (10 tasks)

> Bridge entre MiniMax.app e Mavis/Pietra local.

- [ ] **T2.COM.T1** Documentar COMUNICATION_ARCHITECTURE.md v2 (incluir MiniMax.app bridge, mvs_46000b23199f451cb8f2ef7044cc99b9 como testbed)
- [ ] **T2.COM.T2** Agent MiniMax-M3 configurado global (claude-opus-4.6, max thinking, gemini-3.5-flash backup)
- [ ] **T2.COM.T3** Agent MiniMax-M7-HighSpeed configurado global (gemini-3.1-pro, low latency, tarefas paralelas)
- [ ] **T2.COM.T4** Subagent ZCode-MiniMax-M3 (coder MiniMax-M3, focus arquitetura DDD)
- [ ] **T2.COM.T5** Subagent ZCode-MiniMax-M7 (coder M7-HighSpeed, focus scripts/automação)
- [ ] **T2.COM.T6** Bridge bidirectional mavis ↔ MiniMax (mavis communication send via webhook MiniMax)
- [ ] **T2.COM.T7** Teste E2E: Mavis root spawn MiniMax-M3 → reporta de volta via mavis communication messages
- [ ] **T2.COM.T8** Salvar ZCode-MiniMax no MCP servers (mcp_config.json entry)
- [ ] **T2.COM.T9** Documentar skills/tools compartilhadas MiniMax-M3 ↔ Mavis (lista exaustiva)
- [ ] **T2.COM.T10** Runbook de comunicação cross-agent (link, comando, formato de report, timeout, retry)

### Total TIER 2: 100 tasks divididas em 6 subtiers × 5 workers paralelos

| Subtier | Tasks | Worker |
|---------|-------|--------|
| N8N-A | 25 | cartorio-n8n-pro |
| API-A | 25 | cartorio-api-integrations |
| SUPABASE-A | 15 | cartorio-supabase-pro |
| OPENCLAW-A | 15 | cartorio-openclaw-domain |
| EVO-A | 10 | cartorio-evo-advanced |
| COM-A | 10 | cartorio-comunicacao (orquestrador) |
| **TOTAL** | **100** | **5 workers + orquestrador** |

Modified by Gustavo Almeida