# Skills Smoke — G7.15.T2 / T3 / T4

**Data**: 2026-07-17  
**Tasks**: G7.15.T2 (smoke core), G7.15.T3 (placeholders), G7.15.T4 (SKILLS-MAP sync)  
**Executor**: cartorio-dev (Wave 25 slot A2)  
**Fonte**: `.agents/skills/*/SKILL.md` + `.agents/skills/INDEX.md`  
**Runner**: `python3 scripts/skills_smoke.py` (exit 0 = PASS)

---

## Critérios do smoke (por skill)

| Check | Passa se |
|-------|----------|
| **path exists** | `.agents/skills/<name>/` é diretório |
| **SKILL.md non-empty** | arquivo existe e `size > 0` (gate prático: ≥ 200 bytes) |
| **first-line purpose** | 1º `#` H1 do body OU 1ª linha da `description:` no frontmatter YAML |
| **placeholder detection** | frontmatter **sem** match de `TODO` / `FIXME` / `placeholder` / `coming soon` / `lorem ipsum` / `dummy skill` / `not implemented` / `\bTBD\b` (exceto falso-positivo PT **TODOS**) |

---

## Core skills (obrigatórias no smoke)

| Skill | Path | Exists | SKILL.md | Bytes | Lines | First-line purpose | Placeholder? | Verdict |
|-------|------|--------|----------|------:|------:|--------------------|--------------|---------|
| `api` | `.agents/skills/api/` | ✅ | ✅ | 4252 | 123 | Skill para interagir com a API FastAPI do Cartório via REST, WebSocket e MCP. / H1: *API Backend Central — Skill de Integração* | ❌ none | **PASS** |
| `chatwoot` | `.agents/skills/chatwoot/` | ✅ | ✅ | 4354 | 157 | Skill para interagir com o Chatwoot CRM via API REST e MCP. / H1: *Chatwoot CRM — Skill de Integração* | ❌ none | **PASS** |
| `n8n` | `.agents/skills/n8n/` | ✅ | ✅ | 15387 | 342 | Skill para interagir com N8N Workflow Engine via API REST e MCP. / H1: *N8N Workflow Engine — Skill de Integração (v2 / 2026-06-30)* | ❌ none | **PASS** |
| `supabase` | `.agents/skills/supabase/` | ✅ | ✅ | 5752 | 188 | Skill para interagir com Supabase auto-hospedado via REST, Auth, Storage, Realtime e Edge Functions. / H1: *Supabase — Skill de Integração Completa* | ❌ none | **PASS** |
| `easypanel` | `.agents/skills/easypanel/` | ✅ | ✅ | 4001 | 135 | Skill para interagir com Easypanel via API REST — deploy, gerenciamento de serviços… / H1: *Easypanel — Skill de Deploy e Gerenciamento* | ❌ none | **PASS** |
| `hostinger` | `.agents/skills/hostinger/` | ✅ | ✅ | 4314 | 160 | Skill para gerenciar a VPS Hostinger via SSH, Tailscale e API. / H1: *Hostinger VPS — Skill de Acesso e Gerenciamento* | ❌ none | **PASS** |

**Core summary**: **6/6 PASS**

---

## Skills adicionais (inventário real, não gate do exit code)

| Skill | Path | Exists | SKILL.md | Bytes | First-line purpose | Placeholder? | Notes |
|-------|------|--------|----------|------:|--------------------|--------------|-------|
| `minimax-m3` | `.agents/skills/minimax-m3/` | ✅ | ✅ | 6141 | MiniMax-M3 XMax Thinking via LiteLLM | ❌ | LLM provider |
| `coding-vps-21` | `.agents/skills/coding-vps-21/` | ✅ | ✅ | 7142 | Ativar 21+ coding agents MiniMax-M3 | ❌ | + relatórios de sessão |
| `coding-vps-tools-100` | `.agents/skills/coding-vps-tools-100/` | ✅ | ✅ | 7232 | Catálogo REAL toolkit (62 tools CLI) | ❌ | nome histórico “100” |
| `coding-vps-orchestrator` | `.agents/skills/coding-vps-orchestrator/` | ✅ | ✅ | 4371 | MCP orchestrator CLI/HTTP/stdio | ❌ | |
| `coding-vps-deploy` | `.agents/skills/coding-vps-deploy/` | ✅ | ✅ | 4348 | Deploy agents Docker no coding-vps | ❌ | |
| `coding-vps-monitor` | `.agents/skills/coding-vps-monitor/` | ✅ | ✅ | 5003 | Monitor health 89 serviços | ❌ | |

**Total skills com `SKILL.md`**: **12** (alinhado com `.agents/skills/INDEX.md`)

---

## G7.15.T3 — Placeholder descriptions

Varredura em **description frontmatter** de todas as 12 skills:

| Resultado | Detalhe |
|-----------|---------|
| Placeholders óbvios (`TODO` / `placeholder` / …) | **0** |
| Ações de reescrita em `SKILL.md` | **Nenhuma** — descriptions já são reais e usáveis |
| Falso-positivos evitados | palavra PT **“TODOS”** em n8n/hostinger/easypanel **não** conta |

**Conclusão T3**: não havia descriptions dummy a remover. Estado documentado aqui; skills core e extended estão com purpose real.

> **Nota de segurança (fora do escopo T3, mas observada no smoke)**: vários `SKILL.md` ainda embutem tokens/API keys literais (Chatwoot, Easypanel, MiniMax, etc.). Isso **não** é “placeholder description”; é secret-in-docs. Tratar em task separada de secrets scrub (não reescrito nesta wave).

---

## G7.15.T4 — SKILLS-MAP harness sync

| Artefato | Ação |
|----------|------|
| `.harness/loop-engineer/SKILLS-MAP.md` | Atualizado com inventário **real** de `.agents/skills/` + pointer ao smoke |
| `.agents/skills/INDEX.md` | Já listava as 12 skills (G7.15.T1) — sem mudança necessária nesta wave |
| `scripts/skills_smoke.py` | Runner opcional; exit 0 se core 6/6 |

---

## Como rodar

```bash
# da raiz do repo
python3 scripts/skills_smoke.py
python3 scripts/skills_smoke.py --json
python3 scripts/skills_smoke.py --all   # inclui skills extended no relatório (gate ainda é core)
```

Expected:

```text
Skills smoke G7.15 — PASS · core 6/6
```

---

## Veredito

| Task | Status |
|------|--------|
| G7.15.T2 smoke api/chatwoot/n8n/supabase (+ easypanel/hostinger) | ✅ **PASS 6/6** |
| G7.15.T3 remove placeholder descriptions | ✅ **N/A clean** (0 placeholders; documentado) |
| G7.15.T4 SKILLS-MAP harness sync | ✅ **DONE** (mapa + inventário real) |

**Modified by Gustavo Almeida — G7.15 Wave 25 (2026-07-17)**
