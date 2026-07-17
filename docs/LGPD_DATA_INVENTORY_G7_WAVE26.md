# LGPD Data Inventory — Quarterly Refresh (G7.19.T4 / Wave 26)

> **Data refresh:** 2026-07-17  
> **Anterior:** `docs/LGPD_DATA_INVENTORY_2026-07-16.md` (G6 wave 11, 18 campos PII)  
> **Scanner:** `python3 scripts/lgpd_data_inventory.py`  
> **Owner:** cartorio-lgpd + cartorio-dev  
> **Compliance:** LGPD art. 37 (registro) + art. 18 IV (portabilidade) + art. 46 (segurança)

## 1. Delta vs 2026-07-16

| Métrica | 2026-07-16 | 2026-07-17 (Wave 26) | Δ |
|---------|------------|----------------------|---|
| Total fields PII (scanner) | 18 | **25** | +7 |
| Models hits | 11 | **13** | +2 |
| Schemas hits | 7 | **12** | +5 |
| Funções proteção (`scrub`, `hash_pii`) | 2 | 2 | 0 |

### Novos hits (não estavam no inventário 07-16)

| Origem | Field | Categoria | Motivo |
|--------|-------|-----------|--------|
| `models/lgpd_consent.py` | `ip_hash` | criptografado_hash | Model G6.C.T9 consent log |
| `models/lgpd_consent.py` | `user_agent` | navegacao | Consent trail |
| `schemas/lgpd_dsar.py` | `cpf` | identificacao_direta | DSAR input (titular) |
| `schemas/lgpd_dsar.py` | `email` | contato | DSAR input |
| `schemas/lgpd_dsar.py` | `cpf_hash` | criptografado_hash | DSAR processado |
| `schemas/lgpd_dsar.py` | `email_hash` | criptografado_hash | DSAR processado |
| `schemas/lgpd_dsar.py` | `phone_hash` | criptografado_hash | DSAR processado |

### Models SQLAlchemy no tree (inventário de entidades)

| Model file | Tabela / papel | Contém PII? |
|------------|----------------|-------------|
| `agendamento.py` | agendamentos | sim (`cpf_hash`) |
| `atendimento.py` | atendimentos multi-canal | scrubbed only (`contexto_scrubbed`) |
| `audit_log.py` | audit append-only | sim (ip, ua, hashes chain) |
| `cliente.py` | titulares | sim (nome, email, hashes, consent IP) |
| `conversa.py` | mensagens | hash + scrubbed |
| `cpf_cnpj_validator.py` | util (sem table) | — |
| `documento.py` | docs protocolo | integrity hash (não PII titular) |
| `lgpd_consent.py` | **novo** consent log | sim (ip_hash, ua) |
| `mixins.py` | SoftDelete / Named | `nome` genérico |
| `outbox_message.py` | DLQ | payload JSON (pode carregar PII transitório) |
| `protocolo.py` | protocolos HITL DRAFT | valor/financeiro; FK cliente |
| `webhook_event.py` | webhooks | `payload_hash` |
| `base.py` | declarative base | — |

**Nota scanner:** o script casa **nomes de campo** com regex PII. Campos como
`whatsapp_number`, `telegram_chat_id`, `consentimento_ip`, `ip_truncated`,
`pesquisa_comentario`, `payload` (JSON) **não entram** no total automático se o
nome não casar — ver §4 (gaps manuais).

---

## 2. Resumo por categoria (scanner 2026-07-17)

| Categoria | Total | Base legal | Retenção |
|-----------|------:|------------|----------|
| contato | 2 | art. 7 V (execução do serviço) | 5 anos |
| criptografado_hash | 13 | art. 46 (medidas de segurança) | mesma do dado original |
| identificacao_direta | 3 | art. 7 II (obrigação legal cartorária) | 5 anos (Provimento 74/2018) |
| navegacao | 7 | art. 7 IX (interesse legítimo, segurança) | 6 meses |

---

## 3. Inventory detalhado (auto-gerado)

### 3.1 Models SQLAlchemy (13)

| File | Line | Field | Categoria | Base legal |
|------|-----:|-------|-----------|------------|
| `models/agendamento.py` | 97 | `cpf_hash` | criptografado_hash | art. 46 |
| `models/audit_log.py` | 35 | `ip` | navegacao | art. 7 IX |
| `models/audit_log.py` | 42 | `user_agent` | navegacao | art. 7 IX |
| `models/audit_log.py` | 48 | `prev_hash` | criptografado_hash | art. 46 |
| `models/cliente.py` | 38 | `cpf_hash` | criptografado_hash | art. 46 |
| `models/cliente.py` | 39 | `nome` | identificacao_direta | art. 7 II |
| `models/cliente.py` | 40 | `email` | contato | art. 7 V |
| `models/cliente.py` | 41 | `telefone_hash` | criptografado_hash | art. 46 |
| `models/conversa.py` | 24 | `raw_message_hash` | criptografado_hash | art. 46 |
| `models/lgpd_consent.py` | 25 | `ip_hash` | criptografado_hash | art. 46 |
| `models/lgpd_consent.py` | 26 | `user_agent` | navegacao | art. 7 IX |
| `models/mixins.py` | 20 | `nome` | identificacao_direta | art. 7 II |
| `models/webhook_event.py` | 34 | `payload_hash` | criptografado_hash | art. 46 |

### 3.2 Schemas Pydantic (12)

| File | Line | Field | Categoria | Base legal |
|------|-----:|-------|-----------|------------|
| `schemas/agendamento.py` | 79 | `cpf_hash` | criptografado_hash | art. 46 |
| `schemas/audit.py` | 94 | `ip` | navegacao | art. 7 IX |
| `schemas/audit.py` | 103 | `user_agent` | navegacao | art. 7 IX |
| `schemas/audit.py` | 154 | `prev_hash` | criptografado_hash | art. 46 |
| `schemas/audit.py` | 188 | `ip` | navegacao | art. 7 IX |
| `schemas/audit.py` | 204 | `user_agent` | navegacao | art. 7 IX |
| `schemas/audit.py` | 211 | `prev_hash` | criptografado_hash | art. 46 |
| `schemas/lgpd_dsar.py` | 26 | `cpf` | identificacao_direta | art. 7 II |
| `schemas/lgpd_dsar.py` | 27 | `email` | contato | art. 7 V |
| `schemas/lgpd_dsar.py` | 39 | `cpf_hash` | criptografado_hash | art. 46 |
| `schemas/lgpd_dsar.py` | 40 | `email_hash` | criptografado_hash | art. 46 |
| `schemas/lgpd_dsar.py` | 41 | `phone_hash` | criptografado_hash | art. 46 |

### 3.3 Funções de proteção (2)

| File | Line | Função |
|------|-----:|--------|
| `services/pii.py` | 158 | `scrub` |
| `services/pii.py` | 210 | `hash_pii` |

Camadas adicionais (fora do scanner de fields):

1. Pydantic field validators  
2. Sentry `before_send` scrubber (`services/sentry.py`)  
3. Log `MaskingFilter` (`services/log_masker.py`)

---

## 4. Gaps manuais (revisão lgpd — não no regex)

Campos/estruturas com risco PII **não contados** pelo scanner por nome:

| Local | Campo / nota | Ação recomendada |
|-------|--------------|------------------|
| `cliente.whatsapp_number` | identificador de canal | tratar como contato; mascarar em logs |
| `cliente.telegram_chat_id` | identificador | idem |
| `cliente.consentimento_ip` | IP de consentimento | retencão 6m / hash se possível |
| `audit_log.ip_truncated` | já mitigado (D5) | manter testes t024/t025 |
| `audit_log.payload` | JSON livre | scrub pre-insert |
| `outbox_message.payload` | DLQ pode reter PII | TTL + scrub on DLQ |
| `conversa.raw_message_scrubbed` | texto scrubbed | validar regressão `pii*` |
| `atendimento.contexto_scrubbed` | texto | idem |
| `atendimento.pesquisa_comentario` | free text | pode conter PII; scrub se export |
| `protocolo.numero` | identificador de ato | DATASENSITIVE em eco ao user |
| OpenClaw / LobeChat transcripts | fora do PG | PII pre-LLM obrigatório; ver skills `pii_safe` |

---

## 5. Bases de tratamento (resumo operacional)

| Finalidade | Base legal | Sistemas |
|------------|------------|----------|
| Ato notarial / protocolo | art. 7 II + Provimento 74/2018 | PG `protocolo`, `documento`, `cliente` |
| Atendimento bot multi-canal | art. 7 V | `conversa`, `atendimento`, Evolution/Telegram |
| Segurança / audit chain | art. 7 IX + art. 46 | `audit_log` (HMAC + SHA256) |
| Consentimento | art. 7 I / art. 8 | `lgpd_consent_log`, flags em `cliente` |
| DSAR (acesso/eliminação/etc.) | art. 18 | `schemas/lgpd_dsar`, services `lgpd_*` |
| Emolumento / financeiro | art. 7 V + CN/CGJ-MG | `protocolo.valor_*` |

HITL: protocolo nasce `DRAFT` — bot não emite certidão/escritura sozinho.

---

## 6. Como regenerar

```bash
# Da raiz do repo
python3 scripts/lgpd_data_inventory.py
python3 scripts/lgpd_data_inventory.py --report docs/LGPD_DATA_INVENTORY_2026-07-16.md
python3 scripts/lgpd_data_inventory.py --json | head

# Gate local
make -C backend test-one TEST=tests/test_pii.py  # se existir suite pii
```

**Cadência:** trimestral (G7.19.T4) ou quando:

- novo model em `backend/app/models/`
- novo schema DSAR / LGPD
- mudança em `services/pii.py`

---

## 7. Próximos passos (lgpd, não escopo A3 code)

1. Estender scanner com patterns: `whatsapp_number`, `telegram_chat_id`, `consentimento_ip`, `ip_truncated`.  
2. Cross-check RIPD / Privacy Policy v3 (`G7.19.T3`).  
3. Confirmar retenção job diário 03:00 BRT cobre `lgpd_consent_log`.  
4. Review `cartorio-lgpd` se alterar `audit*` / `pii*`.

---

## 8. Refs

- Inventário base: `docs/LGPD_DATA_INVENTORY_2026-07-16.md`
- Scanner: `scripts/lgpd_data_inventory.py`
- ANPD pack: `docs/ANPD_READY_2026-07-16.md`
- Models: `backend/app/models/`
- PII service: `backend/app/services/pii.py`
- Skills OpenClaw pii flags: `docs/OPENCLAW_SKILLS_REGISTRY_G7.md`

---

**Task:** G7.19.T4 · **Status:** DONE (refresh note Wave 26)  
**Modified by Gustavo Almeida + cartorio-lgpd — Wave 26 A3**
