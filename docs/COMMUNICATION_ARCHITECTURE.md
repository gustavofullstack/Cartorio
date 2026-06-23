# Arquitetura de Comunicacao Mavis / MiniMax

> Documentacao de como o agente Mavis (este ZCode) se comunica com outros agentes MiniMax.
> v0.4.4 (2026-06-23).

---

## Visao geral

`mavis communication` e o protocolo inter-session da plataforma MiniMax. Cada sessao (`mvs_*`) e um agente independente com:
- `sessionId` (UUID)
- `agentName` (ex: Mavis, Pietra, OpenCode)
- `agentRole` (orchestrator, specialist, etc)
- `displayName` (legivel)
- `title` (sub-titulo descritivo)

Os agentes conversam entre si via CLI:
```bash
~/.mavis/bin/mavis communication send --to <sessionId> --command prompt --content "..."
```

---

## Comandos disponiveis

| Comando | Efeito |
|---|---|
| `prompt` | Envia mensagem como prompt para a sessao alvo |
| `summarize` | Pede resumo da sessao |
| `fork` | Cria nova sessao ramificada da alvo |
| `spawn` | Spawna sub-agent (configuravel) |
| `abort` | Aborta sessao alvo |
| `kill` | Mata sessao alvo |

## CLI basico

```bash
# Listar peers ativos (447+ registrados)
~/.mavis/bin/mavis communication peers --session <mySessionId>

# Listar mensagens recebidas/enviadas
~/.mavis/bin/mavis communication messages --to <sessionId> --limit 50

# Enviar mensagem
~/.mavis/bin/mavis communication send \
  --from <mySessionId> \
  --to <targetSessionId> \
  --command prompt \
  --content "Texto da mensagem"

# Filtrar por status
~/.mavis/bin/mavis communication messages --status done --human
~/.mavis/bin/mavis communication messages --status failed --human
```

---

## Squads por papel (Mavis orquestrador)

Quando Gustavo fala com "Mavis", o orquestrador delega para:

- **Mavis orchestrator** (5-10 sessoes simultaneas) - recebe briefings, distribui tasks
- **Pietra / ZCode** - implementa codigo
- **CEO/CTO/CMO/CFO/COO** - decisoes C-Level
- **Tech Lead / Arquiteto** - decisoes tecnicas
- **Dev Backend/Frontend Senior** - implementacao
- **Infra/DevOps** - Docker, CI/CD, deploy
- **PMO/PM** - Tasks/Epicos/Sprints
- **QA Master** - testes E2E, unit, integracao
- **UX/UI Designer** - prototipos, design system
- **Cartorio-Dev / Cartorio-LGPD / Cartorio-N8N** - reins especializados do projeto

---

## MCP Servers (descoberta via `~/.mavis/mcp/clients/cartorio-mcp-config.json`)

5 servers registrados para o projeto Cartorio:

| Server | Tipo | URL | Auth |
|---|---|---|---|
| `n8n` | http | `https://cartorio-n8n.dfgdxq.easypanel.host/mcp-server/http` | Bearer JWT |
| `supabase` | http | `https://supbase.2notasudi.com.br/mcp?features=docs,database,debugging,development` | OAuth (auto) |
| `cartorio-api` | http | `https://mcp.2notasudi.com.br/mcp` | Bearer API key |
| `easypanel` | stdio (npx) | `easypanel-mcp-server@latest` | env: EASYPANEL_URL + TOKEN |
| `openclaw` | websocket | `wss://agent.2notasudi.com.br` | Bearer gateway token |

Endpoint de discovery da API: `GET https://api.2notasudi.com.br/mcp-servers`

---

## Tailscale (rede privada)

8 nos na rede `gustavomar.fullstack@gmail.com` (MagicDNS suffix `tail2fe279.ts.net`):

| Node | IP Tailscale | OS | Ultima conexao |
|---|---|---|---|
| vps-cartorio | 100.99.172.84 | Linux | Connected (SSH Exit Node) |
| macbook-pro-gus | 100.83.180.16 | macOS 26.5.1 | Connected |
| triqhub | 100.110.127.44 | Linux | idle (Exit Node offered) |
| iphone-17-pro | 100.122.101.33 | iOS 26.6.0 | Connected |
| iphone-andre | 100.74.36.41 | iOS 26.5.0 | 13:13 BRT |
| iphone-henrique | 100.76.109.91 | iOS 26.5.0 | 13:05 BRT |
| macbook-air-de-henrique | 100.122.88.49 | macOS 26.2.0 | May 22 (offline 31d) |
| pc-do-andre | 100.112.202.91 | Windows 11 25H2 | Jun 21 (offline 1d) |

OpenClaw acessivel via Tailscale MagicDNS:
- `https://vps-cartorio.tail2fe279.ts.net/` -> 200 OK (rota Traefik custom adicionada na v0.4.3)
- `https://openclaw.tail2fe279.ts.net/` -> mesmo handler (mesma rota regex)

---

## Padroes de uso

### Quando receber briefing grande de Gustavo
1. **NAO** tentar fazer tudo de uma vez
2. Invocar `using-superpowers` skill
3. Auditar estado real via SSH/curl
4. Identificar gaps REAIS (nao os mesmos pedidos repetidos)
5. Executar UMA tarefa concreta por turno
6. Commit + CHANGELOG
7. Documentar UI-only pendentes

### Quando Gustavo pedir comunicacao entre agentes
```bash
~/.mavis/bin/mavis communication send \
  --to <peerSessionId> \
  --command prompt \
  --content "Tarefa especifica que o sub-agent deve fazer"
```

### Quando receber comando `mavis communication messages --to <sessionId>`
Retorna JSON com historico de mensagens. Filtrar por:
- `command: prompt` - mensagens normais
- `command: summarize` - pedidos de resumo
- `status: done` vs `failed` - resultado

---

## Anti-patterns

- **NAO** repetir o mesmo briefing gigante - cada vez custa contexto e tokens
- **NAO** fingir que fez algo que depende de UI web (Easypanel, Cloudflare, Hostinger)
- **NAO** executar comandos destrutivos sem backup antes (ja foi regra do ADR-001)
- **NAO** centralizar DBs de todos os servicos num so (causou o incident de 113 tabelas)

---

## Referencias

- Codigo fonte Mavis: `~/.mavis/bin/mavis`
- Config MCP global: `~/.mavis/mcp/clients/cartorio-mcp-config.json`
- Config geral: `~/.mavis/config.yaml`
- Schema MCP: `https://raw.githubusercontent.com/MiniMax/mavis/main/mcp/schemas/mcp-config-v1.json`

Modified by Gustavo Almeida
