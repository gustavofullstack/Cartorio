# Skills Applicability Map — 2026-06-25

> Decisão por skill: **A** = aplicável agora (uso imediato nesta sessão/projeto), **N** = não aplicável, **D** = adiar (próximo sub-projeto).

**Total catalogado**: 53 skills (33 top-level + 20 em plugins oficiais).
**Skills novas nesta sessão**: 1 (`zcode-fallback`, criada na Fase 2).

## Skills top-level (34 entradas, 1 nova)

### C-levels (UP Tecnologia) — Estratégia corporativa no Cartorio
| Skill | Flag | Justificativa |
|---|---|---|
| `cfo-agent` | **D** | Próximo sprint (modelagem financeira Cartorio) |
| `chro-agent` | **D** | Próximo sprint (RH/escala) |
| `cio-agent` | **D** | Próximo sprint (TI) |
| `cmo-agent` | **D** | Próximo sprint (marketing) |
| `coo-agent` | **D** | Próximo sprint (operações) |
| `cpo-agent` | **D** | Próximo sprint (produto) |
| `cro-agent` | **D** | Próximo sprint (receita) |
| `cso-agent` | **D** | Próximo sprint (vendas) |
| `cto-agent` | **D** | Próximo sprint (arquitetura) |
| `ceo-agent` (provavelmente 9º C-level) | **D** | Idem |
| `up-agent-corporation` | **D** | Orquestrador C-level — próximo sprint |

### Workflow (superpowers) — Em uso nesta sessão
| Skill | Flag | Justificativa |
|---|---|---|
| `brainstorming` | **A** | Em uso |
| `writing-plans` | **A** | Em uso |
| `subagent-driven-development` | **A** | Em uso |
| `executing-plans` | **A** | Em uso |
| `dispatching-parallel-agents` | **A** | Em uso |
| `verification-before-completion` | **A** | Em uso |
| `systematic-debugging` | **A** | Quando bater bug |
| `test-driven-development` | **N** | ZCode é config JSON, não código |
| `using-superpowers` | **A** | Em uso (meta-skill) |
| `using-git-worktrees` | **N** | Trabalho em master direto |
| `finishing-a-development-branch` | **N** | Não estamos finalizando branch |
| `requesting-code-review` | **N** | Sem reviewer externo |
| `receiving-code-review` | **N** | Sem reviewer externo |

### Cartorio-específicas (customizadas) — Quando mexer no Cartorio
| Skill | Flag | Justificativa |
|---|---|---|
| `prompt-cartorio` | **A** | Contexto Cartorio — usar quando relevante |
| `redesim-helper` | **A** | Útil p/ tarefas Redesim |
| `browser-automation` | **A** | MCP Chrome — usar quando precisar |
| `frontend-design` | **D** | Quando mexer em UI |
| `zcode-fallback` (**nova**) | **A** | Routing de providers — em uso nesta sessão |

### MCP/Memória cross-session
| Skill | Flag | Justificativa |
|---|---|---|
| `using-mavis-cross-session` | **A** | Memória cross-session |
| `para-memory-files` | **A** | Formato `.brain/` |

### Skills de outros runtimes (origem: symlinks)
| Skill | Origem | Flag | Justificativa |
|---|---|---|---|
| `algorithmic-art` | opencode | **N** | Não relacionado |
| `brand-guidelines` | opencode | **N** | Não relacionado |
| `diagnose-why-work-stopped` | claude | **N** | Não relacionado |
| `imagegen` | codex | **N** | Não relacionado |
| `kimi-webbridge` | claude | **N** | Kimi específico |
| `migrate-to-codex` | codex | **N** | Codex específico |
| `openai-docs` | codex | **N** | OpenAI docs |
| `paperclip` (5 variantes) | claude | **N** | Paperclip específico |
| `plugin-creator` | codex | **D** | Quando criar plugin |
| `skill-creator` | codex | **A** | Usamos para criar `zcode-fallback` |
| `skill-installer` | codex | **N** | Sem necessidade |
| `terminal-bench-loop` | claude | **N** | Benchmarking |

## Skills em plugins oficiais (20)

### Superpowers (15) — majoritariamente já listadas acima
Já marcadas em "Workflow (superpowers)" (13) + 2 adicionais:
| Skill | Flag | Justificativa |
|---|---|---|
| `writing-skills` | **A** | Criação de skill em uso |

### Android/iOS dev (2) — Quando mexer em mobile
| Skill | Flag | Justificativa |
|---|---|---|
| `android-dev` (android-emulator plugin) | **A** | MCP `mcp__android-emulator__*` já disponível |
| `ios-dev` (ios-simulator plugin) | **A** | MCP `mcp__ios-simulator__*` já disponível |

### Document skills (2) — Quando precisar de docx/pdf
| Skill | Flag | Justificativa |
|---|---|---|
| `pdf` (document-skills plugin) | **D** | Plugin desabilitado — habilitar se precisar |
| `docx` (document-skills plugin) | **D** | Plugin desabilitado — habilitar se precisar |

### Outros (2)
| Skill | Flag | Justificativa |
|---|---|---|
| `restore-legacy-sessions` (plugin enabled) | **N** | Recuperação — não precisamos |
| `skill-creator` (plugin enabled) | **A** | Já temos via top-level |

## MCP servers (4)

| MCP | Flag | Uso |
|---|---|---|
| `mcp__android-emulator__*` | **A** | Já disponível (skill `android-dev`) |
| `mcp__ios-simulator__*` | **A** | Já disponível (skill `ios-dev`) |
| `chrome-bridge` (user-level) | **A** | Skill `browser-automation` |
| `udiapods-api` (user-level) | **D** | Específico do UdiaPods |

## Resumo

| Flag | Top-level | Plugins | Total |
|---|---|---|---|
| **A** (aplicável agora) | 11 | 4 | **15** |
| **D** (adiar) | 12 | 3 | **15** |
| **N** (não aplicável) | 11 | 12 | **23** |
| **TOTAL** | **34** | **19** | **53** |

(Aplicáveis agora: 15. Adiar: 15. Não aplicáveis: 23.)

## Recomendações

1. **Habilitar plugin `document-skills`** se for gerar PDF/docx.
2. **Considerar desabilitar skills não aplicáveis** para reduzir ruído (não urgente).
3. **Próximo sub-projeto natural** (D): orquestração C-level dos 9 agentes no Cartorio via `up-agent-corporation`.