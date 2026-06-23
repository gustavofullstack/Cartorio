# Pendencias SUI (So UI) - Cartorio 2 Notas Uberlandia

> Lista de acoes que DEPENDEM EXCLUSIVAMENTE de UI web (Easypanel, Cloudflare, Hostinger).
> Eu (Mavis/Pietra) nao tenho acesso a esses paineis. Gustavo precisa clicar.
> v0.4.1 (2026-06-23 14:10 BRT).

---

## P0 - Critico (bloqueia features em producao)

### 1. Workflow N8N #07 - Credential Evolution API
**Por que**: Workflow Pesquisa Satisfacao precisa chamar Evolution API para enviar mensagem WhatsApp. Sem credential, nao da pra ativar.

**Como fazer**:
1. Acessar `https://flow.2notasudi.com.br/home/credentials`
2. Clicar "Add Credential" > "Evolution API"
3. Preencher:
   - Name: `evolution-api-cartorio`
   - Base URL: `http://cartorio_evolution-api:8080`
   - API Key: pegar de `cat /etc/easypanel/projects/cartorio/evolution-api/.env` (EVOLUTION_API_KEY=)
4. Salvar
5. Abrir workflow "07 - Pesquisa Satisfacao"
6. No node "Evolution sendText": trocar credencial placeholder pela nova `evolution-api-cartorio`
7. Preencher `instanceName=cartorio-2notas` no node
8. Ativar workflow

**Tempo estimado**: 5 min

### 2. Chatwoot dominio custom + DNS
**Por que**: `chatwoot.2notasudi.com.br` retorna 000. Container UP mas sem DNS publico. FRONTEND_URL do Chatwoot aponta pro easypanel.host default.

**Como fazer**:
1. **Easypanel UI** > Services > `cartorio_chatwoot` > Domains > Add `chatwoot.2notasudi.com.br`
2. **Easypanel UI** > Services > `cartorio_chatwoot` > Env > Editar `FRONTEND_URL=https://chatwoot.2notasudi.com.br`
3. Restart Chatwoot: `docker service update --force cartorio_chatwoot` (SSH) ou UI restart
4. Validar: `curl https://chatwoot.2notasudi.com.br/` retorna JSON do Chatwoot

**Tempo estimado**: 10 min (incluindo propagacao DNS)

---

## P1 - Importante (UX/producao)

### 3. Chatwoot Agent Bot + Inbox
**Por que**: Bot que conecta API + Evolution com Chatwoot. Sem ele, handoff humano nao funciona.

**Como fazer**:
1. **Chatwoot UI** (login como super_admin) > Settings > Agents > Agent Bots > Add
2. Preencher:
   - Name: `cartorio-bot`
   - Description: `Bot do cartorio - recebe PII handoff do N8N workflow #03`
   - Webhook URL: `https://api.2notasudi.com.br/api/v1/webhook/chatwoot` (NOTA: endpoint nao existe ainda, criar na sprint 2)
   - Bot type: `Webhook`
3. Settings > Inboxes > Add > Website/Inbox > API inbox > Channel: WhatsApp via Evolution
4. Configurar Evolution webhook para apontar pro Chatwoot inbox
5. Adicionar env `CHATWOOT_BOT_TOKEN=<token gerado>` no cartorio_api

**Tempo estimado**: 30 min (incluindo criar endpoint backend que ainda nao existe)

### 4. Easypanel API key regenerar
**Por que**: A antiga morreu 401. Pra operacoes via Easypanel API (deploy automatico, restart), precisa de key valida.

**Como fazer**:
1. **Easypanel UI** > Settings > API > Generate Token
2. Salvar em `~/.mavis/secrets/easypanel-api-key.env` (chmod 600) no Mac
3. Substituir `EASYPANEL_API_KEY=<antiga morta>` em todos os scripts que usam

**Tempo estimado**: 2 min

### 5. DNS typo `supbase` -> `supabase`
**Por que**: Afeta UX (URL feia). Decisao: corrigir ou manter como oficial?

**Opcoes**:
- **A) Manter `supbase`** (decisao SUI): nada a fazer
- **B) Corrigir para `supabase`**:
  1. Easypanel UI > Services > `cartorio_supabase` > Domains > renomear de `supbase.2notasudi.com.br` para `supabase.2notasudi.com.br`
  2. Atualizar `SUPABASE_URL` no .env de todos os servicos (api/n8n/workflows)
  3. Atualizar docs (ENV_PRODUCTION.md)
  4. Atualizar workflows N8N que apontam pra supbase

**Tempo estimado**: 15 min (se escolher corrigir)

---

## P2 - Nice-to-have (deixar pra depois)

### 6. OpenClaw port mapping fix
**Por que**: Hoje OpenClaw escuta 18789 (bateu sorte). Args `--bind auto --port 18790 --allow-unconfigured` estao hardcoded pelo Easypanel, nao consigo alterar via `docker service update --args`. Mas esta funcionando agora, entao P2.

**Quando**: quando OpenClaw pedir auth novamente ou subir breaking change

### 7. OpenClaw LLM key (OPENAI_API_KEY ou ANTHROPIC_API_KEY)
**Por que**: Sem LLM key configurada, OpenClaw serve como gateway de UI mas nao faz inference real. Hoje so usamos Opencode-Go direto via API (sem passar pelo OpenClaw).

**Como fazer**:
1. **Easypanel UI** > Services > `cartorio_openclaw-gateway` > Env > Add `OPENAI_API_KEY=<sk-...>`
2. Restart: `docker service update --force cartorio_openclaw-gateway`

**Tempo estimado**: 2 min

### 8. Backup S3 (push remoto)
**Por que**: Hoje backup so fica em `/var/backups/cartorio/` local. Se VPS morrer, backup morre junto. Sprint 2: push pra S3 ou B2.

**Como fazer (Sprint 2)**: adicionar `rclone` + cron separado que faz `rclone sync /var/backups/cartorio b2:cartorio-backups/`

---

## Resumo

| # | Item | Prioridade | Tempo |
|---|---|---|---|
| 1 | Workflow #07 cred Evolution | P0 | 5 min |
| 2 | Chatwoot dominio custom | P0 | 10 min |
| 3 | Chatwoot Agent Bot + Inbox | P1 | 30 min |
| 4 | Easypanel API key regenerar | P1 | 2 min |
| 5 | DNS typo corrigir | P2 | 15 min (se escolher B) |
| 6 | OpenClaw port mapping | P2 | 5 min |
| 7 | OpenClaw LLM key | P2 | 2 min |
| 8 | Backup S3 | P2 | sprint 2 |

**Total P0+P1**: ~47 min de UI

Modified by Gustavo Almeida
