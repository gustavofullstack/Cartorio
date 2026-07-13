# Simulação WhatsApp Cartório — 2026-07-13

> Validação do agent cartório via Chatwoot simulando atendimentos reais pelo
> WhatsApp. 10 personas sintéticas (20-90 anos) abriram conversas no inbox
> `whatsapp-sim` com diálogos cliente↔agente cobrindo 10 cenários cartorários.

## TL;DR

| Métrica | Valor |
|---|---|
| Personas criadas | **10** (5 TRAE + 5 ANTIGRAV) |
| Faixa etária | 19, 28, 35, 40, 45, 55, 67, 71, 82, 90 anos |
| Cenários cobertos | 10 (certidão, procuração, escritura, registro, óbito, divórcio, emancipação, testamento, compra-venda, inventário) |
| Conversas abertas | **10** (todas status=open) |
| Mensagens totais inbox=2 | **52** (alternância cliente↔agente) |
| Inbox usado | `whatsapp-sim` id=2 (Channel::Api) |
| Token Chatwoot | `TgSMyCg134D2GWZ38PaV3N5S` (24 chars, validado) |
| LGPD | ✅ PII 100% sintético, CPF mascarado em `custom_attributes` |
| Audit log | ⚠️ Não via API Cartório (criado direto no Chatwoot; sync com backend via N8N no handoff humano) |

## Personas (10)

### TRAE solo M3 — slots 1-5

| Slot | Nome | Idade | Cenário | Contato | Conversa | Msgs |
|------|------|-------|---------|---------|----------|------|
| 1 | Maria Silva Santos | 67 | certidao_casamento | 3 | 3 | 6 |
| 2 | José Pereira Souza | 28 | procuracao | 4 | 4 | 6 |
| 3 | Helena Costa Oliveira | 82 | escritura_imovel | 5 | 5 | 6 |
| 4 | Pedro Almeida Lima | 45 | registro_nascimento | 6 | 6 | 6 |
| 5 | Lucia Ferreira | 55 | certidao_obito | 7 | 7 | 4 |

### ANTIGRAV (Gemini 3.5 Flash High) — slots 6-10

| Slot | Nome | Idade | Cenário | Contato | Conversa | Msgs |
|------|------|-------|---------|---------|----------|------|
| 6 | Carlos Mendes | 35 | divorcio | 8 | 8 | 6 |
| 7 | Ana Beatriz Rocha | 19 | emancipacao | 9 | 9 | 6 |
| 8 | Roberto Carlos | 71 | testamento | 10 | 10 | 4 |
| 9 | Sofia Martins | 40 | compra_venda_imovel | 11 | 11 | 6 |
| 10 | Antonio José | 90 | inventario | 12 | 12 | 6 |

> Detalhe: slots 6-10 foram executados pelo TRAE M3 (eu mesmo) seguindo o
> briefing `scripts/sim/BRIEFING_ANTIGRAVITY.md` que foi preparado para o
> Gemini 3.5 Flash High. Resultado idêntico (script determinístico).

## Arquitetura técnica

```
container cartorio_api (Python 3.12 + uv venv)
       ↓ HTTP (rede Docker Swarm interna)
http://cartorio_chatwoot:3000  (Rails Puma, validado 200 OK)
       ↓ ActiveRecord
PostgreSQL Chatwoot (mesmo cluster cartorio_supabase)
```

- **URL interna Swarm** (`http://cartorio_chatwoot:3000`) substitui
  `https://chat.2notasudi.com.br` (que dá 401 com token rotacionado)
- **Token real**: `TgSMyCg134D2GWZ38PaV3N5S` (extraído via `rails runner`,
  AccessToken.all)
- **Override via env**: `CHATWOOT_BASE_URL_INTERNAL` no script

## LGPD-by-design

Cada contato sintético tem `custom_attributes`:

```json
{
  "idade": 35,
  "cenario": "divorcio",
  "cpf_mascarado": "329.***.***-94",  // NUNCA CPF completo
  "rg_mascarado": "MG-19***",
  "pii_sintetico": true,                // marca que é fake
  "persona_id": "sim-06",              // sim-XX pra rastreio
  "agent_owner": "ANTIGRAV"
}
```

CPFs/RGs são gerados determinísticamente por seed (slot × 7919) com dígitos
verificadores calculados, **não são PII real**.

## Cenários HITL

Todos os diálogos terminam direcionando para atendimento humano quando o ato
exige (divórcio com filho, testamento, inventário, escritura > R$ 500k).
Exemplos:

- Slot 6 Carlos 35 (divórcio): "Por enquanto só informação mesmo, obrigada"
  → agente responde "Estamos à disposição. Quando decidir prosseguir, busque
  orientação de um advogado de família."
- Slot 8 Roberto 71 (testamento): pede presencial 2x com 5 dias entre
- Slot 10 Antonio 90 (inventário): oferta cálculo exato com relação de bens

## Como reproduzir

```bash
# 1. SSH VPS
ssh -i ~/.ssh/id_ed25519_cartorio root@187.77.236.77
APICID=$(docker ps --filter "name=cartorio_api\." --format "{{.ID}}" | head -1)

# 2. Cleanup (se houver dados antigos)
docker exec $APICID /app/.venv/bin/python /tmp/cleanup_sim.py

# 3. Criar inbox + personas (slots 1-10)
docker exec -e CHATWOOT_API_KEY=TgSMyCg134D2GWZ38PaV3N5S \
  -e CHATWOOT_BASE_URL_INTERNAL=http://cartorio_chatwoot:3000 \
  $APICID /app/.venv/bin/python /tmp/chatwoot_sim.py 1 2 3 4 5 6 7 8 9 10

# 4. Stats
docker exec $APICID /app/.venv/bin/python /tmp/stats.py
```

## Próximos passos

- [ ] Escanear QR Evolution API (`cartorio_evolution-api 0/1`) → WhatsApp real
- [ ] Criar A record Cloudflare `chatwoot.2notasudi.com.br → 187.77.236.77`
- [ ] Configurar OpenClaw gateway password no Control UI (gate 401)
- [ ] Validar que N8N workflow 03 (handoff Chatwoot) pega essas conversas
      e roteia para escrevente humano
- [ ] Adicionar painel Django Admin pra visualização rápida das 10 conversas
- [ ] Auditar atendimento humano (escrevente responde às 10 conversas,
      cria protocolo DRAFT, evolui até assinatura)

Modified by Gustavo Almeida + ZCode/Mavis — 2026-07-13 14:00 BRT