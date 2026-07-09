# Session 2026-07-09 — Coding-VPS optimize + validate (NÃO Cartório)

**Foco:** `coding-vps_apenas_para_auxilio` only. Cartório production **não tocado**.  
**Squads:** 5 em paralelo (inventory / tools E2E / optimize / security / TRAE integration).

## Resultado executivo

| Item | Antes | Depois |
|------|-------|--------|
| RAM used | ~8.9–9.0 Gi | **~4.1–4.7 Gi** (−4+ Gi) |
| Swap | 3.6/4 Gi critical | **~2.9/4 Gi** (reclaiming) |
| Side-stack agents | 9× 1/1 duplicados | **removidos** |
| Heavy non-core | sourcegraph, sonarqube, notebooks, mirotalk… | **scale 0** |
| MCP tools (honest) | claim 100 / real ~60 | **62 tools** (dedupe + aliases) |
| Services up (coding-vps) | ~51/89 flapping | **~26/80 lean core** |
| MiniMax-M3 | OK via LiteLLM | **OK** (`chat_minimax` PING) |
| 9 coding agents `/chat` | falso fail (curl missing) | **fixed** `chat_with_agent` → python3 |

## O que foi otimizado (pior vs melhor)

| Removido / scaled 0 | Motivo (pior / redundante) | Mantido (melhor) |
|---------------------|----------------------------|------------------|
| `coding-vps-agents_*` ×9 | Duplicata dos agents MiniMax do main | main `…_apenas_para_auxilio_*` |
| sourcegraph (~1.3 Gi) | Code search pesado, pouco uso agent | zincsearch (leve) |
| sonarqube + db (~1.3 Gi) | Quality UI offline ok | re-scale se sprint de review |
| open-notebook + surreal | Research UI não core | anything-llm + langflow |
| mirotalk / chartdb | Video / schema viz não agentic | centrifugo WS |
| temporal-admin-tools | CLI só | temporal core já 0/0 se idle |
| claim “100 tools” | stubs DOWN | 62 tools reais + genéricos |

## Segurança (Squad 4)

- Porta **:8100** mcp-orchestrator → **Tailscale only** (`100.64.0.0/10`), rules persistidas.
- EasyPanel :3000 permanece TS-only (policy F2).
- Sem rotação de chaves (regra Gustavo).
- Ver `SECURITY_REPORT_2026-07-08.md`.

## Integração clients

- TRAE / TRAE SOLO / Antigravity / Cursor / Claude Desktop: configs em `scripts/mcp_config.*.json`
- Doc: `INTEGRATION_TRAE_ANTIGRAVITY.md`
- Smoke: `bash scripts/validate_coding_vps_tools_60.sh`

## Core stack verde (1/1)

- Agents: crew-ai, goose, hermes, kilo-org_kilocode, langgraph, openchamber, openclaw, opencode, openhands
- LLM: litellm-app + litellm-db
- RAG/obs: anything-llm, langflow(+db), langfuse (web/worker/db/redis/minio/clickhouse)
- Tooling: mcp-orchestrator, centrifugo, zincsearch, crwal4ai, request-baskets, crowdsec

## Comandos de validação

```bash
python3 scripts/coding_vps_mcp_orchestrator.py call chat_minimax "PING-OK-M3"
python3 scripts/coding_vps_mcp_orchestrator.py call chat_with_agent openclaw "PING-OK"
python3 scripts/coding_vps_mcp_orchestrator.py call list_services stack=main
bash scripts/validate_coding_vps_tools_60.sh
bash scripts/validate_coding_vps_e2e.sh --prompt "PING-OK-21"
```

## Reports desta rodada

- `INVENTORY_OPTIMIZE_2026-07-08.md`
- `OPTIMIZE_REPORT_2026-07-08.md`
- `TOOLS_E2E_REPORT_2026-07-08.md`
- `SECURITY_REPORT_2026-07-08.md`
- `INTEGRATION_TRAE_ANTIGRAVITY.md`
- `MEMORY_2026-07-08.md`
- `AGENTS_E2E_2026-07-08.json` (após re-test post-fix)

## Próximos (quando voltar a este stack)

1. Load avg ainda alto pós-scale — re-checar em 30 min.
2. Zombie 0/0 no EasyPanel: limpar defs órfãs com API/MCP EasyPanel (cuidado).
3. Image prune maior (~26 GB reclaimable) em janela de manutenção.
4. `ep_list_services` 404 — alinhar path RPC EasyPanel v2.
5. Só então retomar foco Cartório bot / Telegram.

Modified by Gustavo Almeida
