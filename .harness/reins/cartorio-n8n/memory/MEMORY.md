### DNS antes de auth (2026-06-23)
Type: cross-project pitfall

Quando usuario reporta "login nao funciona" em servico X, **SEMPRE verificar DNS antes** de assumir problema de auth.

Sinais tipicos de DNS issue (NAO auth): HTTP 000, connection refused, NXDOMAIN, curl 0 com tempo <100ms, `nslookup` retorna NXDOMAIN, IP reverso nao bate.

Diagnostico read-only (sem transmission):
1. `nslookup <host> 2>&1 | tail -10`
2. `dig <host> +short`
3. `curl -s -o /dev/null -w "%{http_code}\n" https://<host>/ --max-time 5`
4. Comparar com URL alternativa conhecida-funcional

**Hipotese mais simples primeiro**: usuario esqueceu senha > bug de config. Verificar `password LIKE '$2%'` (bcrypt prefix) + `bcrypt.checkpw` ANTES de assumir bug. 80% das vezes eh isso.

Caso real cartorio 2026-06-23 19:52 BRT: Gustavo reportou "lockout N8N". Diagnostico 2min: DNS NXDOMAIN em `n8n.2notasudi.com.br`, container UP via `flow.2notasudi.com.br`. Lockout NUNCA existiu — era URL errado.

### Credenciais em chat = queimadas (2026-06-23)
Type: cross-project rule (Lesson 17)

**DEFAULT**: ZERO plaintext/hashes em canal logado, mesmo em incident response.

NUNCA postar credenciais via `mavis communication` / scratchpad / commit message — logs permanentes, cred vaza.

**Caminho canonico**: gerar+aplicar via SSH + env var inject.

**Canais seguros (one-time view, expira)**:
- 1Password share link
- Bitwarden Send
- SSH local + `openssl rand` + cat temp file + rm imediatamente
- Telegram DM com auto-delete 1min

**Cred queimadas sao queimadas**: mesmo hash, mesmo prefixo, mesmo nome de variavel = rotacionar. Reusar prefixo vazado = vazamento composto.

### Regra de ouro N8N: arquivos locais != prod (2026-06-23)
Type: cartorio pitfall

OS ARQUIVOS em `infra/n8n-workflows/` sao STAGING/TEMPLATES (`id=null`). NAO sao o que esta em prod. Prod = export via `n8n export:workflow --all --id=X`.

**Antes de editar QUALQUER arquivo em `infra/n8n-workflows/`**: validar qual WF ID eh o de prod. Editar staging pensando que eh prod = mudanca nunca chega em prod.

Detalhe completo (incluindo IDs reais, exemplos de drift, regra de migration roadmap) → `memory/n8n-patterns.md`.

### Pai pode ter contexto git stale (2026-06-23)
Type: delegation rule

Pai me pediu commit em massa de 18 WFs assumindo master = `3b85746` e arquivos untracked. REALIDADE: master = `60a715f`, arquivos JA commitados em `3713d10`.

**3 checks antes de aceitar commit em massa do pai**:
1. `git status -uall <dir>` → working tree tem untracked?
2. `git ls-files <dir>` → arquivos tracked?
3. `git log master -5` → master HEAD real confere?

Se CLEAN + tracked → **REPORTAR BLOCK com evidencia**, NAO `git add` (no-op silencioso) nem re-commit vazio. Pai provavelmente teve contexto pre-snapshot (handoff file stale).

Em paralelo, validar JSON parse de cada arquivo antes de qualquer commit.

### N8N lockout incident - hipotese invalidadas (2026-06-23)
Type: forensic note

3 hipoteses gravadas durante debug live (19:43-22:46 BRT) sobre "N8N locked-out":

1. `settings.userActivated=false` — fix parcial, NAO root cause
2. `email=''` no user entity — INCORRETA (email existe)
3. Gustavo esqueceu senha — parcialmente certa, mas irrelevante

**Root cause real**: DNS NXDOMAIN em `n8n.2notasudi.com.br`. Container UP, URL errado. Ver regra "DNS antes de auth" acima.

Hipoteses 1-3 sao historico forense, NAO sao troubleshooting canonico. Fix: Gustavo ja logou (DNS resolvido). Senhas/DB_PASSWORD/Redis password TEM QUE ser rotacionadas (vazaram em plaintext 19:46 BRT no chat Telegram).