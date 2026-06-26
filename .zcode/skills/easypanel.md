# Skill: Easypanel Management
## Purpose
Manage Docker Swarm services via Easypanel.
## URL
- https://easypanel.2notasudi.com.br
- Admin: admin@2notasudi.com.br
## Project
- Name: cartorio
- Path: /projects/cartorio
## Services (13)
- cartorio_api, cartorio_chatwoot, cartorio_chatwoot-sidekiq
- cartorio_evolution-api, cartorio_n8n, cartorio_n8n-runner
- cartorio_openclaw-gateway, cartorio_redis, cartorio_redis_dbgate
- cartorio_redis_rediscommander, easypanel, easypanel-traefik, vps_whoami
## Deploy
```bash
# Build image
docker build -t easypanel/cartorio/api:vX.X.X .
# Update service
docker service update --image easypanel/cartorio/api:vX.X.X cartorio_api
```
