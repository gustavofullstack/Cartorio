# CD EasyPanel Hook — Continuous Deploy (G7.22.T2)

| Campo | Valor |
|-------|--------|
| **Task** | G7.22.T2 — CD EasyPanel hook documentado |
| **Wave** | G7 Wave 25 |
| **Rein** | cartorio-sre / cartorio-brain |
| **Prod** | EasyPanel + Docker Swarm (Hostinger VPS) |
| **Regra** | Este doc **não muta prod** — só descreve o fluxo atual e o checklist pós-deploy |
| **Fontes** | `docs/DEPLOYMENT.md`, `.github/workflows/{cd,deploy,ci}.yml`, `scripts/deploy.sh`, `docs/OUTAGE_RECOVERY_RUNBOOK.md`, `docs/platforms/API_HEALTH_RADAR.md` |

---

## 0. TL;DR

```
PR merge → master
    │
    ├─► GitHub Actions CI (ci.yml) ──── quality gates (ruff/mypy/pytest/secrets)
    │
    ├─► GitHub Actions CD (cd.yml) ──── Render Ohio (staging/legado, NÃO é prod cartório)
    │
    ├─► GitHub Actions Deploy (deploy.yml)
    │       quality → SSH VPS → git pull → restart services → smoke
    │       (requer secrets VPS_*; pode falhar se path/compose não bater com Swarm real)
    │
    └─► EasyPanel (prod canônico)
            source: build a partir do git / imagem local Swarm
            trigger: UI "Deploy" | webhook/API (parcial) | docker service update
```

**Prod canônico do cartório = EasyPanel + Swarm em `187.77.236.77`**, não Render.  
Render (`cd.yml`) é caminho paralelo (free/Ohio) — útil para smoke externo, **não** substitui o stack VPS.

---

## 1. Como o CD funciona **hoje** (estado real)

### 1.1 Camadas

| Camada | O que dispara | Onde roda | Status |
|--------|---------------|-----------|--------|
| **CI** | push/PR → `ci.yml` | GitHub runners | **Ativo** — gates de qualidade |
| **CD Render** | push `master` paths `backend/**` → `cd.yml` | Render service Ohio | **Ativo** (legado/staging) |
| **Deploy VPS GHA** | push `master` / tag `v*` / manual → `deploy.yml` | SSH → VPS | **Parcial** — assume `git pull` + `docker compose` |
| **EasyPanel rebuild** | UI Deploy / git hook / API | Swarm service cartorio_system-api | **Canônico prod** |
| **`scripts/deploy.sh`** | manual local | tag + push + (TODO) API EasyPanel | **Hook EasyPanel ainda TODO** |

### 1.2 EasyPanel — modelo de fonte

Serviços do projeto `cartorio` no painel:

| Serviço Swarm | Imagem típica | Domínio |
|---------------|---------------|---------|
| cartorio_system-api | easypanel/cartorio/system-api:<tag> | api.2notasudi.com.br |
| `cartorio_n8n` | `n8nio/n8n:1.94.x` | `flow.2notasudi.com.br` |
| `cartorio_evolution-api` | `evolutionapi/evolution-api:v2.3.7` | `whatsapp.2notasudi.com.br` |
| `cartorio_chatwoot` (+ sidekiq) | `chatwoot/chatwoot:v3.x` | `chat.2notasudi.com.br` |
| `cartorio_openclaw-gateway` | openclaw gateway | `agent.2notasudi.com.br` |
| `cartorio_redis` | redis:8 | interno |
| supabase stack | self-hosted | `supbase.2notasudi.com.br` |
| easypanel + traefik | painel + LE | `easypanel.2notasudi.com.br` |

**API (backend deste repo):**

- **Build context:** raiz do repositório (`Dockerfile` na root; `COPY backend/…`).
- **Imagem local Swarm:** `easypanel/cartorio/api:<tag>` (ex.: `latest`, `turno22`, digests `@sha256:…`).
- **Registry alternativo documentado:** `gustavofullstack/cartorio-api:v0.6.0` (quando push externo).
- **Auto-deploy git:** quando o service no EasyPanel está ligado a um **Git source** (repo + branch `master`), um push/merge que o EasyPanel enxerga **pode** disparar rebuild. Em prática:
  1. Confirmar no UI: Service → **Source** → Git connected + branch + auto-deploy ON.
  2. Se auto-deploy **OFF** ou source for **image-only**: deploy é **manual** (botão Deploy / force update).
  3. Histórico real: rebuilds já ocorreram após push (ex. lesson TASKS P1.2 — push → task Starting → health 200), mas **não** se deve assumir 100% automático sem validar o toggle no painel.

### 1.3 O que **não** é o caminho prod

| Fluxo | Por quê não é prod cartório |
|-------|-----------------------------|
| Render `cd.yml` | Service Ohio free; stack incompleto (sem Evolution/N8N/Swarm cartório) |
| `docker compose` puro no laptop | Prod é **Swarm mode** sob EasyPanel |
| Commit direto em `master` sem PR | Viola regra de branch + review (AGENTS.md) |

---

## 2. Gatilhos operacionais (como fazer deploy)

### 2.1 Preferido — EasyPanel UI (seguro, auditável)

```
1. PR → review → merge em master
2. make qa   # local, antes/depois
3. https://easypanel.2notasudi.com.br
   → Project cartorio
   → Service cartorio_system-api
   → Deploy / Redeploy
4. Aguardar task Swarm 1/1
5. Smoke + radar (§5)
```

### 2.2 Force update Swarm (SSH Tailscale — com autorização)

```bash
# Host canônico Tailscale
ssh root@100.99.172.84

# Preflight sem mutação
infra/scripts/deploy_system_api.sh --check

# Só após revisão e autorização explícita do rollout
CARTORIO_DEPLOY_APPROVED=YES infra/scripts/deploy_system_api.sh --apply
```

**Swarm host-mode (port conflict):** se o service publicar porta em modo `host`, fazer **scale 0 → 1**, nunca 1→1 direto (AGENTS.md).

### 2.3 GitHub Actions `deploy.yml`

1. Quality job: ruff + mypy + pytest + n8n validator + openapi snapshot + secrets scan.
2. Deploy job (se quality OK): SSH com `VPS_SSH_KEY` → `git pull` em path configurado → `uv sync` / alembic (best-effort) → restart compose services.
3. Smoke: curl `/health`, N8N `/healthz`, radar expanded, OpenClaw.
4. Notifica Telegram (success/failure) se secrets de bot estiverem setados.

**Secrets GHA necessários (não commitar):**

| Secret | Uso |
|--------|-----|
| `VPS_HOST` | IP/host SSH (ex. Tailscale ou público) |
| `VPS_USER` | `root` ou `cartorio` |
| `VPS_SSH_KEY` | chave privada |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | notify opcional |
| `RENDER_API_KEY` | só `cd.yml` (Render) |
| `GITHUB_TOKEN` | auto (comments/issues) |

### 2.4 `scripts/deploy.sh` (local)

```bash
./scripts/deploy.sh staging   # ou prod
# 1 pre-check git
# 2 make qa / test-all
# 3 backup N8N workflow #09 se N8N_API_KEY set
# 4 tag + push
# 5 EasyPanel: se EASYPANEL_API_KEY → TODO trigger (ainda não implementado)
```

Hoje o passo 5 imprime **TODO: implementar trigger Easypanel** — ou seja, o “hook” documentado aqui **ainda depende de UI ou `docker service update`** até a API ser wired.

### 2.5 MCP EasyPanel (ops)

- Skill: `docs/platforms/MCP_SKILL_EASYPANEL.md`
- Tools típicos: `ep_login`, `ep_list_*`, `ep_deploy` (inventário em `scripts/mcp_manifest.json`)
- URL painel: `https://easypanel.2notasudi.com.br`
- Env locais (nomes apenas): `EASYPANEL_URL`, `EASYPANEL_API_KEY`, `EASYPANEL_PROJECT=cartorio` — ver `.env.example` / `docs/ENV_PRODUCTION.md`. **Nunca commitar valores.**

---

## 3. Variáveis de ambiente (deploy-relevant)

Fonte de verdade de **nomes** (não valores): `docs/ENV_PRODUCTION.md`, `docs/DEPLOYMENT.md`, EasyPanel UI → Service → Env.

### 3.1 Onde moram em prod

| Local | Conteúdo |
|-------|----------|
| EasyPanel UI → Env | overrides por serviço (persistidos no service spec) |
| VPS `/etc/easypanel/projects/cartorio/...` | files/volumes do projeto |
| Secrets host | `/etc/cartorio-backup/…`, chmod 600 |
| Mac dev | `~/.mavis/secrets/cartorio.env` (consulta local only) |

### 3.2 API (`cartorio_api`) — checklist mínimo

```bash
# Core
DATABASE_URL=postgresql+psycopg://...@...:5432/cartorio
REDIS_URL=redis://default:...@cartorio_redis:6379/0
ENVIRONMENT=production
LOG_LEVEL=INFO

# Segurança / LGPD
AUDIT_HMAC_KEY=<hex 64>
CARTORIO_API_KEY=<hex>
PII_SCRUB_ENABLED=true

# Integrações internas (DNS Swarm, não IP público frágil)
EVOLUTION_BASE_URL=http://cartorio_evolution-api:8080
EVOLUTION_API_KEY=...
N8N_BASE_URL=http://cartorio_n8n:5678
N8N_API_KEY=...
N8N_WEBHOOK_SECRET=...
OPENCLAW_BASE_URL=http://cartorio_openclaw-gateway:18789
OPENCLAW_API_KEY=...
SUPABASE_URL=http://cartorio_supabase-kong:8000
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...

# LLM (default isolado em testes via opencode_go)
LLM_DEFAULT_PROVIDER=opencode_go
OPENCODE_GO_API_KEY=...
OPENCODE_GO_BASE_URL=...
OPENCODE_GO_MODEL=...

# Webhooks
WEBHOOK_EVOLUTION_HMAC_SECRET=...
WEBHOOK_CHATWOOT_HMAC_SECRET=...
```

### 3.3 Gotchas de redeploy (lições reais)

1. **Env do Swarm pode reverter** se o source de verdade no EasyPanel UI não tiver as vars (Lesson VALIDATION_TURNO_20/21 — `OPENCODE_GO_*` sumiu após redeploy). Sempre gravar no **Env do service** no painel, não só no container vivo.
2. **DATABASE_URL legada** com IP externo/`supabase_admin` errado derruba Evolution/Chatwoot/N8N (Lesson 176) → 502 com Traefik OK.
3. **Secrets nunca no git**; `scripts/check_no_literal_keys.py` e `scripts/secrets_scan.py` no CI.
4. **Alembic:** preferir `make -C backend alembic-up` com DB de prod **só** com aprovação; single head documentado em `docs/ALEMBIC_HEADS_REPORT_G7.md`.

---

## 4. Pré-deploy (gate humano + CI)

```bash
# Na raiz do repo
make pre-commit          # lint + test-fast
make qa                  # lint + test com coverage gate (mesmo do CI)

# Opcional composite G7
make g7-composite        # exit 0 local OK; exit 2 = prod HOLD (dns/radar)
```

Checklist curto:

- [ ] Branch from `master`, PR com template completo
- [ ] Sem PII/secrets no diff
- [ ] Mudança em `audit*` / `pii*` → sign-off `cartorio-lgpd`
- [ ] Backup se mexer schema/DB (`docs/BACKUP_DRYRUN_REPORT_G7_WAVE24.md`)
- [ ] Janela de deploy alinhada com escrevente se for canal WhatsApp

---

## 5. Health **depois** do deploy

### 5.1 Ordem mínima (API)

```bash
# 1) Liveness
curl -fsS -o /dev/null -w 'health %{http_code}\n' https://api.2notasudi.com.br/health
# esperado: 200

# 2) Readiness (DB + audit init)
curl -fsS -o /dev/null -w 'ready %{http_code}\n' https://api.2notasudi.com.br/ready
# esperado: 200

# 3) Radar multi-serviço
curl -sS https://api.2notasudi.com.br/api/v1/health/radar | python3 -m json.tool
# esperado: status green (ou red com lista clara de offline)

# 4) Radar expanded (DNS/Traefik/SSH/disk) — exige imagem com endpoint
curl -sS -o /dev/null -w 'radar/expanded %{http_code}\n' \
  https://api.2notasudi.com.br/api/v1/health/radar/expanded
# esperado: 200 (HOLD se 404 = imagem antiga sem expanded)

# 5) Smoke Makefile (se disponível)
make -C backend smoke
# ou: make radar-smoke  (quando target existir)
```

### 5.2 Domínios edge (5–10 s cada)

```bash
for d in api flow whatsapp chat agent supbase easypanel; do
  code=$(curl -sk -o /dev/null -m 10 -w '%{http_code}' "https://$d.2notasudi.com.br/")
  echo "$d.2notasudi.com.br → $code"
done
```

Interpretação rápida (ver `docs/PLAYBOOK_502_VS_NXDOMAIN_G7.md`):

| HTTP | Significado pós-deploy |
|------|-------------------------|
| 200/301/302 | Edge + upstream respondendo |
| 502 | Traefik OK, **upstream** down/crashloop |
| 404 easypanel page | Router/serviço ausente |
| 000 + NXDOMAIN | DNS, não é deploy da API |

### 5.3 Logs se falhar

```bash
docker service ps cartorio_api
docker service logs --tail 100 cartorio_api
# Se host-mode stuck: docker service scale cartorio_api=0 && docker service scale cartorio_api=1
```

---

## 6. Rollback

### 6.1 EasyPanel UI (preferido)

1. `easypanel.2notasudi.com.br` → projeto `cartorio` → serviço.
2. Aba **Deployments** → último deploy **GREEN**.
3. **Rollback to this deployment**.
4. Re-rodar §5.

### 6.2 Swarm por digest

```bash
docker service ps cartorio_api --no-trunc
# anotar easypanel/cartorio/api@sha256:<digest_bom>
docker service update --image easypanel/cartorio/api@sha256:<digest_bom> cartorio_api
sleep 30
curl -fsS https://api.2notasudi.com.br/health
```

### 6.3 Git revert + redeploy

```bash
git revert <sha_ruim>
# PR + merge
# EasyPanel Deploy ou force update
```

### 6.4 Banco

**Nunca** restore de Postgres sem alinhamento explícito com Gustavo (perda irreversível). Ver `docs/OUTAGE_RECOVERY_RUNBOOK.md` §5.3.

Redis: restart ok (cache/idempotency 24h se repovoa).

---

## 7. Radar check pós-deploy (contrato de aceite)

| Check | Critério WORK | HOLD / FAIL |
|-------|---------------|-------------|
| `/health` | 200 | 502/000 = rollback ou recovery |
| `/ready` | 200 | DB/audit não ready |
| `/api/v1/health/radar` | `status=green` **ou** red **explicado** (só serviços known-broken SUI) | red inesperado em `database`/`redis` = FAIL |
| `/radar/expanded` | 200 JSON | 404 = imagem sem feature (redeploy API) |
| DNS aliases `chatwoot`/`n8n`/`supabase` | A → `187.77.236.77` | NXDOMAIN = SUI Cloudflare (não rollback de app) |
| `make g7-composite` | exit 0 (local) / exit 2 se só prod HOLD | exit 1 = quebrou quality local |

**Aceite de deploy da API (mínimo):** health+ready 200 **e** radar alcançável.  
**Aceite de go-live canal WhatsApp:** ver `docs/MVP_CUTLINE_G7.md` (QR open + 1 msg emolumento).

---

## 8. Diagrama mental (prod)

```
GitHub (master)
    │ CI green
    ▼
EasyPanel build/pull image ──► Swarm service cartorio_* 
    │                              │
    │                              ▼
    │                         Traefik + LE (TLS)
    │                              │
    ▼                              ▼
Env no service spec          *.2notasudi.com.br
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
                 /health    /health/radar   canais (WA/TG)
```

---

## 9. Gaps conhecidos (não fechar sem task)

| Gap | Impacto | Follow-up |
|-----|---------|-----------|
| `deploy.sh` EasyPanel API TODO | Hook semiauto incompleto | implementar `ep_deploy` / REST deploy |
| Dual CD Render vs EasyPanel | confusão de “prod” | manter Render como non-prod ou desligar |
| `deploy.yml` compose path | pode não espelhar Swarm EasyPanel | alinhar SSH script a `docker service update` |
| Auto-deploy git toggle | comportamento “às vezes” | documentar screenshot/toggle no painel (SUI) |

---

## 10. Referências

- `docs/DEPLOYMENT.md` — step-by-step stack
- `docs/ENV_PRODUCTION.md` — nomes de env
- `docs/OUTAGE_RECOVERY_RUNBOOK.md` — ordem redeploy + rollback
- `docs/PLAYBOOK_502_VS_NXDOMAIN_G7.md` — diagnóstico edge
- `docs/platforms/API_HEALTH_RADAR.md` — contrato radar
- `docs/platforms/MCP_SKILL_EASYPANEL.md` — skill painel
- `.harness/SUI_CHECKLIST.md` — blockers UI Gustavo
- `.github/workflows/ci.yml` / `cd.yml` / `deploy.yml`

---

**Modified by Gustavo Almeida** — G7 Wave 25 (G7.22.T2)
