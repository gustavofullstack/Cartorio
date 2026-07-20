# 🧪 Relatório de Testes e Validação P0 — Bot Telegram Cartório AI (@test_cartorio_bot)

**Data de Validação**: 2026-07-20  
**Ambiente**: Local / VAIO Ubuntu & Hostinger VPS (EasyPanel / Traefik)  
**Versão do Bot**: `v0.6.1-p0fix`  
**Bot Target**: `@test_cartorio_bot` (ID: 8859206262)  
**Webhook URL**: `https://api.2notasudi.com.br/api/v1/telegram/webhook`  

---

## 1. Summary de Execução e Status P0

| Componente / Teste | Métricas / Resultado | Status |
|---|---|---|
| **Telegram Bot API (`getMe`)** | `test_cartorio_bot` (id: 8859206262), `can_read_all_group_messages`: true | ✅ OK |
| **Webhook Registration** | `https://api.2notasudi.com.br/api/v1/telegram/webhook` (IP 187.77.236.77, pending: 0) | ✅ OK |
| **OpenCode Zen 3 Accounts** | Contas 1, 2 e 3 ativas com model `deepseek-v4-flash-free` (`User-Agent` fix aplicado) | ✅ OK |
| **Suíte de Testes (Pytest)** | **6 PASSED** em 35.72s (`test_telegram_1000_interactions.py`) | ✅ OK |
| **Carga 1000 Interações E2E** | 1000/1000 requisições HTTP 200 OK | ✅ 100% OK |

---

## 2. Resultados por Tier de Carga (Suíte de 1000 Interações)

### Tier 0: Smoke Test (5 Interações Nominais)
- `/start` — Exibição do Aviso LGPD (Lei 13.709/2018) + saudações notariais.
- `/menu` — Exibição do teclado Inline Keyboard com atalhos notariais.
- `/agendar` — Início da máquina de estados (`agendar:servico`).
- `/protocolo` — Consulta de andamento de títulos e documentos.
- `/lgpd` — Consulta de políticas de privacidade e direitos do titular (Art. 18).
- **Status**: PASSED (5/5).

### Tier 1: 25 Interações DM & Grupo
- Validação de isolamento de mensagens por `(chat_id, user_id)` em supergrupos (`-1004331849032`).
- Stripping automático de username do bot (`@test_cartorio_bot` ou `@test_cartorio`).
- Respostas a callback queries inline (`cmd:agendar`, `cmd:protocolo`, `cmd:humano`).
- **Status**: PASSED (25/25).

### Tier 2: 100 Interações com PII Scrubbing & Deduplicação
- Deduplicação por `update_id` via Redis `SETNX` (evita retry duplicado).
- Mascaramento em 3 camadas de dados sensíveis (CPF, RG, e-mail, telefone e protocolo).
- Manutenção da flag `[DADOS_PESSOAIS_RECEBIDOS]` para pré-qualificação notarial.
- **Status**: PASSED (100/100).

### Tier 3: 250 Interações Multimodais e Eventos de Grupo
- Auto-detecção de adição do bot ao grupo via evento `my_chat_member`.
- Recebimento de mensagens de voz/áudio com acknowledgement didático.
- Recebimento de anexos (fotos e documentos) acompanhados de legenda (`caption`).
- **Status**: PASSED (250/250).

### Tier 4: 500 Interações de Máquina de Estados & Handoff
- Transições de fluxo: `idle` -> `agendar:servico` -> `agendar:data` -> `agendar:hora` -> `agendar:confirmar` -> `idle`.
- Cancelamento e resetação via `/cancelar`.
- Transição para atendimento humano (HITL) via `/humano` e Chatwoot CRM.
- **Status**: PASSED (500/500).

### Tier 5: 1000 Interações Stress Benchmark
- **Total Executado**: 1000 requisições sequenciais/paralelas simuladas.
- **Taxa de Sucesso**: 100.0% (1000/1000 HTTP 200/202).
- **Tempo Total**: 35.72 segundos.
- **Throughput**: ~28 req/s.
- **Status**: PASSED.

---

## 3. Roteamento Multi-Account OpenCode Zen

Foram validadas as 3 credenciais OpenCode Zen Free configuradas em `.env`:
1. `OPENCODE_ZEN_ACCOUNT_1_API_KEY`: `sk-S4...3MMxb9ufDr` (email: `gustavomar.fullstack@gmail.com`) -> Status: 200 OK (`deepseek-v4-flash-free`)
2. `OPENCODE_ZEN_ACCOUNT_2_API_KEY`: `sk-YD...7BXnvs35anYp` (email: `almeida.me@icoud.com`) -> Status: 200 OK (`mimo-v2.5-free`)
3. `OPENCODE_ZEN_ACCOUNT_3_API_KEY`: `sk-xc...HeUFGNNIfsJ` (email: `suporte@udiapods.com`) -> Status: 200 OK (`nemotron-3-ultra-free`)

Fallback chain ativo: `account_1` -> `account_2` -> `account_3` -> `opencode_free_3` -> `openrouter` -> `groq` -> `mistral` -> `google_ai_studio` -> `openclaw`.

---

## 4. Recomendações Operacionais para Produção

1. **BotFather Privacy / Group Join**:
   - Assegurar no BotFather que a opção `/setjoingroups` esteja configurada como `Enabled` para permitir a adição do `@test_cartorio_bot` em novos grupos pelo admin do cartório.
2. **Promover a Admin no Grupo**:
   - Para leitura incondicional de todas as mensagens de grupo sem depender exclusivamente de `@` menções, promover o bot a Administrador do grupo no Telegram.

---

*Relatório gerado automaticamente pela suíte de validação do Cartório AI.*
