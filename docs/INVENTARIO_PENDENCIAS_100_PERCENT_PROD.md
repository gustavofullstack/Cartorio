# Inventário Completo de Pendências — Bot Agent AI Cartório 100% Produção

> **Serviço**: 2º Serviço Notarial de Uberlândia (Tabelionato Djalma de Oliveira)  
> **Regra Canônica**: `CONNECTED != OPERATIONAL`. `Harness PASS != Transport PASS`.  
> **Status de Runtime Atual**: `https://api.2notasudi.com.br/api/v1/health/radar` retorna `status: green` na infraestrutura, mas canais individuais e dependências de hardware/humanas possuem pendências críticas listadas abaixo.

---

## 🛑 1. Bloqueios Humanos e de Hardware (P0 — Ações Externas)

| ID | Componente | Status Atual | Ação Exata Necessária | Dono |
|---|---|---|---|---|
| **B1** | **Pareamento WhatsApp (Evolution 2.3.7)** | `DEGRADED` (`whatsapp_session: close`) | Escanear QR Code de pareamento do número oficial do cartório na interface da Evolution API em `https://flow.2notasudi.com.br`. | Gustavo |
| **B2** | **Nó Hardware VAIO (`agent-os`)** | `HOST_OFFLINE` (`100.116.49.17`) | Ligar fisicamente a máquina VAIO `agent-os` e iniciar daemon Tailscale (`tailscaled`) para hospedar os 6 runtimes Hermes fora do MacBook. | Gustavo |
| **B3** | **Sign-off DPO & Migration Alembic 0028** | `BLOCKED_REVIEW` | Assinar `docs/LGPD_REVIEW_AUDIT_0028_2026-07-24.md` (ADR-030) e rodar `make -C backend alembic-up` no Supabase prod. | DPO / Gustavo |
| **B4** | **Rotação de Secrets Sensíveis** | `BLOCKED_SUI` | Purgar e rotacionar tokens em `infra/n8n-workflows/`, Telegram BotFather token e Webhooks de Alertas. | Gustavo |

---

## 📱 2. Testes de Transporte Real por Canal (P0 — Validação E2E)

### 2.1 WhatsApp (Evolution API 2.3.7)
- **Estado**: API REST operacional, mas sessão desconectada (`connectionState: close`).
- **Gap**: Nenhuma mensagem real WhatsApp chega ao bot até que o pareamento por QR Code seja concluído.

### 2.2 iMessage / Photon Sidecar (T2 Re-Proof & Tool Calling)
- **Estado**: Mensagens trafegam no canal Photon (`:8793`), porém no teste Stage 4.2 o bot respondeu valor numérico (R$ 8,46) **sem** registrar a chamada da ferramenta FastMCP `cartorio_calcular_emolumento`.
- **Gap**:
  1. Re-executar teste real com "Quanto custa reconhecer firma?" e verificar no log a chamada explícita `mcp__cartorio__cartorio_calcular_emolumento`.
  2. Confirmação de recebimento no handset físico do Felipe (`iphone_delivery_confirmed = true`).

### 2.3 Telegram (`@TestCartorioBot`)
- **Estado**: Webhook ativo em `app/api/v1/telegram.py` com sanitização de tags `<think>` e `<reasoning>`.
- **Gap**: Execução de bateria de 20 cenários reais em handset físico de teste para homologação de botões inline e enquetes.

---

## ⚖️ 3. Governança LGPD, PII & Auditoria Imutável

1. **HITL Obrigatório**:
   - Atos com valor declarado (escrituras), isenções fiscais (MCMV), procurações e atas notariais devem **SEMPRE** ser criados com status `DRAFT` ou `HITL_REQUIRED`. O bot nunca emite ato jurídico final.
2. **PII Scrubbing 3-Camadas**:
   - `app/services/pii.py` aplica redação em regex P0 antes de qualquer chamada LLM externa.
   - Sentry `before_send` e `MaskingFilter` filtram logs.
3. **Cadeia de Auditoria SHA256 + HMAC**:
   - `AuditService` preserva ordenação canônica dos blocos. A migração `0028` ajustará o trigger `fn_auto_audit` para alinhamento 100% com o parser Python.

---

## 📊 4. Test Cobertura Codebase (Gate 90%)

- **Status**: Cobertura global em **87%** (`--cov-fail-under=90` falha o CI se acionado isoladamente).
- **Módulos com Cobertura Abaixo da Meta**:
  - `backend/app/api/v1/router.py`: **17.0%** (1.161 linhas)
  - `backend/app/integrations/jules.py`: **57.1%**
  - `backend/app/api/v2/clientes.py`: **53.1%**
  - `backend/app/api/v2/protocolos.py`: **45.6%**
  - `backend/app/api/v2/emolumento.py`: **59.2%**
- **Ação Técnica**: Adicionar testes de integração cobrindo as rotas REST legadas e v2.

---

## 🚀 5. Checklist de Liberação para 100% Produção

- [ ] **Escanear QR Code do WhatsApp**: `https://flow.2notasudi.com.br`
- [ ] **Ligar Servidor VAIO**: Restabelecer SSH no IP `100.116.49.17`
- [ ] **Aplicar Migration 0028**: `make -C backend alembic-up`
- [ ] **Re-prova Tool Call iMessage**: Enviar pergunta de valor e auditar log MCP
- [ ] **Subir Cobertura de Testes**: Elevar `router.py` de 17% para >= 75% para bater gate de 90%
