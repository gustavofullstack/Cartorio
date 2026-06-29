# Linear — 22 tasks Done 2026-06-24

> Sessão: ZCode + MiniMax-M3 (orquestrador).
> **Resultado: 22/100 tasks Linear Done (22% de progresso)**.

## Tasks marcadas Done hoje (22)

### Bloco 1 (agent, 6 tasks — squad A)
- CAR-7 (A01) — listar tabelas reais
- CAR-8 (A02) — versionar schema SQL
- CAR-9 (A03) — 11 tabelas novas
- CAR-11 (A05) — pg_cron 5 jobs
- CAR-13 (A07) — vault 8 secrets REAIS
- CAR-16 (A10) — backup automatizado

### Bloco 2 (ZCode, 16 tasks — squads B/C/G/H)
- **SQUAD B** (Evolution API):
  - CAR-17 (B01) — health-check Evolution
  - CAR-18 (B02) — 2 webhooks oficiais
  - CAR-21 (B05) — Evolution client httpx
  - CAR-22 (B06) — mapear eventos → filas
  - CAR-23 (B07) — validar 1 instância
  - CAR-25 (B09) — doc Evolution v2
  - CAR-26 (B10) — OpenAPI/Postman
- **SQUAD C** (N8N):
  - CAR-27 (C01) — audit 33+ workflows
  - CAR-28 (C02) — ativar error-handler
- **SQUAD G** (API FastAPI):
  - CAR-67 (G01) — pytest full suite
  - CAR-68 (G02) — 8 health endpoints
  - CAR-71 (G05) — 6 endpoints LGPD
  - CAR-72 (G06) — metrics
  - CAR-74 (G08) — WS (validado)
  - CAR-76 (G10) — doc API completa
- **SQUAD H** (Chatwoot):
  - CAR-77 (H01) — Chatwoot health-check

## Erro encontrado + workaround

**Erro original**: `issueUpdate(input: { stateType: "completed" })` → 
```
"Field \"stateType\" is not defined by type \"IssueUpdateInput\""
```

**Workaround**: usar `stateId` (UUID) em vez de `stateType` (string):
```graphql
mutation {
  issueUpdate(id: "ISSUE_UUID", input: { stateId: "21b530b3-abf7-4fff-8b6d-2f3c50d37ce4" }) {
    success
  }
}
```

**Done state UUID** (Cartorio-uberlandia-2 team): `21b530b3-abf7-4fff-8b6d-2f3c50d37ce4`

## Progressão

- **Total tasks**: 100
- **Done**: 22 (22%)
- **Backlog**: 74 (74%)
- **In progress**: 4 (4%)

## Próximos passos

### Marcar mais Done (próxima sessão)
- **SQUAD D** (LGPD) — D37-D46 (DPA + direitos)
- **SQUAD I** (Redis) — I87-I96 (já em uso, várias Done)
- **SQUAD E** (OpenClaw) — E47-E56 (M3 fix + Telegram bot)
- **SQUAD F** (Telegram) — F57-F66 (workflow 31 v2 + E2E)
- **SQUAD J** (DevOps) — J97-J106 (Render sync, DNS, etc)

### Linear API token
- **NÃO rotacionar** (regra Gustavo)
- Salvo em `.secrets/linear.env` + `~/.mavis/secrets/cartorio-global.env` (chmod 600)

Modified by Gustavo Almeida
