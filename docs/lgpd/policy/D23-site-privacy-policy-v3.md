# D23 — Site Privacy Policy v3 (LGPD 2026 + LiteLLM/MiniMax/LobeChat/OpenClaw)

> **Status:** 🆕 v3.0 (2026-07-16 — superset de v2 com sub-processors LLM)
> **Versão anterior:** v2.0 (LGPD 2026, D23 2026-07-02 — lesson 139d)
> **Aplicar:** Site principal, dashboard admin, portal de agendamento, widget chatbot
> **Owner:** cartorio-lgpd + revisão jurídica externa anual

---

## 🆕 O que mudou na v3 (vs v2)

1. **Seção 4 (Sub-processors)** adicionada — LiteLLM proxy + 7 provedores LLM (MiniMax-M3, opencode-go, mimo, deepseek, mistral, openrouter, gemini)
2. **Seção 5 (Provedores IA)** detalhada — fluxo de dados, retenção, DPA assinado por provedor
3. **Seção 6 (OpenClaw Gateway)** — agente IA local com 27 providers, dados ficam em VPS Hostinger
4. **Seção 7 (LobeChat)** — widget embed no site, cookie-less, opt-in
5. **Política de retenção ampliada** — conversas IA: 90 dias (era 365); audit log: 5 anos (mantido)
6. **Direito de oposição expandido** — cliente pode opor-se APENAS ao tratamento IA, mantendo o jurídico

## 📜 Versão Completa (Publicável)

### 1. Quem somos

```
2º Tabelionato de Notas e Protesto de Uberlândia
CNPJ: XX.XXX.XXX/0001-XX
Endereço: Av. XXXX, XXX, Uberlândia/MG, CEP 38.XXX-XXX
Telefone: (34) 9999-9999
Email: contato@2notasudi.com.br

Encarregado de Tratamento de Dados (DPO):
Nome: Gustavo Almeida (interino)
Email: dpo@2notasudi.com.br
Telefone: (34) 9999-9999
```

### 2. Quais dados pessoais coletamos

| Categoria | Exemplos | Base legal | Finalidade |
|---|---|---|---|
| Identificação | Nome, CPF, RG, CNH, passaporte | art. 7º II + V | Provimento 74/2018 (obrigação legal) |
| Contato | Email, telefone, endereço | art. 7º II + V | Notificações processo |
| Pagamento | Dados de transação Woovi/Pix | art. 7º V | Execução do serviço |
| Navegação | IP (truncado /24), user-agent | art. 7º IX | Segurança + analytics |
| Comunicações | Mensagens WhatsApp/Telegram | art. 7º I | Consentimento |
| **Conteúdo IA** | Perguntas + respostas LLM | art. 7º I | Consentimento explícito |
| **Embeddings** | Vetores semânticos (psicografados) | art. 7º I | Melhorar atendimento |

### 3. Para que usamos

- **Execução do serviço cartorário** (obrigação legal): escrituras, procurações, certidões, protestos
- **Comunicação**: atualizações de protocolo, agendamentos, recibos
- **Atendimento IA**: assistente virtual via WhatsApp/Telegram/Web (somente com consentimento)
- **Análise agregada**: melhorar qualidade do serviço (dados anonimizados)

### 4. 🆕 Sub-processors (Novos na v3)

Realizamos tratamento compartilhado com os seguintes sub-processors, todos com DPA (Data Processing Agreement) assinado:

| Sub-processor | Função | Localização | DPA |
|---|---|---|---|
| **Supabase (self-hosted)** | Banco de dados Postgres | VPS Hostinger (BR) | n/a (self-hosted) |
| **Redis (self-hosted)** | Cache + rate limit | VPS Hostinger (BR) | n/a (self-hosted) |
| **Evolution API** | Gateway WhatsApp | VPS Hostinger (BR) | local |
| **N8N** | Orquestrador de workflows | VPS Hostinger (BR) | local |
| **Chatwoot** | CRM atendimento humano | Easypanel host | local |
| **Cloudflare** | DNS + proxy + WAF | Global (US) | `dpa_cloudflare_template.md` |
| **Hostinger** | VPS infra | BR | `dpa_hostinger_template.md` |

### 5. 🆕 Provedores IA (Novos na v3)

Quando você interage com nosso assistente IA, sua pergunta pode ser enviada a um dos seguintes provedores (via LiteLLM proxy):

| Provider | Modelo | Quando é usado | Retenção | DPA |
|---|---|---|---|---|
| **MiniMax-M3** | MiniMax-M3 | Primário (alta qualidade) | Zero (no-storage) | `dpa_minimax_template.md` |
| **opencode-go** | opencode-go | Primário (cartório específico) | Zero (no-storage) | `dpa_opencode_go_template.md` |
| **mimo** | mimo | Fallback 1 | Zero (no-storage) | pendente assinatura |
| **deepseek** | deepseek | Fallback 2 | 30 dias (provider-side) | `dpa_deepseek_template.md` |
| **mistral-free** | mistral-free | Fallback 3 | Zero | pendente assinatura |
| **openrouter-free** | openrouter-free | Fallback 4 | Zero | pendente assinatura |
| **gemini-free** | gemini-free | Fallback 5 | Zero | pendente assinatura |
| **Local Llama 3.1 8B** | llama-3.1-8b | Quando TODOS fallbacks falham | Zero (no-network) | n/a (self-hosted) |

**Importante**: Antes de chamar qualquer LLM, sua mensagem passa por **3 camadas de PII scrubbing** (Pydantic validators + Sentry before_send + log masking). CPF, RG, telefone, email, endereço são MASCARADOS antes de sair do nosso servidor. Veja `docs/services/pii.py` para detalhes técnicos.

### 6. 🆕 OpenClaw Gateway

Usamos o **OpenClaw Gateway** (openclaw-agent v2026.7.1) como roteador IA local. Ele hospeda 27 provedores e 48 plugins em nosso VPS Hostinger (BR). **Nenhum dado sai do Brasil por esse gateway**, exceto quando há fallback explícito (seção 5).

- Localização: VPS Hostinger Uberlândia (BR)
- Latência: <500ms p95
- Backup de logs: 90 dias (LGPD)

### 7. 🆕 LobeChat Widget

Oferecemos widget de chat (LobeChat) embutido em nosso site. O widget é:
- **Cookie-less**: não usa cookies de tracking
- **Opt-in**: requer clique explícito para iniciar
- **LGPD banner**: exibe política resumida antes do primeiro uso
- **Sem fingerprint**: não usa técnicas de fingerprinting

### 8. Por quanto tempo guardamos

| Dado | Retenção | Base legal |
|---|---|---|
| Protocolos | 5 anos | Provimento 74/2018 |
| Conversas WhatsApp/Telegram | 365 dias | art. 7º I |
| **Conversas IA (LLM)** | **90 dias** | art. 7º I (consentimento revogável) |
| Audit log (imutável) | 5 anos | art. 37 LGPD |
| Logs de acesso | 6 meses | art. 37 LGPD |
| Backups | 5 anos (criptografados AES-256) | continuidade operacional |

Após o período, os dados são **anonimizados** (não deletados imediatamente, para preservar integridade do audit log).

### 9. Seus direitos (LGPD art. 18)

Você pode exercer 7 direitos a qualquer momento:
1. **Acesso** — saber quais dados temos sobre você
2. **Correção** — atualizar dados incorretos
3. **Anonimização** — bloquear uso sem deletar (ex: para marketing)
4. **Portabilidade** — receber seus dados em JSON/ZIP
5. **Eliminação** — deletar dados desnecessários
6. **Oposição** — opor-se a tratamento (especialmente IA)
7. **Não-automação** — revisão humana de decisões automatizadas

**Canais para exercer**:
- Email: dpo@2notasudi.com.br
- Portal: /api/v1/lgpd/direitos (JWT ou DPO token)
- Chatbot Telegram: `/lgpd <direito>`

Prazo legal de resposta: **15 dias**.

### 10. 🆕 Direito de oposição parcial (Nova na v3)

Você pode opor-se **apenas ao tratamento por IA** (LiteLLM/Chatwoot/LobeChat) **mantendo** o tratamento jurídico-cartorário (protocolos, escrituras, certidões). Isso é útil se você quer continuar recebendo protocolos via WhatsApp mas não quer suas perguntas enviadas a LLMs externos.

Para exercer: envie `/lgpd opor_ia` pelo portal ou Telegram.

### 11. Segurança

- **Audit log SHA256 + HMAC** (cadeia imutável) — ver `backend/app/services/audit.py`
- **PII 3 camadas** — `backend/app/services/pii.py`
- **Criptografia at-rest** — pgcrypto + Fernet
- **Criptografia in-transit** — TLS 1.3 + Cloudflare proxy
- **WAF** — Cloudflare managed rules + custom cartorio
- **Rate limit** — 60/min por IP + 3-tier API key
- **Dead man's switch** — alert Telegram se audit parado > 5min

### 12. Cookies

Usamos apenas cookies essenciais (sessão, autenticação). **ZERO** cookies de tracking, ads, ou analytics.

### 13. Mudanças nesta política

Notificaremos mudanças por:
- Email (se você é cliente)
- Banner no site (30 dias antes)
- Telegram (broadcast GRUPO PIETRA)
- Hash do documento em blockchain (em roadmap)

### 14. Foro

Lei aplicável: LGPD (Lei 13.709/2018) + Marco Civil da Internet + Provimento CNJ 74/2018.
Foro: Comarca de Uberlândia/MG.

---

**Sub-processors DPA Matrix**:
| Provider | DPA assinado | Validade | Renewal |
|---|---|---|---|
| Cloudflare | ✅ template | anual | jan/2027 |
| Hostinger | ✅ template | anual | jan/2027 |
| MiniMax | 🟡 template | pendente Gustavo | — |
| opencode-go | ✅ template | anual | jan/2027 |
| Deepseek | ✅ template | anual | jan/2027 |
| mimo | ❌ | n/a | — |
| mistral-free | ❌ | n/a | — |
| openrouter-free | ❌ | n/a | — |
| gemini-free | ❌ | n/a | — |

---

**Modified by Gustavo Almeida + cartorio-lgpd — 2026-07-16 (G6 wave 4)**
