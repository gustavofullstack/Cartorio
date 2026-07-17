# OpenClaw Skills Registry + Agent-Tools Sync (G7.14.T2)

> **Wave 26 / A3** · `cartorio-dev` · 2026-07-17  
> Inventário canônico: configs JSON (OpenClaw / LobeChat) **vs** `.agents/skills` **vs** runtime cartorio skills.

## 1. Três camadas (não confundir)

| Camada | Path | Papel | Contagem (repo) |
|--------|------|-------|-----------------|
| **A. Platform skills** (coding agents / harness) | `.agents/skills/*/SKILL.md` | Skills para Claude/Codex/Mavis no repo | **12** |
| **B. CartorioBot runtime skills** | `infra/openclaw-agent/skills/cartorio-*.md` + `registry.json` | Skills carregadas no OpenClaw (`plugin-skills`) | **7** |
| **C. Agent tools registry** | `infra/openclaw-agent/agent-tools-registry.json` | Tools HTTP/MCP que o agent chama | **20** tools |
| **D. Agent config (spec)** | `infra/openclaw/cartorio-bot.openclaw.json` | Spec cartorio-bot (tools + hooks + skills abstratas) | 8 tools + 5 skills abstratas |
| **E. Gateway snapshot** | `infra/openclaw-agent/gateway-config-snapshot-t49.json` | Estado desejado `openclaw.json` (prod volume) | 7 skills allowlist |
| **F. LobeChat import** | `infra/lobechat/agent_cartorio_import.json` | Persona LobeChat (não registra skill folders) | 1 agent + provider OpenClaw |

**Regra:** A ≠ B. Platform skills (`.agents/skills`) **não** são auto-montadas no OpenClaw. Runtime skills (B) vivem em `infra/openclaw-agent/skills/` e no container em `/home/node/.openclaw/plugin-skills`.

---

## 2. Inventário A — `.agents/skills` (INDEX G7.15.T1)

| Skill folder | Categoria | Status | Uso OpenClaw runtime? |
|--------------|-----------|--------|------------------------|
| `api` | INTEGRATION | ✅ | Indireto (docs endpoints) |
| `chatwoot` | INTEGRATION | 🟡 | Indireto (handoff) |
| `n8n` | WORKFLOW | 🟡 | Indireto (WFs) |
| `supabase` | DATABASE | ✅ | Indireto |
| `easypanel` | INFRA | ✅ | Não |
| `hostinger` | INFRA | 🟡 | Não |
| `minimax-m3` | LLM | ✅ | Modelo/provider |
| `coding-vps-21` | AGENT | ✅ | Não (coding VPS) |
| `coding-vps-tools-100` | INFRA | ✅ | Não |
| `coding-vps-orchestrator` | AGENT | ✅ | Não |
| `coding-vps-deploy` | INFRA | ✅ | Não |
| `coding-vps-monitor` | MONITORING | ✅ | Não |

Fonte: [`.agents/skills/INDEX.md`](../.agents/skills/INDEX.md).

---

## 3. Inventário B — CartorioBot runtime skills

Fonte: `infra/openclaw-agent/skills/registry.json` + `INDEX.md`.

| Skill | Intent(s) | tools_used (registry) | pii_safe | MD file |
|-------|-----------|----------------------|----------|---------|
| `cartorio-saudacoes` | saudacao_inicial, retorno, primeira_vez | cartorio_api_health, opencode_go_chat | true | `cartorio-saudacoes.md` |
| `cartorio-protocolo-tracker` | consultar_protocolo, status, andamento | cartorio_api_protocolo_consultar, n8n:04 | false | `cartorio-protocolo-tracker.md` |
| `cartorio-emolumento-calc` | calcular_emolumento, quanto_custa | cartorio_api_emolumento_calcular, redis_* | true | `cartorio-emolumento-calc.md` |
| `cartorio-handoff-trigger` | atendente_humano, reclamacao_grave | chatwoot_*, n8n:03-handoff | false | `cartorio-handoff-trigger.md` |
| `cartorio-agendamento` | agendar, marcar, horario | cartorio_api_agendamento_*, n8n:05 | false | `cartorio-agendamento.md` |
| `cartorio-segunda-via` | segunda_via, copia | cartorio_api_protocolo_consultar, n8n:06 | false | `cartorio-segunda-via.md` |
| `cartorio-pesquisa-satisfacao` | feedback, nps | n8n:07, chatwoot_add_label | true | `cartorio-pesquisa-satisfacao.md` |

**Gateway allowlist** (`agents.defaults.skills` no snapshot T5.0/T5.1):

```
cartorio-saudacoes
cartorio-protocolo-tracker
cartorio-emolumento-calc
cartorio-handoff-trigger
cartorio-agendamento
cartorio-segunda-via
cartorio-pesquisa-satisfacao
```

`skills.load.extraDirs`: `["/home/node/.openclaw/plugin-skills"]`.

**Sync B ↔ gateway:** ✅ nomes idênticos (7/7).

---

## 4. Inventário C — agent-tools-registry (20 tools)

| # | Tool | Provider | pii_safe | Skills B que usam |
|---|------|----------|----------|-------------------|
| 1 | `cartorio_api_health` | api | true | saudacoes |
| 2 | `cartorio_api_emolumento_calcular` | api | true | emolumento-calc |
| 3 | `cartorio_api_protocolo_criar` | api | false | (spec D: criar_protocolo; não em tools_used skill MD) |
| 4 | `cartorio_api_protocolo_consultar` | api | false | protocolo-tracker, segunda-via |
| 5 | `cartorio_api_agendamento_disponibilidade` | api | true | agendamento |
| 6 | `cartorio_api_agendamento_criar` | api | false | agendamento |
| 7 | `n8n_workflow_trigger` | n8n | false | protocolo, handoff, agendamento, 2a via, NPS |
| 8 | `supabase_rest_query` | supabase | false | — (ops / MCP) |
| 9 | `supabase_graphql` | supabase | false | — |
| 10 | `supabase_realtime_subscribe` | supabase | false | — |
| 11 | `supabase_storage_upload` | supabase | false | — |
| 12 | `redis_cache_get` | redis | false | emolumento-calc |
| 13 | `redis_cache_set` | redis | false | emolumento-calc |
| 14 | `chatwoot_pausar_agente` | chatwoot | false | handoff-trigger |
| 15 | `chatwoot_canned_response` | chatwoot | true | — (hook canned) |
| 16 | `chatwoot_add_label` | chatwoot | true | handoff, NPS |
| 17 | `evolution_send_message` | evolution | false | — (canal WhatsApp) |
| 18 | `evolution_check_number` | evolution | false | — |
| 19 | `opencode_go_chat` | opencode_go | false | saudacoes (+ LLM path) |
| 20 | `openclaw_status` | openclaw | true | health |

**Metadata registry:** `total_tools=20`, `pii_safe_tools=7`, providers =
`api | n8n | supabase | redis | chatwoot | evolution | opencode_go | openclaw`.

---

## 5. Inventário D — `cartorio-bot.openclaw.json` (spec)

### Tools (nome lógico → path API)

| Spec tool | Method/path | HITL | LGPD | Map → C (agent-tools) | Map → B (skill) |
|-----------|-------------|------|------|------------------------|-----------------|
| `consultar_emolumento` | POST `/api/v1/emolumento/calcular` | no | no | `cartorio_api_emolumento_calcular` ⚠ method GET no C | emolumento-calc |
| `consultar_protocolo` | GET `/api/v1/protocolo/{numero}` | no | yes | `cartorio_api_protocolo_consultar` | protocolo-tracker |
| `criar_protocolo` | POST `/api/v1/protocolo` | **yes** | yes | `cartorio_api_protocolo_criar` | — (HITL; não skill MD dedicada) |
| `agendar_atendimento` | POST `/api/v1/agendamento` | yes | yes | `cartorio_api_agendamento_criar` | agendamento |
| `segunda_via` | POST `/api/v1/documento/segunda-via` | yes | yes | (não listado em C; via n8n:06) | segunda-via |
| `lgpd_direitos` | POST `/api/v1/lgpd/{direito}` | yes | yes | — **gap em C** | — |
| `audit_verify` | POST `/api/v1/audit/verify` | no | no | — **gap em C** (MCP tem) | — |
| `handoff_humano` | POST `/api/v1/integrations/chatwoot/handoff` | yes | yes | chatwoot_pausar_agente / n8n:03 | handoff-trigger |

### Skills abstratas (hooks, não = B)

| Spec skill | Papel | Runtime B / hooks |
|------------|-------|-------------------|
| `pii_scrubber` | PII pre/post LLM | hooks `on_message_in` / `on_response_out` |
| `lgpd_consent_checker` | consent antes tool | `on_tool_call` |
| `audit_logger` | audit append | `on_message_in` |
| `canned_response_matcher` | templates Chatwoot | tool `chatwoot_canned_response` |
| `hitl_router` | DRAFT / handoff | handoff-trigger + HITL tools |

### MCPs declarados

`cartorio_mcp_api` · `cartorio_mcp_supabase` · `cartorio_mcp_chatwoot`

---

## 6. Inventário F — LobeChat

`infra/lobechat/agent_cartorio_import.json`:

- Agent id: `agent-cartorio-2notas-uberlandia`
- Provider: `openai-compatible-custom-openclaw` → `https://agent.2notasudi.com.br/v1`
- Skills citadas no systemRole (texto, não registry): saudacoes, protocolo-tracker, emolumento-calc, agendamento, segunda-via, pesquisa-satisfacao, handoff-trigger (**7/7 = B**)
- `meta.sourcePersonaFiles` aponta **7** skills MD (alinhado Wave26)

---

## 7. Matriz de sync / gaps (G7.14.T2)

| Par | Status | Notas |
|-----|--------|-------|
| B registry ↔ B MD files | ✅ | 7 MD + 7 registry entries |
| B ↔ E gateway allowlist | ✅ | mesmos 7 nomes |
| B ↔ F LobeChat systemRole | ✅ | 7 nomes |
| B ↔ F sourcePersonaFiles | ✅ | 7/7 skills MD (Wave26 sync) |
| C tools ↔ B tools_used | ✅ parcial | todas tools_used de B existem em C |
| D tools ↔ C tools | 🟡 | nomes diferentes; `lgpd_direitos` e `audit_verify` ausentes em C; `segunda_via` só via n8n |
| D skills abstratas ↔ B | N/A by design | hooks vs intent skills |
| A `.agents/skills` ↔ B | N/A by design | camadas distintas; INDEX já documenta |
| C `updated_at` | ✅ | `2026-07-17` + `metadata.skills_registry_sync` |
| B registry `updated_at` | ✅ | `2026-07-17` + cross-ref agent-tools |

### Gaps recomendados (não bloqueiam Wave 26 doc)

1. **Adicionar a C:** `cartorio_api_lgpd_direito`, `cartorio_api_audit_verify`, `cartorio_api_documento_segunda_via` (alinhar D).
2. **Normalizar method** emolumento: D diz POST, C/API real GET — preferir GET (código backend).
3. **Não** copiar `.agents/skills/coding-vps-*` para OpenClaw plugin-skills.

---

## 8. Mapa de intenção → skill → tool (runtime)

```
msg in
  → pii_scrubber (D hook)
  → intent detect
      saudacao     → cartorio-saudacoes      → health + LLM
      emolumento   → cartorio-emolumento-calc → API calcular (+ redis)
      protocolo    → cartorio-protocolo-tracker → API consultar
      agendar      → cartorio-agendamento     → disponibilidade + criar
      2a via       → cartorio-segunda-via     → n8n 06 / doc API
      humano/PII   → cartorio-handoff-trigger → chatwoot + n8n 03
      nps          → cartorio-pesquisa-satisfacao → n8n 07
  → lgpd_consent_checker se tool pii_safe=false
  → audit_logger
  → output_scrub
```

---

## 9. Como revalidar (sem SSH)

```bash
# Runtime skills no repo
ls infra/openclaw-agent/skills/cartorio-*.md | wc -l   # expect 7

# Registry JSON
python3 -c "import json; d=json.load(open('infra/openclaw-agent/skills/registry.json')); print(len(d['skills']), [s['name'] for s in d['skills']])"

# Tools
python3 -c "import json; d=json.load(open('infra/openclaw-agent/agent-tools-registry.json')); print(d['metadata']['total_tools'], len(d['tools']))"

# Platform skills
ls -d .agents/skills/*/ | wc -l   # expect 12

# Gateway allowlist
python3 -c "import json; d=json.load(open('infra/openclaw-agent/gateway-config-snapshot-t49.json')); print(d['agents']['defaults']['skills'])"
```

Deploy prod (SUI): skills no volume `plugin-skills` + `openclaw config get agents.defaults.skills`.

---

## 10. Refs

| Artefato | Path |
|----------|------|
| Skills INDEX platform | `.agents/skills/INDEX.md` |
| Skills INDEX bot | `infra/openclaw-agent/skills/INDEX.md` |
| Registry skills | `infra/openclaw-agent/skills/registry.json` |
| Registry tools | `infra/openclaw-agent/agent-tools-registry.json` |
| Spec bot | `infra/openclaw/cartorio-bot.openclaw.json` |
| Gateway snapshot | `infra/openclaw-agent/gateway-config-snapshot-t49.json` |
| LobeChat | `infra/lobechat/agent_cartorio_import.json` |
| Context guards | `docs/OPENCLAW_CONTEXT_GUARDS_G7.md` |
| Lesson 170 | `.harness/memory/lesson-170-lobechat-agent-fix-2026-07-14.md` |

---

**Task:** G7.14.T2 · **Status doc:** DONE (inventário + gaps; sem deploy VPS)  
**Modified by Gustavo Almeida — Wave 26 A3 (cartorio-dev)**
