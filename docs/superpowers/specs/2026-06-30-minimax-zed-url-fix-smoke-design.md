# Design: MiniMax Coding Plan no Zed — Correção de URL + Smoke Test

**Data:** 2026-06-30
**Autor:** ZCode (brainstorming)
**Status:** RASCUNHO — aguardando aprovação do usuário antes do `writing-plans`

---

## 1. Contexto e motivação

Em 2026-06-30, o usuário Gustavo Almeida colou o provider config oficial do seu coding plan (MiniMax IO Token Plan · Monthly Max, $50/mês, ~5.1B tokens M3, contexto 1M). O bloco mostra:

- Provider: `minimax-coding-plan`
- Base URL: `https://api.minimax.io/anthropic`
- Formato: Anthropic messages (`/v1/messages`)
- Modelos: `minimax-m3` (1M ctx) e `minimax-m2.7-highspeed` (205K ctx)

Auditoria local do `~/.config/zed/settings.json` (modificado hoje às 11:55) mostra que o provider `minimax-coding-plan` JÁ está cadastrado no Zed, mas com `api_url` divergente: `https://api.minimax.io/v1` (formato OpenAI-compatible) em vez de `https://api.minimax.io/anthropic` (formato Anthropic Messages que o coding plan expõe).

O bloco `language_models.openai_compatible.minimax-coding-plan` em `~/.config/zed/settings.json` usa o nome do provider `openai_compatible` — incompatível com o formato Anthropic real do endpoint. Logo, hoje o Zed não consegue chamar o coding plan corretamente: ou retorna 404/401, ou cai no fallback padrão (Google/gemini-3.5-flash, que é o `default_model` atual).

Existe um backup pré-correção em `~/.config/zed/settings_backup_pre_minimax_20260630_101334.json` (timestamp 2026-06-30 10:13:34). Ele confirma o estado anterior e serve como ponto de rollback.

### Restrições do projeto

- `AGENTS.md` (raiz) proíbe commitar `.env` ou chaves de API em arquivos do repo. Toda referência a chave neste spec usa **prefixo + últimos 4 caracteres** (`sk-cp-...r_7j5s`).
- Working tree atualmente tem **1 arquivo modificado**: `.brain/memory/2026-06-30.md` (não relacionado, manter).
- Zed está em `/usr/local/bin/zed` (instalado via Homebrew x86_64) — versão Intel-rosetta numa máquina arm64. Não é escopo desta spec trocar a arquitetura do binário.
- O usuário confirmou que **nunca** quer rotação da chave `sk-cp-...r_7j5s`. Ela é compartilhada apenas entre ele e o agente desta sessão.

## 2. Não-objetivos

- **Não adicionar os outros 5 provedores** (opencode-free x3, mistral-free, openrouter, groq, google-studio) ao Zed. Eles já existem como chaves coladas, mas wiring de 6 provedores é uma spec separada (P3 do roadmap macro).
- **Não criar hierarquia de 10 agents** (CEO→CTO→COO→CMO→CFO→TechLead→Senior→Pleno→Junior→Intern). Isso é uma spec de Paperclip separada.
- **Não tocar em ~/.claude/ ou ~/.codex/** — esta spec é Zed-only.
- **Não criar commit** que mencione a chave completa. Apenas prefixo + 4 chars.
- **Não habilitar macOS Accessibility/TCC** nem rodar `tccutil reset`. Permissões de automação são decisão do usuário no painel de Segurança & Privacidade.

## 3. Arquitetura proposta

### 3.1 Mudança mínima no Zed

```
~/.config/zed/settings.json
└─ language_models.openai_compatible.minimax-coding-plan.api_url
   ├─ ANTES: "https://api.minimax.io/v1"
   └─ DEPOIS: "https://api.minimax.io/anthropic/v1"
              ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
```

> **Decisão importante**: o provider config no Zed usa `openai_compatible`, mas o endpoint `https://api.minimax.io/anthropic/v1/messages` espera **formato Anthropic Messages**, não OpenAI Chat Completions. Existem duas rotas viáveis:

| Rota | O que muda | Risco | Custo |
|---|---|---|---|
| **A — Manter `openai_compatible` + URL `/anthropic/v1`** | Apenas `api_url`. Continua falando OpenAI-style com o endpoint Anthropic. | **Alto**: o endpoint rejeita com 400 (`invalid request format`) porque headers/body são OpenAI mas servidor é Anthropic. | Baixo (1 linha) |
| **B — Trocar para provider `anthropic`** | Mover config de `openai_compatible` para `language_models.anthropic` com `api_url` apontando para `/anthropic/v1`. | **Médio**: requer editar a estrutura (não só URL). Pode conflitar com `claude-acp` agent server. | Médio (~10 linhas) |

**Recomendação**: **Rota A como primeiro teste** (uma linha, ver se funciona) e fallback documentado para Rota B no spec do plano. Justificativa: se A funcionar, é 1 linha e zero risco estrutural. Se A falhar, B é a correção real e o spec do plano cobre o rollback.

### 3.2 Smoke test

Script bash simples em `scripts/minimax-smoke.sh` que:

1. Carrega `MINIMAX_API_KEY` de `~/.zshenv` (ou `.env.local` se existir).
2. Faz `curl -sS -X POST https://api.minimax.io/anthropic/v1/messages` com payload mínimo Anthropic (`model: minimax-m3`, `max_tokens: 32`, `messages: [{role:user, content:"Reply with the single word: pong"}]`).
3. Imprime status HTTP + `content[0].text`.
4. Exit code 0 se 200 + texto contiver `pong`; exit 1 caso contrário.

**Por que smoke test**: validar que a URL/header/body batem com o que o endpoint aceita ANTES de qualquer integração maior. Se o smoke test passar, a config do Zed está correta.

### 3.3 Rollback

Se algo quebrar, voltar `api_url` para `https://api.minimax.io/v1` (estado atual) ou restaurar do backup `settings_backup_pre_minimax_20260630_101334.json` com `cp`. **Não deletar** o backup.

### 3.4 Componentes

| Componente | Tipo | Path | Propósito |
|---|---|---|---|
| Mudança no `settings.json` | config edit | `~/.config/zed/settings.json` | Corrigir `api_url` do provider `minimax-coding-plan` |
| `minimax-smoke.sh` | script | `scripts/minimax-smoke.sh` (novo) | Validar endpoint com 1 chamada Anthropic Messages |
| Entrada na memória do dia | memory | `.brain/memory/2026-06-30.md` | Anotar achado + correção + teste |
| Entrada em `docs/superpowers/specs/` | spec | este arquivo | Rastro de design |

## 4. Decisões de design

### 4.1 Onde guardar a chave no runtime

- **Opção X — `~/.zshenv`**: o usuário já tem o costume de exportar via shell. Vantagem: sobrevive reboot, e Zed lê env no launch. Desvantagem: arquivo é lido por qualquer processo do user.
- **Opção Y — `~/.config/zed/settings.json` direto**: alguns providers Zed suportam campo `api_key` inline. Vantagem: autocontido. Desvantagem: arquivo `chmod 600` mas fica exposto em qualquer diff de git (já é gitignored pelo time, confirmar).
- **Opção Z — keychain do macOS via `security` CLI**: mais seguro, mas Zed não lê automaticamente.

**Recomendação**: **Opção X** (`~/.zshenv`) por consistência com o que o usuário já tem. **Nunca** gravar a chave no `settings.json` em texto puro, mesmo em arquivo gitignored — vai contra `AGENTS.md`.

### 4.2 Modelo default

A spec **NÃO** troca `agent.default_model` nem `agent.default_profile.builder.default_model`. O usuário escolhe manualmente na hora de usar. Default atual continua sendo `google/gemini-3.5-flash` (que está funcionando).

### 4.3 Validação do smoke test

- **Sucesso**: HTTP 200, JSON com `content[0].type == "text"` e texto contendo `pong` (case-insensitive).
- **Falha conhecida #1 — 401/403**: chave inválida/expirada. Reportar e parar. **Não** sugerir rotação (usuário proibiu).
- **Falha conhecida #2 — 404**: URL errada (a causa mais provável hoje). Reportar URL tentada e listar variações sugeridas (`/v1`, `/anthropic/v1`, `/anthropic`).
- **Falha conhecida #3 — 400 invalid format**: confirma hipótese da Rota A acima; sugerir fallback para Rota B (provider `anthropic` em vez de `openai_compatible`).

### 4.4 Testes e gates

Esta spec é **infra pessoal**, não passa pelos gates do backend Cartório (pytest, mypy, ruff). Não há `pyproject.toml` para alterar. Verificação é:

1. Diff manual de `settings.json` (1 linha).
2. Execução de `bash scripts/minimax-smoke.sh` retorna `pong`.
3. Inspeção visual no Zed (panel do Agent) confirma `minimax-coding-plan` listada como provider.

## 5. Riscos e mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| URL `/anthropic/v1` retorna 404 (servidor só aceita `/v1`) | Média | Smoke test falha | Rollback + tentar `/v1/messages` direto, ou mover para provider `anthropic` |
| Formato OpenAI vs Anthropic mismatch | Alta (Rota A) | 400 invalid_format | Fallback documentado para Rota B |
| Chave expirada ou quota excedida | Baixa | 401/429 | Reportar sem sugerir rotação; usuário decide |
| Backup corrompido | Muito baixa | Sem rollback | Backup já é `cp` do estado válido anterior |
| macOS Firewall bloqueando saída para `api.minimax.io` | Muito baixa | Timeout | Smoke test usa `--max-time 10` para falhar rápido |

## 6. Arquivos tocados

- `~/.config/zed/settings.json` — 1 linha alterada (`api_url`).
- `scripts/minimax-smoke.sh` — novo, ~30 linhas.
- `docs/superpowers/specs/2026-06-30-minimax-zed-url-fix-smoke-design.md` — este arquivo (já criado).
- `.brain/memory/2026-06-30.md` — append de 5-10 linhas com achado/correção.

**Nenhum arquivo novo no repo Cartório além do spec e do script.** O `settings.json` é externo.

## 7. Plano de execução (alto nível)

1. **Backup** do `settings.json` atual → `settings_backup_pre_smoke_20260630_HHMMSS.json`.
2. **Editar** `~/.config/zed/settings.json`: trocar `api_url` de `https://api.minimax.io/v1` para `https://api.minimax.io/anthropic/v1` (Rota A).
3. **Criar** `scripts/minimax-smoke.sh` com 30 linhas + `chmod +x`.
4. **Executar** o smoke test. Se `pong` → sucesso. Se erro → fallback documentado para Rota B (mover config para `language_models.anthropic`).
5. **Documentar** em `.brain/memory/2026-06-30.md` o resultado (sucesso/falha) e a próxima ação.

> **Próximo passo após aprovação**: invocar skill `superpowers:writing-plans` para gerar `docs/superpowers/plans/2026-06-30-minimax-zed-url-fix-smoke-plan.md` com tasks TDD-style numeradas.