# Lesson 203 — G7 Wave 27 A4: 3 intents + Traefik merge + radar redeploy (2026-07-17)

Type: project + reference  
Agents: cartorio-dev / cartorio-n8n hybrid  

## Tasks

| ID | Result |
|----|--------|
| G7.06.T4 | Synthetic E2E 3 intents LobeChat→OpenClaw→API offline (`test_g7_lobechat_openclaw_intents.py` + doc) |
| G7.12.T3 | `infra/traefik/routers-merged-g7.yaml` + `docs/TRAEFIK_ROUTERS_MERGE_G7.md` — deploy SUI |
| G7.18.T1 | Code radar/expanded verified; `docs/RADAR_EXPANDED_REDEPLOY_G7.md` — prod SUI |
| G7.25.T3 | Index entry started (full consolidada end-of-wave) |

## Artefatos

- `backend/tests/test_g7_lobechat_openclaw_intents.py`
- `docs/LOBECHAT_OPENCLAW_3INTENTS_E2E_G7.md`
- `infra/traefik/routers-merged-g7.yaml`
- `docs/TRAEFIK_ROUTERS_MERGE_G7.md`
- `docs/RADAR_EXPANDED_REDEPLOY_G7.md`

## Validação

```bash
cd backend && uv run pytest -q --no-cov tests/test_g7_lobechat_openclaw_intents.py
```

## Notas

1. **Live chain HOLD** — LobeChat key + OpenClaw cartorio-bot + Chatwoot DNS ainda SUI; synthetic cobre contrato de tools/HITL.
2. **HITL**: `POST /protocolo/criar-api` rejeita `hitl_draft=false`; status persistido `DRAFT`.
3. **Dois formatos de número**: tool consultar usa `YYYY-NNNNN`; criar-api gera `CART-YYYY-XXXXXX` — testes cobrem ambos.
4. **Traefik merge** não é dynamic ativo no VPS — só artifact; DNS A records (G7.12.T1) antes do merge.
5. **`/radar/expanded`** já em master (`health_radar_expanded.py`); prod 404 = imagem stale, não falta de código.
6. Cross-refs: Lesson 170 (LobeChat), 177 (OpenClaw E8), 179 (DNS/Traefik), 176 (502 env).

**Modified by Gustavo Almeida — G7 Wave 27**
