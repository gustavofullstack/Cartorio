# RIPD — Relatório de Impacto à Proteção de Dados

**Cartório 2º Serviço Notarial de Uberlândia** | **Versão:** 1.5 | **Data:** 2026-07-18

> **LGPD-REVIEW-PENDING** — Versão 1.5 aguarda sign-off formal do DPO
> (Encarregado) antes da publicação definitiva. Owner: `cartorio-lgpd`.
> Migra de v1.4 (`docs/ripd.md` 2026-07-16 + addendum LobeChat/OpenClaw/
> LiteLLM/MiniMax) e incorpora deltas pós-Wave 48 (G8): secrets scanning
> CI, tabela emolumentos parametrizada, retentions + radar expandido.

> Documento elaborado conforme **LGPD Art. 38** e **Resolução CD/ANPD
> nº 4/2023**, que disciplina a hipótese de elaboração de Relatório de
> Impacto à Proteção de Dados Pessoais.

---

## 1. Identificação do Tratamento

| Item | Valor |
|---|---|
| Controlador | 2º Serviço Notarial de Uberlândia |
| CNPJ | XX.XXX.XXX/0001-XX (preencher antes do go-live final) |
| Endereço | Av. XX, nº XXX, Centro, Uberlândia/MG (preencher) |
| DPO (Encarregado) | `[definir — nome + email + telefone]` |
| DPO designado por | Gustavo Almeida (tableholder) |
| Operações cobertas | Atendimento multi-canal via bot WhatsApp/Telegram/Web |
| Categorias de dados | PII — CPF, RG, CNS, CNH, telefone, email, protocolos, escrituras |
| Base legal primária | LGPD Art. 6º (serviço público delegado) + Art. 7º (consentimento) |
| Volume estimado | 200–500 clientes/mês (peak IR + vendas imóveis) |

## 2. Descrição dos Tratamentos

### 2.1 Atendimento multi-canal
- **Canais**: WhatsApp (Evolution API 2.3.7), Telegram, Web (formulário).
- **Dados coletados**: nome, CPF, RG, telefone, email, número de protocolo,
  dados do ato notarial (escritura, certidão, procuração).
- **Finalidade**: prestação de serviços notariais (Lei 8.935/94).
- **Hipótese de tratamento**: execução de serviço público delegado
  (Art. 23, Lei 8.935/94) + execução de contrato (Art. 7º V) +
  obrigação legal (Art. 7º II, fé pública).
- **Sub-processadores**: OpenClaw Gateway, LiteLLM, MiniMax-M3 (DPA pending),
  Evolution API, Chatwoot 4.x (HITL handoff), Supabase (Postgres + Storage).

### 2.2 Auditoria (SHA256 chain + HMAC)
- **Dados**: log imutável de mutações (insert/update/delete + contexto).
- **Composição**: hash_chain `H(n) = SHA256(H(n-1) || payload)` +
  assinatura HMAC do payload.
- **Base legal**: LGPD Art. 37 (registro de operações) + Art. 46
  (segurança).
- **Retenção**: 5 anos (Art. 16) **ou** até revogação do titular
  (prevalece o maior). Dead-man's-switch verifica integridade a cada
  15 min; alerta Telegram GRUPO PIETRA em caso de quebra.

### 2.3 PII Scrubbing pré-LLM
- **Dados**: mascarados antes de chegar a qualquer LLM.
- **Camadas (3)**:
  1. **Input** — Pydantic v2 field validators mascaram CPF/RG/telefone/email.
  2. **Pre-LLM** — pipeline scrub em `app/services/pii.py` aplicado por
     todo chat handler antes da chamada upstream.
  3. **Output** — `Sentry before_send` (`app/services/sentry.py`) +
     log `MaskingFilter` (`app/services/log_masker.py`) removem PII de
     eventos externos e logs.
- **Base legal**: LGPD Art. 46 (medidas de segurança adequadas).

### 2.4 Sub-processadores de IA
- **OpenClaw Gateway** — router multi-provider + skills (T14 da v1.4).
- **LiteLLM** — fallback multi-provider (T15 da v1.4).
- **MiniMax-M3 (DPA pending)** — LLM coding/ops (T16 da v1.4).
- **LobeChat** — UI operador/agente (T13 da v1.4).
- Dados que tocam: prompts scrubbed (PII mascarada), tool calls
  anonimizados, respostas pós-scrub no output.

## 3. Avaliação de Necessidade e Proporcionalidade

- **Princípio da necessidade (Art. 6º III)**: coleta limitada ao mínimo
  indispensável para o ato notarial (CPF, RG, dados do ato). Não
  coletamos dados sensíveis (Art. 5º II — religião, saúde, opinião
  política, etc).
- **Princípio da adequação (Art. 6º I)**: finalidades legítimas,
  específicas e explícitas — execução de serviço público delegado.
- **Princípio da finalidade (Art. 6º IV)**: uso exclusivo para a finalidade
  declarada; vedada reutilização para marketing sem consentimento
  específico (Art. 7º I).
- **Princípio da livre acesso (Art. 6º II)**: titular pode consultar,
  corrigir, anonimizar, portabilizar e eliminar dados a qualquer tempo
  (Art. 18 — endpoints v1).

## 4. Riscos Identificados

### 4.1 Risco de vazamento via LLM (Probabilidade Média → Resíduo Baixo)

| Vetor | Cenário |
|---|---|
| LLM público recebe PII | Eco de CPF/RG em prompt não scrubbed |
| Log de prompt compartilhado | Console log captura dado antes do scrub |
| Erro humano em novo canal | Integração sem passar pelo pipeline PII |

**Mitigação**:
- PII scrubbing 3 camadas (validators + pre-LLM + output).
- Code review `cartorio-lgpd` obrigatório em qualquer integração nova
  com LLM.
- Testes de regressão falham se `app/services/pii.py` regredir
  (`tests/test_pii.py`).
- DPA MiniMax pending — bloqueia uso em prod até assinatura.

**Resíduo**: Baixo (PII nunca chega ao provider upstream).

### 4.2 Risco de acesso não-autorizado (Probabilidade Baixa → Resíduo Baixo)

| Vetor | Cenário |
|---|---|
| Atendente valida ato jurídico | Bot decide sozinho isenção/urgência/certidão |
| Credencial API comprometida | Token sem rotação expõe canais |

**Mitigação**:
- **HITL obrigatório**: protocolo nasce `DRAFT`. Escrevente valida
  antes do processamento. Bot nunca decide sozinho em isenção,
  urgência, validação jurídica ou emissão.
- Auth JWT + audit chain SHA256 + HMAC + rate limit 3-tier (N8N 600,
  DPO 60, default 30 req/min).
- Idempotência Redis 24h dedupe webhook.

**Resíduo**: Baixo (princípio HITL = camada humana obrigatória).

### 4.3 Risco de retenção excessiva (Probabilidade Média → Resíduo Baixo)

| Vetor | Cenário |
|---|---|
| Backup mantido indefinidamente | Postgres + Storage sem TTL |
| Conversa esquecida | Conversa fica meses sem anonimização |
| Soft delete sem purge | Dados marcados mas nunca apagados |

**Mitigação**:
- Retenção configurável por categoria: conversa 90 dias (T036),
  atendimento 365 dias, protocolo 5 anos (Art. 16), LLM logs 30 dias.
- **LGPD retenção scheduler** — job diário 03:00 BRT aplica TTL
  (`app/main.py` lifespan).
- Soft delete + purge job. Art. 18 IV/VI — direito de eliminação
  aplicável a qualquer tempo via `/api/v1/lgpd/erase` (autenticação
  DPO + JWT).

**Resíduo**: Baixo (automatização + endpoint dedicado).

### 4.4 Risco de segredo vazado em código (Probabilidade Média → Resíduo Baixo)

| Vetor | Cenário |
|---|---|
| API key cai em commit | `lin_api_*`, `sk-*`, etc. commitados |
| `.env` versionado | Acidentalmente `git add .env` |

**Mitigação**:
- **Secrets scanning CI** (G8.14.T3 — `scripts/check_no_literal_keys.py`).
  Bloqueia patterns `lin_api_*`, `sk-*`, `rnd_*`, `AQ.*`, `gAAAAA`,
  `ghp_*`, `xox*`, `AKIA*`, `AIza*`. Opt-out: `# noqa: ALLOW_KEY_FALLBACK`.
- `.env` no `.gitignore`. Template em `.env.example` apenas.
- Pre-commit hook com detect-secrets local.

**Resíduo**: Baixo (gate CI bloqueia merge).

### 4.5 Risco de quebra do canal (Probabilidade Média → Resíduo Baixo)

| Vetor | Cenário |
|---|---|
| Telegram parse_mode HTML quebra | LLM output com `<think>`/`<reasoning>` causa 502 |
| Evolution API formato ambíguo | Legacy root-level vs nested `data.message` |
| Webhook replay | Reenvio duplica atendimento |

**Mitigação**:
- Telegram wrap + retry/backoff (`backend/app/api/v1/telegram.py`,
  fix 2026-07-01).
- Evolution API parser aceita ambos formatos (legado + aninhado).
- HMAC signature + idempotência Redis 24h.

**Resíduo**: Baixo.

## 5. Medidas de Mitigação (LGPD Art. 38)

- ✅ PII scrubbing 3 camadas (validators Pydantic / pipeline
  pre-LLM / output Sentry+logs).
- ✅ Audit log chain SHA256 + HMAC (tamper-evident).
- ✅ HITL obrigatório em ato jurídico (DRAFT → validação escrevente).
- ✅ Backup criptografado em repouso (Supabase SSE-KMS) + em trânsito
  (TLS 1.3 / Traefik).
- ✅ RLS (Row Level Security) 100% das tabelas com PII.
- ✅ Secrets scanning CI (`scripts/check_no_literal_keys.py`, G8.14.T3).
- ✅ Rate limit 3-tier por API key (N8N / DPO / default).
- ✅ Idempotência Redis 24h em webhook dedupe.
- ✅ LGPD Art. 18 direitos implementados via `/api/v1/lgpd/*`.
- ✅ Dead-man's-switch audit + LGPD retenção scheduler (lifespan).
- ✅ Radar expandido (`/health/radar/expanded`) — DNS/Traefik/SSH/disk.

## 6. Salvaguardas dos Direitos do Titular (LGPD Art. 18)

| Direito | Endpoint | Status |
|---|---|---|
| Confirmação de existência de tratamento | `/api/v1/lgpd/confirm` | ✅ |
| Acesso aos dados | `/api/v1/lgpd/access` | ✅ |
| Correção | `/api/v1/lgpd/correct` | ✅ |
| Anonimização, bloqueio ou eliminação | `/api/v1/lgpd/erase` | ✅ |
| Portabilidade | `/api/v1/lgpd/portability` | ✅ (T064) |
| Oposição | `/api/v1/lgpd/opposition` | ✅ (T065) |
| Não-automação de decisões | HITL mandatory | ✅ |
| Revisão de decisão automatizada | `/api/v1/lgpd/v2/review` (alpha) | ✅ (Art. 20) |

Autenticação: JWT (titular) + DPO bearer (operações destrutivas).
Logs de cada requisição Art. 18 vão ao audit chain.

## 7. Plano de Resposta a Incidentes (Art. 48)

- **Detecção**: radar contínuo via `/health/radar/expanded` (DNS,
  Traefik, SSH, disk, auditoria). Prometeus metrics + Alertmanager
  com canal Telegram GRUPO PIETRA.
- **Resposta**: dead-man's-switch (audit check a cada 15 min) +
  rota de incidentes (`docs/platforms/`).
- **Notificação DPO**: <24h após detecção (Art. 48).
- **Notificação ANPD**: <2 dias úteis se risco elevado (Art. 48 §1º).
- **Notificação titulares**: <72h se houver exposição de PII.
- **Audit log consultado para timeline**: replay completo via SHA256
  chain reconstruction.
- **Root cause + Lesson**: escrita em `.harness/memory/` (padrão
  `lesson-NNN-*.md`).
- **Tabela DPO + contatos**: vigente em `.harness/memory/` + runbooks
  por plataforma em `docs/platforms/`.

## 8. Revisão Periódica

- **Frequência**: anual (próxima revisão: **2027-07-18**).
- **Trimestral**: DPO + `cartorio-lgpd` (revisão operacional).
- **Ad-hoc**: mudanças em coleta/finalidade/compartilhamento/canal/
  sub-processador — RIPD atualizado antes do deploy.
- **Trigger automático**: nova integração com LLM, novo canal, novo
  sub-processador, novo endpoint com PII.
- **DPA quarterly review**: `docs/lgpd/dpa_quarterly_review.md` mantém
  inventário de sub-processadores atualizado.

## 9. Aprovação

| Papel | Nome | Assinatura | Data |
|---|---|---|---|
| DPO (Encarregado) | `[aguardando assinatura cartorio-lgpd]` | ⏳ PENDING | 2026-07-18 |
| Controlador | Gustavo Almeida | ✅ tableholder | 2026-07-18 |
| Owner técnico | `cartorio-lgpd` + `cartorio-dev` | ✅ revision pending | 2026-07-18 |

> **LGPD-REVIEW-PENDING**: este RIPD v1.5 **NÃO deve ser publicado**
> para stakeholders externos até que o DPO (Encarregado) tenha
> assinado formalmente. Comentários devem ir via
> `cartorio-lgpd` no PR de revisão.

## 10. Anexos

- **LIÇÃO 246** — Wave 48 strategy direct-master
  (`.harness/memory/lesson-246-g8-wave-48-direct-master-2026-07-18.md`).
- **LIÇÃO 216** — Honesty Gate enforcement
  (`.harness/memory/lesson-216-g8-honesty-reset-dlq-t4-2026-07-17.md`).
- **LGPD-016** evidence pack (Wave 43–49) — DPA MiniMax + radar
  expandido + secrets scanning CI.
- **RIPD v1.4 base** — `docs/ripd.md` (2026-07-16).
- **RIPD v1.4 addendum** — `docs/lgpd/RIPD_v1.4_ADDENDUM.md` (G6.C.T1).
- **RIPD histórico** — `docs/archive/ripd_v1.3_2026-06-23.md`,
  `docs/ripd-cartorio-2026-06-25.md` (v1.0 detalhado).
- **DPA templates** — `docs/lgpd/dpa_*.md` (8 sub-processadores).
- **AUDITORIA_BLOCKERS** — `docs/lgpd/AUDITORIA_BLOCKERS.md`.

---

## Histórico de versões

| Versão | Data | Mudança | Owner |
|---|---|---|---|
| 1.0 | 2026-06-25 | Baseline inicial (fluxo completo) | `cartorio-lgpd` |
| 1.1 | 2026-06-26 | Ajustes pós-revisão DPO | `cartorio-lgpd` |
| 1.2 | 2026-06-30 | Sub-processadores OpenCode-Go / N8N | `cartorio-lgpd` |
| 1.3 | 2026-07-06 | Correção inconsistência OpenCode-Go/DeepSeek | `cartorio-lgpd` |
| 1.4 | 2026-07-16 | Addendum LobeChat + OpenClaw + LiteLLM + MiniMax | `cartorio-lgpd` (G6.C.T1) |
| **1.5** | **2026-07-18** | **10 seções LGPD Art. 38 + 4 novos riscos (G8.Wave 48) + Secrets CI** | **`cartorio-lgpd` (G8.18.T3)** |

---

**Modified by Gustavo Almeida + cartorio-lgpd — 2026-07-18 (G8.18.T3)**
