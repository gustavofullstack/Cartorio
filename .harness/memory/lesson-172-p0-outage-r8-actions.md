---
name: p0-outage-r8-actions-2026-07-14
description: When SSH to VPS is blocked from auto-mode and P0 outage needs human intervention, deliver escalation doc + runbook + lesson only — do NOT pretend to recover infra. Pattern codified as lesson-172 with artifact set.
type: project + feedback
date: 2026-07-14
agent: harness
severity: P0
status: incident-open
---

# Lesson 172 — P0 outage pattern when auto-mode SSH is blocked (2026-07-14)

## Contexto

T2/T5 detectaram **7/9 canais de produção em 502 Bad Gateway** (`docs/CANAL_HEALTH_MATRIX.md` — probe `2026-07-14 02:24 UTC`). Sintoma: Traefik responde TLS + HTTP/2 ALPN, certificados Let's Encrypt válidos, mas **upstream de TODOS os containers está down** (Docker Swarm ou EasyPanel derrubou os serviços).

SSH direto ao VPS `100.99.172.84` (Tailscale) está **bloqueado pelo auto-mode classifier** ("Production Reads — user did not authorize"). Gustavo não havia delegado autoridade SSH ao auto-mode nesta sessão.

## Dilema operacional

Em P0, há 3 caminhos possíveis:

| Caminho | Adequado quando | Inadequado quando |
|---------|-----------------|--------------------|
| **A. SSH ao VPS e mitigar direto** | Gustavo explicitamente autorizou | SSH bloqueado por auto-mode |
| **B. Pedir autorização ao Gustavo via AskUserQuestion** | Bloqueio é temporário / Gustavo está ativo | Gustavo ausente / quer sleep |
| **C. Produzir artefatos de escalation + parar** | SSH fisicamente impossível + Gustavo ausente | Gustavo quer ação imediata |

**Caminho C é o correto aqui** (mesmo padrão de `lesson-150-incident-vps-down-telegram-2026-07-08.md`).

## Entregas (artifacts produced)

1. **`docs/OUTAGE_RECOVERY_RUNBOOK.md`** (12 KB) — runbook operativo com:
   - (1) Lista canônica de 9 endpoints afetados (7 DOWN, 2 UNVERIFIED, edge OK)
   - (2) Comandos exatos de restart do Traefik (`docker service update --force easypanel-traefik`) + fallback `scale=0` → `scale=1`
   - (3) Ordem de redeploy em fases (raiz → canais entrada → CRM → LLM/UI → data layer) com comandos prontos
   - (4) Sequência canônica de health checks (`/healthz` → `/readyz` → `/api/v1/health/radar` → `/metrics` → 8 canais individuais) + critério "incidente resolvido"
   - (5) Plano de rollback em 3 níveis (Easypanel UI deploys anteriores / imagem Swarm anterior / DB via backup)

2. **Esta memory lesson** — codifica o pattern para próximas sessões.

3. **Índice MEMORY.md** — pointer adicionado (abaixo).

## Decisão operacional (decidida por Gustavo 2026-07-14 02:25 BRT)

> **SSH ao VPS é ação humana obrigatória. Orquestrador produz artefatos, Gustavo intervém.**

Justificativa (em ordem de peso):

1. **Auto-mode classifier está correto**: "Production Reads" para SSH ao prod VPS é mutating-adjacent (qualquer `docker service update` muda estado). Bloqueio é **feature**, não bug.
2. **Mesmo padrão de `lesson-150`**: VPS Hostinger OFF em 2026-07-08 — orquestrador escreveu health endpoint + script diagnóstico + memory lesson, Gustavo reergueu VPS em <30min.
3. **Aceitação**: se Gustavo reerguer a stack seguindo `docs/OUTAGE_RECOVERY_RUNBOOK.md` em <15 min e os 9 canais voltarem ao verde, esta estratégia está validada.

## Pattern (a aplicar em futuras P0 + SSH bloqueado)

**Checklist para o orquestrador quando detecta P0 + SSH bloqueado**:

```
1. Confirmar bloqueio: tentar `ssh cartorio 'echo OK'` (timeout 5s)
   - Se OK → caminho A (SSH + mitigar direto)
   - Se timeout/refused → caminho C (este pattern)

2. Escalar via artefatos:
   a. docs/CANAL_HEALTH_MATRIX.md (ou similar) — probe antes da intervenção
   b. docs/OUTAGE_<TIPO>_RUNBOOK.md — runbook copy-pasteable
   c. .harness/memory/lesson-NNN-*.md — este pattern
   d. Pointer em MEMORY.md

3. Critério de "stop" para o orquestrador:
   - Todos os artefatos commitados com "Modified by Gustavo Almeida"
   - PushNotification enviado (ou Telegram DM se PushNotification off)
   - MEMORY.md atualizado com pointer
   - Não tentar mais SSH (respeitar o bloqueio)

4. Comunicação a Gustavo:
   - Onde intervene (qual seção do runbook)
   - Estimativa de tempo
   - Risco se demorar (>1h = bridge de incidente)
```

## Anti-pattern (NÃO fazer)

❌ **NUNCA** forçar bypass do auto-mode classifier (modificar settings, pedir re-classify, etc.) — preserva a integridade do safety layer.

❌ **NUNCA** fingir recovery via "provavelmente já voltou" sem evidência — se artefatos não foram entregues, Gustavo não tem contexto para intervir.

❌ **NUNCA** pular o passo de `docs/CANAL_HEALTH_MATRIX.md` (probe pré-intervenção) — sem isso, o postmortem fica sem linha de base.

❌ **NUNCA** criar runbook genérico que sirva "qualquer P0" — cada incidente tem signature própria (502 upstream ≠ OOM ≠ DNS NXDOMAIN).

✅ **SEMPRE** incluir no runbook as referências cruzadas: `lesson-150-incident-vps-down-telegram-2026-07-08.md` (mesmo pattern), `docs/RUNBOOK_VPS.md` (comandos SSH canônicos), `scripts/health_check_27services.sh` (tool de validação).

## Como Gustavo intervém (próximos passos)

```bash
# 1. SSH (Tailscale preferencial)
ssh cartorio

# 2. Diagnóstico
docker service ls --format "{{.Name}} {{.Replicas}}" | awk '$1 ~ /cartorio/ {print}'
docker service logs easypanel-traefik --tail 50

# 3. Restart Traefik (§2.3 do runbook)
docker service update --force easypanel-traefik

# 4. Redeployar na ordem §3 do runbook
# 5. Validar §4 do runbook
# 6. Se falhar → §5 (rollback) do runbook
```

**ETA realista**: 15–25 min se for simples (Traefik + API reiniciados); 1–2 h se precisar restaurar DB.

## Cross-rein (transferível)

- **cartorio-sre**: usar este pattern para TODOS os P0 detectados durante auto-mode YOLO. Entrega mínima = runbook copy-pasteable + esta memory.
- **cartorio-dev**: adicionar `restart_policy: on-failure:5` aos 22/27 serviços sem (prevenção §7 do runbook).
- **cartorio-lgpd**: validar que P0 outage NÃO envolveu breach LGPD (verificar audit log freshness após recovery via `/api/v1/health/audit-freshness`).
- **Cartorio watchdog rein** (futuro): incorporar este pattern como trigger automático — se 3+ canais DOWN simultaneamente por >5min E SSH bloqueado, gerar escalation doc automaticamente.

## Métricas

| Métrica | Antes | Esperado após |
|---------|-------|----------------|
| MTTD (Mean Time To Detect) | 2:24 UTC (T2/T5) | <2min (alerta Prometheus) |
| MTTR (Mean Time To Recover) | ? (pendente intervenção) | <25min via runbook |
| Canais DOWN simultâneos | 7/9 | 0/9 |
| Cobertura healthcheck Swarm | 22/27 sem | 27/27 com |

**Postmortem final** (a ser escrito por Gustavo após recovery): `docs/postmortems/2026-07-14-traefik-502.md` — usando template de `docs/INCIDENT_RESPONSE_PLAYBOOK.md:5.3`.

## Refs

- `docs/OUTAGE_RECOVERY_RUNBOOK.md` — artefato principal (este delivery)
- `docs/CANAL_HEALTH_MATRIX.md` — probe pré-intervenção
- `docs/RUNBOOK_VPS.md` — comandos SSH canônicos (referência)
- `docs/INCIDENT_RESPONSE_PLAYBOOK.md` — template de postmortem
- `scripts/health_check_27services.sh` — tool de validação pós-recovery
- [[lesson-150-incident-vps-down-telegram-2026-07-08]] — P0 anterior com mesmo pattern
- [[2026-07-14-canal-health-matrix-r8-p0-outage]] — probe inicial (session memory)
- [[2026-07-13-yolo-round-8-ruff-deadcode]] — R8 que originou o probe T2/T5

Modified by Gustavo Almeida — 2026-07-14 02:35 BRT
