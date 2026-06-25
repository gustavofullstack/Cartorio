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

## 📊 Estatísticas

- **Total de incidentes registrados**: 3 (até 2026-06-26)
- **P0 críticos**: 1 (INC-002 Supabase Auth)
- **P1 altos**: 1 (INC-003 agendamento.py)
- **P3 baixos**: 1 (INC-001 SSH key)
- **MTTR médio**: ~17min
- **Root causes mais comuns**: misconfiguração (66%), syntax error (33%)

---

## 🎯 Top 5 Lessons Aprendidas (consolidadas)

1. **Sempre usar `ssh vps-cartorio`** (alias) — não IP direto
2. **Validar credenciais após regeneração** (especialmente DB passwords)
3. **Sintaxe Python verificar antes de commit** (usar `ast.parse` em CI gate)
4. **Backup antes de regeneração** (rollback rápido se algo quebrar)
5. **Documentar TODOS os incidentes** mesmo pequenos (P3) — aprendizados valem muito

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

**Mantido por**: ZCode/Mavis (orquestrador)
**Última atualização**: 2026-06-26
**Próxima revisão**: a cada novo incidente
**Status**: ✅ C10 SQUAD C DONE
