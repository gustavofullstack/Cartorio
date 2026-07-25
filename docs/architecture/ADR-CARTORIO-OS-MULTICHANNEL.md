# ADR-CARTORIO-OS-MULTICHANNEL — Arquitetura do Bot Multicanal (2026-07-25)

> Status: **ACEITO (v1 implementada)** · Escopo: iMessage live; WhatsApp/Telegram/Web nas próximas waves.

## 1. Decisão

**Reuso da frota Hermes-profile-per-project (provada em produção no mesmo dia)** em vez de
reimplementar um spectrum-gateway TS standalone (echo-app pattern do vendor).

| Componente | Implementação v1 | Papel |
|---|---|---|
| **Transport iMessage** | Spectrum/Photon shared line — projeto `CARTORIO BOT TEST` (`438527e1-2399-49dc-967c-22e33986035a`) | channel transport |
| **Agent runtime** | Hermes profile `cartorio` (`~/.hermes/profiles/cartorio`) — LaunchAgent `ai.hermes.gateway.cartorio`, sidecar **127.0.0.1:8793** | guardrail engine + session |
| **Persona/governance** | `SOUL.md` do profile (HITL #1, LGPD #2, Emolumentos MG 2026 #3, anti-injeção) | policy engine declarativa |
| **LLM** | `Kimi-k3-256k` via bridge local `http://127.0.0.1:8767/v1` (model.custom, api_key=bridge-local) | cérebro (fallbacks do bridge: Grok/Codex) |
| **Tools (14)** | MCP `cartorio` → `https://api.2notasudi.com.br/mcp` (Bearer `MCP_API_KEY`, timing-safe) — 14/14 enabled | authority layer (FastAPI/Postgres/audit chain) |
| **Operador (TUI/webchat)** | OpenClaw agent `cartorio` 🏛️ (`kimi/Kimi-k3`, workspace com mesma SOUL.md) | session router operador |
| **Control plane** | MegaHub `http://127.0.0.1:43210` (dashboard/REST/WS) — de facto | observabilidade/operação |
| **Phantom Panel** | **NÃO EXISTE no ambiente** → adapter interface stub apenas (§4) | control plane futuro |

## 2. Por que não o scaffold spectrum-ts standalone

- Rule 0 (skill hermes-messaging-channels): vendor echo app é diagnóstico, não estado final.
- Um segundo consumer no mesmo projeto Spectrum **rouba a stream** do sidecar Hermes (one-project-per-process).
- O profile Hermes já entrega: debounce, session, pairing/allow-all, MCP client, TTS, launchd KeepAlive.

## 3. Inbound público — limitação REAL (shared pool)

- A linha free/shared **só responde a telefones registrados como users do projeto** (Gustavo registrado ✓).
- `PHOTON_ALLOW_ALL_USERS=true` ativo: qualquer registrado é atendido sem pairing.
- **"Qualquer contato sem cadastro" exige upgrade para número dedicado (Photon Business)** — decisão humana pendente (B-public-line). Não há bypass técnico legítimo; não implementar gambiarras sobre o pool.
- Outbound proativo: apenas transacional em conversa ativa (política do SOUL/Contrato §2). Sem broadcast.

## 4. Phantom Panel — adapter stub (não inventar API)

Nenhum repo/package/serviço/URL "Phantom Panel" foi encontrado no ambiente (busca 2026-07-25: mdfind, npm -g, brew, ~/projetos, /Applications — zero).
Per contrato §4/§17: o core **não depende** do painel. Quando a API real for descoberta, implementar
`PhantomPanelAdapter` conformando à interface `ControlPlaneAdapter` (listAgents/getAgent/listConversations/
sendMessage/pauseAgent/resumeAgent/handoff/getHealth/getMetrics). Implementações ativas hoje:
`OpenClawControlPlaneAdapter` (gateway :18789) e `LocalAdminAdapter` (MegaHub :43210).

## 5. Fluxo v1 (iMessage)

```
iPhone cliente → Spectrum cloud → sidecar :8793 → Hermes gateway (profile cartorio)
  → SOUL.md policy → MCP tools (api.2notasudi.com.br/mcp, Bearer) / LLM Kimi-k3-256k via :8767
  → PII scrub (SOUL + scrub server-side) → resposta → space.send → cliente
```

HITL: protocolos nascem DRAFT (tool `criar_protocolo_draft`); handoff humano via Chatwoot (tool MCP).

## 6. Evidências (2026-07-25 ~18:01)

- `Spectrum started { providers: 'iMessage' }` + `✓ photon connected` no gateway.log do profile.
- `hermes mcp list`: cartorio ✓ enabled (14/14 tools).
- Bridge: `Kimi-k3-256k` → `HERMES_CARTORIO_OK`.
- OpenClaw: `openclaw agent --agent cartorio` → `CARTORIO_OS_OK`.
- Round-trip real iPhone→bot→iPhone: **UNVERIFIED** — depende do Gustavo textar a linha (managed lines são reply-only).

## 7. Próximas waves

- W2: WhatsApp (Evolution já online no radar; Spectrum provider ou Evolution direto) + Telegram (bot token).
- W3: webchat (FastAPI /ws/atendimentos já existe) + identity cross-channel (IdentityLink).
- W4: número dedicado (se aprovado) + PhantomPanelAdapter real + red-team prompt-injection nos canais.

_Modified by Gustavo Almeida — 2026-07-25._
