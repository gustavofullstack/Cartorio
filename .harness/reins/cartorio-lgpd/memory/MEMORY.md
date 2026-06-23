
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
