# ADR-015: Chatwoot restart loop (Puma + Docker Swarm)

**Data:** 2026-06-23
**Status:** Investigation pending (requer acesso SSH à VPS)
**Sprint:** Sprint 2, task 8

## Contexto

Container `cartorio_chatwoot` reinicia a cada 1-2 minutos (exit 1).
HTTP interno responde 200 OK durante uptime, então serviço funciona enquanto está up.
Sintoma: logs de SIGTERM + exit 1 repetido.

**Achado da sessão 18:50 (vide `docs/SESSION_SUMMARY_2026-06-23.md`):**
- Puma sobe e escuta porta 3000 OK
- Depois recebe SIGTERM e morre (exit 1)
- 4 restarts nas últimas 2h, todos Failed exit 1
- Container responde HTTP durante uptime (200 com HTML completo)
- Restart é por algo no shutdown/keepalive

## Hipóteses (em ordem de probabilidade)

### H1. OOM kill (mais provável)
Docker Swarm mata o container quando bate o memory_limit.
**Verificar:**
```bash
ssh gustavo@100.99.172.84
docker inspect cartorio_chatwoot | grep -A5 Memory
docker service ps cartorio_chatwoot --no-trunc | grep -i "oom\|killed"
```
**Fix se confirmado:** aumentar memory_limit de 512M para 1G via Easypanel UI.

### H2. Healthcheck timeout
Swarm healthcheck espera `curl http://localhost:3000/` retornar 200 em <start_period>.
Puma pode demorar >30s pra inicializar (assets precompile, DB check).
**Verificar:**
```bash
docker inspect cartorio_chatwoot | grep -A20 Health
```
**Fix se confirmado:** aumentar `start_period` de 60s para 180s.

### H3. DB connection drop
Puma abre conexão no boot, mas se Supabase reinicia, Puma não reconecta.
Chatwoot tenta reconnect → falha → exit.
**Verificar:**
```bash
docker logs cartorio_chatwoot --tail 200 2>&1 | grep -iE "db|pg|connection"
```
**Fix se confirmado:** adicionar `preconnect_rails_puma_worker_killer` ou forçar reconnect no boot.

### H4. keepalive / graceful shutdown mal configurado
Puma recebe SIGTERM, tenta drain de conexões, mas timeout >10s do Swarm → SIGKILL → exit 1.
**Verificar:**
```bash
docker inspect cartorio_chatwoot | grep -A5 "StopGracePeriod\|StopSignal"
```
**Fix se confirmado:** adicionar `force_stop=true` no docker-compose ou aceitar exit 1 (Swarm já trata).

## Comando único de diagnóstico

```bash
ssh gustavo@100.99.172.84 'docker service ps cartorio_chatwoot --no-trunc --format "{{.Name}} {{.CurrentState}} {{.Error}}" | head -10 && echo "---" && docker inspect cartorio_chatwoot.1.$(docker service ps cartorio_chatwoot --no-trunc --format "{{.ID}}" | head -1) 2>/dev/null | grep -A2 -iE "memory|health|restart|stop" | head -30'
```

## Decisão (placeholder — preencher após investigação)

**A ser decidido após Gustavo rodar o comando acima e postar resultado.**

Opções prováveis:
- **A) Se OOM:** aumentar memory_limit → ação SUI (UI Easypanel)
- **B) Se healthcheck:** relaxar `start_period` → patch no `docker-compose.yml` do Chatwoot
- **C) Se DB:** adicionar reconnect no boot → PR no repo do Chatwoot
- **D) Se nada óbvio:** aceitar e adicionar `restart: always` + alerta no radar (N8N #11)

## Consequências esperadas

- Downtime reduzido de 1-2min para 0
- Logs limpos
- Monitoramento proativo via `/health/backup` watch pattern

## Ações de follow-up

- [ ] Gustavo roda comando de diagnóstico acima
- [ ] Gustavo posta output em `docs/INCIDENTE_CHATWOOT_LOOP_2026-06-23.md`
- [ ] Aplicar fix escolhido
- [ ] Validar uptime >24h estável
- [ ] Adicionar alerta no workflow N8N #11 (Monitor Cartório)

## Referências

- `docs/PENDENCIAS_SUI_2026-06-23.md` (bug B1)
- `docs/SESSION_SUMMARY_2026-06-23.md` (achado 18:50 BRT)
- `infra/traefik/` (se for issue de proxy/TLS)
