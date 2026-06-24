# Linear Sync 2026-06-24 — 100 tasks criadas

> Sessão: ZCode + MiniMax-M3 (orquestrador).
> Token: `lin_api_9Bmfyw0EAeAGMzEClLB9OncAT5A66TuQGtCNpLPl` (em `.secrets/linear.env`).
> Team: `Cartorio-uberlandia-2` (key=CAR).

## Resultado

**4 Projects criados** (squads A-D) + **100 Issues criadas** (CAR-7 → CAR-106).

### Projects
| Squad | ID | Nome |
|---|---|---|
| A | `8e7824ab-c10d-46ef-9ce9-094922c59acc` | SQUAD A — API + DB Hardening (25 tasks) |
| B | `c72ab29c-fdd8-4e60-acd8-994f3d01d550` | SQUAD B — N8N Polish (25 tasks) |
| C | `9ff9eb7d-1f39-44ee-a65d-4a2088d511c1` | SQUAD C — Observability + Docs (25 tasks) |
| D | `ed65b8b7-fbec-48d8-af3e-5455e96644d2` | SQUAD D — LGPD Compliance (25 tasks) |

**Nota**: Squads E-J (60 tasks) foram criadas com **project_id de A-D como catch-all** (temporário). Para separar, criar 6 projects adicionais depois.

### Issues (100)
- **Squad A (10)**: CAR-7 a CAR-16 (API + DB Hardening)
- **Squad B (10)**: CAR-17 a CAR-26 (N8N Polish)
- **Squad C (10)**: CAR-27 a CAR-36 (Observability + Docs)
- **Squad D (10)**: CAR-37 a CAR-46 (LGPD Compliance)
- **Squad E (10)**: CAR-47 a CAR-56 (OpenClaw Agent)
- **Squad F (10)**: CAR-57 a CAR-66 (Telegram Bot)
- **Squad G (10)**: CAR-67 a CAR-76 (API FastAPI)
- **Squad H (10)**: CAR-77 a CAR-86 (Chatwoot CRM)
- **Squad I (10)**: CAR-87 a CAR-96 (Redis)
- **Squad J (10)**: CAR-97 a CAR-106 (Infra DevOps CI/CD)

**Skip**: 6 issues (já existiam CAR-1 a CAR-5 + 1 falha). Total final: **106 issues** (100 nossas + 5 legacy + 1 falhou).

## Estimativa de pontos
- **1 point** = ~40min
- Total estimado: ~250 points = **~17 horas de trabalho**

## Próximos passos
1. Criar 6 projects adicionais (SQUAD E-J) e migrar as 60 issues pra eles
2. Adicionar labels por squad (SQUAD_A, SQUAD_B, etc)
3. Configurar Views: Roadmap (por sprint), Backlog (por squad)
4. Vincular issues com PRs do GitHub (auto-close on merge)
5. Sincronizar status com Render deploys

## Comando usado
```bash
TOKEN="lin_api_9Bmfyw0EAeAGMzEClLB9OncAT5A66TuQGtCNpLPl"
curl -sS -X POST https://api.linear.app/graphql \
  -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"mutation { issueCreate(input: { teamId: \"...\", projectId: \"...\", title: \"...\", priority: 1, estimate: 13 }) { success issue { id identifier } } }"}'
```

## Token não rotaciona
Regra absoluta Gustavo: `lin_api_9Bmfyw0EAeAGMzEClLB9OncAT5A66TuQGtCNpLPl` salva em `.secrets/linear.env` + `~/.mavis/secrets/cartorio-global.env` (chmod 600).
