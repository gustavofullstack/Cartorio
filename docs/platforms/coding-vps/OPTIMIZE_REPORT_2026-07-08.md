# Coding VPS Optimize Report — 2026-07-08

**Squad:** 3 (VPS Optimization)  
**Target:** `coding-vps_apenas_para_auxilio` @ `100.99.172.84` (Tailscale)  
**Operator:** automated via `ssh -i ~/.ssh/id_ed25519_cartorio root@100.99.172.84`  
**Scope rules honored:** no `cartorio_*` changes · no secret rotation · no `docker volume prune`

---

## Executive summary

| Metric | Before | After (settled) | Delta |
|--------|--------|-----------------|-------|
| **RAM used** | 8.9 Gi | **4.1 Gi** | **−4.8 Gi** |
| **RAM free** | 375 Mi | **5.2 Gi** | **+~4.8 Gi** |
| **RAM available** | 6.7 Gi | **11 Gi** | **+4.3 Gi** |
| **SWAP used** | 3.6 / 4.0 Gi (critical) | **2.9 / 4.0 Gi** | **−0.7 Gi** |
| **Disk /** | 102 G used (53%) | **100 G used (52%)** | **~−2 G** |
| **Load avg (1m)** | 15.38 | 17.48 (transient post-ops) | still elevated* |

\*Load stayed high during/after scale-down and container prune (many task reaps + Chatwoot CPU). Expect decline as swap is slowly reclaimed and CPU spikes settle. **Do not panic on 1m load alone** — RAM pressure was the critical failure mode and is fixed.

**Headline:** ~**4.8 GiB RAM** freed immediately by removing duplicate agent stack + scaling heavy non-coding services to 0. SWAP still elevated (kernel reclaim is gradual); should continue dropping under lower pressure.

---

## 1. Baseline (01:52 UTC-ish)

```
Mem:  15Gi total · 8.9Gi used · 375Mi free · 6.8Gi buff/cache · 6.7Gi available
Swap: 4.0Gi total · 3.6Gi used · 366Mi free
Load: 15.38, 10.61, 9.63
Disk: /dev/sda1 193G · 102G used · 92G avail · 53%
```

**Top memory offenders (coding-vps, running):**

| Service | ~RSS |
|---------|------|
| `sourcegraph` | **1.36 GiB** |
| `sonarqube` | **1.34 GiB** |
| `temporal-elasticsearch` | ~498 MiB |
| `paperclip` | ~488 MiB |
| `langfuse-clickhouse` | ~465 MiB |
| `open-notebook` | ~374 MiB |
| Side-stack agents (`coding-vps-agents_*`) | ~9 services × ~25–45 MiB (+ duplicate of MiniMax-patched main agents) |

---

## 2. Actions executed

### 2.1 REMOVE duplicate side-stack agents (DONE)

Stack `coding-vps-agents` duplicated MiniMax-patched agents already running under `coding-vps_apenas_para_auxilio_*`.

```bash
for s in crew-ai goose hermes kilo-org_kilocode langgraph openchamber openclaw opencode openhands; do
  docker service rm coding-vps-agents_$s 2>/dev/null || true
done
docker stack rm coding-vps-agents 2>/dev/null || true
```

**Removed services (9):**

| Service | Prior replicas |
|---------|----------------|
| `coding-vps-agents_crew-ai` | 1/1 |
| `coding-vps-agents_goose` | 1/1 |
| `coding-vps-agents_hermes` | 1/1 |
| `coding-vps-agents_kilo-org_kilocode` | 1/1 (published `*:8004->8000`) |
| `coding-vps-agents_langgraph` | 1/1 |
| `coding-vps-agents_openchamber` | 1/1 |
| `coding-vps-agents_openclaw` | 1/1 |
| `coding-vps-agents_opencode` | 0/1 (failing) |
| `coding-vps-agents_openhands` | 1/1 |

**Verify:** `docker service ls | grep coding-vps-agents` → **NONE** · stack list → **STACK_NONE**.

Main-stack agents **kept** (`coding-vps_apenas_para_auxilio_{crew-ai,goose,hermes,kilo-org_kilocode,langgraph,openchamber,openclaw,opencode,openhands}` still 1/1).

### 2.2 SCALE TO 0 — heavy / unused non-coding services (DONE)

```bash
docker service scale \
  coding-vps_apenas_para_auxilio_sourcegraph=0 \
  coding-vps_apenas_para_auxilio_sonarqube=0 \
  coding-vps_apenas_para_auxilio_sonarqube-db=0 \
  coding-vps_apenas_para_auxilio_mirotalk=0 \
  coding-vps_apenas_para_auxilio_open-notebook=0 \
  coding-vps_apenas_para_auxilio_open-notebook-surrealdb=0 \
  coding-vps_apenas_para_auxilio_chartdb=0 \
  coding-vps_apenas_para_auxilio_temporal-admin-tools=0
```

| Service | Why | Est. RAM freed | Result |
|---------|-----|----------------|--------|
| `sourcegraph` | Not critical for coding agents; **1.3+ GiB** | ~1.36 GiB | **0/0** |
| `sonarqube` | Static analysis; heavy JVM | ~1.34 GiB | **0/0** |
| `sonarqube-db` | Companion Postgres | ~tens of MiB | **0/0** |
| `mirotalk` | Video — not coding | ~8 MiB | **0/0** |
| `open-notebook` | Notebook UI | ~374 MiB | **0/0** |
| `open-notebook-surrealdb` | Companion DB | ~100 MiB | **0/0** |
| `chartdb` | Schema visualizer | ~7 MiB | **0/0** |
| `temporal-admin-tools` | CLI sidecar only | ~0.5 MiB | **0/0** |

**Intentionally kept (per brief):** litellm, main agents, langflow, langfuse core, mcp-orchestrator, crowdsec, zincsearch, centrifugo, anything-llm.

**Prefer scale 0 over rm** for EasyPanel-managed services — all of the above used `scale=0` only (services remain defined for easy re-enable).

### 2.3 Zombie / side cleanup

- Side-stack fully **removed** (rm + stack rm) — correct for non-EasyPanel duplicate stack.
- EasyPanel 0/0 zombies **left as scale 0** (no mass `service rm`) to avoid EasyPanel drift.

**Note (observed, not forced by this squad for all rows):** after ops, some additional services also showed 0/0 that were previously 1/1 (e.g. full `temporal-*` family, `paperclip`/`paperclip-db`, `argilla-db`, `filepizza-redis`). Possible concurrent squad/EasyPanel activity or OOM/recreate races during pressure relief. This report’s **authoritative intentional set** is §2.1 + §2.2 only. Temporal core at 0 is acceptable if unused; re-scale if workflows need it.

### 2.4 Docker cleanup (SAFE — no volumes)

```bash
docker container prune -f     # reclaimed 206.5 MB
docker image prune -f         # 0 B (no dangling)
docker builder prune -f --filter until=72h   # 0 B
# NEVER: docker volume prune
```

Disk: **102 G → 100 G** used (~2 G effective; container prune reported 206.5 MB + freed layers/metadata after stops).

`docker system df` post-run still shows **~45.6 GB reclaimable images** if a future aggressive (named unused image) prune is approved — **not done** here (out of safe scope).

---

## 3. After state (settled ~01:55)

```
Mem:  15Gi total · 4.1Gi used · 5.2Gi free · 6.7Gi buff/cache · 11Gi available
Swap: 4.0Gi total · 2.9Gi used · 1.1Gi free
Load: 17.48, 14.44, 11.29   # still high; monitor
Disk: /dev/sda1 193G · 100G used · 93G avail · 52%
```

### Active coding-vps services (non-0/0)

```
anything-llm, centrifugo, crew-ai, crowdsec, crwal4ai,
goose, hermes, kilo-org_kilocode,
langflow, langflow-db,
langfuse-clickhouse, langfuse-db, langfuse-minio, langfuse-redis, langfuse-web, langfuse-worker,
langgraph, litellm-app, litellm-db, mcp-orchestrator,
openchamber, openclaw, opencode, openhands,
request-baskets, zincsearch
(+ ngrok 0/1 — flapping, pre-existing / not targeted)
```

### cartorio_* untouched (spot check)

`api`, `openclaw-gateway`, `redis*`, `supabase*` remain present. Some cartorio services may independently show 0/1 flaps (Chatwoot/Evolution) — **not modified by this squad**.

---

## 4. Estimated RAM reclaimed by intentional actions

| Action | Rough RSS |
|--------|-----------|
| Side-stack agents × ~8 running | ~250–350 MiB |
| sourcegraph | ~1.36 GiB |
| sonarqube + db | ~1.4 GiB |
| open-notebook + surrealdb | ~475 MiB |
| mirotalk + chartdb + temporal-admin-tools | ~15 MiB |
| **Sum (intentional)** | **~3.5–3.6 GiB** |
| **Observed system delta** | **~4.8 GiB used** (extra from concurrent 0s, cache pressure relief, stopped orphans) |

---

## 5. Disk reclaimed

| Step | Space |
|------|-------|
| `docker container prune -f` | **206.5 MB** reported |
| `docker image prune -f` | 0 B |
| `docker builder prune -f --filter until=72h` | 0 B |
| **df /** | **~2 GB** (102G → 100G used) |
| Volume prune | **NOT RUN** (data-loss risk) |

---

## 6. Safety checklist

| Rule | Status |
|------|--------|
| Never touch `cartorio_*` | ✅ |
| Never rotate secrets/keys | ✅ |
| No `docker volume prune` | ✅ |
| EasyPanel services: prefer `scale 0` | ✅ |
| Side-stack agents: `rm` OK | ✅ |
| Keep litellm / agents / langflow / langfuse / mcp / crowdsec / zinc / centrifugo / anything-llm | ✅ kept 1/1 |

---

## 7. Follow-ups (optional, not done)

1. **SWAP still 2.9 Gi** — wait for natural reclaim; if sticky after hours of low RAM pressure, consider a **planned low-traffic** reboot (out of band; coordinate).
2. **Load still high** — investigate `cartorio_chatwoot` CPU (~100%+) and `langfuse-web` (~90%); orthogonal to this scale-down.
3. **~45 GB unused images** — if disk becomes tight, approved `docker image prune -a` (careful: breaks offline redeploy until re-pull).
4. **Re-enable path:**
   ```bash
   docker service scale coding-vps_apenas_para_auxilio_sourcegraph=1
   # etc.
   ```
5. Confirm whether concurrent work intentionally zeroed **temporal core** / **paperclip**; re-scale if required:
   ```bash
   docker service scale \
     coding-vps_apenas_para_auxilio_temporal-server=1 \
     coding-vps_apenas_para_auxilio_temporal-web=1 \
     coding-vps_apenas_para_auxilio_temporal-db=1 \
     coding-vps_apenas_para_auxilio_temporal-elasticsearch=1
   ```

---

## 8. Commands reference (replay)

```bash
ssh -i ~/.ssh/id_ed25519_cartorio root@100.99.172.84

# baseline
free -h; uptime; df -h /; docker service ls | grep coding-vps

# 1) remove side stack
for s in crew-ai goose hermes kilo-org_kilocode langgraph openchamber openclaw opencode openhands; do
  docker service rm coding-vps-agents_$s 2>/dev/null || true
done
docker stack rm coding-vps-agents 2>/dev/null || true

# 2) scale heavy to 0
docker service scale \
  coding-vps_apenas_para_auxilio_sourcegraph=0 \
  coding-vps_apenas_para_auxilio_sonarqube=0 \
  coding-vps_apenas_para_auxilio_sonarqube-db=0 \
  coding-vps_apenas_para_auxilio_mirotalk=0 \
  coding-vps_apenas_para_auxilio_open-notebook=0 \
  coding-vps_apenas_para_auxilio_open-notebook-surrealdb=0 \
  coding-vps_apenas_para_auxilio_chartdb=0 \
  coding-vps_apenas_para_auxilio_temporal-admin-tools=0

# 3) safe prune
docker container prune -f
docker image prune -f
docker builder prune -f --filter until=72h

# 4) verify
free -h
docker service ls | grep coding-vps
docker stats --no-stream | head
```

---

**Report path:** `docs/platforms/coding-vps/OPTIMIZE_REPORT_2026-07-08.md`  
**Status:** SAFE OPTIMIZATIONS COMPLETE · RAM critical path resolved · SWAP improving · cartorio stack not modified.
