# 🔐 Secrets Management — C10

> **SQUAD C** | **Owner**: cartorio-zcode + cartorio-dev
> **Data**: 2026-06-26
> **Status**: ✅ DONE

Política e procedimentos de gestão de credenciais, secrets e API keys do projeto Cartório 2º Notas Uberlândia.

> ⚠️ **REGRA ABSOLUTA**: NUNCA rotacionar chaves (regra #1 do Super Prompt v4.0.0).
> Apenas Gustavo e o agent têm acesso. Não há risco algum.

---

## 📋 Inventário de Credenciais

### Por plataforma (estado REAL 2026-06-26)

| Plataforma | Tipo | Local de armazenamento | Variáveis |
|------------|------|------------------------|------------|
| **Minimax.io Coding Plan** | API Key | `.env` + MacBook Pro global | `MINIMAX_API_KEY` |
| **Telegram Bot** | Bot Token | `.env` + MacBook Pro | `TELEGRAM_BOT_TOKEN` |
| **Jules Agent** | API Key | `.env` + MacBook Pro | `JULES_API_KEY` + `JULES_URL` |
| **Render** | API Key | `.env` + MacBook Pro | `RENDER_API_KEY` + `RENDER_API_URL` |
| **Linear** | API Key | `.env` + MacBook Pro | `LINEAR_API_KEY` + `LINEAR_API_URL` |
| **OpenCode-Go (OpenClaw)** | API Key | `agent.json` na VPS + `.env` | `OPENCODE_GO_API_KEY` |
| **OpenClaw Gateway** | API Key | `.env` (container openclaw) | `OPENCLAW_API_KEY` |
| **MCP Server** | API Key | `.env` (api) | `MCP_API_KEY` |
| **JWT v2 (HS256)** | Secret | `.env` (api) | `JWT_SECRET` |
| **Postgres Cartório** | Password | `.env` + Vault Supabase | `DATABASE_URL` |
| **Redis** | Password | `.env` + MacBook Pro | `REDIS_PASSWORD` (`@Techno832466`) |
| **Auditoria HMAC** | Chave | `.env` (api) | `AUDIT_HMAC_KEY` |

### Por serviço (VPS)

```bash
/etc/easypanel/projects/cartorio/
├── api/code/.env              → MINIMAX, DATABASE_URL, REDIS, JWT_SECRET, AUDIT, MCP, EASYPANEL
├── n8n/.env                    → DB connection, encryption key, N8N_API_KEY
├── evolution-api/.env          → AUTHENTICATION_API_KEY (429683C4...), DB
├── chatwoot/.env               → SECRET_KEY_BASE, DB
├── supabase/.env               → POSTGRES_PASSWORD, JWT_SECRET, ANON_KEY, SERVICE_ROLE_KEY
├── openclaw-gateway/.env       → OPENCLAW_API_KEY (fz1qzo2xk...), modelo config
├── redis/.env                  → REDIS_PASSWORD (@Techno832466)
```

### Detalhes técnicos importantes (junho/2026)

- **Modelo OpenCode-Go**: `minimax-m3` (1M context, $0 cost) — **substituiu** `deepseek-v4-flash` em 2026-06-24
- **OpenClaw context**: 1.048.576 tokens (1M) — **fix já aplicado** por Gustavo 2026-06-24 14:58 BRT
- **Thinking mode**: `adaptive` (não `enabled` simples)
- **LiteLLM**: **REMOVIDO** 2026-06 (hackeado) — placeholder mantido para referência
- **JWT_SECRET**: 64-char hex (HS256) para API v2 — **NÃO rotacionado**
- **TELEMETRY_OPENCODE_DAILY_LIMIT_USD=5.0**: limite diário OpenCode-Go
- **EASYPANEL_API_KEY**: para gerenciar containers
- **SUPABASE_ANON_KEY + SERVICE_ROLE_KEY**: defaults da imagem Docker (ATENÇÃO: SUI substituir antes white-label)

---

## 🔒 Princípios

### 1. NUNCA rotacionar chaves
- Regra absoluta do Super Prompt v4.0.0
- Apenas Gustavo pode autorizar rotação
- Se chave vazar, mover para outra chave (sem rotação forçada)
- Salvar chave nova globalmente no MacBook Pro

### 2. NUNCA commitar .env
- `.env` está no `.gitignore` (verificar periodicamente)
- Apenas `.env.example` é commitado (template)
- Usar `git diff --staged` antes de qualquer commit

### 3. Cada serviço tem seu próprio .env
- **Separação total** entre API, N8N, Evolution, Chatwoot, Supabase, OpenClaw
- Sem compartilhamento de secrets entre serviços
- Facilita rotação granular se necessário

### 4. Vault Supabase para credenciais críticas
- 8 vault entries ativas
- Usar para credentials que múltiplos serviços acessam
- Maior segurança que .env files

---

## 🔄 Procedimento de Atualização de Credencial

### Quando necessário
1. Chave atual comprometida (log de acesso não-autorizado)
2. Gustavo autoriza nova chave
3. Prazo de expiração de chave externa
4. Mudança de provedor / modelo

### Fluxo de execução (SEM rotacionar automaticamente)

```bash
# 1. Gustavo gera nova chave (ou recebe do provider)

# 2. Atualizar .env NA VPS (via SSH Tailscale)
ssh root@100.99.172.84
# Exemplo: atualizar N8N encryption key
docker service exec cartorio_n8n env | grep ENCRYPTION
# Editar /etc/easypanel/projects/cartorio/n8n/.env
nano /etc/easypanel/projects/cartorio/n8n/.env

# 3. Restart do servico
docker service update --force cartorio_n8n

# 4. Validar
curl https://flow.2notasudi.com.br/healthz

# 5. Atualizar MacBook Pro
vim ~/.mavis/secrets/cartorio-global.env

# 6. Atualizar Vault Supabase (se aplicavel)
# via Supabase Studio > SQL Editor

# 7. Commit no repo (apenas .env.example)
git add .env.example
git commit -m "docs(secret): update example env for N8N encryption"
```

### Locais a atualizar (checklist)

- [ ] VPS — `/etc/easypanel/projects/cartorio/<service>/.env`
- [ ] MacBook Pro — `~/.mavis/secrets/cartorio-global.env`
- [ ] Vault Supabase (se aplicável)
- [ ] `.env.example` (template atualizado)
- [ ] `docs/SECRETS_MANAGEMENT.md` (este doc — atualizar se novos serviços)
- [ ] `.harness/memory/MEMORY.md` (adicionar L<num> sobre o incidente)

---

## 🛡️ Proteção por Camada

### Camada 1: Filesystem
- Permissões: `chmod 600 .env` (rw apenas para owner)
- Owner: `root:root` (serviços rodam como non-root)
- Backup criptografado: `gpg --encrypt`

### Camada 2: Vault Supabase
- Para credenciais compartilhadas entre API + N8N
- 8 entries ativas (post B06 vault migration)
- Acesso via MCP/SQL: `select * from vault.secrets`

### Camada 3: Network
- Tailscale VPN para SSH (acesso restrito a nodes autorizados)
- Firewall Easypanel: portas 6379, 1001, 8000 apenas internas
- HTTPS Traefik + Cloudflare (TLS 1.3)

### Camada 4: Aplicação
- API: requer X-API-Key para /admin/* (64 char hex validated)
- N8N: HMAC signature para webhooks
- Evolution: API key no header
- OpenClaw: API key per agent

### Camada 5: Auditoria
- Audit log: `audit_log` (LGPD art. 37 — 5 anos)
- Todo acesso a secrets logado
- request_id correlation (B09: X-Correlation-ID)

---

## 🔄 Auditoria de Secrets

### Mensal
```bash
# Verificar permissoes de .env em todos os servicos
for svc in api n8n evolution-api chatwoot openclaw-gateway; do
  echo "=== $svc ==="
  ssh root@100.99.172.84 "ls -la /etc/easypanel/projects/cartorio/$svc/.env 2>/dev/null || echo 'MISSING'"
done
```

### Trimestral
```bash
# Verificar que .env NAO foi commitado
git log --all --full-history -- '*.env'
# Esperado: vazio

# Verificar .env.example atualizado
diff <(ssh root@100.99.172.84 "cat /etc/easypanel/projects/cartorio/api/code/.env" | grep -v "^#" | cut -d= -f1 | sort) \
     <(grep -v "^#" .env.example | cut -d= -f1 | sort)
# Esperado: mesmas chaves
```

### Anualmente
- Renovar API keys (apenas se expirado)
- Auditar quem tem acesso (Gustavo + agent)
- Revisar permissões Vault

---

## 📚 Procedimentos Específicos

### Como adicionar uma nova credencial
1. Adicionar ao `.env.example` (template público)
2. Adicionar ao `.env` real na VPS + MacBook
3. Se compartilhada: adicionar ao Vault Supabase
4. Documentar no `MEMORY.md` (lesson L<num>)
5. Atualizar este `SECRETS_MANAGEMENT.md`

### Como remover uma credencial
1. Identificar todos os usos (grep no repo)
2. Remover de `.env` + Vault + código
3. Substituir por novo fluxo (se aplicável)
4. Documentar no `MEMORY.md`

### Como debugar erro de credencial
1. Verificar `.env` (cat / grep)
2. Verificar Vault (`select * from vault.secrets`)
3. Verificar logs do serviço
4. Testar endpoint de health (curl /health)
5. Se persistir: regenerar credencial (com Gustavo)

---

## 🚨 Incidentes e Lições

### INC-001: SSH key incorreta (2026-06-23)
- **Problema**: Gustavo conectou com key errada
- **Resolução**: confirmou alias Tailscale correto
- **Lição**: sempre usar `ssh vps-cartorio` (alias do ~/.ssh/config)
- **Doc**: `docs/INCIDENTE_SSH_2026-06-23.md`

### INC-002: Supabase Auth falhando (2026-06-23)
- **Problema**: cliente Supabase sem password
- **Resolução**: regenerou password + atualizou .env
- **Lição**: validar credenciais após geração
- **Doc**: `docs/INCIDENT_2026-06-23_SUPABASE_AUTH.md`

---

## 🔗 Links Úteis

- **Vault Supabase**: https://supbase.2notasudi.com.br/project/default/database/vault
- **MacBook Pro secrets**: `~/.mavis/secrets/cartorio-global.env`
- **MEMORY.md**: `.harness/memory/MEMORY.md` (L155, L178, L179)
- **Super Prompt v4.0.0**: PROMPT.MD (Bloco 2.1 — Rotação de Chaves)

---

**Mantido por**: ZCode/Mavis (orquestrador)
**Última atualização**: 2026-06-26
**Próxima revisão**: 2026-09-26 (trimestral)
**Status**: ✅ C10 SQUAD C DONE
