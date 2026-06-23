# ADR-013: Backup Mount Watchdog (2026-06-23)

## Contexto
- Endpoint `/api/v1/health/backup` quebrou em 2026-06-23 18:36 BRT retornando
  `[Errno 2] No such file or directory: 'docker'`.
- Causa raiz: bind mount `/var/backups/cartorio -> /var/backups/cartorio (readonly)`
  no `cartorio_api` service tinha sumido da spec (ver `docker service inspect`).
- Reproduzivel: qualquer `docker service update --image ...` ou restart
  (rolling update, deploy via Easypanel) descarta mounts customizados.
- Backup diario continuou rodando (cron OK, 7 tarballs em /var/backups/cartorio/),
  mas API nao conseguia reportar o status.

## Decisao
- Criar watchdog `cartorio-backup-mount-watchdog.sh` que detecta mount ausente
  e reaplica em <30s.
- Rodar a cada 15min via cron `/etc/cron.d/cartorio-watchdog`.
- Log em `/var/log/cartorio-watchdog.log` para auditoria.

## Consequencias
- (+): /api/v1/health/backup volta a ser confiavel mesmo apos deploys
- (+): detecta o problema antes do N8N workflow #09 Monitor Backup
- (-): requer SSH key + permissao root na VPS (ja temos)
- (-): adiciona 4 chamadas SSH/15min = 16/dia = 5840/ano (insignificante)

## Alternativas consideradas
- A) Script no entrypoint do container: rejeitado, requer rebuild + re-deploy
- B) Healthcheck do Swarm mais agressivo: rejeitado, nao detecta mount
- C) Volume em vez de bind mount: rejeitado, complicaria backup external
