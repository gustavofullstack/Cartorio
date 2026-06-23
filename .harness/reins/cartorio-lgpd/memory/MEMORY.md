
### LGPD review patterns — 5 decisões duráveis de PR review (2026-06-23)
Type: pattern

Contexto: review do commit e487081 (cartorio-dev Sprint 1 backend) — 3 perguntas LGPD respondidas. Decisões que se aplicam a QUALQUER projeto B2B SaaS/LGPD que eu (cartorio-lgpd) revisar.

**1. LGPDBlockedResponse / erro de consentimento — copy defensável**
Sempre incluir no body do erro:
  - citação do art. + inciso + parágrafo (não só a lei) — ex: "LGPD art. 7o, I e art. 8o, par. 5o"
  - contato DPO (art. 41)
  - link da política de privacidade (art. 9 + art. 50)
  - como remediar (consentimento=true ou contato DPO)
  - direito à revogação (art. 8 par 5)
Status HTTP: 422 (Unprocessable Entity) é defensável — request foi compreendido, falha de precondição regulatória.

**2. Retenção de hash/dado pessoal — separar por base legal**
NÃO tratar "tudo" como 5 anos ou "tudo" como até-revogação. Separar:
  - Base legal art. 7 II (obrigação legal/regulatória): retenção MÍNIMA obrigatória = regra do setor (cartório = 5 anos Provimento CNJ 74; outros setores = verificar norma específica)
  - Base legal art. 7 I (consentimento): retenção ATÉ REVOGAÇÃO ou até cessar finalidade
  - Para cartório especificamente: cliente COM protocolo = 5y (anonimizar após), cliente SEM protocolo = até revogação (deletar)
Job retenção deve distinguir esses 2 caminhos.

**3. IP é dado pessoal (LGPD art. 5 I) — capturar via middleware + truncar**
IP puro identifica pessoa. Padrão:
  - Middleware FastAPI que captura request.client.host (fallback X-Forwarded-For se atrás de proxy reverso)
  - Persistência completa com retenção curta (2 anos) — IP perde relevância operacional depois
  - Exibição no painel admin: truncar /24 (IPv4) ou /48 (IPv6) — privacy-by-design
  - Audit log: incluir request_ip em toda entrada (não só o actor_id)
  - Consentimento IP: registrar em coluna `consentimento_ip` (separado do IP de log) — base legal art. 37 + art. 8 par 2 (registro verificável)

**4. Soft delete LGPD-aware — coluna motivo_encerramento ENUM**
Não basta ter `deleted_at`. Distinguir:
  - revogacao_consentimento (cliente pediu pra sair — LGPD art. 18 IX)
  - retencao_5y (job automático após prazo legal)
  - exercicio_direito_titular (LGPD art. 18 IV — anonimização/bloqueio)
  - outros (auditoria manual)
Cada caminho tem obrigação regulatória diferente. Sem distinção, vira caixa-preta em auditoria.

**5. Status 422 vs 403 vs 400 — semântica regulatória**
  - 400: request malformado (sintaxe)
  - 403: autenticado mas sem permissão
  - 422: request OK sintaticamente, mas falha de precondição SEMÂNTICA/REGULATÓRIA ← LGPD_BLOCKED entra aqui
  - 412: precondição de header falhou (não usar)
LGPDBlocked = 422. Audit log da tentativa bloqueada (LGPD art. 37 — registro de tratamento).

### Auditoria opencode_go.py — 8 blockers LGPD identificados (2026-06-23)
Type: pattern

Contexto: PR do cartorio-dev entrega `backend/app/integrations/opencode_go.py` (250 linhas, wrapper HTTP p/ OpenCode-Go LLM). Auditoria revelou 8 blockers — 2 CRÍTICOS, 3 ALTOS, 3 MÉDIOS.

**Padrão observável (reutilizável em QUALQUER integração LLM/wrapper):**

Quando o módulo de integração LLM aceita `messages: list[dict]` e envia via HTTP sem scrubbar internamente, é SEMPRE shift-the-burden. Toda função de integração LLM DEVE:
1. Chamar `pii.scrub()` em cada `message["content"]` internamente (defense-in-depth)
2. Gravar `AuditService.log()` com hash do payload (request + response) — LGPD art. 37
3. Validar `consent.granted=true` antes de chamar — LGPD art. 7º I
4. Ter fallback para provider alternativo (LiteLLM) com mesmo scrubbing
5. Ter teste de regressão (`test_*_no_pii.py`) com mock httpx que falha se payload bruto chegar
6. Ter rate limit por sessão/usuário
7. Docstring + RIPD + opencode.json devem declarar o MESMO modelo (não deepseek vs minimax)

**Sinal verde (manter, não exigir mudança):**
- Bearer auth via header (não query string)
- Timeout 30s
- Não loga payload bruto
- `raw=None` por padrão (response pode ecoar PII)
- Erros tipados sem leak
- Docstring dizendo que caller DEVE scrubar (intenção boa, mas insuficiente sem scrubbing interno)

**Severidade de cada gap:**
- PII scrubbing interno = CRÍTICO (não ALTO) porque é a ÚNICA barreira real contra leak
- Audit log = ALTO (LGPD art. 37 explícito)
- Consent gate = ALTO (LGPD art. 7º I explícito)
- Teste de regressão = ALTO (sem teste, refactor futuro regride)
- Fallback/rate limit/modelo = MÉDIO (disponibilidade/custo, não-compliance direto)

**Lição para mim (cartorio-lgpd):** ao auditar QUALQUER wrapper de LLM API, SEMPRE exigir scrubbing interno + audit log. Docstring "caller DEVE scrubar" é boa intenção mas na prática é falha.

### Compliance anti-pattern — test softened to match limited regex (2026-06-23)
Type: anti-pattern

Contexto: review do commit a8581fe no projeto Cartorio. O refactor 8d9cbfe criou test_payload_com_pii_bloqueia_e_marca_pii_blocked com sample PIS="123.456789.00" (formato 3-6-2). Esse formato NAO casa com a regex PIS (\b\d{3}\.?\d{5}\.?\d{3}\b, formato 3-5-3). O commit a8581fe (ZCode-Mavis) "consertou" mudando o sample para "123.45678.901-23" (3-5-3 com dash) e ainda suavizou o test removendo as asserções de body["status"]=="pii_blocked"/pii_blocked=True/needs_human_handoff=True. Resultado: teste passou, MAS o regex bug original (3-6-2 não-casa) e o gap de mascaramento de compliance (sempre status=ok na response) foram silenciados.

**P0 gaps identificados (CRÍTICOS):**
1. Webhook response SEMPRE retorna status="ok" mesmo quando PII detectada+handoff. Sistema de monitoramento externo (N8N, Chatwoot) perde sinal. → LGPD art. 9 (informar titular), art. 46 (medidas seguranca), art. 50 (boas praticas).
2. Audit log grava DETECCAO (action=conversa.received com findings) mas NAO grava BLOQUEIO/HANDOFF separadamente. Investigacao de quem tentou exige cruzar tabela conversas, nao audit_log chain. → LGPD art. 37.
3. CNH (11 dig) NAO detectada como CNH — casa como CPF (falso positivo perigoso). CNH identifica pessoa tanto quanto CPF.
4. CNS (15 dig, dado SENSIVEL art. 5 II) NAO detectado — casa como cartao+phone_br. Vazamento de dado de saude para LLM externa = violacao GRAVE.

**Padrão observável (reutilizável em QUALQUER projeto LGPD):**
Sempre que revisar PR que toca deteccao de PII/scrubbing, fazer 3 perguntas:
  Q1. O test passou porque o regex MELHOROU ou porque a FIXTURE foi adaptada ao regex limitado? (diferenca crucial)
  Q2. A response da API ainda carrega o sinal de compliance (status=pii_blocked, needs_human_handoff) ou foi silenciada?
  Q3. O audit log distingue DETECCAO de BLOQUEIO, ou so registra o primeiro?

**Heuristica "test is too easy to pass":**
Se um test de PII com 50 amostras passou em <1 tentativa, ou se o sample foi trocado de formato sem justificativa regulatória, ou se asserções de status/flag foram removidas em commit subsequente, PROVAVELMENTE há gap de detecção mascarado. Investigar sempre.

**Lista de PII brasileiros que SEMPRE devem estar na regex (LGPD/regulatorio):**
  - CPF, CNPJ, PIS/PASEP (3-5-2 oficial, 3-5-3, 11 solto)
  - RG, CNH (11 dig E 9 dig antigo), Titulo Eleitor
  - CNS (dado SENSIVEL art. 5 II — 15 dig ou 15+2)
  - Passaporte BR (AB + 6 dig)
  - Email, Phone BR, CEP, Cartao (16/15)
  - Placa veiculo
  - Data BR (DD/MM/YYYY) E ISO (YYYY-MM-DD)

**Acao ao auditar QUALQUER servico de PII em QUALQUER projeto:**
1. Listar todos os regex ativos
2. Rodar detect_only() contra os 14 formatos BR canonicos (script rapido)
3. Verificar response shape de endpoint principal (signal de compliance intacto?)
4. Verificar audit log (detecção E bloqueio E handoff logados separadamente?)
5. Verificar RIPD/doc LGPD (CNS, CNH mencionados?)

**Cross-project:** Esse padrão (test softened to match limited regex) NAO é especifico de cartorio. Aparece em QUALQUER sistema que tenha compliance tests. Aplicar a udiapods-pii, futuros SaaS B2B, etc.
