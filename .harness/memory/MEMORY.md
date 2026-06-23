# MEMORY — Cartorio Chatbot (cross-rein)

Licoes, decisoes e gotchas que sobrevivem alem de um unico PR.
Criterio pra escrever aqui: a licao afeta mais de um rein ou mais de uma sprint.

---

## 2026-06-23 — Sprint 0.5 hardening + bugs descobertos

### OpenClaw crash loop (resolvido parcialmente)
- **Causa 1**: `--bind lan` exige auth explicita. Sem `OPENCLAW_GATEWAY_TOKEN` no env OU `--token` no CLI, OpenClaw recusa: `Refusing to bind gateway to lan without auth`.
- **Causa 2**: Config `openclaw.json` em `/etc/easypanel/projects/cartorio/openclaw-gateway/volumes/config/` precisa ter `gateway.mode=local` OU passar `--allow-unconfigured`.
- **Args do Swarm service**: hardcoded em `--bind lan --port 18790 --allow-unconfigured` (original do Easypanel). `docker service update --args` ACEITA a mudanca mas o container ignora command hardcoded do service spec.
- **Workaround**: mudar args pra `--bind auto --port 18790 --allow-unconfigured` via Easypanel UI (Service > Edit > Command). Testado manual funciona 100%.
- **User**: rodar como `node` (UID do OpenClaw), nao root. `docker service update --user node` funciona mas ainda nao validado contra a config do service.

### n8n com senha Supabase errada
- n8n usa `DB_POSTGRESDB_USER=supabase_admin` + `DB_POSTGRESDB_PASSWORD=e999b7439deb35dfe05c33f265dae1ea` + host `db`.
- Host `db` resolve via rede Compose `cartorio_supabase_default`. Swarm n8n NAO esta nessa rede por padrao.
- `cartorio-network-monitor.sh` em `/usr/local/bin/` mantem n8n na rede compose. SEM systemd unit + SEM cron = NAO roda.
- **Fix imediato**: `ALTER USER supabase_admin WITH PASSWORD '<env_pwd>'` via `docker exec cartorio_supabase-db-1 psql -U supabase_admin -h 127.0.0.1`.
- **Fix permanente**: criar systemd unit pro monitor + reiniciar n8n via `docker service update --force cartorio_n8n`.

### API .env ainda aponta pra LiteLLM morto
- `LITELLM_BASE_URL=http://litellm:4000` + `LITELLM_MODEL_PRIMARY=claude-opus-4-5` (modelo inexistente no LiteLLM/Claude oficial)
- LiteLLM foi hackeado e removido (zero processos no host)
- **Acao**: atualizar `DATABASE_URL`, `REDIS_URL` ja estao OK. Adicionar OpenClaw como provider direto (`OPENCLAW_BASE_URL=http://cartorio_openclaw-gateway:18790`).

### DNS typo `supbase` vs `supabase`
- DNS em todos os Traefik routers aponta pra `supbase.2notasudi.com.br` (typo).
- O Gustavo precisa decidir: corrigir DNS pra `supabase` (mais profissional, mais demorado) ou aceitar `supbase` como oficial.

### Stack Supabase antiga rodando em paralelo
- 4 containers sem prefixo (`supabase-db-1`, `supabase-meta-1`, `supabase-vector-1`, `supabase-imgproxy-1`) conflitavam com `cartorio_supabase-*`.
- **Resolvido em 2026-06-23**: parados e removidos, rede `supabase_default` deletada.

### SSL/TLS funciona em todos os 6 dominios
- Traefik gerando certs Let's Encrypt via DNS-01 (Cloudflare?) automaticamente.
- Verificado CN correto em `api`, `whatsapp`, `easypanel`, `agent`, `supbase`, `flow.2notasudi.com.br`.

### Stack Supabase 14 containers saudaveis
- db, auth, rest, storage, supavisor, kong, studio, meta, analytics, realtime, functions, vector, imgproxy — todos UP.
- Kong responde 401 em `/auth/v1/health` (correto, Supabase exige API key).

### DominiOS respondendo (Mac)
- api.2notasudi.com.br 200 (Swagger + health)
- whatsapp.2notasudi.com.br 200 (Evolution)
- easypanel.2notasudi.com.br 200
- agent.2notasudi.com.br 502 (OpenClaw down)
- supbase.2notasudi.com.br 401 (Kong correto)
- flow.2notasudi.com.br 200 (n8n)

### Rede do Swarm
- `easypanel` overlay (geral)
- `easypanel-cartorio` overlay (servicos do projeto)
- Sem rede dedicada `cartorio`. OpenClaw debug funcionou com `easypanel-cartorio` apenas.

### Decisao arquitetural HIBRIDA (recomendada)
- **Logica cartorio**: Python/FastAPI no `backend/` (Sprint 0 ja tem 22 testes, 90% coverage)
- **Workflows**: n8n em `flow.2notasudi.com.br` (multi-canal, DB, emails, webhooks)
- **Gateway messaging**: OpenClaw em `agent.2notasudi.com.br` (Telegram, Discord, future)
- **WhatsApp**: Evolution API em `whatsapp.2notasudi.com.br`
- **Provider LLM**: OpenAI gpt-5.5 (ja configurado no OpenClaw como fallback Anthropic). Para Sprint 1 (consulta emolumento), gpt-5.5 da conta. Para acoes juridicas, HITL obrigatorio.

### Pipeline de prospeccao cartorios (LGPD-safe)
- CEO-assistant pesquisa melhores cartorios do Brasil (Google, ranking ANOREG).
- ROTEIRO de abordagem LGPD-safe redigido pelo `cartorio-lgpd` ANTES de envio em massa.
- Gustavo dispara do WhatsApp pessoal DEPOIS de revisar copy.
- NAO usar WhatsApp pessoal pra envio em massa > 50/dia (risco de ban + LGPD).

### Proximos passos (ordem de execucao)
1. Gustavo via Easypanel UI: cartorio_openclaw-gateway > Service > Edit > Args `--bind auto --port 18790 --allow-unconfigured` + User `node` + ANTHROPIC_API_KEY ou OPENAI_API_KEY
2. Criar systemd unit `/etc/systemd/system/cartorio-network-monitor.service` pro `cartorio-network-monitor.sh`
3. Atualizar `backend/app/core/config.py` pra ler `OPENCLAW_BASE_URL` (substituir LiteLLM)
4. Sprint 1: implementar `GET /api/v1/emolumento/calcular` + workflow n8n #1
5. LGPD: redigir texto do termo de consentimento + politica privacidade
6. Sprint 0.5.T3 backup diario Supabase (cron)
7. Sprint 0.5.T4 seed tabela emolumento MG 2026

Modified by Gustavo Almeida