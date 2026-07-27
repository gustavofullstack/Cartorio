# Inventário Completo de Prontidão — Bot Agent AI Cartório (100% VPS Cartório)

> **Serviço**: 2º Serviço Notarial de Uberlândia (Tabelionato Djalma de Oliveira)  
> **Infraestrutura**: Servidor Único VPS Cartório (`187.77.236.77` / Tailscale `100.99.172.84` / `api.2notasudi.com.br`)  
> **Regra Canônica**: `CONNECTED != OPERATIONAL`. `Harness PASS != Transport PASS`.  
> **Status de Runtime Atual**: `https://api.2notasudi.com.br/api/v1/health/radar` retorna `status: green` na infraestrutura VPS.

---

## 🏗️ 1. Arquitetura 100% VPS Cartório (Sem Nós Externos)

Toda a pilha operacional do 2º Ofício Notarial roda exclusivamente no Docker Swarm / Easypanel da VPS Hostinger do Cartório:

1. **Hermes Cartório Gateway**: Orquestrador e agente IA notarial alimentado por **MiniMax Coding Plan** (chave oficial mantida sem rotação).
2. **API Backend**: FastAPI 0.115 + FastMCP (15 ferramentas notariais publicadas) + PII Scrubbing 3-camadas + Log de Auditoria SHA256/HMAC.
3. **Postgres 16 / Supabase**: Banco de dados relacional com RLS e schema Alembic.
4. **Redis 8**: Cache, rate-limiting por janela deslizante e idempotência SETNX (24h).
5. **Chatwoot 3.x/4.x**: CRM unificado de atendimento (Telegram, WhatsApp, iMessage, Web Widget, Handoff Humano/HITL).
6. **Photon Gateway**: Bridge de iMessage e roteamento de transporte.
7. **Evolution API 2.3.7 & Evo-Hub / WA-CLI**: Transporte WhatsApp multi-instância.
8. **N8N**: Engine de Workflows (38 workflows ativos em `flow.2notasudi.com.br`).
9. **CNJ Export**: Serviço de exportação e conformidade CNJ Provimento 74.
10. **Tailscale & SSH**: Acesso seguro via `100.99.172.84` / `187.77.236.77`.

---

## 🛑 2. Bloqueios Humanos e de Homologação Real (Ações de Produção)

| ID | Componente | Status Atual | Ação Exata Necessária | Dono |
|---|---|---|---|---|
| **B1** | **Pareamento WhatsApp (Evolution 2.3.7)** | `DEGRADED` (`whatsapp_session: close`) | Escanear QR Code de pareamento do número oficial do cartório na interface da Evolution API em `https://flow.2notasudi.com.br`. | Gustavo |
| **B2** | **Sign-off DPO & Migration Alembic 0028** | `BLOCKED_REVIEW` | Assinar `docs/LGPD_REVIEW_AUDIT_0028_2026-07-24.md` (ADR-030) e aplicar migração no Supabase da VPS (`make -C backend alembic-up`). | DPO / Gustavo |
| **B3** | **Rotação de Secrets Sensíveis** | `BLOCKED_SUI` | Purgar e rotacionar tokens em `infra/n8n-workflows/`, Telegram BotFather token e Webhooks de Alertas (mantendo a chave MiniMax intocada). | Gustavo |

---

## 📱 3. Testes de Transporte Real por Canal

### 3.1 WhatsApp (Evolution API 2.3.7)
- **Estado**: Container online na VPS Cartório, mas sessão desconectada (`connectionState: close`).
- **Pendente**: Escanear QR Code para iniciar o tráfego de mensagens reais no WhatsApp.

### 3.2 iMessage / Photon Transport (Re-prova de Chamada MCP)
- **Estado**: Mensagens trafegam no canal Photon (`:8793`). No teste Stage 4.2 o bot respondeu valor numérico (R$ 8,46) **sem** registrar a chamada da ferramenta FastMCP `cartorio_calcular_emolumento`.
- **Pendente**: 
  1. Re-executar teste real com "Quanto custa reconhecer firma?" e verificar no log a chamada explícita `cartorio_calcular_emolumento`.
  2. Confirmação de recebimento no handset físico do Felipe (`iphone_delivery_confirmed = true`).

### 3.3 Telegram (`@TestCartorioBot`)
- **Estado**: Webhook ativo na VPS em `app/api/v1/telegram.py` com sanitização de tags `<think>` e `<reasoning>`.
- **Pendente**: Homologação final de 20 cenários em handset físico.

---

## ⚖️ 4. Governança LGPD, PII & Auditoria Imutável

1. **HITL Obrigatório**:
   - Atos com valor declarado (escrituras), isenções fiscais (MCMV), procurações e atas notariais são criados com status `DRAFT` ou `HITL_REQUIRED`. O bot nunca emite ato jurídico final.
2. **PII Scrubbing 3-Camadas**:
   - `app/services/pii.py` aplica redação em regex P0 antes de qualquer chamada LLM externa.
   - Sentry `before_send` e `MaskingFilter` filtram logs.
3. **Cadeia de Auditoria SHA256 + HMAC**:
   - `AuditService` preserva ordenação canônica dos blocos. A migração `0028` ajusta o trigger `fn_auto_audit` da VPS.

---

## 🚀 5. Checklist de Liberação de Produção (100% VPS Cartório)

- [ ] **Escanear QR Code do WhatsApp**: `https://flow.2notasudi.com.br`
- [ ] **Aplicar Migration 0028 na VPS**: `make -C backend alembic-up`
- [ ] **Re-prova Tool Call iMessage**: Enviar pergunta de valor e auditar log MCP
- [ ] **Acesso ao Dashboard**: Disponível ao vivo em `https://api.2notasudi.com.br/dashboard`
