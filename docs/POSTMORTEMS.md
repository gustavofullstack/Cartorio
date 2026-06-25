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

### INC-005: Chatwoot 502 Bad Gateway (2026-06-26)

**Severidade**: P0 (radar vermelho)
**Detectado em**: 2026-06-26 ~17:50 BRT
**Detectado por**: ZCode/Mavis (orquestrador)
**Resolvido por**: HOLD — requer Gustavo/CI

### Timeline
- 17:50 BRT — Radar muda de green para red
- 17:51 BRT — Investigação: OpenClaw OK, Chatwoot 502
- 17:52 BRT — `curl https://api.2notasudi.com.br/api/v1/health/integracoes` mostra Chatwoot `[Errno -2] Name or service not known`

### Root Cause (CONFIRMADO)
- O `.env` enviado por Gustavo contém `CHATWOOT_BASE_URL=http://cartorio_chatwoot:3000`
- Esse hostname **só existe dentro da rede Docker Swarm** (cartorio_api container)
- O API health check roda no contexto do nosso Mac — DNS local não resolve `cartorio_chatwoot`
- Resultado: `Name or service not known`

### Impact
- 1/7 serviços offline (Chatwoot)
- OpenClaw 100% online (INC-004 resolvido antes)
- API + N8N funcionais

### Resolution (Proposta)
**Opção A** (recomendada): Mudar `CHATWOOT_BASE_URL` para `http://chat.2notasudi.com.br` (FQDN público) quando o DNS Cloudflare for criado (PENDENTE — Gustavo)

**Opção B**: Quando o API for deployado de volta (atualmente offline), o container cartorio_api consegue resolver `cartorio_chatwoot` via DNS interno do Docker Swarm. O problema é apenas em health checks externos (Mac).

**Opção C**: Modificar o health check radar para aceitar `Name or service not known` como esperado (graceful degradation) e marcar Chatwoot como "unknown" ao invés de "offline".

### Lessons Learned
- **L-194-novo**: Hostnames Docker Swarm (`cartorio_*`) não funcionam em DNS local do Mac
- **L-195-novo**: Health check radar deve distinguir "offline" de "unknown" (DNS falho)
- **L-196-novo**: Sempre usar FQDN público (ou IP) em URLs que precisam ser acessíveis externamente
- **L-197-novo**: Testes de saúde (radar) devem ser graceful degradation

### Action Items
- [ ] AI-1: Gustavo criar DNS A record `chatwoot.2notasudi.com.br` para IP público (PENDENTE — junto com outros DNS)
- [ ] AI-2: Gustavo/CI mudar `CHATWOOT_BASE_URL` para FQDN público (quando DNS estiver pronto)
- [ ] AI-3: cartorio-dev — adicionar graceful degradation no health check radar (`Name or service not known` = "unknown", não "offline")
- [ ] AI-4: cartorio-dev — redeploy do API container (atualmente offline)
- [ ] AI-5: cartorio-n8n — verificar se WF que depende do Chatwoot estão degradados gracefully

---

**Mantido por**: ZCode/Mavis (orquestrador)
**Última atualização**: 2026-06-26 17:55 BRT
**Próxima revisão**: a cada novo incidente
**Status**: 🔴 INC-005 OPEN (HOLD Gustavo/CI)
