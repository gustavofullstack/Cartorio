# 🚨 RUNBOOK VPS — Cartório 2 Notas Uberlândia

> **REGRA DE OURO**: SEMPRE use `ssh cartorio`. **NUNCA** use `ssh vps` (IP stale 100.120.250.91 não existe).
> **Versão**: 1.0.0 (2026-06-23)
> **Owner**: ZCode + cartorio-devops

---

## 1. Acesso à VPS

### Tailscale (RECOMENDADO)
```bash
ssh cartorio
# ou
ssh cartorio-ts
# ou
ssh 100.99.172.84
# Key: ~/.ssh/id_ed25519_cartorio
```

### IP público (fallback)
```bash
ssh cartorio-public
# ou
ssh 187.77.236.77
# Key: mesma
```

### ⚠️ NÃO use
```bash
ssh vps           # IP stale 100.120.250.91 (NÃO EXISTE)
ssh vps-tailscale # mesmo IP stale
ssh vps-public    # 148.230.75.172 caiu em outro projeto (udiapods_*)
```

---

## 2. Comandos úteis

### Estado geral
```bash
# Containers UP
ssh cartorio 'docker service ls --format "table {{.Name}}\t{{.Replicas}}\t{{.Image}}" | grep cartorio'

# Health por container
ssh cartorio 'docker ps --filter "name=cartorio" --format "{{.Names}}: {{.Status}}"'

# Logs últimos 50
ssh cartorio 'docker service logs cartorio_api --tail 50'
```

### Restart seguro
```bash
# N8N (raro quebrar)
ssh cartorio 'docker service update --force cartorio_n8n'

# API (deploy)
ssh cartorio 'docker service update --force cartorio_api'

# Redis (cuidado, perde cache)
ssh cartorio 'docker service update --force cartorio_redis'
```

### Validar domínios públicos
```bash
for d in api flow whatsapp agent easypanel supbase chatwoot; do
  code=$(curl -s -m 5 -o /dev/null -w "%{http_code}" https://${d}.2notasudi.com.br/)
  echo "$d.2notasudi.com.br -> $code"
done
```

Status esperado:
- api/flow/whatsapp/agent/easypanel → 200
- supbase → 401 (Kong OK)
- chatwoot → 000 (DNS pendente, configurar na Hostinger)

---

## 3. Trilha de auditoria (3 ground truths)

**Antes de declarar "sistema down", validar:**

1. **SSH conecta** com alias correto? (`ssh cartorio`)
2. **Container UP**? (`docker service ls | grep cartorio`)
3. **Domínio responde** com status esperado? (curl acima)

Se os 3 passam → sistema está no ar. Problema é de acesso local ou interpretação de status code.

---

## 4. Pendências VPS (T0.7-T0.12 do SUPER_PLANO v0.6.0)

### cartorio-devops (T0.7-T0.8)
- [ ] T0.7: cert wildcard + Traefik router `*.tail2fe279.ts.net`
- [ ] T0.8: Tailscale ACL tag `tag:cartorio`

### Pietra UI (T0.9-T0.12)
- [ ] T0.9: DNS `chatwoot.2notasudi.com.br` (Hostinger/Cloudflare)
- [ ] T0.10: Chatwoot Agent Bot (webhook → `/api/v1/webhook/chatwoot`)
- [ ] T0.11: Easypanel API key regenerar (a antiga morreu 401)
- [ ] T0.12: Decidir typo `supbase` vs `supabase` (P2 opcional)

---

## 5. Contatos de emergência

- **CEO/Dono**: Pietra (Gustavo Almeida) — `gustavomar.fullstack@gmail.com`
- **DPO**: `dpo@2notasudi.com.br` (LGPD)
- **Easypanel UI**: `https://easypanel.2notasudi.com.br`
- **Hostinger painel**: `https://hpanel.hostinger.com`
- **Cloudflare**: `https://dash.cloudflare.com`
- **Tailscale admin**: `https://login.tailscale.com/admin`

---

## 6. Comandos PROIBIDOS (vai quebrar)

```bash
# NÃO execute sem Gustavo autorizar
ssh cartorio 'docker service rm cartorio_*'        # remove serviço
ssh cartorio 'docker network rm easypanel-cartorio' # remove rede
ssh cartorio 'rm -rf /var/lib/docker/volumes/*'     # deleta volumes (DADOS)
ssh cartorio 'docker swarm leave --force'           # sai do swarm
```

Modified by ZCode (Pietra session 2026-06-23)
