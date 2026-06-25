# Sessão 2026-06-25 — Resumo Final

**Tema**: Provisionamento de provedores LLM free (opencode/openrouter/groq/mistral) no ZCode.app para reduzir consumo da cota MiniMax IO.

**Duração**: ~13:00 → ~13:20 (ZCode time)

## Entregas (9 commits no master)

| # | Commit | Mensagem curta |
|---|---|---|
| 1 | `b0edc8f` | docs(specs): ZCode free-provider fallback chain + audit design |
| 2 | `8e2091b` | docs(plans): ZCode free-fallback chain implementation plan |
| 3 | `1253194` | fix(spec+plan): Task 0.3 adicionada (achado empírico enabled=null) |
| 4 | `c38c52a` | docs(audit): ZCode config snapshot 2026-06-25 |
| 5 | `c0b5b0a` | chore(config): 4 provedores free ativados |
| 6 | `d83213c` | chore(memory): cross-session MEMORY.md criado |
| 7 | `8d2170f` | chore(memory): log skill creation |
| 8 | `b605c83` | docs(skills): applicability map (53 skills: 15A/15D/23N) |
| 9 | `0a23104` | test(override): empirical test (display-only) |

## Mudanças aplicadas em ~/.zcode/ (fora do repo)

| Path | Mudança | Tamanho |
|---|---|---|
| `~/.zcode/v2/config.json` | 4 free providers: `enabled: null → true` | +4 linhas |
| `~/.zcode/memory/MEMORY.md` | **criado** | 130 linhas / 7 KB |
| `~/.zcode/skills/zcode-fallback/SKILL.md` | **criado** | 73 linhas |
| `~/.zcode/skills/zcode-fallback/references/provider-registry.md` | **criado** | 86 linhas |
| `~/.zcode/skills/zcode-fallback/references/subagent-routing.md` | **criado** | 81 linhas |

## Backups criados (rollback possível)

- `~/.zcode/cli/config.json.bak.20260625-125226` (Task 0.1)
- `~/.zcode/v2/config.json.bak.20260625-125226` (Task 0.1)
- `~/.zcode/v2/config.json.bak.pre-activation.20260625-125612` (Task 0.3, antes da ativação dos free)
- `/tmp/redesim-helper-agent.json.bak.20260625-130344` (Fase 4, antes do teste de override)

## Achados empíricos importantes

1. **Estrutura real da config v2**: `~/.zcode/v2/config.json:.provider.<UUID>` — NÃO top-level como minha exploração inicial sugeriu.

2. **4 provedores free estavam com `enabled: null`** (não `false`):
   - `15568793-...` opencode-free
   - `a84a18da-...` openrouter-free
   - `4ff49ce7-...` groq-free
   - `04873a4d-...` mistral-free

3. **`default-minimax` ≠ `minimax-coding-plan`**: o default estava em proxy opencode-go, não no coding plan real. Mas durante esta sessão, o parent mudou para `c997ca58-.../minimax-m3` (coding plan real via `api.minimax.io/anthropic`) — provavelmente ação manual do usuário.

4. **Override de model em subagent JSON NÃO funciona**: campo `model` em `~/.zcode/subagents/*.json` é display-only. O subagent herda o provider do parent.

5. **`killall ZCode` derruba a sessão de chat**: qualquer alteração em config requer avisar o usuário antes do restart.

## Estado final do ZCode

- **Providers enabled**: 6 (default-minimax, minimax-coding-plan, opencode-free, openrouter-free, groq-free, mistral-free)
- **Default model** (parent atual): `c997ca58-.../minimax-m3` (coding plan real)
- **Skills user-level**: 34 (33 originais + 1 nova `zcode-fallback`)
- **Memória cross-session**: `~/.zcode/memory/MEMORY.md` populada

## Como usar (passo-a-passo)

### Para uma tarefa exploratória (Modo B — free chain)
1. GUI: Settings → Model Provider → `groq-free` → `openai/gpt-oss-120b` (mais rápido)
2. Trabalhar normalmente. Subagents herdam.
3. Quando terminar, voltar para `minimax-coding-plan` no Settings.

### Para uma tarefa crítica (Modo A — pago)
1. Garantir que o parent está em `minimax-coding-plan/minimax-m3` (já está).
2. Trabalhar normalmente.

### Para tentar override de subagent (Modo C — NÃO recomendado)
- ❌ Não funciona. Subagent sempre herda o parent.

## Próximas sessões sugeridas

- [ ] Usar a skill `zcode-fallback` em uma sessão real para validar heurística
- [ ] Orquestração C-level no Cartorio via `up-agent-corporation` (próximo sprint)
- [ ] Habilitar plugin `document-skills` se for gerar PDF/docx
- [ ] Criar skill `cartorio-context` se padrões do Cartorio forem usados com frequência

## Limitações conhecidas deste plano

- **Subagent-driven puro não foi possível**: a tool `Agent` só tem `Explore` (read-only). Para tasks de escrita, executei manualmente. Isso é pragmático mas perde algumas garantias da skill `subagent-driven-development`.
- **Skill `zcode-fallback` ainda não foi testada em produção**: foi criada mas ainda não carregada pelo app em uso real. Próxima sessão que invocar a skill vai validar se o app a reconhece.
- **Teste de override confirma display-only**: mas não investiguei 100% como o app resolve a string (bundle ofuscado). Pode ser que em versão futura do ZCode o override passe a funcionar.