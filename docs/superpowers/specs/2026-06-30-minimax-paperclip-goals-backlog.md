# Backlog de Objetivos — MiniMax / Paperclip / Zed Integration

**Data:** 2026-06-30
**Autor:** ZCode (brainstorming)
**Status:** PROPOSTA — derivado da request colada pelo usuário em 2026-06-30 13:07
**Fonte**: paste em `/Users/gustavoalmeida/.zcode/tmp/paste-attachments/2026-06-30/pasted-text-20260630-130733-56494362.txt`
**Spec relacionada (já aprovada em forma de draft, aguardando aprovação)**: `2026-06-30-minimax-zed-url-fix-smoke-design.md`

---

## Propósito

O usuário pediu, em texto livre, "ATIVE TUDO" cobrindo simultaneamente:
1. Paperclip (instalar + documentar)
2. ~10 plataformas nomeadas (MiniMax/OpenCode/Hermes/Claude-Code/Antigravity/Codex/ZCode-Agent/Codex-Bar/OpenChamber/ACPX)
3. Hierarquia de 10 agents (CEO→CTO→COO→CMO→CFO→TechLead→Senior→Pleno→Junior→Intern)
4. Integração Zed + Claude-Code + Codex + minimax-coding-plan
5. Ingestão global de todos os projetos do MacBook Pro no Zed
6. macOS Accessibility/TCC liberado
7. "Melhorar visual do Zed"
8. Suite de skills/MCPs/plugins
9. Documentação completa (Swagger/Postman do MiniMax)

Cada item abaixo vira **um ciclo independente**: brainstorm → spec → plan → implement → review.
Itens marcados `[READY]` já têm spec escrito ou contexto suficiente para iniciar imediatamente.
Itens marcados `[BLOCKED]` dependem de confirmação/ação manual do usuário antes de prosseguir.

---

## Backlog priorizado

### OBJETIVO 0 — Higiene de segredos (gatekeeper)
**Status**: `[BLOCKED]` por decisão do usuário manter chaves em texto puro.
**Escopo**: nada a fazer aqui — usuário decidiu manter as 8 chaves em chat sem rotação. Apenas registrar a decisão.
**Ação**: nenhuma, exceto documentar a política no `.brain/memory/2026-06-30.md`.
**Por que primeiro**: tudo abaixo usa essas chaves; política precisa estar clara antes de qualquer wiring.

### OBJETIVO 1 — Corrigir URL do MiniMax Coding Plan no Zed + smoke test
**Status**: `[READY]` — spec já em `docs/superpowers/specs/2026-06-30-minimax-zed-url-fix-smoke-design.md`.
**Escopo**:
- Trocar `api_url` em `~/.config/zed/settings.json` provider `minimax-coding-plan` de `https://api.minimax.io/v1` para `https://api.minimax.io/anthropic/v1`.
- Criar `scripts/minimax-smoke.sh` que valida com `curl /v1/messages`.
- Backup do settings antes (já existe `settings_backup_pre_minimax_20260630_101334.json`).
**Esforço**: ~20 min. **Risco**: baixo (1 linha + 1 script).
**Próximo passo**: usuário aprova spec → eu invoco `superpowers:writing-plans` → implemento.

### OBJETIVO 2 — Auditoria dos 6 provedores reais (MiniMax + 5 free)
**Status**: `[READY]`.
**Escopo**: para cada um dos provedores abaixo, fazer `curl $BASE/v1/models` (ou equivalente) e produzir `docs/PROVIDERS_AUDIT_2026-06-30.md`:

| Provider | Base URL | Formato | Auth |
|---|---|---|---|
| `minimax-coding-plan` | `https://api.minimax.io/anthropic` | Anthropic | `sk-cp-...r_7j5s` |
| `opencode-free-1` | `https://opencode.ai/zen/v1` | OpenAI | `sk-xcR...` |
| `opencode-free-2` | `https://opencode.ai/zen/v1` | OpenAI | `sk-S4V...` |
| `opencode-free-3` | `https://opencode.ai/zen/v1` | OpenAI | `sk-YDb...` |
| `mistral-free` | `https://api.mistral.ai/v1` | OpenAI | `grr6...` |
| `openrouter` | `https://openrouter.ai/api/v1` | OpenAI | `sk-or-v1-...` |
| `groq` | `https://api.groq.com/openai/v1` | OpenAI | `gsk_...` |
| `google-studio` | `https://generativelanguage.googleapis.com/v1beta/openai` | OpenAI | `AIza...` |

**Saída**: tabela markdown com `model_id`, `context_window`, `alive (yes/no)`, `latency_ms`, `format`, `auth_scheme`. Chave sempre mascarada como `sk-cp-...r_7j5s`.
**Esforço**: ~1 h. **Risco**: baixo (somente leitura).
**Pré-requisito**: OBJETIVO 0 fechado.

### OBJETIVO 3 — Adicionar os 5 provedores free ao Zed
**Status**: `[BLOCKED]` até OBJETIVO 2 entregar dados vivos.
**Escopo**: adicionar entradas `openai_compatible` em `~/.config/zed/settings.json` para `opencode-free-1/2/3`, `mistral-free`, `openrouter`, `groq`, `google-studio`, cada uma com `api_url` + `available_models` derivados da auditoria. Fonte da chave: `~/.zshenv`.
**Esforço**: ~1 h. **Risco**: médio (conflito de nomes de provider; precisa ser validado no Zed).
**Pré-requisito**: OBJETIVO 2.

### OBJETIVO 4 — Validar Claude-Code e Codex CLIs com MiniMax
**Status**: `[BLOCKED]` até OBJETIVO 1 fechar.
**Escopo**:
- Configurar `~/.claude/settings.json` para usar MiniMax via env (`ANTHROPIC_BASE_URL=https://api.minimax.io/anthropic`, `ANTHROPIC_AUTH_TOKEN=$MINIMAX_API_KEY`).
- Configurar `~/.codex/config.toml` similar (Codex usa OpenAI-compatible; pode precisar LiteLLM proxy).
- Smoke test: rodar `claude -p "say pong"` e `codex -p "say pong"` e validar resposta.
**Esforço**: ~1 h. **Risco**: médio (depende de OBJETIVO 1; Codex precisa de proxy se MiniMax for Anthropic-only).
**Pré-requisito**: OBJETIVO 1.

### OBJETIVO 5 — Paperclip local: subir e criar 1 agente CEO
**Status**: `[BLOCKED]` até validar docs e binário.
**Escopo**:
- Ler `~/projetos/paperclip/README.md`, `AGENTS.md`, `cli-config.yaml.example`, `acp_adapter/`, `acp_registry/`.
- Subir Paperclip Python (já instalado) com 1 agente CEO apontando para MiniMax.
- Validar heartbeat + criação de issue + checkout + comentário.
**Esforço**: ~2 sprints curtos. **Risco**: médio (precisa entender o runtime Rust-ACPX vs Python que o usuário mencionou).
**Pré-requisito**: OBJETIVO 1 (chave MiniMax funcionando).
**Nota**: o paste menciona "Rust-ACPX" mas `~/projetos/paperclip` é Python. A confirmar com usuário.

### OBJETIVO 6 — Hierarquia de 10 agents no Paperclip
**Status**: `[BLOCKED]` até OBJETIVO 5.
**Escopo**: criar CEO, CTO, COO, CMO, CFO, TechLead, Dev-Senior, Dev-Pleno, Dev-Junior (+1 a definir), cada um com chain-of-command e budget. Skills por papel (CTO = revisão técnica; CFO = custos; etc.).
**Esforço**: ~3 sprints. **Risco**: alto (10 agents com budget e chain precisa de testes de governança).
**Pré-requisito**: OBJETIVO 5.

### OBJETIVO 7 — Ingestão global dos projetos do MacBook Pro no Zed
**Status**: `[BLOCKED]` — depende de decisão do usuário sobre escopo.
**Escopo candidato**: indexar `~/projetos/{Cartorio,bank-app,finance-hub-os,hate-of-miss,paperclip,triqhub,udiapods}` no Zed LSP, gerar `.zed/contexts/` em cada projeto. **MAS**: precisa de consentimento explícito — esses projetos têm código privado, alguns com segredos em `.env`.
**Esforço**: ~1 sprint. **Risco**: alto (vazamento cross-project de contexto se não houver fronteira por projeto).
**Pré-requisito**: OBJETIVO 5 + política de fronteira.

### OBJETIVO 8 — Catálogo Postman/Swagger do MiniMax Coding Plan
**Status**: `[BLOCKED]` — a API doc pública em `platform.minimax.io/docs/token-plan/intro` precisa ser validada via WebFetch. Se for uma página marketing-only, este objetivo vira "não-fornecido pelo vendor" e devemos gerar um OpenAPI por observação.
**Escopo**: gerar `docs/minimax-coding-plan.openapi.yaml` a partir de:
1. WebFetch da doc pública (se houver).
2. Inspeção empírica: `curl /v1/messages`, `curl /v1/models`, etc.
3. Request `OPTIONS` ou trace de headers.
**Esforço**: ~meio sprint. **Risco**: baixo.
**Pré-requisito**: OBJETIVO 1 (endpoint validado).

### OBJETIVO 9 — macOS Accessibility/TCC para agentes
**Status**: `[BLOCKED — REQUER CLIQUE MANUAL]`.
**Escopo**: instruir o usuário (você) a abrir **manualmente**:
- System Settings → Privacy & Security → Accessibility → habilitar Terminal / Zed / Claude / Codex.
- System Settings → Privacy & Security → Automation → conceder permissões pedidas.
- System Settings → Privacy & Security → Full Disk Access (se necessário para varredura de `~/projetos`).
**Por que manual**: macOS exige clique físico em "Allow" — nenhum agente consegue driblar isso sem abuso de `tccutil`. E dar essa permissão a múltiplos processos simultaneamente é o tipo de ação `AGENTS.md` pede confirmação explícita.
**Esforço**: 5 min manuais. **Risco**: zero (você controla).
**Pré-requisito**: nenhum.

### OBJETIVO 10 — "Melhorar visual do Zed"
**Status**: `[DEFERRED]` — extremamente vago. Precisa de especificação (tema? font? keymap? layout? extensions list?).
**Escopo candidato**: trocar tema `Ayu Dark` por algo mais moderno (One Dark Pro / Catppuccin / Tokyo Night), instalar extension pack mínimo de syntax/lint/format, configurar fontes (`JetBrains Mono`, `Berkeley Mono`), ajustar `ui_font_size`/`buffer_font_size`.
**Esforço**: ~30 min. **Risco**: zero (reversível com backup do settings).
**Pré-requisito**: nenhum.

### OBJETIVO 11 — Investigar produtos não-confirmados (Antigravity / OpenChamber / Hermes.app / Codex-Bar / ZCode-Agent)
**Status**: `[BLOCKED]`.
**Escopo**: WebFetch de cada URL mencionada (`antigravity.app`, `openchamber.app`, `hermes.app`, `codex-bar.app`, `zcode-agent.app`, `acpx`, etc.) e classificar cada um em:
- **(R) Real, instalável, com docs públicas** → entra em OBJETIVO futuro.
- **(M) Marketing/branding wrapper** sobre Paperclip → marcar como tal e ignorar.
- **(F) Fantasma / não resolve / honeypot** → ignorar e remover do escopo.
**Saída**: tabela em `docs/PLATFORM_AUDIT_2026-06-30.md`.
**Esforço**: ~30 min. **Risco**: baixo.
**Pré-requisito**: nenhum.

### OBJETIVO 12 — Suite de skills/MCPs/plugins para os novos agents
**Status**: `[BLOCKED]` até OBJETIVO 6 criar os agents.
**Escopo**: para cada agent em OBJETIVO 6, listar skills (já parcialmente escritas em `~/.zcode/skills/`, `~/.agents/skills/`) e MCPs que ele deve usar. Migrar skills entre projetos conforme apropriado.
**Esforço**: ~2 sprints. **Risco**: médio.
**Pré-requisito**: OBJETIVO 6.

---

## Como ler este backlog

- **Posso começar OBJETIVO 1 hoje** se você aprovar a spec (`2026-06-30-minimax-zed-url-fix-smoke-design.md`). É ~20 min e dá um ground-truth concreto (o smoke test retorna `pong` ou erro específico).
- **OBJETIVO 2 é independente** e desbloqueia 3, 4 e 8. Posso rodar em paralelo.
- **OBJETIVOS 5, 6, 7, 12** dependem da hierarquia de agents, que é a parte mais arriscada. Eu sugiro **NÃO** começar essa thread até OBJETIVO 1 + 2 estarem verdes.
- **OBJETIVO 9 é seu**, não meu. Eu produzo o passo-a-passo; você clica.
- **OBJETIVO 10** eu posso fazer agora se você quiser um Zed mais bonito, sem depender de nada.
- **OBJETIVO 11** eu posso fazer agora — é só WebFetch — e ele me diz quais URLs do paste original eram reais vs marketing.

## Por que não estou executando "TUDO" agora

1. Skills `brainstorming` + `using-superpowers` colocam HARD-GATEs que você mesmo instalou.
2. Seu `AGENTS.md` exige o workflow `analisar → testar → corrigir → melhorar → otimizar → documentar → comentar → salvar na memória`. Pular para "melhorar + otimizar + ATIVE TUDO" sem "analisar + testar" quebra o contrato.
3. OBJETIVOS 5–7 envolvem mexer em TCC/macOS, criar hierarquia de 10 agents com budget, e indexar código privado cross-project — cada um desses é, por si só, uma sessão de planejamento separada.
4. Vários "ATIVE TUDO" do paste original mencionam produtos que ainda não validei (OBJETIVO 11) — se forem marketing-only, 50% do backlog evaporaria.

## O que peço agora (uma única coisa)

Diga-me qual OBJETIVO deste backlog você quer atacar primeiro. Sugestão:

- **Se quer algo visível em 20 min**: OBJETIVO 1 (aprovar a spec que já está escrita).
- **Se quer visibilidade antes de investir**: OBJETIVO 11 (auditar os produtos não-confirmados, em 30 min).
- **Se quer Zed mais bonito**: OBJETIVO 10.
- **Se quer desbloquear o resto**: OBJETIVO 2 (auditoria dos 6 provedores).

Eu não faço nada até você escolher. Esse é o gate final da brainstorming.