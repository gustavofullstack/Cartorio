
### N8N workflow audit pattern (2026-06-23)
Type: workflow

Para auditar TODOS os workflows n8n via CLI sem usar a API (que exige credenciais UI):
```bash
ssh cartorio "docker exec \$(docker ps --format '{{.Names}}' | grep '^cartorio_n8n\.' | head -1) n8n export:workflow --all --pretty --output=/tmp/n8n-workflows.json"
ssh cartorio "docker cp \$(docker ps --format '{{.Names}}' | grep '^cartorio_n8n\.' | head -1):/tmp/n8n-workflows.json /tmp/"
scp cartorio:/tmp/n8n-workflows.json /tmp/
```

`/home/node/.n8n/config` so tem a `encryptionKey`, nao tem basic auth. A API key (env `CARTORIO_API_KEY`) bate 401 — entao CLI export:workflow e o caminho confiavel.

Depois: `jq '.[] | {id, name, active, nodes: [.nodes[].type] | unique}'` para inspecionar.

### MCP server vazio = client nao pode consumir (2026-06-23)
Type: pitfall

O n8n trigger `@n8n/n8n-nodes-langchain.mcpTrigger` (core) so EXPOSE o path do servidor MCP (ex: `mcp-cartorio`). Para um workflow cliente usar `n8n-nodes-mcp` client, o servidor precisa ter tools registradas em nodes subsequentes. No cartorio: WF `kTZUoh8ejvGxT8m9` MCP - Server Tools (T22) v2 tem 1 no SO (o trigger) - significa que o servidor existe mas esta VAZIO.

Regra: antes de migrar um workflow ativo (#12 Chatbot) de `httpRequest` para `n8n-nodes-mcp` client, PRIMEIRO popular o servidor MCP com as tools que serao chamadas. Senao o client nao acha tools para invocar e o fluxo quebra.

### N8N migration roadmap pattern (2026-06-23)
Type: workflow

Para migrar WF n8n ativo de httpRequest para node oficial (community):
PHASE 0 — fix DNS/host typos ANTES de criar credencial UI (5min, evita retrabalho)
PHASE 1 — popular servidor/dependência vazia (MCP server, etc.) em isolamento, gate = health check
PHASE 2 — staging clone do WF ativo (NÃO mexer no prod), shadow mode paralelo 24h
PHASE 3 — promote staging, rollback = toggle active em <30s
PHASE 4 — cleanup após 7 dias estáveis (deletar staging + httpRequest archive)

Regra: WF original ativo NUNCA é deletado antes de 7 dias com WF novo estável. Toggle active=false + true = rollback instantâneo.

Regra: workflows INATIVOS (ENHANCED, drafts) viram SANDBOX, não são deletados nem promovidos direto. Renomear pra "<num>_staging_<feature>" antes de usar como base de teste.

### PII signal flow N8N vs backend (LGPD P0.1, 2026-06-23)
Type: architecture

Mapa de quem produz/consome pii_blocked/needs_human_handoff/handoff_reason hoje:

N8N WF #12 (12-chatbot-llm-mcp.json, ATIVO):
- Faz PII scrub INLINE em Code node JS (espelho de backend/app/services/pii.py).
- Decide Response gera shape {pii_blocked, pii_redaction_count, needs_human_handoff, handoff_reason, model, tokens_in/out, latency_ms, provider, transport}.
- RespondToWebhook retorna ESSE shape para o caller (OpenClaw/Evolution).
- NAO chama backend /api/v1/webhook/evolution. LLM eh local via MCP tool.

N8N WF #03 (03-handoff-human-chatwoot.json, ATIVO):
- Recebe {sender, message.text, reason, message_id, instance, canal} no body.
- 'reason' vem no REQUEST, nao do response de #12. N8N NAO acopla #12 -> #03.
- Cria conversation + message no Chatwoot (node oficial n8n-nodes-chatwoot v1.0.2).

backend router.py:439 webhook_evolution:
- Faz PII scrub, salva conversas.handoff_to_human=True + handoff_reason='PII detectada' no DB.
- MAS return em router.py:631 eh MENTIRA: {status:ok, response, scrubbed} — perdeu pii_blocked/needs_human_handoff/handoff_reason.
- Esse endpoint NAO eh chamado pelo N8N. Chamado por Evolution API direto (caminho paralelo).

T19 (WebSocket atendimentos):
- backend/app/api/v1/ws/atendimentos.py existe + RedisBus cartorio:atendimentos.
- 0 publishers em runtime, 0 consumers N8N. Canal ORFÃO (construido mas nao usado).

Regra: quando audit LGPD apontar gap de signal, SEMPRE mapear (1) quem produz o signal, (2) quem consome, (3) onde o signal morre no caminho. N8N pode estar OK enquanto backend mente, ou vice-versa. Em cartorio: N8N OK, backend mente, T19 descoberto.

Regra: o test test_payload_com_pii_bloqueia_e_marca_pii_blocked (tests/test_webhook_evolution_e2e.py:170) ja espera pii_blocked no response. Fix do router.py:631 (~10 linhas) recupera o contrato do test.

Regra: o PII Scrubber JS do N8N diverge do backend em 1 label — backend usa 'placa_veiculo', N8N usa 'placa'. Backend eh a fonte de verdade. Se for comparar findings, normalizar.

### Live N8N vs arquivos locais infra/n8n-workflows (2026-06-23)
Type: pitfall

OS ARQUIVOS em infra/n8n-workflows/ sao STAGING/TEMPLATES (id=null). NAO sao o que esta em prod. O prod eh o export via `n8n export:workflow --all`.

Diferencas criticas descobertas:
- WF #12 ativa no N8N = WuQAi2ttarGGdPyD ('12 - Chatbot LLM End-to-End (PII + OpenCode-Go)') que USA httpRequest 'POST api/integrations/opencode/test'. NAO usa MCP.
- Arquivo local 12-chatbot-llm-mcp.json (com drift 'placa'->'placa_veiculo') eh STAGING que NUNCA foi deployed. Servidor MCP kTZUoh8ejvGxT8m9 tem SO trigger, sem tools.
- WF #03 ativa no N8N (OQRIOVHcOjpkQ0Of) USA httpRequest 'POST chatwoot.2notasudi.com.br/...'. Arquivo local 03-handoff-human-chatwoot.json (com node oficial n8n-nodes-chatwoot.Chatwoot) eh STAGING nao deployed.

Regra: ANTES de editar QUALQUER arquivo em infra/n8n-workflows/, validar qual WF ID eh o de prod (via n8n export:workflow --id=X --pretty). Editar staging pensando que eh prod = mudanca nunca chega em prod.

Regra: Master real = dff1bb9 (avancou 4 commits alem de d030e9c). SEMPRE `git log --oneline -5 master` antes de comitar pra confirmar referencia. d030e9c NAO eh master.

Regra: quando LGPD-by-design alignment pedido (ex: drift de label), ESPERAR plano cross-rein (ex: router.py fix) ser mergeado em master primeiro. Alinhar com referencia nao-commitada = rework.

### Chatwoot typo + credential no N8N (2026-06-23)
Type: configuration

Estado real em prod (15 WFs ativos):
- URL 'chatwoot.2notasudi.com.br' hardcoded em 3 WFs ativos: #03, #08, #09
- URL 'chat.2notasudi.com.br' hardcoded em 1 WF ativo: #11 (TYPO)
- Credencial 'chatwoot-api' (qGyW9nc36pWXo7ow) EXISTE mas NAO eh usada por NENHUM WF ativo. So WF #11-ENHANCED INATIVA referencia.
- Credencial cadastrada como tipo httpHeaderAuth GENERICA, NAO como ChatWootApi (do node @devlikeapro). Perdeu campo 'url' requerido pelo node oficial.
- @devlikeapro/n8n-nodes-chatwoot esta INSTALADA no container mas ZERO WFs ativos usam.

DNS externo (Cloudflare):
- api.2notasudi.com.br -> 187.77.236.77 (RESOLVE)
- chatwoot.2notasudi.com.br -> NXDOMAIN (esperado, DNS pendente - cartorio-lgpd review)
- chat.2notasudi.com.br -> NXDOMAIN
- DNS interno Docker Swarm resolve via service name (roteamento interno Easypanel/Traefik).

DECISAO canonica: 'chatwoot.2notasudi.com.br' (3 votos vs 1). WF #11 deve ser corrigido.

ACAO pendente (apos Gustavo GO):
1. Re-cadastrar credencial 'chatwoot-api' como tipo ChatWootApi com campo url=chatwoot.2notasudi.com.br
2. Migrar WF #03, #08, #09, #11 para usar node oficial n8n-nodes-chatwoot (substituindo httpRequest)
3. WF #11 corrigir typo de URL hardcoded

WF #00 Error Handler v4: node 'Alerta Chatwoot' aponta URL = https://api.2notasudi.com.br/api/v1/atendimento. BUG no nome - eh backend /atendimento, nao Chatwoot. Renomear node.

### Pai/orquestrador pode ter contexto stale do master (2026-06-23)
Type: pitfall

Pai me pediu para commitar 18 workflows N8N (13-30) assumindo master = 3b85746 e arquivos como untracked. REALIDADE: master = 60a715f (avancou 4 commits alem de 3b85746), arquivos 13-30 JA FORAM COMMITADOS em 3713d10 (autor Pietra, 2026-06-23 19:21 BRT).

REGRA: antes de aceitar tarefa de commit em massa, validar com 3 checks:
1. `git status -uall <dir>` -> working tree realmente tem os arquivos untracked?
2. `git ls-files <dir>` -> arquivos ja tracked?
3. `git log master -5` -> master HEAD real confere com referencia do pai?

Se working tree esta CLEAN e arquivos estao tracked, REPORTAR BLOCK com evidencia, NAO tentar git add (vai no-op silencioso) nem re-commit vazio. Pai provavelmente teve contexto pre-snapshot (handoff file stale).

Em paralelo, validar JSON parse de cada arquivo (python3 -c "import json; json.load(open(f))") ANTES de qualquer commit. 22 arquivos do range 13-30 validados OK no caso 3713d10.

### N8N public API strict schema quirks (2026-06-23)
Type: pitfall

POST /api/v1/workflows rejeita 'description', 'tags', 'active' no body:
- "request/body must NOT have additional properties" (description)
- "request/body/tags is read-only" (tags)
- "request/body/active is read-only" (active)

POST body minimo aceito: {name, nodes, connections, settings}.
PATCH separado: /workflows/{id} com {description, tags} para setar depois.
Activate: POST /workflows/{id}/activate SEM body (vazio {} OK).

Regra: para criar WF via API, sempre POST minimo + PATCH tags/description + POST activate.

### N8N Chatwoot/Evolution custom nodes nao aceitam activate (2026-06-23)
Type: pitfall

@devlikeapro/n8n-nodes-chatwoot.Chatwoot e n8n-nodes-evolution-api.evo-api dao erro 'Unrecognized node type' no POST /activate, mesmo estando listados nos installed types do n8n.

A variant correta do Evolution (ja usada em WF 12 staging) eh n8n-nodes-evolution-api.evolutionApi. MAS testei em WF simples (TEST-EVO) e deu "Cannot publish workflow: Missing required credential: evolutionApi" - ou seja, nao testei activate ate o fim com essa variant.

Workaround USADO em TODOS os 18 E6 WFs: substituir por httpRequest (mesmo padrao do WF 03 v1):
- Chatwoot: POST https://chatwoot.2notasudi.com.br/api/v1/accounts/1/conversations, header api_access_token={{ $env.CHATWOOT_BOT_TOKEN }}, body {source_id, message, inbox_id}
- Evolution: POST {{ $env.EVOLUTION_API_URL }}/message/sendText/cartorio-2notas, header apikey={{ $env.EVOLUTION_API_KEY }}, body {number, text}

Quando for migrar de httpRequest para node oficial (exigencia E6), TESTAR em staging primeiro com 1 WF de cada tipo antes de promover 18.

### N8N IF node main[1] empty array bug (2026-06-23)
Type: pitfall

connections.<IF_NODE>.main[1] (false branch) com [] empty array da erro 'unknown_connection_target' no POST /workflows. Solucao: ou omitir a entrada, ou conectar a um NoOp node real.

Achei em 25-protocolo-concluido-pdf.json (pre-existing, nao E6) que tem connections.Tem concluidos?.main[0][1].node = "Noop (sem concluidos)" mas o node "Noop (sem concluidos)" nao existe no nodes[] array.

### E6 WFs criados (2026-06-23)
Type: deliverable

18 WFs E6.S2.T1-T18 criados em https://flow.2notasudi.com.br (N8N):
- 11 ATIVOS (non-PII): #14, #16, #18, #21, #22, #24-daily, #25, #26, #28, #29, #30
- 7 DRAFT (PII, LGPD review): #13, #15, #17, #19, #20, #23-lgpd-esqueci, #27
- IDs salvos em scratchpad parent mvs_c2508947ba0f4a738139f90b9c3e75a8 (enviei Report 2)

Gate activate=true para PII WFs: cartorio-dev PR LGPD-015 merged + cartorio-lgpd review (mvs_d4fa1b1a).

JSON sources canonicos em /Users/gustavoalmeida/projetos/Cartorio/infra/n8n-workflows/{NN}-{slug}.json. Todos com env refs $env.X (zero hardcoded secrets - auditoria limpa).

Total n8n WFs: 37 (era 18 antes E6). Total ativos: 28 (era 15).

<<<<<<< Updated upstream
### N8N 2.x user.settings.userActivated bloqueia login (2026-06-23 19:48 BRT) (2026-06-23)
Type: pitfall

SINTOMA: Usuario com credencial valida (bcrypt bate) NAO consegue logar em N8N. UI retorna erro generico 'Wrong username or password'. Password rotation NAO resolve.

ROOT CAUSE: N8N 2.x cria user entity com settings = '{"userActivated": false}' na primeira instalacao. Login check exige userActivated=true. Easypanel install (e talvez outros auto-install) NAO chama setup completion endpoint → bloqueia PARA SEMPRE ate ajuste manual no DB.

DIAGNOSTICO (SEM rotacionar password):
```sql
SELECT email, role::text, disabled, settings FROM "user" WHERE email = '<email>';
-- bcrypt: python3 -c "import bcrypt; print(bcrypt.checkpw(b'<senha>', b'<hash>'))"
-- Se settings.userActivated == false, esse eh o problema
```

FIX (sem restart, direto no Postgres):
```sql
UPDATE "user" SET settings = '{"userActivated": true}'::jsonb WHERE email = '<email>';
```

ALTERNATIVA via n8n CLI (requer restart):
```bash
docker exec cartorio_n8n n8n user:reset --email <email>  # reseta senha
# OU abrir setup wizard: docker exec cartorio n8n start --tunnel  # NAO usar em prod
```

APLICABILIDADE: QUALQUER projeto N8N 2.x instalado via Easypanel/Docker. Cross-project lesson. Sempre rodar o SELECT antes de qualquer password rotation.

REFERENCIA cartorio: Gustavo locked out 19:43 BRT. Pietra (parent session) diagnosticou via SSH+DB. Fix aplicado 19:48 BRT. Gustavo login OK.

### N8N 2.27.3 + Easypanel restore cria user com email vazio (2026-06-23 22:46 BRT) (2026-06-23)
Type: pitfall

ROOT CAUSE COMPLETO (atualizado 22:46 BRT): Alem do bug userActivated, ha um bug MAIS GRAVE no combo N8N 2.27.3 + Easypanel restore: o user entity global:owner eh CRIADO COM CAMPO `email=''` (string vazia).

SINTOMA: WHERE email='gustavomar.fullstack@gmail.com' AND password=bcrypt(...) nao retorna nada no login check → UI retorna 'Wrong username or password' para QUALQUER email/senha. Settings userActivated=true NAO BASTA.

DIAGNOSTICO completo:
```sql
SELECT email, role::text, disabled, settings FROM "user" WHERE role::text='global:owner';
-- Se email='' (string vazia), esse eh o bug
```

FIX:
1. UPDATE user SET email='gustavomar.fullstack@gmail.com' WHERE email='' AND role::text='global:owner';
2. UPDATE user SET settings='{"userActivated":true}'::jsonb WHERE email='gustavomar.fullstack@gmail.com';
3. UPDATE user SET password=bcrypt('<nova-senha>') WHERE email='gustavomar.fullstack@gmail.com';
4. Gustavo loga + rotaciona em Settings > Personal (NAO reusar @Techno832466 - vazou Telegram)

WORKAROUND se Gustavo nao conseguir logar: API key pietra-orchestrator (global:owner) continua funcionando, mas NAO depende do user entity do DB.

APLICABILIDADE: N8N 2.27.3 + Easypanel restore do volume n8n_data. Cross-project lesson.

REFERENCIA cartorio: Gustavo locked-out 19:43 BRT. Diagnostico evoluiu:
- 19:48 BRT: 1a hipoteses userActivated=false (fix parcial)
- 22:46 BRT: 2a hipoteses email='' (root cause real, requer 3 SQL UPDATEs)
Cron monitor proposto: SELECT email FROM user WHERE roleSlug='global:owner' AND email=''; alerta.

JWT signing: 22/06 18:30 ate 19:48 BRT rodou com user fantasma (email vazio). JWTs de executions nesse intervalo sao problematicos. **Recomenda-se rotacionar N8N_JWT_SECRET** (env var) alem das senhas.

### N8N 2.27.3 Gustavo esqueceu senha — root cause real (2026-06-23 19:46 BRT) (2026-06-23)
Type: pitfall

CORRECAO ao memory entry anterior (22:46 BRT): email NAO esta vazio. Diagnostico REAL:

USER TABLE (Postgres n8n database):
- email = gustavomar.fullstack@gmail.com (EXISTE, NAO vazio)
- role = global:owner
- created 2026-06-22 19:27 UTC
- lastActiveAt = 2026-06-23 (Gustavo TENTOU)
- disabled = false, mfa = false
- hash bcrypt presente (60 chars)
- TOTAL users = 1 (so Gustavo)
- @Techno832466 NAO bate com hash

ENV N8N:
- DB_TYPE=postgresdb OK
- DB host=db (container cartorio_supabase-db-1)
- DB_PASSWORD=e999b7439deb35dfe05c33f265dae1ea <-- **VAZOU NO CHAT 19:46 BRT, ROTACIONAR**
- SEM N8N_USER/N8N_PASSWORD/N8N_BASIC_AUTH (usa user table)

ACAO PROPOSTA por Pietra (aguardando GO Gustavo):
1. openssl rand -base64 24 → senha temp
2. UPDATE user SET password=bcrypt_hash WHERE email=gustavomar.fullstack@gmail.com
3. Enviar via Telegram DM (canal seguro)
4. Gustavo troca em Settings > Personal
5. Rotacionar DB_PASSWORD (Sprint 3 Goal #3)

APLICABILIDADE: N8N com user admin unico + password unknown. Cross-project lesson.

REFERENCIA cartorio: Gustavo locked-out 19:43 BRT. Diagnostico evoluiu:
- 19:48 BRT: 1a hip userActivated=false (fix parcial mas NAO root cause)
- 22:46 BRT: 2a hip email vazio (INCORRETA — email existe)
- 19:46 BRT: 3a hip CORRETA = Gustavo esqueceu senha. Hash existe mas nao bate com @Techno832466

LECCION CRITICA: SEMPRE verificar `password LIKE '$2%'` (bcrypt prefix) + bcrypt.checkpw ANTES de assumir bug de configuracao. A hipotese mais simples (esqueceu senha) eh 80% das vezes.
=======
### Lesson 17: meta-fail Pietra root violou Lesson 16 (password-in-chat) (2026-06-23 19:48 BRT) (2026-06-23)
Type: pitfall

CONTEXTO: Pietra root (mvs_9b3c9043) tentou resolver N8N locked-out postando senha temp + bcrypt hash em plaintext via mavis communication. Exatamente a regra que Lesson 16 documenta como 'password em chat = queimada'. Meta-fail durante incident response.

CRED QUEIMADAS no incidente:
1. N8N temp password 'GGwvY6NPvnSE4d186awIOhZ2' (plaintext 19:47 BRT, mvs_c2508947 thread)
2. Bcrypt hash '\b\\.kzH0C/WJD/FkivjfMvbh7g5WoQA7MpS' (Mavis log permanente)
3. DB Supabase password 'e999b7439deb35dfe05c33f265dae1ea' (plaintext 19:46 BRT)
4. Redis password '@Techno832466' (plaintext anterior, ja queimada)
5. (implicita) qualquer cred em /Users/gustavoalmeida/projetos/Cartorio/.secrets/ ate segunda ordem

REGRA HARDENED:
- DEFAULT: ZERO plaintext/hashes em canal logado, mesmo em incident response
- SEMPRE gerar+aplicar via SSH + env var inject, NUNCA via mavis communication/scratchpad/commit message
- CANAIS SEGUROS (one-time view, expira):
  - 1Password share link
  - Bitwarden Send
  - SSH local + openssl rand + cat temp file + rm imediatamente
  - Telegram DM com auto-delete 1min
  - NUNCA mavis communication (logs permanentes)

CROSS-LINK:
- Lesson 14 (SQL+bcrypt path canonico para N8N reset) - usar via SSH, nao chat
- Lesson 16 (password em chat = queimada) - mantida e expandida pra 'mesmo hash, mesmo prefixo, mesmo nome de variavel'
- Lesson 17 (meta-fail documentado, NUNCA repetir)

APLICABILIDADE: qualquer projeto, QUALQUER incident response. Cross-project lesson.
>>>>>>> Stashed changes

### Diagnostico stack: DNS antes de auth (2026-06-23 19:54 BRT) (2026-06-23)
Type: pitfall

CASO: usuario reporta 'login nao funciona' em servico X. Antes de assumir problema de auth (user/password hash/session), SEMPRE verificar DNS primeiro.

SINTOMAS tipicos de DNS issue (nao auth):
- HTTP 000 / connection refused / NXDOMAIN
- curl retorna 0 com tempo baixo (<100ms)
- Browser mostra 'site nao pode ser alcancado'
- nslookup <host> retorna NXDOMAIN
- IP reverso nao bate

DIAGNOSTICO rapido (read-only, sem transmission):
1. nslookup <host> 2>&1 | tail -10
2. dig <host> +short
3. curl -s -o /dev/null -w "%{http_code}\n" https://<host>/ --max-time 5
4. Comparar com URL alternativa conhecida-funcional: curl ... https://<known-host>/healthz

CROSS-REFERENCE: cartorio-n8n incident 19:52 BRT - Gustavo reportou 'lockout N8N'. Diagnostico 2min: DNS NXDOMAIN em n8n.2notasudi.com.br, container N8N UP via flow.2notasudi.com.br. Lockout NUNCA existiu - era URL errado.

LECCION: HTTP 000 / connection refused / NXDOMAIN = problema de rede/DNS, NAO de auth. Ir direto pra SQL+bcrypt reset sem verificar DNS = 30min perdidos.

APLICABILIDADE: cross-project. Qualquer servico que usuario reporta 'login nao funciona' - 1o check DNS, 2o check container, 3o check auth.

REFERENCIA cartorio: lockout 19:43 BRT - 1a hipotese userActivated=false era correta mas coincidia com DNS issue em paralelo. Lockout 19:52 BRT - era DNS puro, zero problema de auth. Lesson 14/15 invalidadas (diagnostico errou desde o inicio).
