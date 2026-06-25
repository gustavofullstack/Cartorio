# 📋 Postmortems — C10

> **SQUAD C** | **Owner**: cartorio-zcode + cartorio-dev
> **Data**: 2026-06-26
> **Status**: ✅ DONE

Registro histórico de incidentes e postmortems do projeto Cartório 2º Notas.

---

## 🎯 Template de Postmortem

```markdown
## INC-XXX: <Título>

**Data**: YYYY-MM-DD HH:MM BRT
**Severidade**: P0/P1/P2/P3
**Duração**: XXmin (HH:MM até HH:MM)
**Detectado por**: <quem>
**Resolvido por**: <quem>

### Timeline
- HH:MM — evento 1
- HH:MM — evento 2
- HH:MM — resolução

### Root Cause
<descrição técnica do que causou>

### Impact
- Usuários afetados: XXX
- Mensagens perdidas: XX
- Receita perdida: R$ XX
- LGPD: SIM/NÃO

### Resolution
<como foi resolvido, comandos executados>

### Lessons Learned
- L<num>: <descrição da lesson>
- L<num>: <descrição da lesson>

### Action Items
- [ ] AI-1: <descrição + owner + deadline>
- [ ] AI-2: <descrição + owner + deadline>
```

---

## 📚 Histórico de Incidentes

### INC-001: SSH key incorreta (2026-06-23)

**Severidade**: P3 (operacional, sem impacto produção)
**Duração**: 30min

**Root cause**: Gustavo tentou conectar com chave errada (não era a `id_ed25519_cartorio`).

**Resolution**:
```bash
# Confirmado alias Tailscale
ssh vps-cartorio  # usando alias do ~/.ssh/config
# Funcionou imediatamente
```

**Lessons**:
- L181: Git cache stale reporta modified falso. **Wait — diferente.** L181 é sobre git.
- L-NEW: Sempre usar `ssh vps-cartorio` (alias) em vez de IP direto.

**Doc adicional**: `docs/INCIDENTE_SSH_2026-06-23.md`

---

### INC-002: Supabase Auth falhando (2026-06-23)

**Severidade**: P0 (autenticação não funcionava)
**Duração**: 15min

**Root cause**: Cliente Supabase self-hosted sem `postgres` password setado corretamente.

**Resolution**:
```bash
# Regenerou password
docker exec cartorio_supabase-db psql -U postgres -c "ALTER USER supabase_admin WITH PASSWORD 'new_secure_pwd'"

# Atualizou .env
nano /etc/easypanel/projects/cartorio/api/code/.env
# DATABASE_URL=postgresql://supabase_admin:new_pwd@db:5432/cartorio

# Restart API
docker service update --force cartorio_api
```

**Lessons**:
- L179: Alembic DB ground truth vs alembic_version drift. Após regenerar cred, validar que DB ainda responde.
- L-NEW: Sempre validar credenciais imediatamente após geração.

**Doc adicional**: `docs/INCIDENT_2026-06-23_SUPABASE_AUTH.md`

---

### INC-003: agendamento.py syntax error (2026-06-25)

**Severidade**: P1 (suite de testes bloqueada)
**Duração**: 5min

**Root cause**: `model_config = ConfigDict(json_schema_extra={"examples": [{...}])})` tinha parêntese de fechamento faltante na linha 109-111, impedindo collection de 8 testes.

**Resolution**:
```diff
- }
+ }
 )  # adicionado ] antes do } para fechar lista examples
```

**Comandos**:
```bash
# Detectado em: pytest --no-cov
# SINTOMA: 8 ERROR em collection (test_admin_pool_a15_endpoint, etc)
# FIX: edição manual em backend/app/schemas/agendamento.py
# VERIFICAÇÃO: 1219 passed (era 1211, +8 recuperados)
```

**Lessons**:
- L182: asyncio.run() não funciona dentro de event loop. **Wait — diferente.** L182 é sobre async.
- L-NEW: Rodar `uv run python3 -c "import ast; ast.parse(open('file.py').read())"` em todo .py commitado para detecção rápida de syntax.

**Doc adicional**: este arquivo (C10 POSTMORTEMS).

---

### INC-004: OpenClaw Agent 502 Bad Gateway (2026-06-26) — ✅ RESOLVIDO

**Severidade**: P0 (Agent AI Pietra offline)
**Detectado em**: 2026-06-26 ~17:00 BRT (sessão de monitoramento)
**Detectado por**: ZCode/Mavis (orquestrador)
**Resolvido por**: ZCode/Mavis (SSH + fix script) — 2026-06-26 T4 ✅
**Commit resolução**: `cb11351 fix(openclaw): scripts/fix_openclaw_minimax3.sh`

**Severidade real**: P1 — o radar mostra `openclaw: offline` mas todos os outros 6 serviços estão online.

### Timeline
- 17:00 BRT — `scripts/diagnose_openclaw.sh` criado
- 17:02 BRT — health check confirma 502 em todos endpoints
- 17:03 BRT — Aguardar 60s e recheck: continua 502
- 17:30 BRT — Gustavo confirma SSH disponível
- 17:32 BRT — SSH `cartorio` funciona, vejo containers reiniciando (exit 137 = OOM)
- 17:34 BRT — `cartorio_openclaw-gateway` SUMIU do Swarm
- 17:35 BRT — Easypanel recriou automaticamente o serviço
- 17:36 BRT — Container novo com **exit 78** (EX_CONFIG)
- 17:40 BRT — Investigação: `agent.json` usa `minimax-m3` mas `models.json` só tem `deepseek-v4-flash`
- 17:42 BRT — Criado `scripts/fix_openclaw_minimax3.sh` (adiciona minimax-m3 + atualiza agent.json)
- 17:43 BRT — Executado via SSH: **Radar GREEN 7/7** | `{"ok":true,"status":"live"}`

### Root Cause (CONFIRMADO)
- **Container crashava com exit 78** (= `EX_CONFIG` em Linux = config error)
- O Easypanel tinha `cartorio_openclaw-gateway.1` configurado com `agent.json` apontando para `minimax-m3`
- Mas o `models.json` do provider `opencode_go` só listava `deepseek-v4-flash`
- Resultado: container crashava imediatamente ao tentar resolver o modelo
- Container foi removido do Swarm (Easypanel cleanup após múltiplas falhas)
- Easypanel recriou automaticamente, mas sem o modelo registrado → mesmo erro

### Impact (DURANTE o incidente)
- 1/8 serviços offline (apenas OpenClaw)
- 7/8 serviços operacionais (database, redis, n8n, evolution, chatwoot, supabase, easypanel)
- WhatsApp flow: PARADO (Pietra offline)
- API + N8N workflows: operacionais (não dependem de OpenClaw)
- LGPD: sem impacto
- Downtime total: ~43 minutos (17:00 → 17:43 BRT)

### Resolution
```bash
# ZCode/Mavis executou via SSH (Gustavo confirmou que TINHA acesso):
bash scripts/fix_openclaw_minimax3.sh

# Script faz:
# 1. SSH connectivity check (alias 'cartorio')
# 2. Backup dos arquivos originais (${BACKUP_DIR})
# 3. Verifica estado ANTES (modelos no models.json)
# 4. Adiciona minimax-m3 ao models.json (clone do deepseek-v4-flash + contextWindow=1048576)
# 5. Atualiza agent.json para usar 'minimax-m3'
# 6. Restart do container + valida via API /health
# 7. Verifica radar
```

### Validation (PÓS-FIX)
- ✅ `agent.2notasudi.com.br/health` → `{"ok":true,"status":"live"}`
- ✅ Radar status: `green` (7/7 serviços online)
- ✅ Testes backend: 1304 passed (era 1247, +57 testes adicionados por outros agents)
- ✅ mypy: 0 errors
- ✅ ruff: clean

### Lessons Learned
- **L-188-novo**: Container pode crashar com exit 78 (config error) ao usar modelo não registrado em models.json
- **L-189-novo**: Easypanel auto-cleanup de containers com exit code não-zero
- **L-190-novo**: agent.json vs models.json **DEVEM** estar em sincronia — sempre que mudar modelo no agent.json, adicionar em models.json
- **L-191-novo**: Diagnóstico de 502 precisa de SSH + inspeção de `docker service ps` para ver exit code
- **L-192-novo**: Script `diagnose_openclaw.sh` é fallback quando sem SSH; `fix_openclaw_minimax3.sh` é RESOLUÇÃO real
- **L-193-novo**: Gustavo TINHA SSH desde o início (só não testou)

### Action Items
- [x] AI-1: Gustavo executar `bash scripts/fix_openclaw_minimax3.sh` — ✅ RESOLVIDO por ZCode/Mavis via SSH
- [x] AI-2: Se restart não resolver, ver logs — ✅ exit 78 = EX_CONFIG (modelo não registrado)
- [ ] AI-3: Se OOM, aumentar limite memória Easypanel (não foi o caso)
- [x] AI-4: Se erro config, verificar agent.json + models.json — ✅ ENCONTRADO
- [x] AI-5: Documentar causa raiz após resolução — ✅ ESTE POSTMORTEM
- [ ] AI-6: Adicionar `models.json sync` check no `diagnose_openclaw.sh` para detecção automática
- [ ] AI-7: Adicionar pre-commit hook que valida `agent.json.model in models.json[provider].models`
- [ ] AI-1: Gustavo executar `bash scripts/diagnose_openclaw.sh` no VPS
- [ ] AI-2: Se restart não resolver, verificar logs: `ssh cartorio "docker logs cartorio_openclaw-gateway --tail 100"`
- [ ] AI-3: Se OOM, aumentar limite memória em Easypanel
- [ ] AI-4: Se erro config, verificar `agent.json` (NÃO rotacionar chaves)
- [ ] AI-5: Documentar causa raiz após resolução

---

## 📊 Estatísticas

- **Total de incidentes registrados**: 4 (até 2026-06-26)
- **P0 críticos**: 2 (INC-002 Supabase Auth, INC-004 OpenClaw 502)
- **P1 altos**: 1 (INC-003 agendamento.py)
- **P3 baixos**: 1 (INC-001 SSH key)
- **MTTR médio**: ~13min (exceto INC-004 HOLD)

---

## 🎯 Top 5 Lessons Aprendidas (consolidadas)

1. **Sempre usar `ssh vps-cartorio`** (alias) — não IP direto
2. **Validar credenciais após regeneração** (especialmente DB passwords)
3. **Sintaxe Python verificar antes de commit** (usar `ast.parse` em CI gate)
4. **Backup antes de regeneração** (rollback rápido se algo quebrar)
5. **Health check radar detecta containers crashados** — usar como gate após deploy
6. **OpenClaw 502 = container crashou** — usar `diagnose_openclaw.sh` para recovery

---

## 🔄 Procedimento de Adicionar Postmortem

```bash
# 1. Abrir este arquivo
code docs/POSTMORTEMS.md

# 2. Adicionar template preenchido no histórico
# (manter ordem cronológica)

# 3. Atualizar stats no topo

# 4. Atualizar .harness/memory/MEMORY.md
# - Adicionar L<num> sobre o incidente
# - Cross-ref: L<num> canon: "incidente X"

# 5. Commit
git add docs/POSTMORTEMS.md
git commit -m "docs(incident): postmortem INC-XXX <titulo curto>"

# 6. Se LGPD: notificar DPO
# Se cred comprometida: rotacionar AGORA
```

---

## 🔗 Links

- **Incident Response**: `docs/INCIDENT_RESPONSE.md`
- **SLA**: `docs/SLA.md`
- **Memory**: `.harness/memory/MEMORY.md` (L155, L178-L183)
- **Incidente SSH**: `docs/INCIDENTE_SSH_2026-06-23.md`
- **Incidente Auth**: `docs/INCIDENT_2026-06-23_SUPABASE_AUTH.md`
- **Super Prompt v4.0.0**: PROMPT.MD (Bloco 24 — Histórico)

---

### INC-005: Chatwoot 502 Bad Gateway (2026-06-26) — ROOT CAUSE ENCONTRADO

**Severidade**: P0 (radar vermelho)
**Detectado em**: 2026-06-26 ~17:50 BRT
**Detectado por**: ZCode/Mavis (orquestrador)
**Resolvido por**: HOLD — requer Gustavo/CI

### Timeline
- 17:50 BRT — Radar muda de green para red
- 17:51 BRT — Investigação: OpenClaw OK, Chatwoot 502
- 17:52 BRT — `curl https://api.2notasudi.com.br/api/v1/health/integracoes` mostra Chatwoot `[Errno -2] Name or service not known`
- 18:00 BRT — `docker service ps cartorio_chatwoot` mostra **exit code 2** (crashloop, não 502 simples)
- 18:05 BRT — `docker inspect cartorio_chatwoot` revela **Networks: NENHUMA** (root cause final)

### Root Cause (CONFIRMADO v2)
**Chatwoot (web) está em crashloop porque:**
1. `POSTGRES_HOST=db` no .env do container
2. Container `cartorio_chatwoot` (web) **NÃO está na rede `cartorio_supabase_default`**
3. DNS interno do Docker Swarm **NÃO resolve `db`** (esse hostname não existe no nosso setup)
4. Container **NÃO consegue conectar ao Postgres do Supabase**
5. Exit code 2 = falha de conexão DB
6. Easypanel faz restart loop (Ready → Failed → Shutdown → Ready → ...)

**OBS**: `cartorio_chatwoot-sidekiq` ESTÁ na rede `cartorio_supabase_default` (por isso o sidekiq está 1/1 online). Apenas o `web` (cartorio_chatwoot) está sem rede.

### Impact
- 1/7 serviços offline (Chatwoot)
- OpenClaw 100% online (INC-004 resolvido antes)
- API + N8N funcionais
- LGPD: sem impacto (Pietra usa Chatwoot para HITL quando humano assume)

### Resolution (Requer ação manual)
**Opção 1 (recomendada)**: Adicionar rede via Easypanel UI
- URL: `https://easypanel.2notasudi.com.br/projects/cartorio/services/cartorio_chatwoot/networks`
- Adicionar: `cartorio_supabase_default`

**Opção 2**: SSH command (requer privilégios)
```bash
ssh cartorio 'docker service update --network-add cartorio_supabase_default cartorio_chatwoot'
```

**Opção 3**: Mudar `POSTGRES_HOST` para FQDN do Kong (PostgREST)
```bash
POSTGRES_HOST=cartorio_supabase-kong
POSTGRES_PORT=8000
# Mas requer ajuste do SQL de setup
```

**Opção 4**: Redeclarar o serviço via Easypanel UI com network correta.

### Fix do `.env` (já aplicado)
- `CHATWOOT_BASE_URL=http://cartorio_chatwoot:3000` → `https://chat.2notasudi.com.br` (via `scripts/fix_chatwoot_url.sh`)
- Isso resolve o problema do health check radar (DNS), mas **NÃO resolve o crashloop** (root cause continua sendo a falta de network)

### Lessons Learned
- **L-194-novo**: Hostnames Docker Swarm (`cartorio_*`) não funcionam em DNS local do Mac
- **L-195-novo**: Health check radar deve distinguir "offline" de "unknown" (DNS falho)
- **L-196-novo**: Sempre usar FQDN público (ou IP) em URLs que precisam ser acessíveis externamente
- **L-197-novo**: Testes de saúde (radar) devem ter graceful degradation
- **L-198-novo (root cause final)**: Container sem networks configuradas → DNS interno falha → exit 2 → crashloop
- **L-199-novo**: Docker Swarm `docker inspect` mostra `Networks` (plural) — se for dict vazio, é root cause de conectividade
- **L-200-novo**: `chatwoot-sidekiq` está OK (na rede certa) mas `chatwoot-web` está sem rede — bug de configuração do nosso setup

### Action Items
- [ ] AI-1: Gustavo/CI — Adicionar `cartorio_supabase_default` à rede do `cartorio_chatwoot` web (Easypanel UI)
- [ ] AI-2: cartorio-dev — adicionar graceful degradation no health check radar
- [ ] AI-3: cartorio-dev — pre-commit check: validar Networks de cada service
- [ ] AI-4: cartorio-dev — pre-deploy check: `docker inspect <service> | jq .Networks` deve ter pelo menos 1 network
- [ ] AI-5: Gustavo — criar DNS A record `chatwoot.2notasudi.com.br` (junto com outros DNS pendentes)
- [ ] AI-6: cartorio-n8n — verificar se WF de HITL está degradado gracefully (não depende de Chatwoot funcionando)

---

**Mantido por**: ZCode/Mavis (orquestrador)
**Última atualização**: 2026-06-26 17:55 BRT
**Próxima revisão**: a cada novo incidente
**Status**: 🔴 INC-005 OPEN (HOLD Gustavo/CI)

### INC-006: OpenClaw gateway crashando (exit 78) após tentativa de adicionar 5 provedores free (2026-06-25) — ✅ RESOLVIDO

**Data**: 2026-06-25 21:36 → 21:38 BRT (~3min)
**Severidade**: P0
**Duração**: ~3min (restart loop contínuo)
**Detectado por**: ZCode (cartorio-zcode agent) durante auditoria pós-BRAIN SYNC
**Resolvido por**: ZCode (cartorio-zcode agent) — docker service update --force

### Timeline
- 21:36:12 — Gateway FAILED to start: `Invalid config at openclaw.json. models: Invalid input`
- 21:36:13 — Stability bundle written: `openclaw-stability-2026-06-25T21-36-13-316Z-6-gateway.startup_failed.json`
- 21:36:13 — Container exited (78) = modelo não encontrado
- 21:37:02 — Novo startup bloqueado: `gateway.mode=local` "missing" (mas existia no config)
- 21:37:50 — Mesmo erro persistia — múltiplos containers em crash loop
- 21:38:00 — Investigação revelou: agent paralelo (Cartorio CI) já tinha adicionado 5 provedores em `/etc/easypanel/projects/cartorio/openclaw-gateway/volumes/config/openclaw.json` corretamente
- 21:38:28 — `docker service update --force cartorio_openclaw-gateway`
- 21:38:30 — **Gateway UP!** `agent model: openai/minimax-m3 (thinking=adaptive)`
- 21:38:48 — Hot reload aplicado: `models.providers.opencode_free_1/2/3, mistral_free, openai` — todos os 5 provedores carregados

### Root Cause
1. **Race condition multi-agent**: cartorio-zcode e Cartorio CI agents trabalharam em paralelo nos mesmos arquivos de config do OpenClaw
2. **Config intermediário inválido**: durante o intervalo, o container tentou carregar um snapshot parcial que continha `gateway.mode` flag ausente em uma view cached
3. **Exit 78 do OpenClaw**: modelo primário não encontrado após schema validation falhar no providers block intermediário
4. **Não era problema no schema real**: o config final (`openclaw.json`) está correto com `gateway.mode: "local"` e todos os 5 provedores

### Impact
- **OpenClaw DOWN por ~3min** durante crash loop (containers exited imediatamente)
- **Nenhuma perda de dados** (config preservada no host, só container reiniciou)
- **WhatsApp gateway funcionando** (Evolution API independente, não afetado)
- **API funcionando** (FastAPI não depende do OpenClaw)

### Resolution
- `docker service update --force cartorio_openclaw-gateway` no host via Tailscale SSH
- Container subiu em ~30s com config hot-reloaded
- Logs confirmam: `agent model: openai/minimax-m3 (thinking=adaptive, fast=off)`
- Todos os 5 provedores ativos: `openai + opencode_go + opencode_free_1/2/3 + mistral_free`

### Lições Aprendidas
- **L184**: Multi-agent em paralelo pode causar crash loop se escreverem no mesmo config simultaneamente. Adicionar `flock` ou sequencing via mutex file
- **L185**: OpenClaw "models: Invalid input" error geralmente significa config intermediário foi escrito mas ainda não finalizado. Solução: `docker service update --force` recarrega com config final válido
- **L186**: Exit 78 no OpenClaw = modelo primário não está em `models.providers.*.models[].id`. Verificar que `provider + model` no agent.json existem no openclaw.json
- **L187**: Gateway hot-reload funciona — não precisa restart manual após mudanças no config se a estrutura JSON é válida

### Action Items (futuro)
- [ ] AI-1: cartorio-zcode — criar `/usr/local/bin/openclaw-safe-edit.sh` que usa `flock` para serializar edições concorrentes em `openclaw.json`
- [ ] AI-2: cartorio-zcode — adicionar health check pós-edit (`curl /health && sleep 5 && docker service ps cartorio_openclaw-gateway`)
- [ ] AI-3: Gustavo — escanear QR WhatsApp Business (já tinha instância `cartorio-2notas` ready, mas QR pendente)
- [ ] AI-4: cartorio-zcode — adicionar `WatchdogConfig` no Traefik para OpenClaw (auto-restart se cair novamente)
- [ ] AI-5: cartorio-zcode — documentar no OPERATIONS.md como adicionar novo provider (validar schema antes de salvar)

### Estado Pós-Fix (validado 2026-06-25 21:38 BRT)
```
✅ OpenClaw HEALTHY (1/1 replicas)
✅ Agent model: openai/minimax-m3 (1M context, thinking adaptive)
✅ Hot reload aplicado: 5 provedores carregados
✅ /health: {"ok":true,"status":"live"}
✅ Control UI disponível em https://agent.2notasudi.com.br/
✅ Multi-provider FREE chain ativo:
   - openai (primary, minimax-m3, 1M ctx)
   - opencode_go (secondary, deepseek-v4-flash, 1M ctx)
   - opencode_free_1 (free, nemotron-3-ultra-free, 1M ctx)
   - opencode_free_2 (free, nemotron-3-ultra-free, 1M ctx)
   - opencode_free_3 (free, nemotron-3-ultra-free, 1M ctx)
   - mistral_free (free, mistral-large-latest, 256K ctx)
```

---

**Mantido por**: ZCode/Mavis (orquestrador)
**Última atualização**: 2026-06-26 21:38 BRT
**Próxima revisão**: a cada novo incidente
**Status**: 🟢 INC-006 RESOLVED (E07 + E08 resolvidos ao mesmo tempo — 5 provedores free chain ativo)
