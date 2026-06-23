# Bloqueios LGPD — Auditoria Sprint Integração Pesada

> **Documento vivo** do Rein `cartorio-lgpd` para registrar bloqueios ativos até resolução.

**Data de criação:** 23/06/2026
**Sprint:** Integração pesada (OpenCode-Go Tailscale, OpenCode-Go API, Chatwoot+Supabase, N8N creds, workflows novos)
**Rein responsável:** `cartorio-lgpd` (sessão `mvs_f7a29511daec40b7995718801be1a2c5`)

---

## 🚫 BLOQUEIO ATIVO #1 — Integração OpenCode-Go (item 1 da delegação) — **AUDITADO**

**O que foi auditado:** `backend/app/integrations/opencode_go.py` (250 linhas, criado em 23/06/2026 13:51 pelo `cartorio-dev`).

**Quem auditou:** Rein `cartorio-lgpd` (sessão `mvs_f7a29511daec40b7995718801be1a2c5`) em 23/06/2026 13:53.

**Estado:** Código aceito mas **NÃO CONFORME LGPD** — 8 blockers identificados (2 críticos, 3 altos, 3 médios).

**Quem resolve:** `cartorio-dev`.

**Bloqueio LGPD:** Merge **NÃO AUTORIZADO** até correção de:
- [ ] **🔴 CRÍTICO**: PII scrubbing interno em `chat()` — chamar `pii.scrub()` em cada `message["content"]` antes de enviar (defense-in-depth, não shift-the-burden)
- [ ] **🔴 CRÍTICO**: DPA com MiniMax assinado (`docs/lgpd/dpa_minimax.pdf`) — Gustavo + DPO. Até lá, ambiente é **STAGING ONLY**
- [ ] **🟠 ALTO**: Audit log de chamadas (hash do payload enviado/recebido) via `AuditService.log()` — LGPD art. 37
- [ ] **🟠 ALTO**: Consent gate (`consent.granted=true`) validado antes de chamar OpenCode-Go — LGPD art. 7º I
- [ ] **🟠 ALTO**: Teste de regressão `tests/integration/test_opencode_go_no_pii.py` (mock httpx, assert que payload bruto NÃO chega)
- [ ] **🟡 MÉDIO**: Fallback `chat_with_fallback()` para LiteLLM (OpenAI/Anthropic) com mesmo scrubbing
- [ ] **🟡 MÉDIO**: Rate limit por sessão (60 chamadas/min)
- [ ] **🟡 MÉDIO**: Alinhar inconsistência de modelo (docstring diz `deepseek-v4-flash`, opencode.json diz MiniMax, RIPD diz MiniMax — qual é o real?)

**Pontos fortes já implementados (manter):**
- ✅ Bearer auth via header (não URL)
- ✅ Timeout 30s
- ✅ Não loga payload bruto
- ✅ `raw=None` por padrão (LGPD-friendly)
- ✅ Erros tipados sem leak
- ✅ Docstring explicita que caller DEVE scrubar

**Documentação completa:** `docs/lgpd/opencode_go_audit.md` v1.0 (com correção de código proposta em diff)

---

## 🚫 BLOQUEIO ATIVO #2 — Workflow WF-NOVO-01 OpenClaw Webhook (item 2 da delegação)

**O que falta:** Workflow `WF-NOVO-01 (OpenClaw Webhook Receiver)` precisa ser criado pelo `cartorio-n8n`.
**Estado atual:** Workflow **NÃO EXISTE**. `infra/n8n-workflows/` só tem 01-11 antigos.
**Quem resolve:** `cartorio-n8n`
**Quando auditar:** Imediatamente após `cartorio-n8n` entregar.
**Bloqueio LGPD:** Merge/ativação **NÃO AUTORIZADA** até:
- [ ] Cabeçalho de autenticação correto (token em header `Authorization: Bearer` ou `X-Webhook-Secret`, **NUNCA** em query string)
- [ ] Token NUNCA aparece em log de execução do N8N
- [ ] Dados persistidos em `openclaw_messages` (Supabase) passam por `pii.scrub()` ANTES do INSERT
- [ ] Coluna `payload_hash` (SHA-256) gravada junto
- [ ] Tabela `openclaw_messages` tem RLS habilitado (apenas DPO + tabelião leem)
- [ ] Política de retenção: job diário apaga registros > 90 dias (LGPD art. 16 — Tratamento 5 espelha)
- [ ] Audit log do FastAPI registra cada webhook recebido (`/webhooks/openclaw`)

---

## 🚫 BLOQUEIO ATIVO #3 — Workflow WF-NOVO-02 OpenCode-Go Router (item 3 da delegação)

**O que falta:** Workflow `WF-NOVO-02 (OpenCode-Go Router)` precisa ser criado pelo `cartorio-n8n`.
**Estado atual:** Workflow **NÃO EXISTE**.
**Quem resolve:** `cartorio-n8n`
**Quando auditar:** Imediatamente após `cartorio-n8n` entregar.
**Bloqueio LGPD:** Merge/ativação **NÃO AUTORIZADA** até:
- [ ] Workflow chama `pii.scrub()` em node Function ANTES de montar o prompt (regex 11 tipos)
- [ ] Prompt NÃO concatena campos brutos (`{{$json.cliente.cpf}}`, `{{$json.cliente.nome}}`, etc.) — devem ser substituídos por tokens ou hash
- [ ] Audit log da execução registra `payload_hash` do prompt enviado
- [ ] Se OpenCode-Go falhar → fallback para LiteLLM (OpenAI/Anthropic) com mesmo scrubbing
- [ ] Teste no N8N: input com CPF bruto → assert que output NÃO contém CPF (regex `\d{3}\.\d{3}\.\d{3}-\d{2}`)

**Severidade:** **CRÍTICA**. LGPD proíbe envio de dado pessoal pra API de terceiro sem consentimento específico. Consentimento atual (workflow boas-vindas) é para tratamento geral, não para sub-processor específico.

---

## 🚫 BLOQUEIO ATIVO #4 — Workflow WF-NOVO-03 Prospecção (item 4 da delegação)

**O que falta:** Workflow `WF-NOVO-03 (Prospecção)` precisa ser criado pelo `cartorio-n8n`.
**Estado atual:** Workflow **NÃO EXISTE**.
**Quem resolve:** `cartorio-n8n`
**Quando auditar:** Imediatamente após `cartorio-n8n` entregar.
**Bloqueio LGPD:** Merge/ativação **NÃO AUTORIZADA** até:
- [ ] Leads vêm **exclusivamente** de fonte pública (ANOREG, CNJ, site oficial do cartório, Google Meu Negócio) — **NUNCA** de lista comprada ou scrape não autorizado
- [ ] Consentimento de marketing coletado ANTES do primeiro envio (opt-in affirmative)
- [ ] Opt-out **funcional**: keywords `PARAR`, `SAIR`, `CANCELAR`, `STOP` em qualquer canal → inserir em `opt_out_log` (Supabase) + parar envios imediatamente + confirmar com mensagem "ok, removido"
- [ ] Limite de 20 mensagens/dia/WhatsApp pessoal (anti-spam)
- [ ] Cada envio registra: lead_id, timestamp, canal, conteúdo, opt-in flag, hash do texto enviado
- [ ] Retenção da lista de prospecção: 5 anos (log comercial — Tratamento 3 do RIPD) — após, deletar ou anonimizar
- [ ] Roteiro LGPD-safe usado: `docs/prospeccao-roteiro.md` (já existe, revisar aderência)

**Severidade:** **ALTA**. LGPD art. 7º I (consentimento) + art. 18 IX (revogação) + art. 50 (boas práticas). Sem opt-out funcional → multa + bloqueio da ANPD.

---

## ⚠️ PENDÊNCIA #5 — Chatwoot unificado no Supabase Postgres (item 5 da delegação) — **VALIDADO PARCIALMENTE**

**O que foi auditado:** Conexão Chatwoot ↔ Supabase via SSH em VPS `100.99.172.84`.

**Quem auditou:** Rein `cartorio-lgpd` (sessão `mvs_f7a29511daec40b7995718801be1a2c5`) em 23/06/2026 13:53.

**Estado:** Unificação **CONFIRMADA** mas com **pendência de segurança**.

**Achados positivos:**
- ✅ Database `chatwoot` está dentro do Postgres Supabase (junto com `cartorio`, `evolution`, `n8n`) — antes era Postgres separado
- ✅ Container `cartorio_chatwoot` rodando (Up 40 minutes)
- ✅ Backup `supabase_chatwoot_*.dump` é gerado 4x/dia automaticamente em `/var/backups/cartorio/` (317KB cada — pequeno, mas funcional)
- ✅ Postgres versão 15.8.1 (Supabase gerenciado)

**Achados negativos (pendência P1 — sprint 2):**
- ⚠️ Filesystem da VPS é **ext4 SEM LUKS** (`/dev/sda1 on /var/lib/docker/volumes/...`) — Postgres data at rest **NÃO está criptografado** em nível de disco
- ⚠️ PG_DUMP é **plaintext SQL** — se atacante ler `/var/backups/cartorio/`, tem tudo
- ⚠️ RLS no Supabase precisa ser validado por schema/role (auditoria adicional necessária)
- ⚠️ Audit log de quem acessou conversa Chatwoot (LGPD art. 37) — não verificado

**Quem resolve:** `cartorio-dev` (escolher Opção A, B ou C da pendência L3 de PENDENCIAS_SUI).

**Bloqueio LGPD:** **NÃO BLOQUEIA** unificação (que já está em produção). Mas é **pendência P1 de segurança** que deve entrar no **Sprint 2**. Conversas com clientes podem conter dado pessoal sensível (LGPD art. 5º II — biométrico em reconhecimento de firma).

**Ação imediata (cartorio-dev):**
- [ ] (P1) Habilitar `pgcrypto` e criptografar colunas sensíveis (`conversations.content`, `contacts.email`, `contacts.phone_number`) — Opção A da pendência L3
- [ ] (P1) Criptografar PG_DUMP com gpg + chave em Vault antes de armazenar — Opção C
- [ ] (P2) Configurar RLS para tabelas Chatwoot no Supabase (roles: `chatwoot_agent`, `chatwoot_admin`)
- [ ] (P2) Adicionar audit log de leitura em `conversations` (LGPD art. 37)

---

## 🚫 BLOQUEIO ATIVO #6 — DPA com MiniMax (dependência do item 1)

**O que falta:** Data Processing Agreement (DPA) assinado entre Cartório 2 Notas Uberlândia e MiniMax (provider do OpenCode-Go).
**Estado atual:** **NÃO EXISTE**. Sem contrato formal, MiniMax pode usar dado enviado para melhoria do serviço.
**Quem resolve:** Gustavo + DPO.
**Quando auditar:** Antes de qualquer chamada de produção ao OpenCode-Go com dado real.
**Bloqueio LGPD:** Ambiente **STAGING ONLY** até DPA assinado. Dados reais de clientes **PROIBIDOS**.

**Template DPA:** buscar na Resolução CD/ANPD nº 4/2023 + modelo da IAPP (International Association of Privacy Professionals).

---

## ✅ Auditorias/documentações CONCLUÍDAS nesta sessão

| Item | Status | Arquivo |
|------|--------|---------|
| Item 6 — RIPD atualizado para v1.2 | ✅ Concluído | `docs/ripd.md` |
| Item 7 — PENDENCIAS_SUI atualizado | ✅ Concluído | `docs/PENDENCIAS_SUI_2026-06-23.md` |
| Template auditoria OpenCode-Go | ✅ Concluído | `docs/lgpd/opencode_go_audit.md` |
| Documento de bloqueios (este) | ✅ Concluído | `docs/lgpd/AUDITORIA_BLOCKERS.md` |

---

## 🚫 BLOQUEIO ATIVO #7 — Output LLM não é scrubbed (P0 — descoberto 2026-06-23)

**O que foi auditado:** `backend/app/integrations/opencode_go.py:388-397` — extração de `content = choice["message"]["content"]` do response do provider.

**Quem auditou:** Rein `cartorio-lgpd` (sessão `mvs_3c841fe2622b4755bcd39d89333d4037`) em 23/06/2026 18:39.

**Estado:** Output do LLM é retornado em `ChatResponse.content` SEM chamar `pii.scrub()` novamente. O `content` então é persistido em `conversas.bot_response` e enviado ao cliente via WhatsApp.

**Consequência:** Se o LLM ecoar PII (mesmo que a request tenha ido scrubbed — o LLM pode ter memorizado padrão de CPF/CNS em dados de treino), o cliente recebe o PII de volta no WhatsApp. **Pior caso:** se CNS (dado sensível art. 5 II) for ecoado, dado sensível chega ao titular e ao log de conversa, violando LGPD art. 11 (base legal específica) + art. 46 (medidas de segurança) + a promessa de "PII scrubbing em 3 camadas" feita em `docs/ripd.md:175`.

**Quem resolve:** `cartorio-dev`.

**Bloqueio LGPD:** Merge **NÃO AUTORIZADO** até correção:
- [ ] **🔴 CRÍTICO**: Chamar `scrub(content)` imediatamente após `content = choice["message"]["content"]` (linha 390 do opencode_go.py)
- [ ] **🔴 CRÍTICO**: Adicionar `output_pii_redacted_count` ao `ChatResponse` (separado de `pii_redacted_count` da request)
- [ ] **🟠 ALTO**: Adicionar teste em `test_opencode_go_no_pii.py`: input com CNS, mock LLM que ecoa CNS, assert que `ChatResponse.content` retornado NÃO contém CNS
- [ ] **🟡 MÉDIO**: Atualizar `ripd.md:175` para explicitar que a 3ª camada (output scrub) é defense-in-depth contra LLM ecoando PII

**Severidade agregada LGPD:** CRÍTICA — replica o gap CNS do `pii.py` no boundary de saída. Se deploy acontecer sem este fix, qualquer cliente que enviar CNS via WhatsApp recebe o próprio CNS de volta, dopando a métrica "incidente de segurança LGPD" e podendo gerar autuação direta da ANPD.

---

## ⚠️ PENDÊNCIA #8 — Auditoria opencode_go pós-correção dos 8 originais (LGPD-014 + outros 3)

> **Atualização 2026-06-23 18:39** — auditoria completa do `opencode_go.py` (497 linhas) revelou que dos 8 blockers originais (fechados em commit `01c26df`), 4 NOVOS blockers foram identificados:

- **#9 [P1] Audit log swallow exception** — `opencode_go.py:441-444`. Se `AuditService.log()` falhar (DB down, hash chain corrompido), exceção é silenciosamente engolida. Viola LGPD art. 50 (boas práticas — observabilidade). Solução: dead-letter queue (Redis ou tabela `audit_dead_letter` no Postgres) + alerta N8N.
- **#10 [P0] Output LLM não scrubbed** — ver Bloco #7 acima.
- **#11 [P2] Hash sem HMAC** — `opencode_go.py:239-242` usa SHA-256 simples. Inconsistente com `audit.py:48-50` que usa HMAC. Reusar `AuditService._compute_hmac()`.
- **#12 [P2] Rate limit sem tratamento de falha Redis** — `opencode_go.py:195-210` não trata `redis.RedisError`. Se Redis off, fluxo cai. Solução: try/except + fail-open (permitir com warning) + alerta N8N.

E re-confirmado que **Bloqueio #6 (DPA MiniMax/DeepSeek)** continua PENDENTE — nenhum arquivo DPA no repo (`docs/lgpd/dpa_*.pdf` inexistente).

---

## Próximos passos

1. `cartorio-dev` entrega `backend/app/integrations/opencode_go.py` com fix do Blocker #10 (output scrub) → eu audito em ≤24h
2. `cartorio-n8n` entrega WF-NOVO-01/02/03 → eu audito em ≤24h
3. `cartorio-dev` entrega migrations Chatwoot → eu audito em ≤24h
4. Gustavo/DPO fecha DPA com **DeepSeek** (chines) OU troca provedor para OpenAI/Anthropic (DPA template, país com adequação) → remove Bloqueio #6
5. Sprint 4: implementar Bloqueios #5 (fallback real), #9 (dead-letter queue), #11 (HMAC), #12 (Redis fail-open)
6. Re-run do checklist de auditoria pós-correção

**Cron configurado** para me lembrar em 4h caso dependências ainda não tenham chegado.

Modified by Gustavo Almeida