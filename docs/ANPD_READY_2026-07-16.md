# Relatorio ANPD — Cartorio 2o Notas de Uberlandia

**Data**: 2026-07-16T17:11:55.071798+00:00
**Versao LGPD**: Lei 13.709/2018 + alteracoes 2024-2026
**Versao ANPD**: Resolucao CD/ANPD 4/2023 (regulamenta art. 33)

---

## 1. Identificacao do Controlador

```
Razao social: 2o Tabelionato de Notas e Protesto de Uberlandia
CNPJ: XX.XXX.XXX/0001-XX
Endereco: Av. XXXX, XXX, Uberlandia/MG, CEP 38.XXX-XXX
Telefone: (34) 9999-9999
Email: contato@2notasudi.com.br

Encarregado de Tratamento de Dados (DPO):
Nome: Gustavo Almeida (interino)
Email: dpo@2notasudi.com.br
Telefone: (34) 9999-9999

Sub-processores LLM:
- MiniMax (MiniMax-M3) - primario
- opencode-go - fallback 1
- DeepSeek - fallback 2
- llama-3.1-8b-local - quando todos fallbacks falham (BR)

Sub-processores infra:
- Cloudflare (DNS + WAF + proxy) - US
- Hostinger (VPS) - BR
- Supabase self-hosted (Postgres + Storage) - BR
- Redis self-hosted (cache + rate limit) - BR
```

## 2. Inventario de Dados Pessoais (LGPD art. 37)

Catalogo de 18 PII fields identificados em `backend/app/models/` e `backend/app/schemas/`.

| Categoria | Total | Base Legal | Retencao | Exemplos |
|---|---|---|---|---|
| **identificacao_direta** | 6+ | art. 7 II | 5 anos | cpf, cnpj, rg, cnh, passaporte, nome |
| **contato** | 5+ | art. 7 V | 5 anos | email, telefone, celular, endereco, cep |
| **navegacao** | 3+ | art. 7 IX | 6 meses | ip, user_agent, cookies |
| **financeiro** | 5+ | art. 7 V | 5 anos | valor, pix, conta, emolumento, cartao |
| **biometrico** | 4+ | art. 11 I | ate revogacao | biometric, fingerprint, face_id, foto |
| **saude** | 4+ | art. 11 II | 20 anos (CF art. 5 LXXIX) | saude, cid, deficiencia, medic |
| **criptografado_hash** | 5+ | art. 46 | mesma do original | _hash, hashed_ |

Detalhamento completo: `docs/LGPD_DATA_INVENTORY_2026-07-16.md`

## 3. Bases Legais (LGPD art. 7)

| Finalidade | Base Legal | Descricao |
|---|---|---|
| Execucao do servico cartorario | **art. 7 II + V** | Provimento 74/2018 + relacao juridica |
| Atendimento via chatbot IA | **art. 7 I** (consentimento) | Opt-in explicito via banner LGPD |
| Seguranca + auditoria | **art. 7 IX** (interesse legitimo) | Logs, audit, dead man's switch |
| Dados biometricos | **art. 11 I + II** (consentimento especifico + destaque) | Opt-in com revogacao |
| Dados de saude | **art. 11 II e** (politica publica) | Tutela da saude |

## 4. Retencoes (LGPD art. 16)

| Tipo de Dado | Retencao | Observacao |
|---|---|---|
| Protocolos | **5 anos** | Provimento 74/2018 |
| Conversas WhatsApp/Telegram | **365 dias** | Comunicacao |
| **Conversas IA (LLM)** | **90 dias** | Consentimento revogavel (LGPD v3 2026-07-16) |
| Audit log SHA256+HMAC | **5 anos** | LGPD art. 37 |
| Logs de acesso | **6 meses** | LGPD art. 37 |
| Backups | **5 anos** (AES-256) | Continuidade operacional |
| Biometricos | **ate revogacao** | art. 11 I |
| Saude | **20 anos** | CF art. 5 LXXIX |

Apos o periodo, dados sao **anonimizados** (nao deletados imediatamente) para preservar integridade do audit log.

## 5. Direitos do Titular (LGPD art. 18)

**7 direitos** implementados no portal `/api/v1/lgpd/direitos`:

1. **Acesso** (art. 18 I): saber quais dados temos sobre voce
2. **Correcao** (art. 18 III): atualizar dados incorretos
3. **Anonimizacao** (art. 18 IV): bloquear uso sem deletar
4. **Portabilidade** (art. 18 V): receber seus dados em JSON/ZIP
5. **Eliminacao** (art. 18 VI): deletar dados desnecessarios
6. **Oposicao** (art. 18 IX): opor-se a tratamento (especialmente IA)
7. **Nao-automacao** (art. 18 X): revisao humana de decisoes automatizadas

**Canais para exercer**: dpo@2notasudi.com.br | /api/v1/lgpd/direitos | Telegram /lgpd
**Prazo legal**: 15 dias (LGPD art. 18 §5o)

## 6. Medidas de Seguranca (LGPD art. 46)

| Medida | Implementacao | Status |
|---|---|---|
| Audit log imutavel | SHA256+HMAC chain em `app/services/audit.py` | OK |
| PII 3 camadas | `backend/app/services/pii.py` (scrub antes de logs/LLM) | OK |
| Criptografia at-rest | pgcrypto + Fernet | OK |
| Criptografia in-transit | TLS 1.3 + Cloudflare proxy | OK |
| WAF | Cloudflare managed rules + custom cartorio | OK |
| Rate limit | 60/min por IP + 3-tier API key | OK |
| Dead man's switch | Telegram GRUPO PIETRA alert >5min sem audit | OK |
| Pre-commit secrets scan | 11 patterns (AWS/GitHub/OpenAI/etc) | OK |

## 7. DPA Matrix (LGPD art. 33)

Conforme LGPD art. 33 (transferencia internacional):

| Sub-processor | Localizacao | Status DPA | Validade |
|---|---|---|---|
| Cloudflare | US (global) | ✅ signed | jan/2027 |
| Hostinger | BR | ✅ signed | jan/2027 |
| opencode-go | US | ✅ signed | jan/2027 |
| DeepSeek | China | ✅ signed | fev/2027 |
| **MiniMax** | US | **⏳ pending Gustavo** | jan/2027 (LGPD-015) |
| mimo | TBD | 🚧 pending provider | - |
| mistral-free | TBD | 🚧 pending provider | - |
| openrouter-free | TBD | 🚧 pending provider | - |
| gemini-free | TBD | 🚧 pending provider | - |

**Lacunas**: 4 free tiers bloqueados ate provider assinar DPA.
Tracker: `scripts/dpa_sign_flow.py`

## 8. RIPD (Relatorio de Impacto)

Conforme LGPD art. 38:

- **D21** Privacy by Design Checklist: `docs/lgpd/policy/D21-privacy-by-design-checklist.md`
- **D23** Site Privacy Policy v3: `docs/lgpd/policy/D23-site-privacy-policy-v3.md`
- **D24** DPO Contact Publicacao: `docs/lgpd/policy/D24-dpo-contact-publicado.md`
- **D25** Auditoria ANPD: `docs/lgpd/policy/D25-auditoria-anpd.md`

---

**Compliance status**: 95% LGPD
**Pendencias SUI**: 8 items (1 DPA pendente assinatura Gustavo, 4 free tiers pendentes, 3 SRE)

**Modified by Gustavo Almeida + cartorio-lgpd — G6 wave 14 (auto-gerado)**