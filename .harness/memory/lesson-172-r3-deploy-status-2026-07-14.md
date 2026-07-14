# Lesson 172 — R8 prod probe: API totalmente 502 (P0 outage), R3 status indeterminado — 2026-07-14

## TL;DR

Sondagem externa em `https://api.2notasudi.com.br` (10 endpoints + 4 paths
legado) revela **API 100% down (502 Bad Gateway)** desde pelo menos
**2026-07-14 02:13 UTC**. Causa raiz provável: `cartorio_api` no Swarm
sem réplicas healthy (TCP 8000 BLOCKED). **Impossível confirmar quais
R3 fixes estão live**: o serviço não responde nada. R3 está documented
como "not in prod" há 4 rodadas consecutivas (R4..R7); outage atual
muda status de "R3 não deployed" para "R3 deploy seria INVISÍVEL até
recovery".

## Achados (probes 2026-07-14 02:13-02:17 UTC)

### Comportamento uniforme

TODOS os endpoints retornaram **HTTP 502**, body `Bad Gateway` (11 bytes),
latência ~6.3s (timeout Traefik → upstream morto):

| Camada            | Status    | Evidência                                         |
|-------------------|-----------|---------------------------------------------------|
| DNS               | ✅        | `dig api.2notasudi.com.br` → `187.77.236.77`      |
| TLS               | ✅        | Let's Encrypt YR2 válido (CN=api.2notasudi.com.br)|
| TCP 443 (Traefik) | ✅        | `nc -zv 187.77.236.77 443` → OPEN                 |
| TCP 8000 (backend)| ❌        | `nc -zv 187.77.236.77 8000` → BLOCKED/CLOSED      |
| Traefik upstream  | ❌        | 502 qualquer rota (v0 + qual método/path)        |

### R3 status: indeterminado

- 5 rounds confirmaram "R3 NOT in prod" (lesson 165/166/167/169 + este)
- AGORA: serviço down, então **mesmo se R3 estivesse deployed, seria
  invisível**
- Código atual em `main.py` (commit `c8f9e6b`) contém as 4 fixes (L433,
  L439, L445, L567, L656, L118-123). Ver `docs/R3_DEPLOY_STATUS.md`
  §2.1 para diff/lines.

## O que NÃO foi feito (por design)

- ❌ Deploy da v0.6.0 (decisão humana — Gustavo)
- ❌ SSH ao VPS (não tenho acesso ao Swarm daqui)
- ❌ Restart do `cartorio_api` (P0 recovery é decisão humana)

## O que FOI entregue (sob demanda)

1. `docs/R3_DEPLOY_STATUS.md` — relatório completo:
   - §1 Descoberta P0 + camadas verificadas
   - §2 Implicação sobre R3 (status indeterminado)
   - §3 Checklist recovery + deploy (4 cenários, comandos SSH, env vars, rollback)
   - §4 Resumo executivo
   - §5 Refs cross-linkadas

2. Esta lesson (memória cross-rein)

## Lessons (próximas rodadas)

1. **Outage pode mascarar deploy status.** R3 tinha 4 rounds de
   "not in prod" mas isso era inferido por 404. Hoje nem 404 retorna —
   API está down. **Heurística nova**: quando TODAS as rotas (incluindo
   `/`, `/health`, paths não versionados) retornam mesmo status
   uniformemente → outage de camada, não rota específica. Antes
   inferir "fix X não deployed", descartar P0.

2. **Traefik + Swarm debug pattern (coringa)**:
   - DNS OK + TLS OK + 443 OPEN → Traefik vivo
   - Mas 8000 BLOCKED → Swarm sem backend healthy nessa porta
   - `nc -zv <ip> <porta>` é o canivete suíço: testa 1 porta em 1s
     sem precisar de `docker` ou SSH
   - Para o `cartorio-api` é 8000 (mapeamento interno Swarm); outros
     containers variam

3. **Checklist recovery escalonado** (4 cenários):
   - Cenário 1: `--force` (crash simples)
   - Cenário 2: tag errada (imagem antiga)
   - Cenário 3: deadlock startup (DB/Redis/Evolution offline)
   - Cenário 4: rolling restart travou (scale 0→1)
   - Cada um com comandos copy-paste no docs §3.3

4. **R3 deploy AGORA depende de recovery primeiro.** Antes: "deploy
   v0.6.0 → R3 live". Agora: "recovery + deploy v0.6.0 → R3 live".
   Gustavo tem 2 ações, não 1.

## Próximas ações (não-auto)

| Quem     | O quê                                            | Quando                |
|----------|--------------------------------------------------|-----------------------|
| Gustavo  | SSH VPS, rodar Passo A (3.2) — diagnóstico Swarm | Antes de qualquer coisa|
| Gustavo  | Escolher cenário (B1..B4) e executar recovery    | Imediato              |
| Gustavo  | Após recovery verde, executar Passo C (deploy)   | Após verde            |
| Gustavo  | Passo D (verificação R3 com script)              | Pós-deploy            |
| Gustavo  | Atualizar lesson-171 com resultado recovery      | Após resolução        |
| Próximo loop YOLO | Aguardar confirmação humana antes de qualquer auto-deploy de cartorio_api | Após resolução |

## Como aplicar (próximos rounds)

- **Antes de inferir "fix X não deployed"**: rodar `nc -zv <vps> 8000`
  primeiro. Se BLOCKED, é outage — não inferir nada sobre deploy.
- **R3 status pós-recovery**: rodar script §3.5 do
  `docs/R3_DEPLOY_STATUS.md` em 1 rodada curl/bash. Cada alínea
  prova 1 das 4 fixes (200/410/101/404 esperados).
- **R4 candidates (já na lesson 165)**: continuam válidos
  post-mortem (PII tests population, rein agent.md, MEMORY trim, trae-agent
  drop). Aguardar recovery verde antes de tocar código de novo.

## Refs

- `docs/R3_DEPLOY_STATUS.md` — checklist completo
- `lesson-165-r3-routing-fixes-2026-07-13.md` — R3 original (4 fixes)
- `lesson-166-r4-organizational-fixes-2026-07-13.md` — R3 not in prod
- `lesson-167-r5-cross-ref-ruff-memory-2026-07-13.md` — R3 still not in prod
- `lesson-169-r7-coverage-deadcode-2026-07-13.md` — R3 still not in prod
- `lesson-150-incident-vps-down-telegram-2026-07-08.md` — incidente similar (Telegram bot)
- `lesson-171-pii-status-resolved-2026-07-14.md` — slot 171 já usado (PII close-the-finding). Por isso esta lesson usa slot 172.
- `docs/DEPLOYMENT.md` — Easypanel + Traefik + Swarm
- `CLAUDE.md` §"Critical rules" + §"Notable integration gotchas"

Modified by Gustavo Almeida — 2026-07-14