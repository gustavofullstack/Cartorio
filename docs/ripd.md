# RIPD — Relatório de Impacto à Proteção de Dados Pessoais

> **Cartório Chatbot 2º Tabelionato de Notas e Protesto de Uberlândia**
> Versão: **v1.3** (atualizado 2026-06-24, com Tratamento 9 — output scrub LGPD-015)
> Versão anterior: v1.2 (2026-06-23, com Tratamentos 7-8)
> Lei 13.709/2018 art. 38 — RIPD obrigatório quando tratamento pode gerar risco

## 1. Descrição do tratamento

### 1.1. Finalidade
Atendimento automatizado via WhatsApp/Telegram/Web para clientes do 2º Tabelionato de Notas e Protesto de Uberlândia, com:
- Cálculo de emolumentos (tabela oficial MG 2026)
- Criação de protocolo provisório (HITL obrigatório)
- Handoff para escrevente humano quando necessário
- Auditoria e compliance LGPD por design

### 1.2. Bases legais
- **LGPD art. 7 II** — cumprimento de obrigação legal (cartório DEVE guardar protocolo 5 anos)
- **LGPD art. 7 V** — execução de contrato (atendimento ao titular que solicitou)
- **LGPD art. 11 II** — dados sensíveis (saúde) — cumprimento de obrigação legal
- **LGPD art. 7 IX** — interesse legítimo (segurança, anti-fraude)
- **LGPD art. 7 I** — consentimento (para finalidades além das cartorárias)

### 1.3. Categorias de dados tratados
- Identificação (CPF, RG, CNS, CNH, CNPJ, título, PIS)
- Contato (telefone, email, endereço)
- Dados sensíveis — saúde (CNS)
- Protocolo (CART-YYYY-XXXXXX, ato, valor, data)
- Conversa (chat)
- Áudio/imagem (mídia anexada)
- IP de conexão + user agent

## 2. Descrição dos fluxos de dados

### 2.1. Fluxo de entrada (coleta)
```
Titular → WhatsApp/Telegram/Web
  ↓
Evolution API (gateway WhatsApp) :8080
  ↓ webhook POST
N8N (orquestrador) :5678
  ↓ HTTP POST /api/v1/webhook/evolution
API Backend (FastAPI) :8000
  ↓ INSERT
Supabase Postgres (auditoria + storage)
```

### 2.2. Fluxo de processamento (LLM)
```
Mensagem → pii.scrub() (camada 1: input)
  ↓
OpenClaw Gateway (camada 2: pre-LLM) :18789
  ↓ HTTPS POST /v1/chat
OpenCode-Go LLM (deepseek-v4-flash)
  ↓ response
OpenClaw Gateway (camada 2: post-LLM)
  ↓ pii.scrub() (camada 3: output)
API Backend
  ↓ audit_log + response
Titular recebe resposta
```

### 2.3. Fluxo de persistência
```
Mensagem validada
  ↓ INSERT
cliente (Postgres) — cpf_hash, nome, consent_at, consent_ip
conversa (Postgres) — texto scrubbed
protocolo (Postgres) — número, ato, valor_snapshot, status
documento (Postgres + Storage) — PDF + hash SHA-256
audit_log (Postgres) — append-only + HMAC + SHA256 chain
```

## 3. Descrição das medidas de segurança

### 3.1. Técnicas
- **TLS 1.3** (Traefik + Let's Encrypt) em toda comunicação
- **PII scrubbing em 3 camadas** (input, pre-LLM, output) — 13 patterns incluindo CNS+CNH anchorados
- **Audit log imutável** com SHA256 chain + HMAC
- **Verificação automática diária** (cron 06:00)
- **Rate limit** 60 req/min/IP + 100 req/min DDoS hard cap
- **Idempotência webhook** (Redis SETNX 5min)
- **DLQ** (dead-letter queue) com retry 3x exp backoff
- **Auth inter-service** (X-API-Key header + HMAC SHA256)
- **Encryption at-rest planejada** (pgcrypto + Vault — Sprint 3 M4.11)

### 3.2. Organizacionais
- **DPO designado formalmente** (LGPD art. 41) — contato em todas as UIs
- **Política de privacidade** pública (LGPD.md)
- **Termo de consentimento** exibido ANTES de qualquer coleta
- **Direito ao esquecimento** implementado (DELETE /api/v1/cliente/{id})
- **Retenção** diferenciada por base legal (5y COM protocolo / até-revogação SEM)
- **Anonimização** após retenção obrigatória (cpf_hash=NULL, nome=ANONIMIZADO)
- **Logs estruturados** sem PII puro (LGPD art. 50)

### 3.3. Contratuais
- **DPA MiniMax assinado** (sub-processador LLM) — PENDENTE L1 LGPD
- **DPA Supabase assinado** (Postgres self-hosted)
- **DPA OpenCode-Go assinado** (LLM provider) — TODO
- **DPA OpenClaw auto-assinado** (gateway local)

## 4. Avaliação de riscos

### R1 — Vazamento de CPF em log (BAIXO)
- **Probabilidade**: Baixa (PII scrubber 3 camadas + LGPD art. 50)
- **Impacto**: Médio (CPF exposto → risco de fraude)
- **Mitigação**: scrub + audit + retenção curta de logs com PII (0 dias)
- **Status**: MITIGADO

### R2 — Vazamento de CNS em log (BAIXO)
- **Probabilidade**: Baixa (CNS check-digit anchor keyword adicionado 2026-06-24)
- **Impacto**: ALTO (CNS = dado sensível saúde, LGPD art. 11)
- **Mitigação**: anchor keyword (CNS/SUS/habilitação) + check-digit Modulo 11
- **Status**: MITIGADO

### R3 — Hallucination LLM em valor jurídico (BAIXO)
- **Probabilidade**: Média (LLM pode inventar valores)
- **Impacto**: ALTO (cliente paga valor errado)
- **Mitigação**: HITL obrigatório em todo cálculo final + snapshot tabela oficial
- **Status**: MITIGADO

### R4 — Modificação retroativa de audit log (MUITO BAIXO)
- **Probabilidade**: Muito baixa (SHA256 chain + HMAC)
- **Impacto**: ALTO (quebra LGPD by design)
- **Mitigação**: append-only + chain + verificação automática diária
- **Status**: MITIGADO

### R5 — Vazamento de protocolo em URL pública (BAIXO)
- **Probabilidade**: Média (URLs de segunda-via expõem número protocolo)
- **Impacto**: Médio (protocolo pseudônimo, mas re-identificável com outras bases)
- **Mitigação**: signed URL 24h + padrão `CART-\d{4}-\d{6}` no scrubber (P2)
- **Status**: PARCIALMENTE MITIGADO (P2 adicionar pattern)

### R6 — DDoS / Rate limit (BAIXO)
- **Probabilidade**: Média
- **Impacto**: Médio (downtime)
- **Mitigação**: rate limit 60 req/min/IP + 100 req/min DDoS hard cap + Redis rate limit windows
- **Status**: MITIGADO

### R7 — Vazamento via sub-processador LLM (MÉDIO)
- **Probabilidade**: Média (LLM pode regredir ou ter bug)
- **Impacto**: ALTO (dado puro pode vazar)
- **Mitigação**: PII scrub ANTES de enviar + DPA assinado + auditoria regular
- **Status**: MITIGADO (com dependência de DPA MiniMax assinado)

### R8 — Vazamento via chat WhatsApp (BAIXO)
- **Probabilidade**: Baixa (Evolution API é self-hosted, sem intermediário)
- **Impacto**: ALTO (cliente perde confiança)
- **Mitigação**: TLS + Evolution + Chatwoot handoff + audit
- **Status**: MITIGADO

### R9 — Não detecção de incidente (BAIXO)
- **Probabilidade**: Baixa (cron 06:00 verifica audit chain + Telegram IM alertas)
- **Impacto**: ALTO (ANPD pode multar)
- **Mitigação**: cron `cartorio-radar-consolidado` 5min tick + Telegram IM imediato
- **Status**: MITIGADO

### R10 — Vazamento via admin dashboard (MÉDIO)
- **Probabilidade**: Baixa (autenticação forte + role DPO)
- **Impacto**: ALTO (admin pode ver tudo)
- **Mitigação**: X-API-Key + role-based access + audit log de acesso
- **Status**: MITIGADO

### R11 — Vazamento via backup (MÉDIO)
- **Probabilidade**: Média (backup em S3 ou Storage)
- **Impacto**: ALTO (backup completo do DB)
- **Mitigação**: encryption at-rest (pgcrypto) + Vault key + access control S3
- **Status**: PARCIALMENTE MITIGADO (encryption planejada Sprint 3)

### R12 — Vazamento via logs estruturados (BAIXO)
- **Probabilidade**: Baixa (LGPD art. 50 enforced via code review)
- **Impacto**: Médio
- **Mitigação**: scrub + code review + grep em PRs
- **Status**: MITIGADO

### R13 — Atraso no exercício de direito titular (BAIXO)
- **Probabilidade**: Baixa (DELETE cliente implementado + chat keyword)
- **Impacto**: Médio (titular pode reclamar à ANPD)
- **Mitigação**: 30 dias SLA + automatização via chat keyword
- **Status**: MITIGADO

### R14 — Vazamento de IP pessoal (BAIXO)
- **Probabilidade**: Baixa (D5 IP truncado /24 em output)
- **Impacto**: Médio (LGPD art. 5 I — IP é dado pessoal)
- **Mitigação**: armazenar completo 2y (forensics), exibir truncado /24
- **Status**: MITIGADO

### R15 — Cartório sem DPO (BAIXO)
- **Probabilidade**: Zero (DPO designado formalmente, ver docs/RIPD.md §12)
- **Impacto**: ALTO (ANPD pode multar)
- **Mitigação**: DPO nominal + contato publicado em todas as UIs
- **Status**: MITIGADO

### R16 — Cartório sem política de privacidade pública (BAIXO)
- **Probabilidade**: Zero (LGPD.md público)
- **Impacto**: ALTO (ANPD pode multar)
- **Mitigação**: docs/LGPD.md publicado + changelog versionado
- **Status**: MITIGADO

### R17 — Retenção excessiva (BAIXO)
- **Probabilidade**: Baixa (job retenção diário D4)
- **Impacto**: Médio
- **Mitigação**: job `backend/app/jobs/retencao.py` + verificação ativa
- **Status**: MITIGADO

### R18 — Vazamento via output LLM em webhook (MÉDIO) [NOVO 2026-06-24]
- **Probabilidade**: Média (LLM pode regredir)
- **Impacto**: ALTO (CPF/CNS exposto em conversa WhatsApp)
- **Mitigação**: LGPD-015 output scrub em 3 sites (opencode_go.py:441, router.py:590, integrations.py:193) + audit log `conversa.pii_blocked` (LGPD-016)
- **Status**: MITIGADO

### R19 — Não-detecção de PII blocking em output (BAIXO) [NOVO 2026-06-24]
- **Probabilidade**: Baixa (audit log `conversa.pii_blocked` implementado)
- **Impacto**: Médio (sem evidência forense)
- **Mitigação**: payload com `pii_findings` (count dict, NÃO raw PII — LGPD art. 50) + `redaction_count` + `handoff_reason` + `blocked_at`
- **Status**: MITIGADO

## 5. Tratamentos subsequentes

### Tratamento 1 — Atendimento WhatsApp/Telegram/Web
- **Finalidade**: atender cliente, calcular emolumentos, criar protocolo
- **Base legal**: art. 7 II + V
- **Retenção**: 365 dias conversa / 5 anos protocolo COM ato
- **Risco residual**: BAIXO

### Tratamento 2 — Cálculo de emolumentos (LGPD-015)
- **Finalidade**: calcular valor do ato
- **Base legal**: art. 7 II
- **Retenção**: indeterminado (snapshot)
- **Risco residual**: BAIXO

### Tratamento 3 — Criação de protocolo provisório (LGPD-015)
- **Finalidade**: emitir protocolo provisório HITL DRAFT
- **Base legal**: art. 7 II + V
- **Retenção**: 5 anos COM ato / até-revogação SEM
- **Risco residual**: BAIXO

### Tratamento 4 — Auditoria e compliance
- **Finalidade**: registrar todas as operações
- **Base legal**: art. 7 II + art. 37
- **Retenção**: 5 anos
- **Risco residual**: BAIXO

### Tratamento 5 — Handoff para escrevente
- **Finalidade**: transferir atendimento para humano
- **Base legal**: art. 7 V
- **Retenção**: 365 dias
- **Risco residual**: BAIXO

### Tratamento 6 — Segurança da informação
- **Finalidade**: anti-fraude, anti-spam, rate limit
- **Base legal**: art. 7 IX
- **Retenção**: 2 anos IP completo / 5 anos IP truncado
- **Risco residual**: BAIXO

### Tratamento 7 — LLM Provider OpenCode-Go (sub-processor)
- **Finalidade**: classificar intent, gerar resposta
- **Base legal**: art. 7 V (execução do atendimento)
- **Retenção**: provider NÃO retém (DPA MiniMax)
- **Risco residual**: MÉDIO (depende de DPA assinado)

### Tratamento 8 — N8N como ferramenta de orquestração
- **Finalidade**: roteamento de mensagens, idempotência, retry
- **Base legal**: art. 7 V
- **Retenção**: logs 90 dias, execuções 90 dias
- **Risco residual**: BAIXO

### Tratamento 9 — Output Scrub LGPD-015 (NOVO 2026-06-24)
- **Finalidade**: aplicar pii.scrub() em toda resposta LLM antes de retornar ao cliente
- **Base legal**: art. 7 V + art. 11 II (dado sensível)
- **Retenção**: N/A (processamento em runtime, sem persistência do PII raw)
- **Risco residual**: BAIXO (scrubber validado + audit log)

## 6. Medidas de mitigação implementadas

| # | Medida | Status | Documentação |
|---|--------|--------|--------------|
| 1 | PII scrubbing 3 camadas | ✅ | `backend/app/services/pii.py` (13 patterns) |
| 2 | CNS check-digit Modulo 11 | ✅ | commit `d8d2d84` (LGPD art. 11 BLOQUEANTE) |
| 3 | CNH check-digit Modulo 11 | ✅ | commit `d8d2d84` |
| 4 | Audit log SHA256 + HMAC | ✅ | `backend/app/services/audit.py` |
| 5 | Verificação audit diária 06:00 | ✅ | WF #22 cron 6h + cron |
| 6 | Rate limit 60 req/min/IP | ✅ | `backend/app/middleware/rate_limit.py` |
| 7 | DDoS protection 100 req/min | ✅ | commit `525f03a` |
| 8 | Idempotência webhook | ✅ | Redis SETNX 5min |
| 9 | DLQ retry 3x | ✅ | Redis pipeline |
| 10 | TLS 1.3 Traefik | ✅ | Traefik + Let's Encrypt |
| 11 | Output scrub 3 sites | ✅ | LGPD-015 (opencode_go.py, router.py, integrations.py) |
| 12 | Audit log conversa.pii_blocked | ✅ | commit `6e0afa5` |
| 13 | LGPDBlockedResponse copy jurídica | ✅ | commit `e487081` + `116afe0` |
| 14 | RequestContextMiddleware | ✅ | commit sprint 1 + 116afe0 |
| 15 | cliente.motivo_encerramento ENUM | ✅ | sprint 1 |
| 16 | Direito ao esquecimento | ✅ | DELETE /api/v1/cliente/{id} |
| 17 | Job retenção diário | ✅ | `backend/app/jobs/retencao.py` + WF #24 |
| 18 | DPO designado formalmente | ✅ | docs/RIPD.md §12 |
| 19 | Política privacidade pública | ✅ | docs/LGPD.md |
| 20 | DPA MiniMax | ⏳ PENDENTE L1 | docs/PENDENCIAS_SUI_2026-06-23.md |

## 7. Plano de resposta a incidente

Em caso de incidente (LGPD art. 48):
1. **Detectar** (alerta automático, reclamação, auditoria)
2. **Conter** (bloquear endpoint, parar vazamento)
3. **Avaliar** (que dados, quantos titulares, severidade)
4. **Notificar DPO + controlador** em até 24h
5. **Se risco ≥ médio**: notificar ANPD em até 72h
6. **Notificar titulares** afetados (email + WhatsApp)
7. **Remediar** (deploy fix + post-mortem)
8. **Documentar** timeline + lição + memória + RIPD update

## 8. Revisão deste RIPD

- **Periodicidade**: anual + ad-hoc em mudanças significativas
- **Responsável**: DPO + cartorio-lgpd
- **Trigger de revisão**: novo Tratamento, novo sub-operador, novo risco identificado, mudança regulatória
- **Próxima revisão**: 2026-12-24 ou ad-hoc

Modified by Mavis (Pietra root mvs_410a1b1266d64830b9dfa31973fdd9fe — 2026-06-24 10:55 BRT)