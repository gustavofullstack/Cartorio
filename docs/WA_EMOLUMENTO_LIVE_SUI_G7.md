# WhatsApp → Emolumento live SUI (G7.04.T4)

| Campo | Valor |
|-------|--------|
| **Task** | G7.04.T4 — 1 msg real WA → resposta emolumento |
| **Wave pack** | **Wave28 SUI pack refreshed** (2026-07-17) |
| **Agent-side** | Synthetic E2E **DONE** Wave22 |
| **Live** | **[~] HOLD-GUSTAVO** — não marcar `[x]` sem msg real no celular |
| **Rein** | cartorio-n8n + cartorio-evolution |

---

## Status

| Camada | Estado | Evidência |
|--------|--------|-----------|
| Dual-format parse Evolution | ✅ | `parse_evolution_payload` + G7.04.T3 Hypothesis |
| Cálculo emolumento MG 2026 | ✅ | `procuracao` = **R$ 156,40** (`emolumento.py`) |
| Synthetic WA→parse→calc | ✅ | `backend/tests/test_g7_wave22_integration.py::test_wa_emolumento_synthetic_flow` |
| Evolution UP + QR open | **[~]** | depende G7.04.T1/T2 + Lesson 176 |
| 1 msg real no WhatsApp | **[~]** | este one-pager |

**Regra:** agent **não** executa QR/scan nem manda WA de produção. Só Gustavo.

---

## Pré-requisitos (ordem)

1. **DATABASE_URL Evolution** — `docs/EVOLUTION_DATABASE_URL_QR_CHECKLIST_G7.md` (G7.04.T1)  
2. **Radar evolution** deixa de ser `offline`  
3. **QR open** — manager state `open` / `connected` (G7.04.T2)  
4. Webhook Evolution → API configurado  
5. (Opcional) N8N WF `01-consulta-emolumento` / pipeline chat ativo

```bash
# 0) Saúde
curl -sS https://api.2notasudi.com.br/api/v1/health/radar | jq .services.evolution
curl -sS -o /dev/null -w 'whatsapp:%{http_code}\n' https://whatsapp.2notasudi.com.br/
# meta evolution online + whatsapp 200/302 (não 502)
```

---

## A) Subir Evolution + QR (se ainda 502)

```bash
# EasyPanel → evolution-api → env DATABASE_URL = DNS Swarm + creds atuais Postgres
# Se host-mode port stuck: scale 0 → 1 (nunca 1→1 direto)
```

1. Abrir `https://whatsapp.2notasudi.com.br/manager`  
2. Instância **`cartorio-2notas`**  
3. Connect → escanear QR no WhatsApp Business do cartório  
4. Confirmar state:

```bash
# EVOLUTION_API_KEY só no shell (nunca commit)
export EVOLUTION_BASE="https://whatsapp.2notasudi.com.br"
curl -sS -H "apikey: $EVOLUTION_API_KEY" \
  "$EVOLUTION_BASE/instance/connectionState/cartorio-2notas" | jq .
# esperado: state open | connected
```

Helper N8N: `infra/n8n-workflows/33-whatsapp-qr-scan-helper.json`  
Detalhe: `docs/EVOLUTION_DATABASE_URL_QR_CHECKLIST_G7.md`

---

## B) Webhook Evolution → API

```bash
curl -sS -X POST "$EVOLUTION_BASE/webhook/set/cartorio-2notas" \
  -H "apikey: $EVOLUTION_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://api.2notasudi.com.br/api/v1/webhook/evolution",
    "events": ["MESSAGES_UPSERT", "MESSAGES_UPDATE", "CONNECTION_UPDATE"],
    "enabled": true
  }' | jq .
```

Parse aceita **root** e **nested** `data.message` (prod manda ambos).  
Guia: `docs/WHATSAPP_GUIDE.md`

---

## C) Smoke emolumento **sem** WhatsApp (API)

Valida tabela antes do canal:

```bash
# Público ou com key conforme env prod
curl -sS "https://api.2notasudi.com.br/api/v1/emolumento/calcular?tipo=procuracao&folhas=1&urgencia=false" | jq .
# esperado: total ~ 156.40

# Alternate path (v8-style)
curl -sS "https://api.2notasudi.com.br/api/v1/emolumentos/calcular-api?tipo=procuracao&folhas=1&urgencia=false" | jq .
```

HITL: **não** aplicar isenção/urgência sozinho no bot — só reportar valor base e escalar se cliente pedir isenção.

---

## D) Path sintético (agent / CI — já verde)

```bash
cd backend && uv run pytest -q --no-cov \
  tests/test_g7_wave22_integration.py::test_wa_emolumento_synthetic_flow \
  tests/test_g7_wave22_integration.py::test_wa_emolumento_certidao_casamento
```

Fluxo coberto:

```
Evolution payload (nested messages.upsert)
  → parse_evolution_payload  ("quanto custa procuracao")
  → emolumento.calcular("procuracao")  → Decimal("156.40")
```

---

## E) Path live — 1 msg real (SUI Gustavo)

| Passo | Ação | Esperado |
|-------|------|----------|
| 1 | Celular no WA do cartório (número da instância) | chat aberto |
| 2 | Enviar: `quanto custa procuraçao` (ou `procuração`) | entrega ✓ |
| 3 | Aguardar ≤ 15s | typing + resposta PT-BR |
| 4 | Resposta cita valor **procuração** ≈ **R$ 156,40** (tabela 2026) | sem inventar valor |
| 5 | **Não** ecoar CPF raw se o usuário mandar | PII mask |
| 6 | Se pedir isenção/urgência | handoff HITL / escrevente, não auto-decide |

### Alternativa: sendText Evolution (mesmo número de teste)

```bash
# Só após state=open. Número E.164 sem + (ex.: 5534…)
curl -sS -X POST "$EVOLUTION_BASE/message/sendText/cartorio-2notas" \
  -H "apikey: $EVOLUTION_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "number": "5534XXXXXXXXX",
    "text": "quanto custa procuracao"
  }' | jq .
```

Resposta do bot volta no mesmo JID via pipeline (webhook → API → LLM/tools → sendText).

### Prova de live (anexar no PR / checklist)

- [ ] Screenshot ou log de mensagem inbound + outbound  
- [ ] `jq` do radar: `evolution=online`  
- [ ] Trecho de log API **sem** PII raw (MaskingFilter)  
- [ ] Valor coerente com `EMOLUMENTOS_2026["procuracao"]`

---

## F) Troubleshooting rápido

| Sintoma | Ação |
|---------|------|
| whatsapp 502 | DATABASE_URL + scale 0→1 (Lesson 176) |
| state close | re-QR manager |
| webhook 401/HMAC | `EVOLUTION_WEBHOOK_SECRET` (+ PREV na rotação) |
| parse vazio | dual format root vs `data` — ver G7.04.T3 |
| resposta “inventada” sem 156,40 | forçar tool `consultar_emolumento` / WF 01; nunca hardcode no prompt |
| Telegram ok, WA não | canal Evolution separado; conferir webhook path |

---

## Definition of Done

| Item | Owner | Done |
|------|-------|------|
| Synthetic pytest green | agent | [x] Wave22 |
| One-pager live steps | agent | [x] Wave28 |
| Evolution online + QR open | Gustavo | [~] |
| 1 msg real → 156,40 | Gustavo | [~] → só então `[x]` G7.04.T4 |

---

## Cross-refs

- `docs/EVOLUTION_DATABASE_URL_QR_CHECKLIST_G7.md`  
- `docs/WHATSAPP_GUIDE.md` · `docs/CANAL_HEALTH_MATRIX.md`  
- `backend/tests/test_g7_wave22_integration.py`  
- `infra/n8n-workflows/01-consulta-emolumento.json` · `38-emolumento-calculator.json`  
- Lesson 176 (502 env) · Lesson 194 (Wave22 synth)

**Modified by Gustavo Almeida — G7 Wave28 SUI pack refreshed**
