
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

### LGPD-014 DPA DeepSeek assinado (2026-06-23)
Type: task

TASK P0 BLOQUEADOR — DPA (Data Processing Agreement) com DeepSeek (sub-processor LLM via OpenCode-Go gateway).

**Contexto:** Auditoria 2026-06-23 confirmou que:
- opencode_go.py usa deepseek-v4-flash (DeepSeek chinês) — LGPD art. 33 (transferência internacional sem adequação ANPD)
- Nenhum arquivo DPA no repo (docs/lgpd/dpa_*.pdf inexistente)
- 8 blockers originais do AUDITORIA_BLOCKERS — 6 resolvidos, 2 abertos
- 4 NOVOS blockers identificados (#9, #10, #11, #12)
- Backend em STAGING ONLY até DPA assinado OU troca de provedor

**Cláusulas obrigatórias (15):** identificação partes, objeto+finalidade, base legal art. 33 II, tipos dados, duração, 8 obrigações operador, notificação ≤24h, sub-processadores, transferência internacional, direitos titular art. 18, auditoria, devolução/eliminação ≤30d, responsabilidade solidária art. 42, lei BR + foro Uberlândia, rescisão.

**Estimativa de esforço:**
- Jurídico externo (Doneda/Patricia Peck): 8-16h parecer
- Negociação DeepSeek: 2-6 semanas
- Total: 1-2 meses

**Alternativa estratégica:** trocar para OpenAI/Anthropic (DPA template público, país com adequação, custo +10-30x).

**Decisor:** Gustavo (escalado por Pietra mvs_c2508947... em 2026-06-23 18:39).

**Quem implementa:** jurídico externo (contratação) + Gustavo (decisão) + DPO (assinatura) + cartorio-lgpd (revisão final).

**Reference:** docs/ripd.md v1.3 (atualizado nesta sessão) + docs/lgpd/AUDITORIA_BLOCKERS.md (Bloqueio #6 e #7) + report 2035 do parent session.

### LGPD LLM boundary pattern — sempre auditar boundary 2 (output), nao so 1 (input) (2026-06-23)
Type: pattern

Contexto: 3 integracoes LLM no cartorio backend (opencode_go.py, integrations.py, router.py via webhook_evolution). TODAS as 3 tinham scrubbing INTERNO no INPUT mas NENHUMA tinha scrubbing no OUTPUT (boundary 2). Resultado: Blocker #10 + #13 (P0) + #14 (P1).

**Insight fundamental (reutilizavel em QUALQUER projeto com LLM):**
Toda integracao LLM tem 2 boundaries:
  BOUNDARY 1 (input):  text -> scrub() -> LLM request   [facil de implementar]
  BOUNDARY 2 (output): LLM response -> ??? -> caller    [facil de ESQUECER]

O gap padrao e sempre no BOUNDARY 2. O LLM pode ECOAR PII (memorizou padrao em dados de treino) mesmo se o input foi scrubbed. Se o caller nao scrubar o output, PII volta pro cliente final (WhatsApp, chat, etc).

**Sinal verde (input scrubbed OK):**
  - pii.scrub() chamado ANTES de httpx.post / requests.post / openai.ChatCompletion.create
  - Docstring diz 'caller DEVE scrubar output tambem'
  - Tem `pii_redacted_count` no request

**Sinal vermelho (output NAO scrubbed, mesmo com input OK):**
  - `resp.content` ou `response.content` atribuido direto a variavel que vai pra cliente
  - `bot_response = llm_resp.content` sem scrub reverso
  - Sem `output_pii_redacted_count` na response
  - test verifica apenas input->request, NAO response->client

**Acao de auditoria para QUALQUER projeto LLM (5 perguntas):**
  Q1. Onde o `resp.content` / `llm_resp.content` / `response.content` e atribuido?
  Q2. Esse valor vai direto pro cliente final (HTTP response, WebSocket message, fila, etc)?
  Q3. Ha scrub() no output? (procure por padrao `scrub(llm_resp.content)` ou similar)
  Q4. A response ao cliente tem flag `output_pii_redacted_count`?
  Q5. Os testes verificam que output foi scrubbed? (mock LLM ecoando CPF -> assert response NAO contem CPF)

**Especificacao do fix (defense-in-depth):**
  Adicionar helper `scrub_llm_output(content: str) -> tuple[str, int]` em pii.py que:
    1. Chama scrub(content)
    2. Retorna (scrubbed_text, redaction_count)
  Aplicar em TODO lugar onde `llm_resp.content` for atribuido (3 lugares no cartorio).
  Adicionar campo `output_pii_redacted_count: int` em ChatResponse + OpenCodeTestResponse.
  Adicionar audit log: `action='llm.output_scrubbed'` com payload {sender, output_pii_count, output_length}.

**Severidade tipica do gap:** P0 quando o output vai pro cliente final, P1 quando vai pra admin/operador, P2 quando vai so pra log interno.

**Cross-project:** Esse pattern NAO e especifico de cartorio. Aparece em QUALQUER integracao LLM (OpenAI, Anthropic, OpenClaw, etc). Aplicar a udiapods-pii, futuros SaaS B2B com chatbot, etc.

### N8N workflow LGPD review checklist — PII-tocando (2026-06-23)
Type: checklist

Contexto: cartorio-n8n (mvs_441eef7e) entregando workflows E6.S2 (10 creds + 18 WFs, 15 ativos). Workflows #13/15/17/19/20/23/27 classificados como PII-tocando.

**Checklist obrigatorio (5 itens) — usar em TODO review de WF que move dado pessoal:**

1. **Consent gate ANTES de chamar LLM/provider externo** (LGPD art. 7 I + 8)
   - Node Function/IF verifica `{{$json.consent.granted}} == true` ANTES de chamar OpenCode-Go/DeepSeek/LiteLLM
   - Se False → bloqueia, chama HITL, registra `LGPDBlockedResponse`
   - Padrao copy juridica plugada: commit 116afe0

2. **Scrub 3 camadas (input/pre-LLM/output)**
   - Camada 1: input do webhook (pii.scrub no node Function)
   - Camada 2: pre-LLM (regex 11+ tipos: CPF, RG, CNPJ, CNS, CNH, telefone, email, cartao, CEP, PIS, titulo, placa, data)
   - Camada 3: output do LLM (scrub no response antes de persistir/enviar)
   - Defense-in-depth — LLM pode ecoar PII memorizada de treino

3. **Audit log com request_id + IP /24 truncado** (LGPD art. 37 + D5)
   - Toda execucao grava `execution_entity` (N8N Postgres) com `payload_hash` (SHA-256) + `scrubbed_payload` + `pii_tokens`
   - IP truncado /24 (IPv4) ou /48 (IPv6) para privacy-by-design
   - Sem payload bruto em log

4. **LGPDBlockedResponse copy juridica plugada** (commit 116afe0)
   - Citacao art. + inciso + paragrafo
   - Contato DPO (art. 41)
   - Link politica privacidade
   - Como remediar (consentimento=true ou DPO)
   - Direito revogacao (art. 8 par 5)
   - Status 422 (LGPDBlocked = precondicao semantica/regulatoria)

5. **RequestContextMiddleware ativo**
   - Captura request.client.host (fallback X-Forwarded-For se proxy)
   - Persiste IP completo com retencao curta (2y)
   - Canal/agent_id visiveis no audit

**Workflows NAO-PII (gate mais leve):**
- Backup, monitoramento, audit, FAQ-only: revisao basica de segredos + RLS + retencao

**Severidade por gap:**
- Ausencia consent gate em WF PII-tocando = BLOQUEIO P0
- Scrub ausente em 1 das 3 camadas = BLOQUEIO P1 (revisar caso a caso)
- Audit log sem IP /24 = P2 (privacy-by-design)
- LGPDBlockedResponse copy errada = P2
- RequestContextMiddleware off = P2

**Cross-project:** esse checklist NAO e especifico de cartorio. Aplicavel a QUALQUER projeto com N8N/make.com/zapier + dado pessoal. Usar em udiapods se migrar para N8N.

**Cross-ref:** review de cartorio-dev (LGPD-015) acelerado se este checklist ja estiver satisfeito — revisor sabe o que procurar.

### SoD — LGPD reviewer NAO pode ser implementer (2026-06-23 19:58 BRT) (2026-06-23)
Type: rule

Aprendizado durante review de merge master vs fix branch no Cartorio. Ofereci fazer o merge como "cross-review final". Pietra (root) RECUSOU com理由 correto:

LGPD reviewer (cartorio-lgpd) revisa implications LGPD. NAO pode implementar o que revisa. Quebra Separation of Duties (SoD) — mesmo papel nao pode ser gatekeeper + executor do mesmo PR.

Padrao correto do harness Cartorio:
  cartorio-lgpd → review cross LGPD implications (gatekeeper, NAO implementer)
  cartorio-dev → implementa o merge (ownership implementation)
  Mavis root → quality gate + escalacao D1 (decisao de produto/arquivo)

Aplicacao universal (qualquer projeto LGPD/GDPR/CCPA B2B):
  - Quem revisa compliance NAO commita o codigo revisado
  - Quem audita NAO e

### Multi-LLM sub-processor rule — TODOS STAGING ONLY ate DPA assinado (2026-06-23)
Type: rule

Regra cross-project pra QUALQUER projeto com multiplos sub-processors LLM externos.

**Contexto:** Cartorio tem 4 sub-processors LLM:
- DeepSeek (LGPD-014) — cliente final WhatsApp via OpenCode-Go gateway
- OpenCode-Go — gateway tecnico (complementar a DeepSeek)
- MiniMax (LGPD-015) — harness operacional (reins do Mavis runtime)
- Evolution API (BR) — WhatsApp Business (sem跨境)

**Regra de ferro (LEMBRAR):**
Quando um projeto tem MAIS DE 1 sub-processor LLM, TODOS precisam de DPA assinado antes de qualquer caminho de producao com dado real. NAO basta assinar 1 — basta 1 sem DPA para o backend inteiro ficar STAGING ONLY.

Razao juridica: LGPD art. 33 (transferencia internacional) aplicavel a CADA sub-processor individualmente. Se DeepSeek esta OK mas MiniMax nao esta, dado que passa por MiniMax (mesmo que minimamente) ja e跨境 irregular. Backend inteiro fica nao-conforme.

**Aplicacao pratica (checklist pre-deploy):**
- [ ] DPA DeepSeek assinado? (LGPD-014)
- [ ] DPA OpenCode-Go assinado? (gateway)
- [ ] DPA MiniMax assinado? (LGPD-015)
- [ ] DPA Evolution API assinado? (BR, base legal art. 7 II)
- [ ] Se qualquer um = PENDENTE: STAGING ONLY com dado sintetico
- [ ] Cenario worst case: 1 DPA assinado, 3 pendentes = mesmo nivel de exposicao que 0 assinados (跨境 irregular cumulativa)

**Cross-project:** aplicar a:
- udiapods (se migrar pra multi-LLM): GPT-5.5 + Claude + Gemini providers
- Qualquer SaaS B2B com OpenAI + Anthropic + open-source LLM em paralelo
- Chatbots com fallback multi-provider (LiteLLM com 3+ backends)
