# LGPD Data Inventory

**Data**: 2026-07-17T11:57:10.383164+00:00
**Total fields PII**: 25
**Funcoes protecao**: 2

## Resumo por categoria

| Categoria | Total | Base legal | Retencao |
|---|---|---|---|
| contato | 2 | art. 7 V (execucao do servico) | 5 anos |
| criptografado_hash | 13 | art. 46 (medidas de seguranca) | mesma do dado original |
| identificacao_direta | 3 | art. 7 II (obrigacao legal cartoraria) | 5 anos (Provimento 74/2018) |
| navegacao | 7 | art. 7 IX (interesse legitimo, seguranca) | 6 meses |

## Models SQLAlchemy (13)

| File | Line | Field | Categoria | Base legal |
|---|---|---|---|---|
| `models/agendamento.py` | 97 | `cpf_hash` | criptografado_hash | art. 46 (medidas de seguranca) |
| `models/audit_log.py` | 35 | `ip` | navegacao | art. 7 IX (interesse legitimo, seguranca) |
| `models/audit_log.py` | 42 | `user_agent` | navegacao | art. 7 IX (interesse legitimo, seguranca) |
| `models/audit_log.py` | 48 | `prev_hash` | criptografado_hash | art. 46 (medidas de seguranca) |
| `models/cliente.py` | 38 | `cpf_hash` | criptografado_hash | art. 46 (medidas de seguranca) |
| `models/cliente.py` | 39 | `nome` | identificacao_direta | art. 7 II (obrigacao legal cartoraria) |
| `models/cliente.py` | 40 | `email` | contato | art. 7 V (execucao do servico) |
| `models/cliente.py` | 41 | `telefone_hash` | criptografado_hash | art. 46 (medidas de seguranca) |
| `models/conversa.py` | 24 | `raw_message_hash` | criptografado_hash | art. 46 (medidas de seguranca) |
| `models/lgpd_consent.py` | 25 | `ip_hash` | criptografado_hash | art. 46 (medidas de seguranca) |
| `models/lgpd_consent.py` | 26 | `user_agent` | navegacao | art. 7 IX (interesse legitimo, seguranca) |
| `models/mixins.py` | 20 | `nome` | identificacao_direta | art. 7 II (obrigacao legal cartoraria) |
| `models/webhook_event.py` | 34 | `payload_hash` | criptografado_hash | art. 46 (medidas de seguranca) |

## Schemas Pydantic (12)

| File | Line | Field | Categoria | Base legal |
|---|---|---|---|---|
| `schemas/agendamento.py` | 79 | `cpf_hash` | criptografado_hash | art. 46 (medidas de seguranca) |
| `schemas/audit.py` | 94 | `ip` | navegacao | art. 7 IX (interesse legitimo, seguranca) |
| `schemas/audit.py` | 103 | `user_agent` | navegacao | art. 7 IX (interesse legitimo, seguranca) |
| `schemas/audit.py` | 154 | `prev_hash` | criptografado_hash | art. 46 (medidas de seguranca) |
| `schemas/audit.py` | 188 | `ip` | navegacao | art. 7 IX (interesse legitimo, seguranca) |
| `schemas/audit.py` | 204 | `user_agent` | navegacao | art. 7 IX (interesse legitimo, seguranca) |
| `schemas/audit.py` | 211 | `prev_hash` | criptografado_hash | art. 46 (medidas de seguranca) |
| `schemas/lgpd_dsar.py` | 26 | `cpf` | identificacao_direta | art. 7 II (obrigacao legal cartoraria) |
| `schemas/lgpd_dsar.py` | 27 | `email` | contato | art. 7 V (execucao do servico) |
| `schemas/lgpd_dsar.py` | 39 | `cpf_hash` | criptografado_hash | art. 46 (medidas de seguranca) |
| `schemas/lgpd_dsar.py` | 40 | `email_hash` | criptografado_hash | art. 46 (medidas de seguranca) |
| `schemas/lgpd_dsar.py` | 41 | `phone_hash` | criptografado_hash | art. 46 (medidas de seguranca) |

## Funcoes de Protecao (2)

| File | Line | Funcao |
|---|---|---|
| `services/pii.py` | 158 | `scrub` |
| `services/pii.py` | 210 | `hash_pii` |

---

**Compliance**: LGPD art. 37 (registro das operacoes) + art. 18 IV (portabilidade).

**Modified by Gustavo Almeida + cartorio-lgpd — G6 wave 11 (auto-gerado)**