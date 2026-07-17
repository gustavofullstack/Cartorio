# Coding-VPS orchestrator tools validate — G7.09.T4

**Owner:** `cartorio-dev` (offline gate) / ops com Tailscale (live SSH)  
**Orchestrator:** `scripts/coding_vps_mcp_orchestrator.py`  
**Skill (catálogo real):** `.agents/skills/coding-vps-tools-100/SKILL.md`  
**Smoke shell:** `scripts/validate_coding_vps_tools_60.sh`  
**Inventory unificado:** `scripts/mcp_tools_inventory.py`

> **Nome histórico “tools-100”:** marketing antigo. Catálogo pós Squad 10 + aliases Squad 5 = **≥ 62 tools** registradas no CLI `list`.  
> **Não confiar** em claims “100/92/85 tools” sem rodar o inventário.

---

## 1. O que é “62 tools”

| Métrica | Valor | Como obter |
|---------|-------|------------|
| Tools no registry `TOOLS` | **≥ 62** (snapshot local pode ser 63 se `ep_destroy_service` etc. entraram) | `python3 scripts/coding_vps_mcp_orchestrator.py list` |
| Categorias | ~13 | saída do `list` / inventory |
| Serviços Swarm no VPS | dezenas (up/down separado) | `call list_services` / `health_check_all` — **precisa SSH** |
| Smoke gate | `EXPECTED_MIN_TOOLS=62` | `validate_coding_vps_tools_60.sh` |

**Regra:** floor `>= 62`, não igualdade rígida — aliases novos sobem o count; dedupe pode baixar (não deixar cair do floor sem ADR).

Breakdown canônico (skill):

| Categoria | Exemplos |
|-----------|----------|
| LLM | `chat_minimax`, `chat_with_agent`, `list_models` |
| STATUS | `list_services`, `health_check_all`, `docker_stats`, … |
| DOCKER | `service_logs`, `restart_service`, `scale_service`, … |
| EASYPANEL | `ep_login`, `ep_list_*`, `ep_deploy`, … |
| DB | `postgres_*`, `redis_cmd`, `redis_ping`, … |
| WORKFLOW / CODE-REVIEW / WEBSOCKET / WEBHOOK / RAG / DEV / NETWORKING / UTILITY | ver skill |

Squad 5 aliases críticos: **`redis_ping`**, **`health_check_all`** (função ≠ tool registrada — validar no `list`).

---

## 2. Validação **offline** (sem VPS / sem SSH)

Tudo abaixo roda no laptop, **sem** Tailscale e **sem** secrets de produção.

### 2.1 Inventory unificado

```bash
python3 scripts/mcp_tools_inventory.py
python3 scripts/mcp_tools_inventory.py --min-coding-vps 62 --json | head -c 2500
```

- Importa o orchestrator (só registra `TOOLS` no import — não chama `main()`)
- Fallback AST se import falhar
- Gate: `coding_vps.count >= 62`

### 2.2 CLI `list` (canônico)

```bash
python3 scripts/coding_vps_mcp_orchestrator.py list
# primeira linha: "MCP orchestrator: N tools in C categories"
```

### 2.3 Smoke script `--quick`

```bash
bash scripts/validate_coding_vps_tools_60.sh --quick
```

O que o `--quick` cobre:

| Step | O que valida | Rede? |
|------|--------------|-------|
| `[1/6] list` | count ≥ `EXPECTED_MIN_TOOLS` (default 62) | não |
| `[2/6] required names` | `chat_minimax`, `chat_with_agent`, `list_models`, `list_services`, `health_check_*`, `redis_*`, `openapi_spec`, `service_logs`, `restart_service` | não |
| `[3/6] openapi_spec` | `call openapi_spec` retorna JSON com `"openapi"` | não |
| SSH steps | **skipped** | — |

Exit `0` = offline gate PASS.

### 2.4 `openapi_spec` isolado

```bash
python3 scripts/coding_vps_mcp_orchestrator.py call openapi_spec
# {"openapi": "3.1.0", "tools": <N>}
```

---

## 3. Validação **live** (opcional — precisa Tailscale + SSH)

**Pré-requisitos (não commitar chaves):**

| Var | Uso | Default típico |
|-----|-----|----------------|
| `SSH_PRIVATE_KEY` | key file | `~/.ssh/id_ed25519_cartorio` |
| `SSH_TAILSCALE_HOST` | host mesh | (ver skill / ops; **não** colar secrets) |
| `LITELLM_API_KEY` | só para `--with-llm` | env local |

```bash
# Full smoke (list + openapi + list_services + health_check_all + redis_ping best-effort)
bash scripts/validate_coding_vps_tools_60.sh

# + chat_minimax (lento / depends LiteLLM)
bash scripts/validate_coding_vps_tools_60.sh --with-llm

# E2E agents (script separado)
bash scripts/validate_coding_vps_e2e.sh
```

Se offline: **não** falhar o G7.09.T4 por SSH down — documentar `SKIP` e manter `--quick` verde.

---

## 4. MCP stdio (clients TRAE / Antigravity / Claude / Cursor)

```bash
# Server canônico (stdio)
python3 scripts/coding_vps_mcp_orchestrator.py mcp

# Install configs locais (paths only — sem secrets no git)
bash scripts/install_mcp_clients.sh status
bash scripts/install_mcp_clients.sh install
```

Integração JSON: `docs/platforms/coding-vps/INTEGRATION_TRAE_ANTIGRAVITY.md`.

---

## 5. Critérios de aceite (DoD G7.09.T4)

| # | Critério | Offline | Live |
|---|----------|---------|------|
| 1 | Registry ≥ 62 tools | `list` / inventory / `--quick` | idem |
| 2 | Required tool names presentes | `--quick` step 2 | — |
| 3 | `openapi_spec` callable | `--quick` step 3 | — |
| 4 | Doc + skill alinhados (não “100 tools” fake) | este arquivo + skill | — |
| 5 | SSH tools validados **se** mesh up | N/A | full script |
| 6 | Sem secrets no doc/commit | review | — |

---

## 6. Snapshot de execução (Wave 26 — offline)

Rodado em ambiente de desenvolvimento (sem SSH):

```text
bash scripts/validate_coding_vps_tools_60.sh --quick
== coding-vps tools smoke (min tools=62) ==
[1/6] list (tool count)     OK  list count=63 (>=62)
[2/6] required tool names   OK  (11/11)
[3/6] call openapi_spec     OK
[--quick] skipping SSH-backed tools
pass=13 fail=0 skip=3
ALL CHECKS PASSED
```

> Count **63** ≥ 62: Easypanel inclui `ep_destroy_service` além do breakdown “4 tools” do skill — skill descreve o core; o gate usa floor.

Re-gerar a qualquer momento:

```bash
python3 scripts/mcp_tools_inventory.py
bash scripts/validate_coding_vps_tools_60.sh --quick
```

---

## 7. Lições (skill + harness)

1. **Tool count no marketing ≠ tools que funcionam** — validação antiga ~42% OK em 100 stubs.
2. **Função Python ≠ tool registrada** — `redis_ping` existia e sumia do `list` até Squad 5.
3. **Secrets fora do git** — configs MCP versionadas só com paths; keys em env.
4. **Não re-inflar** o catálogo com wrappers per-agent; preferir `chat_with_agent`, `redis_cmd`, `service_http_*`, `exec_in_container`.

---

## 8. Referências

| Doc / path | Conteúdo |
|------------|----------|
| `.agents/skills/coding-vps-tools-100/SKILL.md` | catálogo real 62+ |
| `docs/platforms/coding-vps/INTEGRATION_TRAE_ANTIGRAVITY.md` | clients |
| `docs/platforms/coding-vps/TOOLS_E2E_REPORT_2026-07-08.md` | E2E histórico |
| `docs/reports/coding_vps_validation_2026-07-08.md` | validação 100-era (legado) |
| `docs/MCP_MOUNT_SMOKE_G7.md` | cartorio `/mcp` (G7.09.T3) |
| `scripts/MCP_USAGE.md` | protocolo MCP |

---

**Modified by Gustavo Almeida — cartorio-dev Wave 26 (G7.09.T4)**
