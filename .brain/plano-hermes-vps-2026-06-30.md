# Plano — Hermes Gateway na VPS do Cartório

**Data:** 2026-06-30 (Turno 39)
**Decisão Gustavo (2026-06-30 09:32):** instalar Hermes gateway na VPS do Cartório, comparar OpenClaw vs Hermes.

## Aviso

**Hermes ≠ OpenClaw.** São camadas diferentes. Comparar um com o outro como "qual fica melhor" é comparar coisas diferentes. O que faz sentido é instalar Hermes e ver qual agente pessoal front-end é mais útil no nosso contexto (Hermes / Antigravity / Claude Code), dado que ambos consomem OpenClaw como gateway LLM (que é o provider real).

## O que é o Hermes

Hermes = NousResearch `hermes-agent` (versão 0.16.0 já no Mac). É um agente pessoal front-end multi-canal:
- **Canais:** Matrix, Telegram, Slack, Discord, Signal, WhatsApp (via WhatsApp bridge)
- **Providers:** qualquer LLM API (OpenAI-compat: OpenAI, Anthropic, OpenRouter, OpenClaw, OpenCode)
- **Modos:** web chat (FastAPI + WebSocket), terminal local (`hermes` CLI), gateway multi-canal
- **Memória:** SQLite local em `~/.hermes/memory/`, persistente por canal/usuário/thread
- **Skills:** carrega SKILL.md de disco, hot-reload

Não é gateway de LLM (isso é OpenClaw). Não é agente backend (isso é cartorio_api). É o front-end conversacional que orquestra tools + memória + LLM provider.

## Arquitetura alvo

```
┌─────────────────────────────────────────────────────┐
│ WhatsApp / Telegram / Web chat (clientes)           │
└──────────────────┬──────────────────────────────────┘
                   │
        ┌──────────┴───────────┐
        │                      │
        ▼                      ▼
  ┌──────────┐           ┌──────────┐
  │ OpenClaw │           │  Hermes  │
  │(atual)   │           │ (novo)   │
  │ :18789   │           │ :8642    │
  │ HTTP+WS  │           │ HTTP+WS  │
  └─────┬────┘           └─────┬────┘
        │                      │
        └──────────┬───────────┘
                   │
                   ▼
            ┌─────────────┐
            │ OpenClaw    │ ← provider único LLM (já no ar)
            │ :18789      │
            └─────────────┘
                   │
                   ▼
            ┌─────────────┐
            │ chain LLM   │ (10 provedores — fallback dinâmico)
            └─────────────┘
```

Hermes recebe mensagem → pensa via OpenClaw (provider) → responde no canal (Telegram/Matrix/etc).

## Pré-requisitos

✅ **Acesso SSH**: VPS `root@100.99.172.84` via Tailscale (key `~/.ssh/id_ed25519_cartorio`)
✅ **Docker Swarm**: já roda, gerenciado por Easypanel. Containers em `cartorio_*`.
✅ **OpenClaw UP**: `cartorio_openclaw-gateway:18789`, HTTP plain (já aceito pelo nosso backend).
⚠️ **DNS_LOST herdado**: `chatwoot.2notasudi.com.br` quebrado (60+ ticks). `hermes.2notasudi.com.br` precisa de entrada CNAME/A — adicionar manualmente em hpanel Hostinger (regra Lesson 181).
⚠️ **Traefik labels**: novo serviço precisa de label Traefik + entrypoint 80/443.
⚠️ **LiteLLM morto**: `.env` aponta `LITELLM_BASE_URL` mas container não existe — irrelevante (OpenClaw direto).

## Plano de deploy (3 etapas)

### Etapa 1 — Preparação (10 min)
1. SSH VPS via Tailscale.
2. Validar que OpenClaw está respondendo: `curl http://agent.2notasudi.com.br/health` → 200 com `{"ok":true}`.
3. Validar Swarm: `docker node ls` → 1 manager Ready.
4. Validar Traefik: Easypanel UI confirma entrypoints 80/443 funcionais.
5. Backup do estado atual: `docker service ls > /tmp/pre-hermes-services.txt`.
6. Validar DNS: `dig +short hermes.2notasudi.com.br @8.8.8.8` → se NXDOMAIN, criar entrada A em hpanel `187.77.236.77` (5 min UI).

### Etapa 2 — Deploy container (20 min)
1. Clonar repo hermes-agent ou usar imagem Docker oficial (NousResearch ainda não tem imagem oficial — provavelmente precisa pip install + Python venv + systemd).
2. Criar docker-compose em `/etc/easypanel/projects/cartorio/hermes/docker-compose.yml`.
3. Container config:
   - Imagem: `python:3.11-slim` + `pip install hermes-agent[matrix,telegram]`
   - Porta: `8642` (default Hermes gateway), bind 0.0.0.0:8642
   - Env:
     - `HERMES_PROVIDER_BASE_URL=http://cartorio_openclaw-gateway:18789`
     - `HERMES_PROVIDER_MODEL=opencode_go`
     - `HERMES_TELEGRAM_BOT_TOKEN=` (Gustavo criar via BotFather SUI)
     - `HERMES_ALLOWED_USERS=` (whitelist inicial — Gustavo + tests)
   - Volume: `~/.hermes` montado persistente
   - Network: `easypanel-cartorio_default` (mesma do backend)
4. `docker stack deploy` ou `docker-compose up -d`.
5. Validar: `curl http://localhost:8642/health` → 200.

### Etapa 3 — Traefik + DNS (15 min)
1. Adicionar Traefik label no docker-compose:
   ```yaml
   labels:
     - "traefik.enable=true"
     - "traefik.http.routers.hermes.rule=Host(`hermes.2notasudi.com.br`)"
     - "traefik.http.routers.hermes.entrypoints=websecure"
     - "traefik.http.routers.hermes.tls.certresolver=letsencrypt"
     - "traefik.http.services.hermes.loadbalancer.server.port=8642"
   ```
2. Easypanel UI: criar entrada DNS `hermes.2notasudi.com.br A 187.77.236.77` em hpanel Hostinger.
3. Test: `curl https://hermes.2notasudi.com.br/health` → 200 (cert Let's Encrypt pode levar 1-2 min).
4. Adicionar entrada no radar cron `cartorio-radar-consolidado` (novo probe `hermes`).

## Rollback

Se der errado:
1. `docker stack rm hermes` ou `docker-compose down -v`.
2. Remover Traefik labels.
3. Apagar entrada DNS em hpanel.
4. Restaurar backup `/tmp/pre-hermes-services.txt` se necessário.

Tempo de rollback: ~3 minutos.

## Riscos

- **DNS_LOST**: Hostinger Parking NS não propaga automático. Se Gustavo esquecer de criar A record, Traefik fallback não acontece.
- **OpenClaw como provider**: ainda não validei que Hermes conversa OpenAI-compat com OpenClaw. Pode precisar adapter layer. **Risco operacional.**
- **Mais container pra manter**: Hermes Agent tem updates frequentes. Precisa entrar no ciclo de update normal.
- **Audit LGPD**: Hermes NÃO tem LGPD compliance built-in. Toda chamada precisa de PII scrub via wrapper (Lesson 11). Provavelmente preciso criar middleware Hermes → OpenClaw com scrub.
- **Sem LGPD consent**: Hermes aceita QUALQUER mensagem por padrão. Vai precisar de `MATRIX_ALLOWED_USERS` / `TELEGRAM_ALLOWED_USERS` desde dia 1.

## Decisão

**Antes de aplicar**, preciso de OK Gustavo para:
1. Adicionar entrada DNS em hpanel Hostinger (5min UI-only).
2. Criar bot Telegram no BotFather (5min UI-only).
3. Deploy do container Hermes (eu rodo).
4. Whitelist inicial: APENAS Gustavo + 1-2 testes. Produção só expande após validação.

**Alternativa mais barata (recomendação real minha)**: instalar Hermes agente LOCAL no seu Mac (`~/.hermes/hermes-agent` já tá lá), conectar Telegram via OpenClaw Tailscale `agent.2notasudi.com.br:18789`. Cartório 100% VPS via OpenClaw. Hermes pessoal roda no Mac só pra você brincar. **Zero risco VPS, zero DNS, zero container extra.** Você só roda `hermes gateway setup` + `hermes extras telegram` + `hermes gateway run`.

**Trade-off**: VPS = redundância real (se OpenClaw cair, Hermes vira alternativa). Mac local = zero overhead operacional, mas morre se Mac desligar.

**Recomendação final minha**: MAC LOCAL primeiro (R$ 0 adicional + zero risco). Depois, se quiser comparar VPS, faz deploy numa branch paralela. Mas Gustavo escolheu VPS — apresentei o plano.
