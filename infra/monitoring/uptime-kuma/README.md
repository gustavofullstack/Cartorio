# C24 — Uptime Kuma (status.2notasudi.com.br)

> **[HOLD-DEPLOY]** Gustavo precisa decidir se vai deployar. Nao aplicar sem GO explicito.

## Visao geral

Uptime Kuma e o painel padrao de status publico para os **7 dominios criticos**
do Cartorio. Roda como container no Swarm, exposto em
**`status.2notasudi.com.br`** via Traefik.

| # | Dominio | Funcao | Alvo SLO |
|---|---|---|---|
| 1 | `api.2notasudi.com.br` | Backend FastAPI + radar 7 servicos | 99.5% |
| 2 | `flow.2notasudi.com.br` | N8N workflow engine | 99.0% |
| 3 | `whatsapp.2notasudi.com.br` | Evolution API v2.3.7 | 99.0% |
| 4 | `cartorio-chatwoot.dfgdxq.easypanel.host` | Chatwoot CRM 3.x | 99.0% |
| 5 | `agent.2notasudi.com.br` | OpenClaw Gateway LLM | 99.0% |
| 6 | `supbase.2notasudi.com.br` | Supabase REST API | 99.5% |
| 7 | `easypanel.2notasudi.com.br` | Painel de deploy | 98.0% |

## Estrutura

```
infra/monitoring/uptime-kuma/
├── docker-compose.yml    # servico uptime-kuma:1 + Traefik labels
├── monitors.json         # 7 monitores + 1 status page (UI import)
├── README.md             # este arquivo (runbook)
└── telegram-alerts.md    # C25 - config alertas Telegram
```

## Pre-requisitos

- DNS A record `status.2notasudi.com.br` apontando para `187.77.236.77` (VPS)
- Traefik router `websecure` com resolver `letsencrypt` (ja existe)
- Network `cartorio` (overlay Swarm) — criado automaticamente
- Token Telegram bot (criar com `@BotFather`) — opcional, so se for usar C25
- Tokens/leaked keys para os 4 monitores com header (`whatsapp`, `chatwoot`, `supabase`)

## Deploy (3 passos)

### Passo 1 — DNS

Adicionar no Cloudflare (gestor DNS do `2notasudi.com.br`):

```
Type: A
Name: status
Content: 187.77.236.77
Proxy: DNS only (cinza) — Traefik cuida do TLS
TTL: 300
```

> **Status atual (2026-07-15)**: registro **NAO criado**. B3 pendente desde 2026-06-26 (NXDOMAIN para chatwoot/n8n/supabase, mesmo dominio).

### Passo 2 — Subir o container

```bash
cd /Users/gustavoalmeida/projetos/Cartorio
scp infra/monitoring/uptime-kuma/docker-compose.yml cartorio@vps-cartorio:/tmp/

ssh cartorio@vps-cartorio
  cd /opt/cartorio/monitoring  # criar dir antes se nao existir
  cp /tmp/docker-compose.yml .
  docker stack deploy -c docker-compose.yml monitoring

  # verificar
  docker service ls | grep uptime-kuma
  docker service logs monitoring_uptime-kuma --tail 50
```

> **Porta**: o compose usa `3001:3001` host. Traefik faz o offload TLS, entao
> a porta `3001` NAO precisa estar exposta externamente — ela vive apenas
> dentro do overlay `cartorio`. Se Traefik nao resolver, validar com
> `curl http://uptime-kuma:3001` de outro container na mesma network.

### Passo 3 — Importar monitors.json

**Opcao A (UI)**: acessar `https://status.2notasudi.com.br` (1o acesso cria
admin), depois `Settings → Backup → Import` colando `monitors.json`.

**Opcao B (API)**: usar o script `backend/scripts/import_uptime_kuma_monitors.py`
(se existir) OU diretamente via `curl`:

```bash
curl -X POST https://status.2notasudi.com.br/api/monitors \
  -H "Authorization: Bearer $UPTIME_KUMA_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d @infra/monitoring/uptime-kuma/monitors.json
```

> **Caveat**: o campo `id` em `monitors.json` e nosso controle (slug);
> Uptime Kuma gera o ID numerico real internamente. O import cria os
> monitores em sequencia e atualiza o mapeamento.

## Pos-deploy

1. **Smoke test**: aguardar ~3 min, abrir `https://status.2notasudi.com.br`
   e confirmar 7 monitores verdes.
2. **Alert test**: forcar DOWN em 1 monitor via UI, validar Telegram (se C25 ativo).
3. **Backup**: adicionar `infra/backup/uptime-kuma.sh` ao cron semanal
   (exporta todos os monitores + status page).

## Rollback

```bash
ssh cartorio@vps-cartorio
  docker service rm monitoring_uptime-kuma
  # container some em ~10s. Dados em volume `uptime-kuma-data` ficam
  # para re-deploy. Para zerar: docker volume rm monitoring_uptime-kuma-data
```

## Gotchas

- **Healthcheck-every-60s** (per spec): ja configurado no compose, mas Uptime
  Kuma usa `interval` 300s (5 min) por monitor — balanceia carga no VPS vs.
  deteccao rapida. Sobe para 60s se Gustavo quiser mais granularidade.
- **`/health/backup` da API** NAO foi incluido como monitor separado (e
  derivado do health radar principal). Cobre em cartorio-api.
- **Whapp `state=close` NAO significa DOWN**: monitor do WhatsApp precisa
  validar `state=open` no body. Workaround: usar status 200 + criar monitor
  separado `JSON Path` em versao futura. Hoje so validamos HTTP 200.
- **Traefik docker network**: se o Swarm foi criado com outra network overlay
  (ex: `traefik_public`), ajustar `traefik.docker.network` no compose.

## Status checklist

- [ ] DNS A record criado
- [ ] Container deployado e respondendo em `/` (200)
- [ ] 7 monitors importados e verdes
- [ ] Status page publica em `status.2notasudi.com.br`
- [ ] Telegram alert testado (C25)
- [ ] Backup cron configurado

## Referencias

- Uptime Kuma: <https://github.com/louislam/uptime-kuma>
- Traefik labels: <https://doc.traefik.io/traefik/providers/docker/>
- Lesson 172 (P0 Traefik 502 outage, 2026-07-14) — case study de incidente
- Lesson 176 (SRE 502 recovery, 2026-07-14) — padrao de resposta

---

**Modified by**: cartorio-sre + Gustavo Almeida
**Status**: [HOLD-DEPLOY]
**Last reviewed**: 2026-07-15