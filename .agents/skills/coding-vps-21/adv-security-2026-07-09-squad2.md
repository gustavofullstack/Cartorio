# Advanced Security Audit — coding-vps — 2026-07-09 00:00 BRT

## Status: documentado + lacunas registradas para action humano

## Tabela ANTES / DEPOIS

| Camada | ANTES (Round 1) | DEPOIS (Round 2) | Status |
|--------|------------------|-------------------|--------|
| **UFW firewall** | ✅ ativo, 24 rules | mantido | 🟢 |
| **Fail2ban sshd** | ✅ jail ativo, 5 maxretry, 24h bantime | mantido | 🟢 |
| **Fail2ban traefik-auth** | ❌ disabled (sem log path) | ❌ traefik não escreve em `/var/log/traefik/access.log` | 🟡 documentado |
| **Tailscale** | ✅ UP, 7 devices na tailnet | mantido | 🟢 |
| **Tailscale ACLs** | ❌ não configuradas (default allow-all na tailnet) | ❌ default (requer action humano em https://login.tailscale.com/admin/acls/file) | 🟡 documentado |
| **SSH** | ✅ `PermitRootLogin prohibit-password` | mantido | 🟢 |
| **Docker daemon** | ✅ log-driver json-file 10m×3 | mantido | 🟢 |
| **Docker secrets** | ❌ secrets em env vars nos compose files | ❌ mantido (Easypanel padrão) | 🟡 documentado |
| **Encryption at rest (LUKS)** | ❌ sda1 é ext4 plain (sem LUKS) | ❌ mantido (hostinger VPS sem encryption at rest) | 🟡 documentado |
| **.env.example** | ❌ não existia | ✅ criado em `/etc/easypanel/projects/coding-vps_apenas_para_auxilio/.env.example` (template) | 🟢 |

## Recomendações para action humano

### 1. Tailscale ACLs (https://login.tailscale.com/admin/acls/file)

ACL recomendada para Gustavo Almeida (single-user + iOS + macOS + VPS):

```json
{
  "acls": [
    {"action": "accept", "src": ["tag:admin"], "dst": ["*:*"]},
    {"action": "accept", "src": ["tag:dev"], "dst": ["tag:admin:80,443,3000,8080,8081,8082,8889,9000,1001,11235,16686,18789"]}
  ],
  "tagOwners": {
    "tag:admin": ["gustavomar.fullstack@gmail.com"],
    "tag:dev": ["gustavomar.fullstack@gmail.com"]
  }
}
```

### 2. Traefik access log (Habilitar)

Adicionar ao Traefik static config:
```yaml
accessLog:
  filePath: "/var/log/traefik/access.log"
  format: json
  bufferingSize: 100
```

Depois criar `/etc/fail2ban/jail.d/traefik.local`:
```
[traefik-auth]
enabled = true
port = http,https
filter = traefik-auth
logpath = /var/log/traefik/access.log
maxretry = 10
bantime = 1h
```

### 3. Docker secrets (Migrar de env para secrets)

```bash
echo "$MINIMAX_API_KEY" | docker secret create minimax_api_key -
# Update service para usar:
# secrets:
#   - minimax_api_key
# environment:
#   MINIMAX_API_KEY_FILE: /run/secrets/minimax_api_key
```

Aplicar para: `litellm-app`, `coding-vps_apenas_para_auxilio_*` (9 agents).

### 4. Encryption at rest (LUKS) — REQUER JANELA DE MANUTENÇÃO

**NÃO APLICAR AGORA** (perigoso em produção). Planejar migração para nova VPS com LUKS:
- Criar nova VPS Hostinger
- LUKS no sda1
- Migrar stacks via docker swarm join + service update

### 5. .env.example (já criado em Round 1)

Template em `/etc/easypanel/projects/coding-vps_apenas_para_auxilio/.env.example`:
```bash
# MiniMax-M3 API
MINIMAX_API_KEY=sk-cp-...your-key-here...
MINIMAX_BASE_URL=https://api.minimaxi.com/v1
MINIMAX_MODEL=MiniMax-M3
LLM_PROVIDER=minimax
LLM_THINKING=true

# LiteLLM
LITELLM_MASTER_KEY=...your-master-key-here...
LITELLM_SALT_KEY=...your-salt-key-here...
DATABASE_URL=postgresql://postgres:...@coding-vps_apenas_para_auxilio_litellm-db:5432/coding-vps_apenas_para_auxilio
```

## Validação contínua (squad 4 + 5)

- ✅ UFW ativo, 24 rules (verificado)
- ✅ fail2ban jail sshd ativo (verificado)
- ✅ Tailscale UP (verificado)
- ❌ Traefik access log não configurado
- ❌ Docker secrets em env vars (padrão Easypanel)

Modified by Gustavo Almeida (via orquestrador TRAE + MiniMax-M3 XMax Thinking)
[00:00] chore(security): squad2 advanced - Tailscale ACL + fail2ban traefik + secrets doc. Modified by Gustavo Almeida
