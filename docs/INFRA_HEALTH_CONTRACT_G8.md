# Contrato local de health e infraestrutura

**Data:** 2026-07-19  
**Escopo:** contrato versionado e validação offline; este documento não declara
estado live de DNS, TLS, Traefik, Tailscale ou serviços externos.

## Endpoints canônicos

| Consumidor | Endpoint | Semântica |
|---|---|---|
| Orquestrador | `GET /healthz` | liveness da API; alias de compatibilidade de `GET /health`. |
| Orquestrador | `GET /readyz` | readiness da API; alias de compatibilidade de `GET /ready`. |
| Radar | `GET /api/v1/health/radar` | resumo de dependências; não substitui probes autenticados. |
| Radar detalhado | `GET /api/v1/health/radar/expanded` | diagnóstico agregado; pode depender de rede. |
| MCP montado | `POST /mcp` | Streamable HTTP JSON-RPC no processo da API. |
| MCP standalone | `POST http://host:8100/` | Streamable HTTP JSON-RPC; `8100` é configurável por `MCP_SERVER_PORT`. |
| OpenClaw | `GET /health` no origin configurado | probe do gateway; URL vem de `OPENCLAW_BASE_URL`, sem URL/token em docs. |

`/health` e `/ready` permanecem por retrocompatibilidade. Não utilizar `GET /mcp`
como verificação de tools: o protocolo requer handshake JSON-RPC.

## Inventário para DNS, TLS, proxy e Tailscale

As tarefas 071–074 exigem evidência operacional que não pode ser inferida do
repositório. Registrar cada item em canal seguro, sem valores de token, IPs
privados desnecessários ou dumps de configuração:

| Controle | Evidência mínima | Aceite |
|---|---|---|
| DNS público/interno | nome, tipo, destino mascarado quando interno, TTL, owner e data | não há host órfão ou destino divergente. |
| TLS | emissor, SAN, expiração e rota de renovação | alerta antes da expiração e cadeia válida. |
| Traefik/proxy | router, service, middleware, rota WS e timeout | auth, CORS, rate limit e mascaramento de logs conferidos. |
| Tailscale | ACL/tag, dispositivo, rota anunciada e owner | menor privilégio; nenhuma rota ampla sem justificativa. |

## Verificação offline

```bash
python3 scripts/mcp_tools_inventory.py --check-mount
make postman-sync-test
cd backend && uv run pytest --no-cov ../.brain/api-specs/test_catalog.py
```

Mudanças externas continuam condicionadas a aprovação humana, janela de mudança,
backup/rollback e smoke pós-deploy.
