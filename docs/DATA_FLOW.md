# Fluxo de Dados - PII (LGPD)

> **Documento canonico do fluxo de dados sensiveis.**
> Versao 1.0 (2026-06-24)
> Audiencia: devs, DPO, auditores externos, ANPD

## Visao geral

```
Cliente (WhatsApp/Telegram/Web)
  |
  v
[1] Evolution API / Telegram Bot
  |
  | webhook POST com payload bruto
  v
[2] API Backend - /api/v1/webhook/evolution
  |
  v
[3] PII Scrubber - Camada 1 (input)
  | - regex CNS/CNH/CPF/telefone/email (com check-digit CNS/CNH)
  | - SUBSTITUI por placeholders: [CPF_REDACTED] etc
  v
[4] ConversaService - processa intencao
  |
  v
[5] PII Scrubber - Camada 2 (pre-LLM)
  | - defense-in-depth: scrub novamente antes de chamar LLM
  v
[6] Opencode-Go / OpenClaw (LLM provider)
  | - recebe APENAS dados scrubbed
  | - NUNCA ve CPF/CNS/CNH/telefone real
  v
[7] Resposta do LLM
  |
  v
[8] PII Scrubber - Camada 3 (output)
  | - checa resposta antes de mandar pro cliente
  | - se PII vazou, BLOQUEIA mensagem
  v
[9] Audit Log (LGPD art. 37)
  | - registra: tipo_pii, request_metadata, response_size
  | - hash chain + HMAC (tamper-evident)
  v
[10] Envio via Evolution API
  |
  v
Cliente (resposta)
```

## Camadas de PII Scrubbing (3 camadas, defesa em profundidade)

| Camada | Quando | O que faz | LGPD |
|---|---|---|---|
| **1. Input** | Imediatamente apos webhook | Regex detecta e mascara CPF/CNS/CNH/tel/email antes de qualquer processamento | art. 6 VIII (prevencao) |
| **2. Pre-LLM** | Antes de chamar Opencode-Go/OpenClaw | Re-scrub (defesa em profundidade, em caso de bypass da camada 1) | art. 46 (seguranca) |
| **3. Output** | Antes de enviar resposta pro cliente | Verifica que resposta NAO contem PII (P0.7 do mega-plano) | art. 6 VIII |

## O que NAO eh coberto por regex (LGPD art. 11 - dado sensivel)

| Tipo | Risco | Mitigacao |
|---|---|---|
| Nome completo | Regex nao detecta semantica | HITL obrigatorio em qualquer acao juridica |
| Endereco | Texto livre | HITL + validacao humana |
| Naturalidade | Texto livre | HITL |
| Data de nascimento | Datas DD/MM/YYYY SAO redacted (com trade-off de falso positivo) | Falsos positivos aceitos, falsos negativos NAO |
| CNS/CNH com typo | DV invalido NAO passa pelo scrubber | P0.5+P0.6 check-digit (commit d8d2d84) |

## Armazenamento de PII

### Banco de dados (PostgreSQL/Supabase)

- **CPF/telefone**: APENAS hash SHA-256 com salt por cliente (`cpf_hash`, `telefone_hash`)
- **Nome/email**: armazenados em texto puro (necessario para operacao)
- **CNS/CNH**: NAO armazenados, apenas validados
- **Audit log**: metadata (tipo_pii, quantidade) mas NAO valores

### Redis (cache)

- TTL: 86400s (24h)
- Chaves: `ratelimit:apikey:<hash>`, `ratelimit:ip:<hash>`, session IDs
- **NAO armazena PII** - apenas identificadores anonimos (hash)

### Logs de aplicacao

- Formato: JSON estruturado (P2.BE.6 - futuro)
- PII: NUNCA em log (sempre scrubbed)
- Audit log: separado, append-only, hash chain + HMAC

## Direitos do titular (LGPD art. 18)

| Direito | Endpoint | LGPD |
|---|---|---|
| Acesso (todos os dados) | `GET /api/v1/cliente/{id}/historico` | art. 18 IV |
| Correcao | `PATCH /api/v1/cliente/{id}` | art. 18 III |
| Eliminacao (esquecimento) | `POST /api/v1/lgpd/direito-esquecimento` | art. 18 VI |
| Portabilidade | (futuro P2.LG.6) | art. 18 V |
| Revogacao de consentimento | `POST /api/v1/cliente/{id}/revogar-consent` | art. 18 IX |
| Oposicao | (futuro) | art. 18 II |

## Fluxo de "direito ao esquecimento" (LGPD art. 18 VI)

```
Cliente solicita esquecimento
  |
  v
[1] Validar identidade (canal autenticado, 2FA se necessario)
  |
  v
[2] DPO confirma (HITL - nao pode ser automatico)
  |
  v
[3] POST /api/v1/lgpd/direito-esquecimento
  | - motivo, confirmacao_dupla, cliente_id
  v
[4] Soft delete (motivo_encerramento, data_encerramento)
  | - dados NAO sao apagados imediatamente
  | - apenas marcados como inativos
  v
[5] Audit log (LGPD art. 37)
  | - registra: cliente_id, motivo, data, quem_solicitou
  | - hash chain + HMAC (tamper-evident)
  v
[6] Aguardar 30 dias (recurso + verificacao legal)
  |
  v
[7] Job de retencao apaga fisicamente
  | - DELETE WHERE motivo_encerramento IS NOT NULL AND data_encerramento < NOW() - INTERVAL '30 days'
  | - AUDIT log preserva registro de que foi apagado (sem o dado)
  v
[8] Confirmar ao cliente (< 15 dias, prazo LGPD)
```

## PII no LLM (provider externo)

```
ANTES (v0.1, inseguro):
  Cliente -> "Meu CPF e 123.456.789-09, ..." -> LLM publico (OpenAI)
  RISCO: dado sensivel foi pra LLM publica, sem contrato DPA

DEPOIS (v0.5+, atual):
  Cliente -> "Meu CPF e [CPF_REDACTED], ..." -> Opencode-Go (DPA assinado)
  RISCO: zero. LLM nunca ve CPF real.

PROVEDORES COM DPA ASSINADO (2026-06-24):
  - Opencode-Go (DeepSeek-v4 flash): sim
  - OpenClaw gateway (Anthropic/OpenAI fallback): em andamento (P1.LG.1)
  - MiniMax (M2.7/M3): em andamento (P1.LG.2)
  - Evolution (WhatsApp): sim
  - Supabase (Postgres + Storage): sim
```

## Pontos de auditoria

| Onde | O que auditar | Quando |
|---|---|---|
| Audit log | Integridade do hash chain | Diario (N8N workflow #08, 03:30 BRT) |
| PII scrubber | Falsos positivos/negativos | Por PR (testes em test_pii.py) |
| Rate limit | Acessos por IP/key | Continuo (Grafana) |
| Direito ao esquecimento | Pedidos processados | Por solicitacao |
| DPA | Vencimento de contratos | Trimestral (P2.LG.10) |

## Referencias

- LGPD: Lei 13.709/2018 (Brasil)
- RIPD: `docs/ripd.md`
- CNS check-digit: `backend/app/services/pii.py::validate_cns`
- CNH check-digit: `backend/app/services/pii.py::validate_cnh`
- Direito ao esquecimento: `backend/app/services/lgpd/direito_esquecimento.py`
- PII scrubbing 3 camadas: `backend/app/services/pii.py` + `backend/app/integrations/opencode_go.py`

Modified by ZCode/Mavis - 2026-06-24
