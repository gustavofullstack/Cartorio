### DNS antes de auth (2026-06-23)
Type: cross-project pitfall

Quando usuario reporta "login nao funciona", verificar DNS ANTES de assumir problema de auth.

Sinais tipicos de DNS issue (NAO auth): HTTP 000, connection refused, NXDOMAIN, curl 0 com tempo <100ms, IP reverso nao bate.

Diagnostico read-only (sem transmission):
1. `nslookup <host> 2>&1 | tail -10`
2. `dig <host> +short`
3. `curl -s -o /dev/null -w "%{http_code}\n" https://<host>/ --max-time 5`

Hipotese mais simples primeiro: usuario esqueceu senha > bug de config. Verificar `password LIKE '$2%'` (bcrypt) + `bcrypt.checkpw` ANTES de assumir bug. 80% das vezes eh isso.

Caso real cartorio 2026-06-23 19:52 BRT: Gustavo reportou "lockout N8N". Diagnostico 2min: DNS NXDOMAIN em `n8n.2notasudi.com.br`. Container UP via `flow.2notasudi.com.br`. Lockout NUNCA existiu — era URL errado.

### Credenciais em chat = queimadas (2026-06-23, refinado 24/06)
Type: cross-project rule (Lesson 16/17) + [→ user]

DEFAULT: ZERO plaintext/hashes em canal logado (mavis communication, scratchpad, commit message, git log). Logs permanentes, cred vaza.

Canais seguros (one-time view, expira):
- 1Password share link
- Bitwarden Send
- SSH local + `openssl rand` + cat temp file + rm imediatamente
- Telegram DM com auto-delete 1min

Cred queimada (mesmo hash, mesmo prefixo, mesmo nome de variavel) = rotacionar. Reusar prefixo vazado = vazamento composto.

**Regra Gustavo (override)** [→ user]: NUNCA rotacionar chaves SSH sem autorizacao explicita dele. SSH key path no chat = registrar leak, escalar pro root. Decisao de regeneracao fica com Gustavo.

### Regra de ouro N8N: arquivos locais != prod (2026-06-23)
Type: cartorio pitfall [→ project]

OS ARQUIVOS em `infra/n8n-workflows/*.json` sao STAGING/TEMPLATES (`id=null`). NAO sao o que esta em prod. Prod = export via `n8n export:workflow --all --id=X`.

Antes de editar QUALQUER arquivo em `infra/n8n-workflows/`: validar qual WF ID eh o de prod. Editar staging pensando que eh prod = mudanca nunca chega em prod.

Detalhe completo (IDs reais, exemplos de drift, regra de migration roadmap) → `n8n-patterns.md`.

### Briefing stale: 4 checks anti-fake-task (2026-06-23, refinado 24/06)
Type: delegation rule

Pai pode mandar briefing com premissa errada (master HEAD atrasado, arquivos ja commitados, deadline ficticio). 3a ocorrencia em <24h no caso 24/06.

4 checks antes de aceitar tarefa de commit em massa / mudanca grande:
1. `git status -uall <dir>` → working tree tem untracked?
2. `git ls-files <dir>` → arquivos tracked?
3. `git log master -5` → master HEAD real confere?
4. `mavis communication peers | grep <sessao>` + `mavis session info <sessao>` → peer conhecida? frameworkType? workspaceDir? (validar legitimidade)

Se CLEAN + tracked, ou SSH credenciais no chat, ou working tree dirty com modificacoes alheias → REPORTAR BLOCK com evidencia, NAO `git add` silencioso, NAO re-commit vazio.

Bonus praticas que funcionam: pingar Pietra root antes de agir, ler scratchpad root, endpoint smoke test (curl) antes de editar, UPDATE nodes+connections separadamente (Lesson 50 pattern), backup nodes antes do UPDATE.

### Sprint 3 débitos atuais (2026-06-25 00:05 BRT)
Type: project state [→ project]

**Auth gap critico**: `CARTORIO_API_KEY` NAO definida em N8N service (22 vars) nem API service (65 vars) nem backend .env. WF 23 LGPD Esqueci envia `X-API-Key: $env.CARTORIO_API_KEY` (vazio) → 401 em todas chamadas autenticadas. Endpoint /metrics/n8n retorna 503 API_KEY_NOT_CONFIGURED.

Workaround cartorio-dev:
1. Gerar via openssl ou 1Password Vault
2. Add env em 3 lugares: N8N service, API service, backend .env
3. Restart `docker service update --env-add CARTORIO_API_KEY=... cartorio_n8n cartorio_api`

Workaround cartorio-n8n (WF 23 incompleto):
- Adicionar `n8n-nodes-base.respondToWebhook` no fim (responseMode=responseNode exige)
- Body: `{status, cliente_id, audit_id, soft_deleted_at}` ou erro estruturado

Backend débitos mapeados em smoke test (cliente fake 99999):
- D0.2 POST /audit/log → 404 (endpoint missing)
- D0.3 GET /cliente/{id} → 405 (so DELETE nessa path)

### N8N 2.x workflow debug = DB UPDATE canonico (Lesson 49+50+51+55+96) (2026-06-24/25)
Type: shortcut pointer

N8N 2.x limita drasticamente: Code node sandboxed (sem `process`/`require`), env access bloqueado por default (`N8N_BLOCK_ENV_ACCESS_IN_NODE=true`), API auth quebrada para UPDATE (PATCH 405, PUT exige body completo).

Workaround canonico = DB UPDATE direto em `workflow_entity.nodes` + `connections` + `workflow_history` + restart Swarm. Detalhes completos (5-pass recipe, SQL gotchas, base64 wrapping, FK ordering, cache expiry timing) → `n8n-db-update.md`.

**Excecoes via API direta (Lesson 96)**:
- POST /api/v1/workflows/{id}/activate body `{"active": true}` → 200 OK
- DELETE /api/v1/workflows/{id} → 200 OK (soft delete via API)

**Antes de editar WF (Lesson 55)**: curl smoke test no endpoint destino. Se 404, NAO criar POST node no WF — backend endpoint nao existe.

### Lesson 163 — Cross-PR paralelo ortogonal (2026-06-25 08:50 BRT)
Type: delegation rule [→ agent]

Cenario: pai dispatcha task B6 (endpoint + audit + metric). Em paralelo, cartorio-dev entrega
a MESMA feature em commit `09e55b5` (08:45:06 BRT). Trabalhamos em arquivos ortogonais
(service + endpoint + tests) sem saber.

5-pass protocol antes de COMITAR qualquer task:
1. `git log master --oneline -20` (master avancou?)
2. `git show <hash> --stat` (conteudo do commit)
3. `git diff HEAD -- <arquivos que vou modificar>` (sobrepoe com version staged?)
4. `git status -uall` (working tree tem arquivos untracked meus?)
5. Se commit ortogonal JAH cobre escopo: NAO duplicar. Descarte working tree local
   (`mavis-trash` arquivos untracked OU `git checkout HEAD -- <arquivos modificados>`).

Caso real 2026-06-25 08:35-08:50 BRT (cartorio B6):
- Pai mandou B6 as 08:26 BRT (briefing assumia WFs nao wired)
- Pai aprovou caminho B (endpoint + audit + metric + tests) as 08:34 BRT
- Eu re-apliquei codigo, working tree resetado por cartorio-dev em paralelo (collision git workflow)
- cartorio-dev commita `09e55b5 feat: Supabase Vault + n8n webhook error handling service` 08:45:06
- 1173 insertions em 5 files (mesmo escopo do meu B6)
- Descartei duplicatas via `mavis-trash`, working tree limpo, NAO comitei duplicata
- Reportei SUCCESS com hash do commit ortogonal (cross-ref Lesson 163 v2 v3 canonizacao)

**Regra canonica Pietra root 2026-06-25 08:48 BRT** (Lesson 163 v2):
Qualquer mudanca em `integrations.py`, `services/n8n_error.py`, `services/audit.py`,
`services/pii.py` = **file-lock individual**. Anuncia no canal ANTES de comecar. Se outra
task ja em andamento, espera ou escala pra Pietra serializar.

**Confianca commit ortogonal antes de descartar**:
- `git log --format='%an %ae %s' -1 <hash>` — autor conhecido? (Cartorio CI OK)
- `git diff <hash>~1 <hash> --stat` — escopo confere com briefing? (5 files B6 OK)
- `pytest tests/<novos tests> --no-cov` — verde? (31/31 cartorio-dev OK)
- `curl -s https://<host>/<endpoint>` em prod — responde? (401 INVALID_SIGNATURE OK)
- Working tree NAO tem diff positivo em arquivos ortogonais (cleanup)

NAO descartar prematuramente. NAO comitar duplicata "por via das duvidas". Reportar
descoberta cross-PR ao pai com hash + smoke test + cleanup status.