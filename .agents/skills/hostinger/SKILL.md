---
name: hostinger
description: |
  Skill para gerenciar a VPS Hostinger via SSH, Tailscale e API.
  Use quando precisar: acessar VPS, verificar recursos, configurar firewall,
  gerenciar Docker Swarm, fazer backup, monitorar performance e SSL.
  VPS: 187.77.236.77 | Tailscale: 100.99.172.84 | Ubuntu LTS
---

# Hostinger VPS — Skill de Acesso e Gerenciamento

## Acesso SSH

```bash
# Via Tailscale (PREFERIDO — mais rápido e seguro)
ssh -i ~/.ssh/id_ed25519_cartorio root@100.99.172.84

# Via IP público (fallback)
ssh -i ~/.ssh/id_ed25519_cartorio root@187.77.236.77

# Alias no SSH config (~/.ssh/config)
Host cartorio
  HostName 100.99.172.84
  User root
  IdentityFile ~/.ssh/id_ed25519_cartorio
  StrictHostKeyChecking no
```

## Credenciais VPS

| Item | Valor |
|------|-------|
| **IP Público** | `187.77.236.77` |
| **IP Tailscale** | `100.99.172.84` |
| **Usuário** | `root` |
| **SSH Key** | `~/.ssh/id_ed25519_cartorio` |
| **SO** | Ubuntu LTS |
| **RAM** | 15.62 GiB (5.1 usado) |
| **Disco** | 193G (16% = 30G usado) |
| **Uptime** | 4+ dias |

## Rede Tailscale

| Nó | IP | Tipo |
|----|-----|------|
| vps-cartorio | 100.99.172.84 | Servidor ✅ |
| macbook-pro-gus | 100.83.180.16 | Dev (Gustavo) ✅ |
| iphone-17-pro | 100.122.101.33 | iOS ✅ |
| iphone-andre | 100.74.36.41 | iOS |
| iphone-henrique | 100.76.109.91 | iOS |
| macbook-air-henrique | 100.122.88.49 | macOS |
| pc-do-andre | 100.112.202.91 | Windows |
| triqhub | 100.110.127.44 | Linux (exit node) ✅ |

## Comandos Essenciais

### Docker Swarm
```bash
# Status de todos os serviços
docker service ls

# Logs em tempo real
docker service logs cartorio_api --follow

# Restart de serviço
docker service update --force cartorio_api

# Stats recursos
docker stats --no-stream

# Ver configuração de serviço
docker service inspect cartorio_api --pretty
```

### Monitoramento
```bash
# CPU + Memória geral
top -bn1 | head -15
free -h

# Disco
df -h /

# Processos pesados
ps aux --sort=-%mem | head -10

# Rede
ss -tulpn  # portas abertas
netstat -an | grep ESTABLISHED | wc -l  # conexões ativas
```

### Backups
```bash
# Verificar último backup
ls -lah /var/backups/cartorio/

# Executar backup manual
/var/backups/cartorio/backup.sh  # se existir

# Backup N8N workflows
curl -s "https://flow.2notasudi.com.br/api/v1/workflows?limit=100" \
  -H "X-N8N-API-KEY: $N8N_API_KEY" > n8n_backup_$(date +%Y%m%d).json
```

### Docker Registry / Easypanel Paths
```bash
/etc/easypanel/projects/cartorio/    # configs de todos serviços
/etc/easypanel/projects/cartorio/api/code/  # código API
/home/node/.openclaw/               # config OpenClaw
```

## Verificação de SSL (Traefik)

```bash
# Certificados gerenciados pelo Traefik (Let's Encrypt auto)
# Verificar via curl:
for domain in api flow agent chat supbase whatsapp easypanel; do
  echo -n "$domain.2notasudi.com.br: "
  echo | openssl s_client -servername $domain.2notasudi.com.br \
    -connect $domain.2notasudi.com.br:443 2>/dev/null | \
    openssl x509 -noout -dates 2>/dev/null | grep notAfter
done
```

## Hostinger API (Gerenciamento)

```bash
# Hostinger tem painel web em hpanel.hostinger.com
# API disponível em: https://www.hostinger.com/api
# Para gerenciar VPS programaticamente via Hostinger API:
# Endpoint: https://api.hostinger.com/v1/vps

# Auth: Bearer token do painel Hostinger
# Gustavo tem acesso pelo painel hpanel.hostinger.com
```

## Segurança

- **Firewall**: Hostinger gerencia via painel (UFW não configurado internamente)
- **Tailscale**: Acesso interno via VPN privada (MagicDNS habilitado)
- **SSH**: Apenas via chave ed25519 (sem password)
- **Docker**: Swarm com overlay network isolada
- **Redis**: Acessível externamente apenas via Tailscale (porta 1001)
- **Traefik**: SSL automático Let's Encrypt para todos os domínios

## Variáveis de Ambiente

```env
VPS_TAILSCALE_IP=100.99.172.84
VPS_PUBLIC_IP=187.77.236.77
VPS_SSH_KEY=~/.ssh/id_ed25519_cartorio
VPS_SSH_ALIAS=cartorio
```

## MCP Server & Client Integration

- **SSH MCP Server**: O host de desenvolvimento local pode rodar um MCP server do tipo `ssh` (ex: `ssh-mcp` ou um shell MCP) conectado à VPS (`100.99.172.84`) usando a chave SSH privada.
- **Docker MCP Server**: Expõe comandos Docker Swarm para monitorar containers (`docker service ls`, `docker stats`) via protocolo MCP.

