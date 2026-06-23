# Tailscale Wildcard + OpenClaw Exposição

**Data:** 2026-06-23 18:05 BRT
**Status:** ✅ OpenClaw acessível via Tailscale (hostname único, sem wildcard nativo)
**Limitações:** Tailscale HTTPS nativo só permite o hostname do node, NÃO wildcard `*.tail2fe279.ts.net`

---

## 🏗️ Arquitetura

```
Tailscale client (Mac, iPhone, Linux, etc)
  │  (encrypted WireGuard tunnel, root CA bundled in OS)
  ▼
vps-cartorio.tail2fe279.ts.net:443 (Tailscale IP 100.99.172.84)
  │
  ▼
Easypanel-managed Traefik (easypanel-traefik)
  │  matches Host(`vps-cartorio.tail2fe279.ts.net`)
  │  TLS cert: Tailscale-issued (vps-cartorio.tail2fe279.ts.net)
  ▼
cartorio_openclaw-gateway:18789
  │
  ▼
OpenClaw Control UI + /health + /v1/* (WSS + HTTP)
```

**Latência medida (Mac → VPS via Tailscale):**
- HTTP UI: 870ms (inclui TLS handshake)
- `/health`: direto via Tailscale IP = 0.96ms (sem TLS)

---

## 🔐 Sobre wildcard `*.tail2fe279.ts.net`

**Não é possível gerar wildcard nativamente via Tailscale.** Restrições:
- `tailscale cert` só aceita o hostname exato do node (`vps-cartorio.tail2fe279.ts.net`)
- Tailscale HTTPS só provê 1 cert por node
- MagicDNS não tem split-DNS customizável para o tailnet

### Alternativas para wildcard real

| Opção | Custo | Setup | Observação |
|---|---|---|---|
| **A. Renomear VPS para `router`** e usar path-based | $0 | 1 min | `router.tail2fe279.ts.net/openclaw/*` → OpenClaw. Não muda DNS, é só um novo nome. |
| **B. ACME DNS-01 com Cloudflare** | $0 | 30 min | Traefik + cert-manager + Cloudflare API. Wildcard real, auto-renova. |
| **C. Internal CA + push via Tailscale admin** | $0 | 1h | Mais complexo, exige instalar CA em todos os clients. |

**Recomendação atual:** Opção A (path-based no hostname único) — já está funcional para o caso de uso OpenClaw.

---

## 📋 Comandos de Setup Executados (2026-06-23)

### 1. Verificar Tailscale na VPS
```bash
ssh cartorio 'tailscale status'
# 100.99.172.84   vps-cartorio             gustavomar.fullstack@  linux    active
# 100.83.180.16   macbook-pro-gus          gustavomar.fullstack@  macOS    active
```

### 2. Verificar OpenClaw exposto
```bash
ssh cartorio 'docker exec cartorio_openclaw-gateway.1.* curl -s http://127.0.0.1:18789/health'
# {"ok":true,"status":"live"}
```

### 3. Testar acesso direto via Tailscale IP (sem TLS)
```bash
ssh cartorio 'curl -s -w "HTTP=%{http_code} time=%{time_total}s\n" -o /dev/null http://100.99.172.84:18789/health'
# HTTP=200 time=0.000965s
```

### 4. Habilitar Tailscale HTTPS no admin
- URL: https://login.tailscale.com/admin/dns
- Toggle "Enable HTTPS" → ON
- Verificar na VPS: `tailscale status --json | jq .HTTPSEnabled` → `true`

### 5. Gerar cert do Tailscale
```bash
ssh cartorio 'tailscale cert vps-cartorio.tail2fe279.ts.net'
# Wrote public cert to vps-cartorio.tail2fe279.ts.net.crt
# Wrote private key to vps-cartorio.tail2fe279.ts.net.key
# Move para /etc/tailscale-certs/
ssh cartorio 'mkdir -p /etc/tailscale-certs && mv /root/vps-cartorio.tail2fe279.ts.net.* /etc/tailscale-certs/'
# Copiar para o dir do Traefik
ssh cartorio 'cp /etc/tailscale-certs/vps-cartorio.tail2fe279.ts.net.crt /etc/easypanel/traefik/tailscale-vps-cartorio.crt'
ssh cartorio 'cp /etc/tailscale-certs/vps-cartorio.tail2fe279.ts.net.key /etc/easypanel/traefik/tailscale-vps-cartorio.key'
```

### 6. Patch no Traefik dynamic config
- Arquivo: `/etc/easypanel/traefik/config/main.yaml`
- Adicionado:
  - `tls.certificates[]` entry apontando para `/data/tailscale-vps-cartorio.{crt,key}`
  - `http.services.tailscale-openclaw` → `http://cartorio_openclaw-gateway:18789`
  - `http.routers.tailscale-openclaw-https` → `Host(\`vps-cartorio.tail2fe279.ts.net\`)` + `entryPoints: [https]`
- Arquivo versionado: `infra/traefik/tailscale-openclaw.json`

### 7. Validar end-to-end
```bash
# Do Mac (qualquer máquina na tailnet):
curl -s -o /dev/null -w "HTTP=%{http_code} time=%{time_total}s cert_verify=%{ssl_verify_result}\n" \
  https://vps-cartorio.tail2fe279.ts.net/
# HTTP=200 time=0.87s cert_verify=0  ← Tailscale TLS cert valid!
```

---

## 🛡️ Firewall + ACL Recomendadas (defesa em profundidade)

1. **Tailscale ACL** (admin panel): permitir apenas o node `vps-cartorio` acessar `tag:cartorio-admin` clients. Bloquear demais.
2. **OpenClaw auth** já está ativo (`--auth password --password @Techno832466` no command do service).
3. **Traefik middleware** `forward-auth-traefik` (já existe para outros serviços) pode ser reaproveitado para OpenClaw se quiser SSO.

---

## 🐛 Problemas Conhecidos

| Sintoma | Causa | Fix |
|---|---|---|
| `tls: failed to verify certificate: x509: certificate is valid for vps-cartorio.tail2fe279.ts.net, not <ip>` | Acessando por IP | Use o hostname ou `--insecure` flag |
| `502 Bad Gateway` | OpenClaw down ou porta errada | `docker service ps cartorio_openclaw-gateway` |
| `404` no `/v1/chat` | OpenClaw v0.4.0 expõe UI HTML em `/`, não API REST em `/v1/chat` | Use o Control UI no browser |
| HTTPS cert expirado em 90 dias | Tailscale cert renova automático? NÃO — expira e precisa regenerar | Cron mensal: `tailscale cert vps-cartorio.tail2fe279.ts.net && cp /root/vps-cartorio.tail2fe279.ts.net.* /etc/easypanel/traefik/tailscale-vps-cartorio.* && docker service update --force easypanel-traefik` |

---

## ✅ Checklist de Validação

- [x] Tailscale up no VPS + Mac
- [x] OpenClaw up com `--bind auto --port 18789 --allow-unconfigured --auth password`
- [x] HTTPS habilitado no admin Tailscale
- [x] Tailscale cert gerado para `vps-cartorio.tail2fe279.ts.net`
- [x] Traefik dynamic config patch com router + service + cert
- [x] End-to-end test: `curl https://vps-cartorio.tail2fe279.ts.net/` → HTTP 200 + cert válido
- [x] Documentação em `infra/traefik/TAILSCALE_OPENCLAW.md`
- [ ] Cron job de renovação de cert (Tailscale certs expiram em 90 dias)
- [ ] Renomear VPS para `router` + path-based routing (opcional, future)
