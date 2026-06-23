# Pendencias SUI (So UI) - Cartorio 2 Notas Uberlandia

> Lista de acoes que DEPENDEM EXCLUSIVAMENTE de UI web (Easypanel, Cloudflare, Hostinger).
> Eu (Mavis/Pietra) nao tenho acesso a esses paineis. Gustavo precisa clicar.
> v0.5.0 (2026-06-23 13:55 BRT) — adicionada seção LGPD com pendências de assinatura DPA.

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

---

## LGPD — Pendências de assinatura / decisão jurídica (2026-06-23 13:55 BRT)

> Ações que **somente Gustavo + DPO** podem destravar. Refletem auditoria do Rein `cartorio-lgpd` na sprint de integração pesada.

### L1. Assinar DPA com MiniMax / OpenCode-Go (BLOQUEIO ATIVO)

**Por que é crítica**: Sem DPA (Data Processing Agreement), `MiniMax` pode usar dados enviados (mesmo anonimizados) para treinar modelos, conforme termos de serviço padrão. LGPD art. 33 exige contrato formal com sub-processor que receba dado pessoal.

**Como fazer**:
1. Gerar draft do DPA com base no modelo da IAPP (International Association of Privacy Professionals) — cláusula obrigatórias: (a) não treinar com nossos dados; (b) não compartilhar com terceiros; (c) notificar incidente ≤72h; (d) permitir auditoria; (e) LGPD compliance total
2. Enviar para jurídico do MiniMax (contato comercial)
3. Após assinado, salvar em `docs/lgpd/dpa_minimax.pdf`
4. Comunicar `cartorio-dev` para remover flag STAGING ONLY do `opencode_go.py`

**Tempo estimado**: 2-4 semanas (depende do jurídico do MiniMax)
**Impacto até assinar**: ambiente é **STAGING ONLY**, dado real de cliente **PROIBIDO** de circular pelo OpenCode-Go. Endpoints `/api/v1/integrations/opencode/test` retornam erro 503 em produção.

### L2. Confirmar modelo LLM real (deepseek-v4-flash vs MiniMax)

**Por que é importante**: `backend/app/integrations/opencode_go.py:6` diz `deepseek-v4-flash`. `.harness/reins/*/opencode/opencode.json` diz MiniMax-M2.7/M3. RIPD v1.2 diz MiniMax. Está inconsistente.

**Como fazer**:
1. Perguntar para `cartorio-dev` qual é o modelo real configurado em `OPENCODE_GO_MODEL` no `.env` da VPS
2. Atualizar: (a) docstring do código; (b) `opencode.json`; (c) RIPD v1.2 Tratamento 7 — para que tudo diga a mesma coisa

**Tempo estimado**: 5 min + commit + re-merge do RIPD
**Impacto até resolver**: auditoria externa (ANPD, certificação) fica confusa. Não é bloqueante, mas é sloppy.

### L3. Encryption at-rest do Postgres Supabase (pendência de segurança)

**Por que é importante**: Auditoria confirmou que VPS usa ext4 **sem LUKS** (ver `mount | grep sda1`). PG_DUMP em `/var/backups/cartorio/` é plaintext SQL. Se VPS for comprometida, dado do Chatwoot (conversas com clientes) vaza em claro.

**Como fazer (escolher UMA)**:
- **Opção A (rápida)**: Habilitar `pgcrypto` e criptografar colunas sensíveis (`conversations.content`, `contacts.email`, `contacts.phone_number`) com chave mestra em `~/.postgresql/pgkey.conf`. ~2h de trabalho de `cartorio-dev`.
- **Opção B (correta)**: Migrar volume do Postgres para LUKS-encrypted block device. Requer reinicializar VPS (~4h).
- **Opção C (intermediária)**: Criptografar os PG_DUMP antes de armazenar (gpg + chave em Vault). 30 min.

**Recomendação**: começar com **Opção A** + **Opção C** combinadas (defense-in-depth).
**Tempo estimado**: Opção A 2h, Opção C 30min, total ~2.5h
**Impacto até resolver**: risco médio LGPD art. 46 (medidas de segurança). Não bloqueante mas **deve entrar no sprint 2**.

### L4. Provisionar OpenClaw LLM key (depende de L1)

**Por que**: Hoje OpenClaw serve como gateway de UI mas sem LLM key (`OPENAI_API_KEY` ou `ANTHROPIC_API_KEY`), não faz inference real. Só usamos OpenCode-Go direto via API.

**Como fazer** (só após L1 resolvido):
1. Easypanel UI > Services > `cartorio_openclaw-gateway` > Env > Add `OPENAI_API_KEY=<sk-...>` OU `ANTHROPIC_API_KEY=<sk-ant-...>`
2. Restart: `docker service update --force cartorio_openclaw-gateway`
3. Atualizar RIPD Tratamento 7 com qual provider foi escolhido

**Tempo estimado**: 2 min
**Pré-requisito**: L1 (DPA) assinado

### Resumo LGPD

| # | Item | Prioridade | Tempo | Bloqueante? |
|---|---|---|---|---|
| L1 | DPA MiniMax assinado | **P0** | 2-4 semanas | **SIM** (até lá, STAGING ONLY) |
| L2 | Alinhar modelo LLM declarado | P2 | 5 min | Não |
| L3 | Encryption at-rest Postgres | P1 | 2.5h | Não (sprint 2) |
| L4 | OpenClaw LLM key | P2 | 2 min | Após L1 |

Modified by Gustavo Almeida
