# MCP Skill: Hostinger VPS

## Visao Geral
- Provedor: Hostinger (VPS)
- IP Publico: 187.77.236.77
- IP Tailscale: 100.99.172.84
- OS: Ubuntu LTS
- SSH Key: ~/.ssh/id_ed25519_cartorio

## Comandos Uteis
- `ssh root@100.99.172.84 -i ~/.ssh/id_ed25519_cartorio` (preferido via Tailscale)
- `ssh root@187.77.236.77 -i ~/.ssh/id_ed25519_cartorio` (via IP publico)

## Docker Swarm
- `docker service ls` - Listar servicos
- `docker service ps <name>` - Detalhes de replicas
- `docker service logs <name> --tail 50` - Logs recentes
- `docker service update --image <image> <name>` - Atualizar imagem

## Recursos
- `df -h /` - Disco (193G total, 16% usado)
- `free -h` - Memoria (15GB, ~38% usado)
- `uptime` - Uptime

## Backup
- Path: /var/backups/cartorio/
- Rotacao: 7 dias
- Horario: 03:00 BRT

## Firewall (iptables)
- Policy: DROP (default)
- Portas abertas: 22 (SSH), 80/443 (HTTP/S), Tailscale
- Redis (1001): Apenas Tailscale
- Easypanel (3000): Apenas Tailscale
