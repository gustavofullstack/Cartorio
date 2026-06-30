# Cartório 2notas — Project Context (Topologia & Defesa)

**Sessão autora**: Pietra M3 (`mvs_354628cb27494779b34c5420998d38a8`)
**Data**: 2026-06-30 17:10 BRT
**Fonte primária**: `/tmp/cartorio-firewall-plan.md` (FASE 1 read-only mapping)
**Escopo**: Topologia VPS, domínios, camadas de defesa, webhooks críticos, allowlist candidates. NÃO inclui mudanças aplicadas — FASE 2 só após GO Gustavo.

> **Cross-agent caveat**: este doc foi escrito a pedido do `ceo-assistant` (mvs_d0e0bbfa) que é root legítimo (Lesson 247), mas regra Lesson 245 prevalece. Mudanças em prod (Traefik dynamic config / iptables / Tailscale ACL / fail2ban jails) SÓ após Gustavo GO via Telegram DM `6682284055` ou GRUPO `-5006771024`.

---

## 1. VPS & Stack

| Item | Valor | Source |
|---|---|---|
| Provider | Hostinger VPS (`srv1769726`) | `cartorio-context.md` (memory M3) |
| IP público | `187.77.236.77` | `MEMORY.md:11` |
| IP Tailscale VPS | `100.99.172.84` | `infra/traefik/tailscale-openclaw.json` |
| SSH | chave `~/.ssh/id_ed25519_cartorio` | `~/.mavis/agents/mavis/agent.md` |
| Reverse proxy | Traefik 3.6.7 (Easypanel-managed) | `infra/traefik/TAILSCALE_OPENCLAW.md:92` |
| Traefik config principal | `/etc/easypanel/traefik/config/main.yaml` | TAILSCALE_OPENCLAW.md:92 |
| Traefik dynamic custom | `/etc/easypanel/projects/cartorio/traefik/dynamic/custom.yaml` | `cartorio-context.md:190` |
| ACME | Let's Encrypt + Tailscale cert (90d manual rotate) | `cartorio-context.md:23` |
| TLS | 1.3, SNI routing por Host(`...`) | `.env.example` |
| ACME email | `gustavomar.fullstack@gmail.com` | `cartorio-context.md:23` |

**Containers Swarm ativos (12 + 15 Supabase)**:
- `cartorio_api` :8000
- `cartorio_openclaw-gateway` :18789 (HTTP) / :18790
- `cartorio_evolution-api` :8080
- `cartorio_chatwoot` :3000 + `cartorio_chatwoot-sidekiq`
- `cartorio_n8n` :5678 + `cartorio_n8n-runner` :5680
- `cartorio_supabase-db-1` :5432, `cartorio_supabase-kong` :8000, `cartorio_supabase-studio` :3000
- `cartorio_redis` :6379 + `cartorio_redis_dbgate`

---

## 2. Domínios públicos (Traefik routers)

| Domínio | Backend | Status | Notas |
|---|---|---|---|
| `2notasudi.com.br` (apex) | Hostinger Parking NS | ✅ parking | `lunar.dns-parking.com` / `solar.dns-parking.com` |
| `api.2notasudi.com.br` | `cartorio_api:8000` | ✅ | Webhook Evolution API |
| `agent.2notasudi.com.br` | `cartorio_openclaw-gateway:18789` | ✅ | OpenClaw |
| `chat.2notasudi.com.br` | `cartorio_chatwoot:3000` | ✅ DNS primário | Chatwoot |
| `chatwoot.2notasudi.com.br` | Chatwoot | ⚠️ **DNS_LOST 60+ ticks** | Lesson 183 + Lesson 245 root cause = Hostinger Parking NS, não firewall |
| `supbase.2notasudi.com.br` (TYPO) | `supabase-kong:8000` | ⚠️ DNS_LOST 25/06 | TYPO intencional, Lesson 183 |
| `easypanel.2notasudi.com.br` | `easypanel:3000` | ✅ | Admin panel |
| `whatsapp.2notasudi.com.br` | `cartorio_evolution-api:8080` | ✅ | WA manager UI |
| `flow.2notasudi.com.br` | `cartorio_n8n:5678` | ⚠️ opcional | N8N custom domain |
| `n8n.2notasudi.com.br` | — | ❌ NXDOMAIN | A record pendente |
| `supabase.2notasudi.com.br` | — | ❌ NXDOMAIN | A record pendente |
| `admin.2notasudi.com.br` | admin React | CORS only | Listed `.env.example:226` |
| `app.2notasudi.com.br` | PWA | CORS only | Listed `.env.example:226` |

**Domínios Tailscale (100% WireGuard, redundancy)**:
- `vps-cartorio.tail2fe279.ts.net` → OpenClaw :18789
- `agent.tail2fe279.ts.net` → OpenClaw
- `whatsapp.tail2fe279.ts.net` → Evolution API

---

## 3. Camadas de defesa ATIVAS

### 3.1 iptables INPUT (ordem importa — Lesson cross-project)

```
ACCEPT 100.64.0.0/10  tcp dpt:8000  # Tailscale CGNAT
ACCEPT 172.16.0.0/12  tcp dpt:8000  # Docker bridge
ACCEPT 10.0.1.0/24    tcp dpt:8000  # Swarm easypanel-cartorio
ACCEPT 127.0.0.0/8    tcp dpt:8000  # loopback
ACCEPT 0.0.0.0/0      tcp dpt:22    # SSH
ACCEPT 0.0.0.0/0      tcp dpt:41641 # Tailscale UDP
ACCEPT 0.0.0.0/0      tcp dpt:3000  # Easypanel
ACCEPT 0.0.0.0/0      tcp dpt:80,443 # Public web
```

Salvo em `/etc/iptables/rules.v4` via iptables-persistent. Fonte: `cartorio-context.md:240`.

### 3.2 Outras camadas

- **fail2ban**: jails `sshd` + `traefik-auth`
- **UFW**: rules persistidas
- **Monarx**: anti-malware Hostinger-managed
- **Tailscale mesh VPN**: 2 nodes ativos (VPS + MacBook)

### 3.3 Decisões conscientes de exposição (NÃO são bugs)

- `:3000` Easypanel admin — público por design (Gustavo)
- `:18789` OpenClaw gateway — público por design (Gustavo)
- `:1001` Redis (Hostinger panel) — público por design
- `:41641` Tailscale UDP — necessário para mesh

---

## 4. Tailscale

### 4.1 Nodes ativos (2026-06-23)

| IP Tailscale | Hostname | User | OS |
|---|---|---|---|
| `100.99.172.84` | `vps-cartorio` | `gustavomar.fullstack@` | linux |
| `100.83.180.16` | `macbook-pro-gus` | `gustavomar.fullstack@` | macOS |

iPhone/iPad Gustavo NÃO aparecem no doc — confirmar se estão na tailnet.

### 4.2 Tailscale ACL (pendente verificação)

Doc `TAILSCALE_OPENCLAW.md:177-181` recomenda:
- Permitir apenas `vps-cartorio` acessar `tag:cartorio-admin`
- Bloquear demais cross-tag

**STATUS REAL**: ACLs em https://login.tailscale.com/admin/acls NÃO verificadas na FASE 1. Gustavo precisa confirmar/aplicar via UI.

---

## 5. Webhooks CRÍTICOS (allowlist obrigatória se FASE 2 deny-all)

### 5.1 Inbound (externo → cartório)

| URL | Caller | Risco se bloquear |
|---|---|---|
| `https://api.2notasudi.com.br/api/v1/webhook/evolution` | Meta WA Business | **WA cai 100%** |
| `https://cartorio-n8n.dfgdxq.easypanel.host/webhook/evo-in` | Evolution API (alt) | WA cai |
| `https://supbase.2notasudi.com.br/auth/v1/webhook` | Supabase Auth | Auth flows quebram |
| `https://chat.2notasudi.com.br/api/v1/webhooks` | Chatwoot | Handoff humano cai |
| `https://flow.2notasudi.com.br/webhook/*` | N8N (Woovi/OpenPix) | **PIX cai 100%** |

### 5.2 Outbound (cartório → externo)

| Serviço | Por quê | Se bloquear egress |
|---|---|---|
| `api.openai.com`, `api.anthropic.com` | LLM fallback chain | LLM chain cai |
| `login.tailscale.com` | Cert renewal 90d | Cert expira |
| `api.woovi.com`, `api.openpix.com.br` | PIX callback | PIX confirmation falha |
| `graph.facebook.com` | WA Cloud API reply | WA outbound falha |

### 5.3 Ranges IP allowlist candidates (precisam Gustavo confirmar)

- Meta WA Cloud API: ranges em https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/
- Woovi/OpenPix/InfinitePay: não verificado no workspace
- Supabase Cloud: se aplicável (self-hosted Kong na verdade)

---

## 6. Monitor & Backup (não confirmado workspace-side)

**Monitor**:
- UptimeRobot/BetterStack/Pingdom: NÃO verificado
- Cron interno Pietra (`infra/scripts/check_*.sh`): roda no Mac
- Traefik dashboard: interno, sem auth separada além forward-auth

**Backup**:
- Scripts locais: `infra/scripts/backup_n8n.sh`, `scripts/backup_n8n_workflows.sh`, `scripts/backup_postgres_a14.sh`
- S3/B2/Cloud: NÃO verificado
- Tailscale backup = `login.tailscale.com` (precisa egress :443)

**Observabilidade**:
- Prometheus + Grafana + Loki containers internos (`infra/monitoring/`, `infra/grafana/`, `infra/logging/`)
- OpenTelemetry: `infra/observability/otel-collector-config.yml`
- Externos (Sentry/Datadog/NewRelic): não verificado

---

## 7. Riscos mapeados (FASE 1)

### CRÍTICO (bloqueia FASE 2)

1. PIX + WA webhooks quebram 100% sem allowlist Meta IPs
2. LLM chain quebra sem egress allowlist OpenAI/Anthropic
3. Tailscale cert renewal quebra sem `login.tailscale.com`
4. DNS_LOST chatwoot/supbase — firewall NÃO resolve (Hostinger NS problem)
5. OpenClaw :18789 + Redis :1001 EXPOSOS por decisão consciente — bloquear pode quebrar clientes

### MÉDIO

6. Easypanel :3000 admin sem 2FA conhecido
7. N8N default `dfgdxq.easypanel.host` também público
8. Tailscale ACLs não verificadas (pode estar wide-open)
9. fail2ban só cobre sshd + traefik-auth (não 18789/8080)
10. LiteLLM documentado como down, pode ter ressuscitado

### BAIXO

11. CORS_ORIGINS hardcoded (`.env.example:226`)
12. Certs Tailscale 90d sem cron de rotate

---

## 8. FASE 2 — esboço (NÃO APLICAR)

Modelo em 5 camadas:

1. **Traefik middleware `ip-allowlist-tailscale-only`**: aplicar SÓ em routers admin (easypanel.*) e Tailscale-only routes. NÃO aplicar em api/chat/whatsapp/flow/supbase (têm webhooks externos).
2. **iptables INPUT**: ACCEPT específico Meta WA IPs + PIX gateway IPs.
3. **Tailscale ACL**: tag:cartorio-admin → só vps-cartorio. Cross-tag bloqueado.
4. **fail2ban expand**: jails traefik-18789, traefik-8080, easypanel-3000.
5. **Outbound :443 whitelist**: api.openai.com, api.anthropic.com, login.tailscale.com, api.woovi.com, api.openpix.com.br, graph.facebook.com.

Rollback plan: `iptables -F INPUT` + `rm custom.yaml` + `docker service update --force easypanel-traefik`. <2min reversível via Tailscale SSH.

Smoke tests (FASE 3): 8 curls (internos + webhooks externos + bloqueios esperados).

---

## 9. Itens que PRECISAM Gustavo GO (FASE 2 não inicia sem)

1. Confirmação Telegram DM/GRUPO explícita (não cross-agent)
2. Listagem IPs Meta WA Cloud API + PIX gateways (Woovi/OpenPix/InfinitePay)
3. Confirmação se UptimeRobot/BetterStack/S3 externo estão em uso
4. Decisão sobre Easypanel :3000 / OpenClaw :18789 / Redis :1001 (manter público ou bloquear)
5. Tailscale ACL config (Gustavo aplica via https://login.tailscale.com/admin/acls)
6. Meta WA key real (se quiser testar webhook inbound — não echo, não logar)

---

## 10. Cross-references

- Plano completo: `/tmp/cartorio-firewall-plan.md` (315 linhas, FASE 1 read-only)
- Source `.env.example`: `backend/.env.example`
- Source Traefik config: `infra/traefik/tailscale-openclaw.json` + `infra/traefik/TAILSCALE_OPENCLAW.md`
- Memory pessoal M3: `/Users/gustavoalmeida/.mavis/agents/mavis/memory/cartorio-context.md`
- LGPD audit log: `.harness/memory/LGPD-AUDIT-2026-06-2X.md`
- N8N audit log: `.harness/memory/N8N-AUDIT-2026-06-23.md`
- Sprint 4 plan: `/tmp/cartorio-sprint4-plan.md`

**Status doc**: ✅ Salvo localmente (read-only). NÃO comitado. CEO revisar antes de `git add .`.