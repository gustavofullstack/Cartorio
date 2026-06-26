# Skill: Hostinger VPS Management
## Purpose
Manage Hostinger VPS infrastructure via SSH and Tailscale.
## Connection
- SSH: `ssh root@100.99.172.84 -i ~/.ssh/id_ed25519_cartorio`
- Direct: `ssh root@187.77.236.77`
- Tailscale IP: 100.99.172.84
## Commands
- Resources: `free -h && df -h / && uptime`
- Docker: `docker service ls && docker ps --format '{{.Names}}\t{{.Status}}'`
- Logs: `docker service logs <service> --tail 50`
- Restart: `docker service update --force <service>`
## Security
- SSH key: ~/.ssh/id_ed25519_cartorio
- No password auth
- Tailscale VPN preferred
