# Squad 5 — Validate Final 2026-07-09

**Sub-squad**: VALIDATE FINAL (Squad 5 / 5)
**Data**: 2026-07-09
**Alvo**: coding-vps_apenas_para_auxilio (Tailscale 100.99.172.84)
**Objetivo**: Confirmar 100% E2E verde pós-squads 1-4

---

## TAREFA 1 — Estado geral dos serviços

| Métrica                              | Valor |
|--------------------------------------|-------|
| Total de serviços coding-vps*        | **89** |
| Serviços UP (1/1)                    | **44** |
| Serviços scale=0 (preservados)       | **45** |
| Serviços com problema (down/crash)   | **0** |
| Memória total / usada                | 15 Gi / 9.2 Gi (61%) |
| Disco / usado                        | 193 G / 128 G (67%) |

**Diagnóstico**: 44 UP = 18 LLM/agents + 26 serviços auxiliares (LiteLLM, Redis, Postgres, RabbitMQ, Prometheus, Grafana, Langfuse, Temporal, etc.). 45 em scale=0 = preservados intencionalmente pelas squads anteriores (estratégia de manter 2ª réplica desligada). **Zero serviços em estado de falha**.

---

## TAREFA 2 — Validação E2E 18 LLM agents

**Método**: Container `coding-vps_apenas_para_auxilio_crew-ai` (tem Python) executa script que chama `/chat` em cada agent com prompt `"Responda exatamente: PING-OK-FINAL"` e verifica se a resposta contém a string e não tem `error:true`.

**Providers**: 7 FastAPI (query params) + 2 Node (kilo=query, opencode=body JSON).

### Main stack (coding-vps_apenas_para_auxilio_*)

| # | Agent               | Runtime | Endpoint              | Modo  | Latência | Resultado |
|---|---------------------|---------|-----------------------|-------|----------|-----------|
| 1 | crew-ai             | FastAPI | POST /chat?prompt=... | qs    | 1.7 s    | OK        |
| 2 | goose               | FastAPI | POST /chat?prompt=... | qs    | 1.2 s    | OK        |
| 3 | hermes              | FastAPI | POST /chat?prompt=... | qs    | 1.2 s    | OK        |
| 4 | langgraph           | FastAPI | POST /chat?prompt=... | qs    | 1.0 s    | OK        |
| 5 | openchamber         | FastAPI | POST /chat?prompt=... | qs    | 1.0 s    | OK        |
| 6 | openclaw            | FastAPI | POST /chat?prompt=... | qs    | 2.2 s    | OK        |
| 7 | openhands           | FastAPI | POST /chat?prompt=... | qs    | 1.2 s    | OK        |
| 8 | kilo-org_kilocode   | Node    | POST /chat?prompt=... | qs    | 1.2 s    | OK        |
| 9 | opencode            | Node    | POST /chat (JSON)     | body  | 2.1 s    | OK        |

### Side stack (coding-vps-agents_*)

| #  | Agent                                | Runtime | Modo | Latência | Resultado |
|----|--------------------------------------|---------|------|----------|-----------|
| 10 | coding-vps-agents_crew-ai            | FastAPI | qs   | 1.2 s    | OK        |
| 11 | coding-vps-agents_goose              | FastAPI | qs   | 0.9 s    | OK        |
| 12 | coding-vps-agents_hermes             | FastAPI | qs   | 0.9 s    | OK        |
| 13 | coding-vps-agents_langgraph          | FastAPI | qs   | 1.6 s    | OK        |
| 14 | coding-vps-agents_openchamber        | FastAPI | qs   | 5.1 s    | OK        |
| 15 | coding-vps-agents_openclaw           | FastAPI | qs   | 1.7 s    | OK        |
| 16 | coding-vps-agents_openhands          | FastAPI | qs   | 1.4 s    | OK        |
| 17 | coding-vps-agents_kilo-org_kilocode  | Node    | body | 1.3 s    | OK        |
| 18 | coding-vps-agents_opencode           | Node    | body | 1.6 s    | OK        |

**TOTAL: 18/18 (100%)** — todos retornam `PING-OK-FINAL` via MiniMax-M3 XMax Thinking com `reasoning_tokens` ativo (17-51 tokens por resposta).

### Observação sobre o endpoint kilo

A spec original do squad5 usava POST com JSON body para kilo — falha com HTTP 422 porque `kilo-org_kilocode main` foi deployado com **PATCH v2.0.0** que moveu `prompt`/`max_tokens` para **query params** (ver `main.py` v2-patched no container). Side stack mantém spec original (JSON body). A correção foi usar o schema correto para cada stack: query para main, body para side.

### LiteLLM proxy health

```bash
curl http://coding-vps_apenas_para_auxilio_litellm-app:4000/health/liveliness
"I'm alive!"
```

Modelo: `MiniMax-M3` (MiniMax Coding Plan, MiniMax.io) com XMax Thinking automático.

---

## TAREFA 3 — Infraestrutura de segurança e orquestração

| Componente         | Status | Detalhes                                                                 |
|--------------------|--------|--------------------------------------------------------------------------|
| UFW Firewall       | OK     | Ativo, allowlist Tailscale + 22/80/443/41641/2377 (Swarm-manager)        |
| fail2ban           | OK     | Ativo, jail `sshd` monitorando tentativas de brute-force                |
| LiteLLM proxy      | OK     | health/liveliness = `"I'm alive!"`, 1 model (`MiniMax-M3`) ativo         |
| Docker log driver  | OK     | json-file com rotação max-size=10m / max-file=3                          |
| Easypanel API      | OK     | Login retorna token JWT (`cmrcqqto3000006pl51xsauby`)                    |
| Docker Swarm       | OK     | 89 serviços total, 44 UP, 0 down, 45 preservados em scale=0             |
| Tailscale SSH      | OK     | Acesso root@100.99.172.84 funcionando via chave `id_ed25519_cartorio`    |

---

## Status consolidado dos 5 squads

| Squad | Tema                          | Doc                                                                 | Status |
|-------|-------------------------------|---------------------------------------------------------------------|--------|
| 1     | Optimize + dedupe             | `optimize-2026-07-08-squad1.md`, `dedupe-2026-07-09-squad1.md`       | OK     |
| 2     | Security (UFW/fail2ban/secrets)| `security-2026-07-08-squad2.md`                                     | OK     |
| 3     | MCP tools registry            | `mcp-tools-2026-07-08-squad3.md`, `MCP-ORCHESTRATOR-100-TOOLS.md`   | OK     |
| 4     | Perf + validate               | `perf-2026-07-09-squad4.md`, `validate-2026-07-08-squad4.md`        | OK     |
| 5     | Docker cleanup + validate final| `docker-cleanup-2026-07-08-squad5.md`, **este doc**                 | OK     |

---

## CONCLUSÃO

✅ **100% VERDE** — coding-vps_apenas_para_auxilio está operacional e validado end-to-end.

- **18/18 LLM agents** respondem corretamente via MiniMax-M3 XMax Thinking
- **44/44 serviços UP** sem nenhum em estado de falha
- **LiteLLM proxy vivo**, Easypanel autenticando, UFW/fail2ban ativos
- **Memória 61%**, disco 67% — folga confortável para operação
- **5 squads completos**, documentação gerada em `.agents/skills/coding-vps-21/`

Nenhuma ação corretiva adicional necessária. Plataforma pronta para produção.