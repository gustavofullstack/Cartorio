# 🦾 PLAN-SUPREMO-2026-07-01 — Super Plano de Melhoria Global

> **Goal master:** Unificar, documentar e otimizar todo o ecossistema MacBook Pro + projetos anexos sem reiniciar/apagar/mover nada.
> **Modo:** `MELHORIA NÃO-AGRESSIVA` (read-only + aditivo).
> **Iniciado:** 2026-07-01.
> **Destino:** `~/projetos/CLAUDE-CODE-SUPREMO/` (hub) + `.brain/` (tracking) + `~/.claude/memory/` (lesson cross-session).
> **Público:** Claude Code (extensão VSCode / Antigravity fork) — MiniMax-M3 [1M] coding-plan via `https://api.minimax.io/anthropic`.

---

## 🎯 Goal Master (G6)

```
"Estabelecer CLAUDE-CODE-SUPREMO como hub unificador read-only do ecossistema,
com auditoria de 11 plataformas, 45 skills, 6 MCPs, 19 containers swarm,
memória cross-session estruturada, e plano de melhoria contínua incremental —
SEM reiniciar/apagar/mover nada."
```

**Critérios de sucesso (pass = 8):**
1. ✅ Hub `CLAUDE-CODE-SUPREMO/` criado com SUPRAMAP + INDEX + ECOSYSTEM-AUDIT
2. ✅ Memory cross-session atualizada (Lesson 119)
3. ✅ Skill `cartorio` continua 100% funcional
4. ✅ Todos os 19 containers swarm seguem UP
5. ✅ Settings.json (`~/.claude/settings.json`) intacto (verificado por mtime)
6. ✅ Nenhum processo killed, nenhuma sessão encerrada
7. ✅ Pelo menos 1 plano de melhoria contínua registrado no `.brain/plans/`
8. ✅ Pelo menos 8 tasks estruturadas no `.brain/tasks/`

---

## 🪜 Milestones

### M6.1 — Auditoria & Indexação (DONE)
**Foco:** descobrir tudo, indexar, sem tocar.
- ✅ T6.1.1 — Auditoria read-only de 11 ecossistemas (Claude/Codex/Hermes/Antigravity/OpenCode/OpenChamber/OpenClaw/Paperclip/Zed/Cartório/Kilo+Cmux+Cline+Goose)
- ✅ T6.1.2 — Criar `~/projetos/CLAUDE-CODE-SUPREMO/` (9 .md files, 48 KB)
- ✅ T6.1.3 — SUPRAMAP.md + ECOSYSTEM-AUDIT-2026-07-01.md
- ✅ T6.1.4 — Skills cross-ecosystem mapeados (Claude 45 / Codex 39 / Hermes 99 / OpenCode 14)
- ✅ T6.1.5 — MCP inventory (cartorio-api / n8n / openclaw / easypanel / seq-thinking / supabase)

### M6.2 — Memory cross-session (DONE)
- ✅ T6.2.1 — Lesson 119 gravada em `~/.claude/projects/-.../memory/lesson-119-claude-code-supremo.md`
- ✅ T6.2.2 — MEMORY.md index atualizado (16 lições, era 15)
- ⚪ T6.2.3 — Cross-link com `.harness/memory/MEMORY.md` (Cartório internal) — próxima sprint

### M6.3 — Cartório Sprint 47 (ongoing — preservar)
- ✅ Telegram produção 100% E2E
- ⚪ SUI1 (DNS chatwoot) — ação do Gustavo
- ⚪ SUI2 (WhatsApp QR scan) — ação do Gustavo
- ⚪ SUI3 (DNS n8n+supabase) — ação do Gustavo

### M6.4 — Plataformas paralelas (mapping done; integração next)
- ⚪ TriqHub — classificar e mapear
- ⚪ Udiapods — classificar (já há skills `udiapods-*` no Claude Code)
- ⚪ Bank-app — classificar
- ⚪ Finance-hub-os — classificar e ligar com `~/.finance-hub/`
- ⚪ Hate-of-miss — classificar
- ⚪ Zcode project — classificar
- ⚪ Paperclip workspace — integrado via `~/paperclip-temp/`

### M6.5 — Otimização contínua (oportunidades)
- ⚪ T6.5.1 — Archival de `~/.codex/logs_2.sqlite` (665 MB) → `~/.codex/archive/`
- ⚪ T6.5.2 — Archival de `~/.hermes/state.db` (81 MB) → snapshot
- ⚪ T6.5.3 — Verificar MCPs `easypanel` e `supabase` (currently needs_config)
- ⚪ T6.5.4 — Settings.json cleanup: 3 backups datados (deepseek, orquestrador) consolidar ou remover
- ⚪ T6.5.5 — Tailscale: 2 nós offline (iphone-andre, macbook-air-henrique) — não crítico

### M6.6 — Context window & ultra thinking (config)
- ✅ Context 1M ativo (validado Lesson 116)
- ⚪ T6.6.1 — Configurar `compaction: 75-80%` no settings.json (read-only proposal) — Gustavo decide
- ⚪ T6.6.2 — Habilitar `sequential-thinking` MCP como primário para reasoning chains
- ⚪ T6.6.3 — Habilitar `inference-sh` skill como helper de LiteLLM/proxy
- ⚪ T6.6.4 — Habilitar `yuanbao` + `kimi-webbridge` se não conflitar com MiniMax

### M6.7 — Cross-ecosystem integrations (futuro)
- ⚪ T6.7.1 — Bridge Hermes ↔ Claude Code sessions
- ⚪ T6.7.2 — Bridge Codex ↔ OpenCode (skill sync)
- ⚪ T6.7.3 — Bridge Antigravity (VSCode fork) ↔ Claude Code ext
- ⚪ T6.7.4 — Bridge Paperclip-board ↔ Scrum-board → um único kanban

### M6.8 — Próxima iteração (sprint planning)
- ⚪ T6.8.1 — Implementar Squad A pendentes (A13-A25) — 13 tasks API/DB hardening
- ⚪ T6.8.2 — Implementar LGPD D19-D25 — direitos do titular
- ⚪ T6.8.3 — Resolver Render key (regra `no_key_rotation`) — ação do Gustavo
- ⚪ T6.8.4 — Investigar pgweb 0/1 flapping (Lesson 119 follow)

---

## 🔒 CLÁUSULAS DE PROTEÇÃO (imutáveis)

```yaml
proibido:
  - reiniciar qualquer container, daemon ou serviço
  - deletar QUALQUER arquivo fora de ~/projetos/CLAUDE-CODE-SUPREMO/ e .brain/
  - commitar sem aprovação explícita do Gustavo
  - editar ~/.claude/settings.json (settings.local.json é OK)
  - matar QUALQUER processo
  - mover QUALQUER arquivo entre ecossistemas
permitido:
  - criar novos .md/.txt/.json em ~/projetos/CLAUDE-CODE-SUPREMO/, .brain/, ~/.claude/projects/-.../memory/
  - ler todos os arquivos (read-only)
  - curl em domínios externos
  - ssh para vps-cartorio (100.99.172.84) em modo batch read-only
```

---

## 📊 Velocity tracking

| Dia | Tasks done | Tasks added | Velocity |
|---|---|---|---|
| 2026-07-01 turn 50 | 13 (Goal 6.1-6.2) | 30 (Goal 6.3-6.8) | bootstrap |

---

Modified by Claude — 2026-07-01 — `MELHORIA NÃO-AGRESSIVA`.
