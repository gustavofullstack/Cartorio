# Design: ZCode Free-Provider Fallback Chain + Auditoria + Memória

**Data:** 2026-06-25
**Autor:** ZCode (brainstorming)
**Status:** RASCUNHO — aguardando aprovação do usuário antes do `writing-plans`

---

## 1. Contexto e motivação

O usuário Gustavo Almeida opera o ZCode.app v3.1.5 (build 1966) com **coding plan MiniMax IO** ativo. Hoje (2026-06-25), o `~/.zcode/cli/config.json` define `"model": "default-minimax/minimax-m3"`, que aponta para `https://opencode.ai/zen/go` (provider `default-minimax`, kind `anthropic`) — **NÃO** para `https://api.minimax.io/anthropic`, que é o coding plan real (provider `c997ca58-cfda-.../minimax-coding-plan`, hoje **não-selecionado**).

A intenção do usuário é:
1. **Reduzir consumo da cota MiniMax IO** usando provedores LLM free (`opencode-free`, `openrouter-free`, `groq-free`, `mistral-free`) em sub-tarefas que não exigem o modelo forte.
2. **Auditar, corrigir, melhorar, otimizar, organizar e documentar** o ambiente ZCode (configuração de providers, subagents, skills/plugins, MCPs, memória).
3. **Persistir aprendizados** no `.brain/memory/` do projeto Cartorio e/ou em `~/.zcode/memory/` global.

Os 4 provedores-alvo já estão **cadastrados** em `~/.zcode/v2/config.json` com chaves de API válidas, mas com `enabled: null` (achado empírico da Task 0.1 em 2026-06-25 — divergindo da hipótese inicial de `enabled: true`). Precisam ser ativados antes de qualquer uso. Falta:
- **Ativação** dos 4 provedores free (de `enabled: null` para `enabled: true`).
- Mecanismo de **routing/fallback** (não existe skill/plug-in nativo para isso).
- **Override explícito por subagent** (campo `model` no JSON de subagent é string livre, sem garantia de honra como `providerId/modelId`).
- **Mapeamento de skills/MCPs/plugins aplicáveis** ao projeto Cartorio.
- **Fluxo de auditoria** estruturado.

## 2. Não-objetivos

- **Não modificar `Cartorio/` em si.** O pedido é sobre o ZCode.app e o ambiente, não sobre o código do projeto. Quaisquer melhorias ao Cartorio viram em specs separados depois.
- **Não patchar o binário ZCode.app** (`/Applications/ZCode.app/Contents/Resources/app.asar`). Apenas config JSON, skills user-level, subagent JSONs, e memoriais.
- **Não trocar o modelo default global** automaticamente. O usuário decide manualmente quando trocar.
- **Não criar dependência obrigatória** em provedores free — eles entram como **rota opcional** e **fallback** em caso de cota MiniMax esgotada.

## 3. Arquitetura proposta

### 3.1 Camadas

```
┌────────────────────────────────────────────────────────────────┐
│  ZCode.app (Electron, v3.1.5) — INTOCÁVEL                       │
│  └─ Lê ~/.zcode/cli/config.json (model default)                 │
│     └─ Resolve provider em ~/.zcode/v2/config.json              │
│        ├─ minimax-coding-plan (pago)         ← preservar       │
│        ├─ opencode-free, openrouter-free,                       │
│        │  groq-free, mistral-free            ← free tier        │
│        └─ default-minimax (opencode-go)      ← preservar       │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│  Camada de orquestração (skill user-level: `zcode-fallback`)   │
│  └─ Decide qual provider/model usar por tarefa                  │
│     ├─ Modo A: tarefa crítica   → minimax-coding-plan          │
│     ├─ Modo B: tarefa exploratória → free tier (fallback chain) │
│     └─ Modo C: subagent override → campo model do JSON          │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│  Memória persistente (2 níveis)                                 │
│  ├─ Global: ~/.zcode/memory/MEMORY.md (cross-session)           │
│  └─ Projeto: Cartorio/.brain/memory/YYYY-MM-DD.md (timeline)    │
└────────────────────────────────────────────────────────────────┘
```

### 3.2 Componentes

| Componente | Tipo | Path | Propósito |
|---|---|---|---|
| `zcode-fallback` skill | user-level skill | `~/.zcode/skills/zcode-fallback/SKILL.md` | Ensina o agente principal a rotear tarefas entre providers conforme criticidade |
| `subagent-routing.md` | referência | `~/.zcode/skills/zcode-fallback/references/subagent-routing.md` | Como (e quando) tentar override de model em subagent JSON |
| `provider-registry.md` | referência | `~/.zcode/skills/zcode-fallback/references/provider-registry.md` | Tabela canônica de providers+models+ratelimits (atualizada manualmente) |
| `~/.zcode/memory/MEMORY.md` | memória global | (existente, vazio) | Lições cross-session sobre ZCode/fallbacks |
| `.brain/memory/2026-06-25.md` | memória do dia | (já modificado, manter) | Timeline da sessão atual |

## 4. Decisões de design

### 4.1 Mecanismo de fallback chain — **3 modos**, agente decide por tarefa

| Modo | Quando usar | Provider | Risco |
|---|---|---|---|
| **A — Pago (preservar)** | Tarefas críticas: edits destrutivos, decisões de arquitetura, raciocínio longo | `minimax-coding-plan` (reconfigurar como default) | Custa quota — usar com parcimônia |
| **B — Free chain (novo)** | Tarefas exploratórias: leitura, grep, classificação, sumarização | `groq-free/openai/gpt-oss-120b` → fallback para `mistral-free/devstral-small-latest` → fallback para `openrouter-free/cohere/north-mini-code:free` → fallback para `opencode-free/north-mini-code-free` | Rate limits agressivos; tools podem não funcionar |
| **C — Override de subagent (testar)** | Sub-tarefa isolada onde vale o risco | Editar `~/.zcode/subagents/<name>.json` campo `model` com `providerId/modelId` válido; despachar; reverter | Não há garantia de honra; reverter SEMPRE após teste |

**Ordem do free chain (B)**: prioriza latência (groq é mais rápido), depois qualidade do modelo (mistral-large), depois disponibilidade (openrouter cohere), depois o opencode como último recurso.

### 4.2 Reconfigurar o modelo default

Hoje o default está errado (`default-minimax` aponta pra `opencode.ai/zen/go`, não pra `api.minimax.io/anthropic`). **Antes de qualquer fallback**, corrigir isso trocando para o provider correto do coding plan:

```diff
# ~/.zcode/cli/config.json (linha ~89)
- "model": "default-minimax/minimax-m3"
+ "model": "c997ca58-cfda-4c2f-8550-69830972bad7/minimax-m3"
```

**Pré-condição**: o usuário precisa confirmar que tem quota MiniMax IO ativa hoje. Se não tiver, **NÃO** fazer essa troca — manter `default-minimax/minimax-m3` (que está funcionando pelo log).

### 4.3 Estratégia de override em subagent custom

Baseado na evidência empírica:
- O campo `model` em `~/.zcode/subagents/*.json` **provavelmente é display label**, não identificador honrado.
- Mas o log mostrou subagents rodando em providers diferentes do parent — há desvio, mas inconclusivo.
- Decisão: **NÃO contar com override por config** para a primeira versão. Em vez disso, **roteamento fica na camada do agente principal** (que decide se vale despachar via `Agent` tool ou executar localmente).

### 4.4 Memória: 2 níveis

- **Global (`~/.zcode/memory/MEMORY.md`)**: lições duradouras sobre ZCode (ex: "default-minimax ≠ minimax-coding-plan", "free tiers têm rate limits agressivos").
- **Projeto (`.brain/memory/YYYY-MM-DD.md`)**: timeline do dia, atualizada incrementalmente.

## 5. Plano de implementação (alto nível — `writing-plans` detalha)

1. **Auditoria inicial** (sem mudar nada):
   - Listar providers ativos vs. enabled
   - Mapear 12 subagents custom → quais são realmente usados
   - Listar skills/plugins/MCPs ativos
   - Medir quota MiniMax IO restante (se houver API de entitlement)

2. **Reconfigurar default** (decisão §4.2): confirmar com usuário, editar `~/.zcode/cli/config.json`, validar via log.

3. **Criar skill `zcode-fallback`**:
   - `SKILL.md` (~150 linhas): ensina roteamento por criticidade
   - `references/provider-registry.md`: tabela providers/models/limits
   - `references/subagent-routing.md`: como (não) confiar em override

4. **Validar empíricamente** o override de model em 1 subagent (`redesim-helper-agent.json` é candidato — baixo risco):
   - Snapshot → editar → despachar → observar log → reverter
   - Documentar resultado em `MEMORY.md`

5. **Atualizar memórias**:
   - `~/.zcode/memory/MEMORY.md`: lições aprendidas
   - `.brain/memory/2026-06-25.md`: timeline desta sessão
   - Index consolidado em `.brain/index.md` se útil

6. **Mapa de skills aplicáveis ao Cartorio** (item do pedido "USE E ATIVE TODAS SKILLS..."):
   - Listar as 33 skills top-level + 14 do plugin superpowers + 2 de document-skills
   - Marcar quais são aplicáveis AGORA ao trabalho do usuário (não ao projeto Cartorio)
   - Resultado: tabela em `.brain/docs/skills-applicability-2026-06-25.md`

7. **Auditoria + otimização da config**:
   - Remover providers enabled que o usuário não usa (se houver)
   - Padronizar campo `model` nos 12 subagents JSONs (escolher 1 string consistente por enquanto — `kimi-k2.6` parece ser a maioria)
   - Validar `~/.zcode/v2/credentials.json` (criptografado ok, mas ver tamanho)

## 6. Riscos e mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| Override de model em subagent não funciona e agente gasta quota à toa | Alta | Médio | **Não usar** override nesta primeira versão; documentar como "experimental" |
| Trocar default para `c997ca58-.../minimax-m3` quebra a sessão (sem quota) | Média | Alto | **Confirmar quota com usuário antes**; ter rollback pronto |
| Rate limits dos free tiers (groq 30/min, openrouter 20/min) bloqueiam tarefas | Alta | Médio | Modo B é só para tarefas leves; ter timeout/backoff na skill |
| Patch em `~/.zcode/cli/config.json` durante sessão ativa corrompe config | Baixa | Alto | Editar só com app fechado, ou usar GUI; fazer backup antes |
| Memória `.brain/` cresce sem controle | Média | Baixo | Política: 1 arquivo por dia; índice consolidado quinzenal |

## 7. Critérios de aceitação

1. `~/.zcode/cli/config.json` tem o provider correto do coding plan selecionado (ou decisão consciente de manter o errado, documentada).
2. Skill `zcode-fallback` existe em `~/.zcode/skills/zcode-fallback/SKILL.md`, ≤ 200 linhas, com referências linkadas.
3. `~/.zcode/memory/MEMORY.md` tem ≥ 3 entradas de lições aprendidas.
4. `.brain/docs/skills-applicability-2026-06-25.md` lista as ~49 skills com flag "aplicável agora / não aplicável / adiar".
5. **Nenhuma quebra**: a sessão ZCode atual continua funcional após a reconfiguração.
6. Teste controlado de override de subagent documentado (mesmo que resultado seja "não funciona").

## 8. Testes

| Teste | Procedimento | Sucesso |
|---|---|---|
| Reconfigurar default preserva funcionalidade | Trocar `model`, observar log da próxima chamada | Sessão pai continua respondendo; subagents herdam |
| Skill `zcode-fallback` carrega | Iniciar nova sessão, skill aparece na lista | Skill é listada e invocável |
| Override de model em subagent | Procedimento §5 do relatório de exploração | Log mostra `providerId` ≠ parent (sucesso) ou igual (registrado como "display-only") |
| Memória global persiste cross-session | Encerrar app, abrir nova sessão, ler `MEMORY.md` | Conteúdo preservado |

## 9. Itens adiados (fora deste spec)

- Migração automática entre providers com base em quota MiniMax (requer API de entitlement e scripting).
- Skill dedicada de "auditoria Cartorio" (próximo sub-projeto depois deste).
- Patch no app.asar para adicionar fallback chain nativo (intencionalmente fora de escopo).
- Tradução de skills em PT-BR (vários C-Levels já são PT; revisar depois).

## 10. Aprovação

Aguardando OK do usuário para prosseguir para `writing-plans` → execução.

**Última coisa a confirmar**: o usuário tem quota MiniMax IO ativa hoje? Se sim, troco o default para `c997ca58-cfda-4c2f-8550-69830972bad7/minimax-m3`. Se não, mantenho `default-minimax/minimax-m3` e documento.
