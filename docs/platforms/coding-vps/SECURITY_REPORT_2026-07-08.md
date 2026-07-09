# Squad 4 — Security Hardening Report (coding-vps)

| Field | Value |
|---|---|
| **Date** | 2026-07-08 / 2026-07-09 UTC |
| **Squad** | 4 — Security Hardening |
| **Host** | `vps-cartorio` / `srv1769726` (Ubuntu 24.04.4 LTS, kernel 6.8.0-124) |
| **Public IP** | `187.77.236.77` |
| **Tailscale IP** | `100.99.172.84` |
| **SSH** | `ssh -i ~/.ssh/id_ed25519_cartorio root@100.99.172.84` |
| **Mode** | READ + SAFE FIX only (no destructive lockouts, no key rotation, no Tailscale ACL changes) |

Related prior work (same day):

- [`docs/operations/F9-FIREWALL-REPORT-2026-07-08.md`](../../operations/F9-FIREWALL-REPORT-2026-07-08.md) — public port lockdown for Redis/PG/pgweb/etc.
- [`docs/security/SECRETS_MIGRATION_REPORT_2026-07-08.md`](../../security/SECRETS_MIGRATION_REPORT_2026-07-08.md) — Swarm secrets mount (env plaintext still present by design).

---

## 1. Executive summary

Overall posture is **better than average** for a multi-stack VPS: default INPUT **DROP**, Tailscale mesh online, fail2ban active on `sshd`, Monarx agent active, and F2/F9 iptables rules already restrict many admin UIs (EasyPanel `:3000`, Evolution `:8080`, Redis `:1001`, Supabase PG `:5094`, pgweb `:8082`, Jaeger `:16686`, OpenClaw `:18789`, OTel debug ports) to **Tailscale CGNAT `100.64.0.0/10`**.

**One critical gap was found and fixed by Squad 4:**

| Item | Before | After (Squad 4) |
|---|---|---|
| `mcp-orchestrator` **:8100** | Published `0.0.0.0:8100`, HTTP **200**, **no** TS-only rules | Tailscale-only via INPUT + DOCKER-USER + `raw:PREROUTING`; persisted in `/etc/iptables/rules.v4` |

**Remaining high-priority risks (not auto-changed):**

1. **DOCKER-USER drops public `:443` / `:80`** while INPUT accepts them — may block public Traefik HTTPS (counter ~1.8k DROPs on 443). Confirm whether production domains must be public.
2. **SSH `PasswordAuthentication` effectively `yes`** (cloud-init conf conflict); root is `PermitRootLogin prohibit-password` (key-only for root).
3. **Secrets still live in skill files / env plaintext** (repo + Swarm env) — migrate to env/secrets only; do not rewrite all skills in this pass.
4. **CrowdSec** runs as a **Swarm container** with CAPI decisions but **no host firewall bouncer** — bans are not enforced on host INPUT.
5. Residual **UFW chains** remain while `ufw` binary is uninstalled (`rc` package) — policy is hybrid/manual iptables.

---

## 2. Checklist results

### 2.1 Firewall

| Check | Result |
|---|---|
| `ufw status verbose` | **Unavailable** — package `ufw` is `rc` (removed, config residual); binary missing |
| INPUT policy | **DROP** (good) |
| Persistence | `netfilter-persistent` **enabled/active**; rules in `/etc/iptables/rules.v4` + `rules.v6` |
| Residual UFW chains | Still hooked in INPUT/FORWARD (`ufw-before-input`, `ufw-user-input`, …) |
| F2 / F9 comments | Present on EasyPanel, Evo, Redis, PG, pgweb, OpenClaw, Jaeger, OTel, iperf3 |

**ufw-user-input residual allows (if traffic reaches it):**

- TCP 22, 80, 443, 3000 from **anywhere**
- Swarm 2377/7946 only from `10.0.0.0/8`, `172.16.0.0/12`, `100.64.0.0/10`
- All traffic from `tailscale0`

Earlier F2/F9 ACCEPT-TS + DROP rules and DOCKER-USER rules usually short-circuit Docker-published admin ports **before** residual UFW accepts. SSH is the main service that still leans on UFW/fail2ban for public exposure control.

### 2.2 Listening ports (`ss -tlnp`)

| Bind | Port | Process | Notes |
|---|---|---|---|
| `0.0.0.0` | 22 | sshd | Public path possible via UFW residual |
| `0.0.0.0` | 80, 443 | docker-proxy (Traefik) | DOCKER-USER currently DROPs non-TS |
| `0.0.0.0` | 3000 | docker-proxy (EasyPanel) | F2 TS-only in DOCKER-USER + INPUT DROP late |
| `0.0.0.0` | 8080 | docker-proxy (Evolution) | F2 TS-only |
| `0.0.0.0` | 8082 | docker-proxy (pgweb) | F9 TS-only |
| `0.0.0.0` | 5094 | docker-proxy (Supabase PG) | F9 TS-only |
| `0.0.0.0` | 1001 | docker-proxy (Redis) | F9 TS-only |
| `0.0.0.0` | 18789 | docker-proxy (OpenClaw GW) | F9 TS-only |
| `0.0.0.0` | 16686 | docker-proxy (Jaeger UI) | F9 TS-only |
| `0.0.0.0` | 8889, 14317, 14318 | OTel collector | F9 TS-only |
| `0.0.0.0` | **8100** | docker-proxy (**mcp-orchestrator**) | **Was public; locked by Squad 4** |
| `*` | 2377, 7946 | dockerd (Swarm) | UFW limits to private + TS nets |
| `*` | 5201 | **iperf3 -s** | F9 TS-only on INPUT; process still running |
| `127.0.0.1` | 65529 | monarx-agent | Local only |
| `100.99.172.84` | 51811 | tailscaled | TS |
| `127.0.0.53/54` | 53 | systemd-resolve | Local DNS |

Most **coding-vps** heavy UIs (Langfuse, SonarQube, AnythingLLM, OpenHands, LiteLLM, Temporal Web, etc.) are **overlay-only** (no host publish) — correct pattern.

### 2.3 Tailscale

```
100.99.172.84   vps-cartorio             gustavomar.fullstack@  linux    -
100.83.180.16   macbook-pro-gus          gustavomar.fullstack@  macOS    active (direct)
… + iPhones / other Macs / Windows (some offline)
100.110.127.44  triqhub                  gustavomar.fullstack@  linux    idle; offers exit node
```

- Mesh healthy; VPS is online as `vps-cartorio`.
- **No ACL changes** made (per safe rules).
- Admin access model assumes operators use Tailscale for EasyPanel, pgweb, Redis, OpenClaw, etc.

### 2.4 Docker published ports (public IP vs overlay)

#### Host-published (`0.0.0.0` / `::`) — must be firewall-guarded

| Port | Service | Public intended? | Firewall status |
|---|---|---|---|
| 80/443 | easypanel-traefik | Prod HTTPS / webhooks | **Ambiguous** — INPUT ACCEPT all 443; DOCKER-USER DROP non-TS 443/80 |
| 3000 | easypanel | Admin UI | TS-only (F2) — **keep Tailscale-only** |
| 8080 | evolution-api | Admin/API | TS-only (F2) |
| 8082 | pgweb | DB UI (no auth) | TS-only (F9) |
| 5094 | supabase PG | DB | TS-only (F9) |
| 1001 | redis | Cache | TS-only (F9) |
| 18789 | openclaw-gateway | LLM gateway | TS-only (F9) |
| 16686 | jaeger UI | Observability | TS-only (F9) |
| 8889/14317/14318 | otel | Debug | TS-only (F9) |
| **8100** | **mcp-orchestrator** | Internal MCP | **TS-only after Squad 4** |

#### Overlay / internal only (good)

Dozens of `coding-vps_apenas_para_auxilio_*` services expose only container ports (8001, 5432, 6379, 9000, …) without host publish. Swarm overlay is the right isolation layer for these.

### 2.5 CrowdSec

| Layer | Status |
|---|---|
| Host systemd `crowdsec` | **inactive / not-found** (no `/etc/crowdsec`) |
| Swarm service `coding-vps_…_crowdsec` | **Running** |
| In-container `cscli metrics` | CAPI decisions present (e.g. ~10k `http:scan`, ~4.6k `ssh:bruteforce`) |
| Host firewall bouncer | **Not active** (`crowdsec-firewall-bouncer` inactive) |

**Verdict:** CrowdSec is **observational / community-signal only** on this host unless a bouncer (or Traefik bouncer) is wired. Do not assume IPs are banned at the host.

### 2.6 fail2ban

| Item | Value |
|---|---|
| Service | **active + enabled** |
| Jails | `sshd` only |
| Currently banned | 0 |
| Total failed (sshd) | 2 |
| Total banned | 0 |

Adequate baseline for SSH; no jails for HTTP/Traefik/Docker.

### 2.7 SSH config (report only — no password disable)

**Effective (`sshd -T`):**

| Directive | Effective value |
|---|---|
| Port | 22 |
| PermitRootLogin | `without-password` (= `prohibit-password`) |
| PubkeyAuthentication | yes |
| PasswordAuthentication | **yes** |
| KbdInteractiveAuthentication | no |
| PermitEmptyPasswords | no |
| X11Forwarding | **yes** |
| MaxAuthTries | 6 |

**Conflicting drop-ins:**

```
/etc/ssh/sshd_config.d/50-cloud-init.conf     → PasswordAuthentication yes
/etc/ssh/sshd_config.d/60-cloudimg-settings.conf → PasswordAuthentication no
```

OpenSSH uses **first obtained value**; `50-…` wins → passwords enabled for non-root users.

**Root keys:** `/root/.ssh/authorized_keys` present (~111 bytes, one `ssh-ed25519` key; file may lack trailing newline — `wc -l` reports 0). Key login **works** (this audit used it).

**SAFE recommendation (not applied):**

1. Confirm a second break-glass key or console access (Hostinger panel).
2. Then set `PasswordAuthentication no` in a single explicit drop-in (e.g. `99-hardening.conf`) and remove/override `50-cloud-init.conf`.
3. Optionally `X11Forwarding no`.
4. Do **not** change `PermitRootLogin` without ensuring key path stays valid.

### 2.8 Secrets in repo skill files

Observed pattern (also covered by Squad 6 secrets migration report):

- MCP skill docs under `docs/platforms/MCP_SKILL_*.md` and agent skill trees may still document or embed operational tokens.
- Swarm migration mounted Docker secrets but **kept env plaintext** for compatibility.

**Recommendation (document only — do not rewrite all skills here):**

1. Move all live credentials to **environment / Docker Swarm secrets / vault** only.
2. Skills should reference **variable names** and retrieval commands, never raw values.
3. Rotate any secret that has ever been committed once migration is complete (out of scope for Squad 4 — user rule: no rotation in this pass).
4. Track remaining plaintext env in a follow-up for `cartorio-n8n` / ops.

---

## 3. Open ports — risk ranking

| Rank | Port | Service | Exposure (intent) | Risk | Rationale |
|---|---|---|---|---|---|
| **P0** | 5094 | Postgres (Supabase) | Bind 0.0.0.0; **TS-only** firewall | Critical if FW fails | Full DB; F9 protects; monitor persistence |
| **P0** | 1001 | Redis | Bind 0.0.0.0; **TS-only** | Critical if FW fails | Often unauth; F9 protects |
| **P0** | 8082 | pgweb | Bind 0.0.0.0; **TS-only** | Critical if FW fails | No auth UI; F9 protects |
| **P1** | 3000 | EasyPanel | Bind 0.0.0.0; **TS-only** | High | Full stack admin; must stay TS-only |
| **P1** | 18789 | OpenClaw GW | Bind 0.0.0.0; **TS-only** | High | LLM/tool gateway |
| **P1** | **8100** | **mcp-orchestrator** | Was public; **now TS-only (F4)** | High → mitigated | MCP surface; HTTP 200 without auth |
| **P1** | 8080 | Evolution API | Bind 0.0.0.0; **TS-only** | High | WhatsApp stack control plane |
| **P1** | 443/80 | Traefik | Public intent vs DOCKER-USER DROP | High (config risk) | Policy conflict; verify prod reachability |
| **P2** | 22 | SSH | Public + fail2ban; root key-only | Medium | Password auth still on for non-root |
| **P2** | 16686 | Jaeger UI | TS-only | Medium | Trace metadata leakage |
| **P2** | 2377/7946 | Swarm | Private/TS via UFW | Medium | Control plane; keep off public |
| **P3** | 5201 | iperf3 | TS-only; process still up | Low–Med | Bandwidth abuse if exposed |
| **P3** | 8889/14317/14318 | OTel | TS-only | Low–Med | Telemetry injection/scraping |
| **P3** | Overlay UIs | Langfuse, Sonar, etc. | No host publish | Low (host) | Risk is Traefik route misconfig, not host bind |

---

## 4. Actions taken (Squad 4)

### 4.1 Applied (safe)

**Lock `mcp-orchestrator` TCP/8100 to Tailscale CGNAT only** (same defense-in-depth pattern as F9):

```bash
# DOCKER-USER
iptables -I DOCKER-USER 1 -s 100.64.0.0/10 -p tcp --dport 8100 -m comment --comment "F4-TS-MCP-ORCH" -j ACCEPT
iptables -I DOCKER-USER 2 -p tcp --dport 8100 -m comment --comment "F4-DROP-MCP-ORCH" -j DROP

# INPUT
iptables -I INPUT 1 -s 100.64.0.0/10 -p tcp --dport 8100 -m comment --comment "F4-IN-TS-MCP-ORCH" -j ACCEPT
iptables -I INPUT 2 -p tcp --dport 8100 -m comment --comment "F4-IN-DROP-MCP-ORCH" -j DROP

# raw PREROUTING (before Docker DNAT → 172.16.1.5:8100)
iptables -t raw -I PREROUTING 1 -s 100.64.0.0/10 -p tcp --dport 8100 -m comment --comment "F4-RAW-TS-MCP-ORCH" -j ACCEPT
iptables -t raw -I PREROUTING 2 -p tcp --dport 8100 -m comment --comment "F4-RAW-DROP-MCP-ORCH" -j DROP

iptables-save > /etc/iptables/rules.v4
```

**Validation:**

| Source | Result |
|---|---|
| `http://100.99.172.84:8100/` (Tailscale) | **HTTP 200** |
| Public IP path | Dropped by F4 rules (DNAT path covered in `raw` + DOCKER-USER) |
| Persistence | Written to `/etc/iptables/rules.v4` (~370 lines); `netfilter-persistent` enabled |

### 4.2 Explicitly NOT applied (safe constraints)

| Action | Why skipped |
|---|---|
| Disable SSH password auth | Risk of lockout if key path incomplete; document only |
| Change Tailscale ACLs | Requires confirmation data |
| Rotate API keys / rewrite skills | User rule + out of scope |
| Re-enable/remove UFW package | Residual chains in use; full UFW redesign is multi-squad |
| Wire CrowdSec host bouncer | Needs design (false positive lockout risk) |
| Stop iperf3 | Optional; already TS-filtered |
| Rebind Docker publishes to `100.x` only | Requires service update; FW already enforces TS-only for admin ports |
| “Fix” DOCKER-USER 443 DROP | Could open or break production; needs product confirmation |

---

## 5. Hardening checklist (ops)

### Already in good shape

- [x] INPUT default DROP  
- [x] Tailscale installed and mesh members present  
- [x] EasyPanel `:3000` restricted to Tailscale (F2)  
- [x] High-risk data ports (PG/Redis/pgweb) restricted (F9)  
- [x] fail2ban `sshd` jail enabled  
- [x] Root SSH password login disabled (`prohibit-password`)  
- [x] iptables persistence via netfilter-persistent  
- [x] Monarx agent active  
- [x] coding-vps heavy UIs mostly overlay-only (no host publish)  
- [x] mcp-orchestrator `:8100` TS-only (F4)

### Recommended next steps (priority order)

1. **[P0-verify] Public HTTPS / Telegram path**  
   - From an off-Tailscale network, test `https://api.2notasudi.com.br` and Telegram webhook delivery.  
   - If production must be public: add DOCKER-USER exceptions for required sources (or remove blanket F2-DU-HTTPS-DROP) **without** opening admin UIs.  
   - If intentional TS-only edge: document clearly and keep Telegram on an alternate path.

2. **[P1] SSH hardening (after break-glass confirmed)**  
   - Single drop-in: `PasswordAuthentication no`.  
   - Ensure `authorized_keys` has trailing newline; add second key.  
   - Consider `AllowUsers root` or non-root + `sudo`, `X11Forwarding no`.

3. **[P1] Rebind or unpublish host ports long-term**  
   - Prefer `published: 8100, mode: host` bound only via TS IP, or remove host publish and use Traefik on TS.  
   - Same for 3000/8080/8082/5094/1001/18789 when EasyPanel/Swarm allows.

4. **[P1] Secrets**  
   - Env/Swarm secrets only; strip literals from skills and docs.  
   - Complete plaintext env removal after consumers read `/run/secrets/*`.  
   - Then rotate (separate change window).

5. **[P2] CrowdSec**  
   - Either install `crowdsec-firewall-bouncer-iptables` on host, or Traefik bouncer for HTTP.  
   - Or remove unused container to reduce noise.

6. **[P2] fail2ban expansion**  
   - Optional jails for recidive; avoid blind HTTP bans without Traefik log parsing.

7. **[P2] Clean hybrid firewall**  
   - Choose **one** control plane: pure iptables+nft **or** reinstall UFW with explicit policy.  
   - Document F2/F9/F4 rule scripts under `/usr/local/sbin/` and run from a systemd unit after Docker.

8. **[P3] iperf3**  
   - Stop when not measuring (`systemctl`/kill `iperf3 -s`); keep F9 TS-only rules.

9. **[P3] IPv6 parity**  
   - Confirm F9/F4-style port locks exist on `ip6tables` for the same services (F2 has partial v6 on 8080).

---

## 6. Recommended EasyPanel `:3000` lockdown (document)

**Current (already enforced):**

- Docker still publishes `0.0.0.0:3000->3000`.  
- DOCKER-USER: ACCEPT `100.64.0.0/10` → DROP others (`F2-DU-EASYPANEL-*`).  
- Operators reach UI via Tailscale: `http://100.99.172.84:3000` (or MagicDNS name).

**Preferred long-term (no change applied this pass):**

1. In EasyPanel / Swarm, publish only on Tailscale IP if supported, **or** stop host publish and put EasyPanel behind Traefik with TS-only middleware.  
2. Keep iptables as defense-in-depth even after rebind.  
3. Never expose EasyPanel on public `:3000` or public hostname without SSO + MFA.

---

## 7. Remaining risks (concise)

| Risk | Severity | Mitigation status |
|---|---|---|
| FW rules lost on reboot if persistence fails | High | netfilter-persistent enabled; re-verify after next reboot |
| DOCKER-USER public 443/80 DROP vs prod need | High | **Investigate** — not auto-fixed |
| SSH password auth on + residual UFW ACCEPT 22 | Medium | fail2ban + root key-only; harden passwords later |
| Secrets in skills / plaintext env | Medium–High | Documented; migrate gradually; no rotation this pass |
| CrowdSec without bouncer | Medium | Container only; no host enforce |
| Host-published data ports rely on iptables | Medium | F9+F4; prefer unpublish |
| iperf3 process still listening | Low | TS-filtered |
| X11Forwarding yes | Low | Report only |
| Multi-device Tailscale tailnet | Low–Med | Review offline devices / exit node ACL later |

---

## 8. Return payload (for orchestrator)

### Open ports risk ranking (top)

1. **P0** — PG `:5094`, Redis `:1001`, pgweb `:8082` (host-published; FW-dependent)  
2. **P1** — EasyPanel `:3000`, OpenClaw `:18789`, Evolution `:8080`, **mcp-orchestrator `:8100` (mitigated)**  
3. **P1** — Traefik `:443/:80` policy conflict  
4. **P2** — SSH `:22` public with password auth enabled  
5. **P3** — Observability/debug/iperf3 (TS-filtered)

### Actions taken

- Audited firewall, Tailscale, Docker publishes, CrowdSec, fail2ban, SSH, Swarm overlay vs host ports.  
- **Applied** Tailscale-only lockdown for **`:8100` (mcp-orchestrator)** on INPUT + DOCKER-USER + raw PREROUTING; **persisted** iptables.  
- **Documented** EasyPanel TS-only recommendation and secrets-in-skills migration (no skill rewrites, no key rotation).

### Remaining risks

- Confirm public HTTPS/Telegram vs DOCKER-USER 443 DROP.  
- SSH password + hybrid UFW residual.  
- Secrets still in skills/env.  
- CrowdSec not enforcing on host.  
- Host-published sensitive ports still exist (defense is iptables, not bind address).

---

## 9. Audit metadata

| Item | Value |
|---|---|
| Auditor | Squad 4 (Security Hardening) / coding-vps |
| Host time (UTC) | 2026-07-09 ~01:55 |
| Public IP | 187.77.236.77 |
| Tailscale | 100.99.172.84 (`vps-cartorio`) |
| Safe changes | F4 rules for TCP/8100 + `iptables-save` |
| Report path | `docs/platforms/coding-vps/SECURITY_REPORT_2026-07-08.md` |

**Modified by Gustavo Almeida** (report authored under Cartorio multi-agent workflow).
