
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

### IP /24 truncation helper — IPv4 + IPv6 edge cases (2026-06-23)
Type: code-pattern

Contexto: review LGPD-015 — `backend/app/integrations/opencode_go.py:189-216` implementa `_truncate_ip_to_24()` para LGPD D5 (IP truncado em /24 no audit log). Verifiquei todos os edge cases.

**Implementação canonical (helper):**
```python
def _truncate_ip_to_24(ip: str) -> str:
    if not ip or ip == "unknown":
        return ip or "unknown"
    # IPv4
    if "." in ip and ":" not in ip:
        parts = ip.split(".")
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
    # IPv6 (truncado em /32)
    if ":" in ip:
        groups = ip.split(":")
        if len(groups) >= 2:
            return f"{groups[0]}:{groups[1]}::/32"
    return ip  # formato nao reconhecido, retorna como veio
```

**Tabela de comportamento (verificada em todos os edge cases):**

| Input | Output | Status |
|-------|--------|--------|
| `192.168.1.123` | `192.168.1.0/24` | ✓ |
| `127.0.0.1` (loopback) | `127.0.0.0/24` | ✓ (loopback é /8, mas /24 truncation dá 127.0.0.0/24, válido) |
| `10.0.1.0/24` (já truncado) | `10.0.1.0/24` | ✓ (parts[3]='0/24' descartado, appends '.0/24') |
| `2001:db8::1` | `2001:db8::/32` | ✓ |
| `fe80::1` | `fe80::/32` | ✓ |
| `::1` (IPv6 loopback) | `::/32` | ✓ (válido IPv6 prefix, todos zeros /32) |
| `localhost` | `localhost` | ✓ (sem PII, retorna como veio) |
| `""` (vazio) | `unknown` | ✓ |
| `unknown` | `unknown` | ✓ |
| `fe80::1%eth0` (zone ID) | `fe80::/32` | ✓ (groups[1]='' trata zone ID) |

**Por que /24 para IPv4 e /32 para IPv6:**
- IPv4 /24 = primeiros 3 octetos (24 bits) — preserva util de geo/ASR, remove host identifier
- IPv6 /32 = primeiros 2 grupos (32 bits) — alinhado com alocação comum de blocos IPv6 (/32 é tipicamente o bloco de uma organização)

**Risco LGPD:**
- IPv4 /24 ainda permite identificar pessoa em rede pequena (ex.: empresa, prédio) — considerar /16 ou /20 se contexto exigir mais anonimização
- IPv6 /32 ainda é único por organização — pode correlacionar usuário único

**Quando usar:**
- Audit log de acesso (LGPD art. 37) — /24 OK (precisa de util operacional)
- Display em painel admin — /24 OK
- Compartilhamento com terceiro — /16 ou /20 (anonimização mais forte)
- Dataset público (estatísticas) — remover IP completamente

**Testes obrigatorios:**
- IP valido IPv4, IPv6, loopback, localhost, vazio, formato invalido
- IP já truncado (idempotencia)
- IP com zone ID IPv6

**Severidade do gap se mal implementado:**
- P0: NÃO trunca (vaza PII no audit log) — viola LGPD art. 37 + art. 5 I
- P1: Trunca mas retorna string malformada (audit log ilegivel) — dificulta investigação
- P2: Trunca parcialmente (preserva host identifier) — anonimização insuficiente

**Cross-project:** esse pattern aparece em QUALQUER sistema que loga IP para compliance (LGPD, GDPR, CCPA, HIPAA). Usar em udiapods, futuros SaaS B2B.

### DPA template — 15 clauses obrigatórias para sub-processors LGPD (2026-06-23)
Type: pattern

Contexto: Sprint 3 — fechamento LGPD-011/LGPD-014 (DPA DeepSeek pendente). cartorio-lgpd criou 3 templates DPA em `docs/lgpd/dpa_*_template.md` cobrindo os 3 sub-processors ativos.

**15 cláusulas obrigatórias** (modelo ANPD + Resolução CD/ANPD nº 4/2023 + IAPP):

1. Identificação das partes (controlador + operador + DPOs)
2. Objeto e finalidade (VEDAÇÃO EXPRESSA a treinamento, compartilhamento não autorizado, finalidade própria)
3. Base legal (LGPD art. 7 — incisos específicos) + **transferência internacional** (LGPD art. 33 + mecanismo: SCC art. 33 II + consentimento específico art. 33 I)
4. Tipos de dados tratados (PII scrubbed, dados sensíveis art. 5 II, vedações)
5. Duração e retenção (específica por categoria + eliminação ≤30d pós-revogação)
6. **8 obrigações do operador** (LGPD art. 39): instruções documentadas, sem sub-contratação sem aprovação, segurança art. 46, **vedação treinamento**, DPO próprio, registro de operações, eliminação/devolução, observação dos princípios art. 6
7. Confidencialidade e sigilo (indefinido ou 5y)
8. Notificação de incidentes (≤24h — **MAIS restritivo que art. 48**)
9. Sub-processadores (lista atual, autorização prévia, responsabilidade solidária)
10. Direitos do titular (LGPD art. 18) — operador auxilia controlador
11. Auditoria (anual + on-demand + certificações ISO 27001/SOC 2)
12. Devolução ou eliminação (≤30d + certificado + logs mantidos 5y)
13. Responsabilidade (solidária art. 42 + limite R$ 5M seguro RC + sem limite em dolo)
14. Lei aplicável BR + foro Uberlândia + renúncia
15. Disposições finais (vigência, alterações, nulidade, integração com contrato principal)

**Estrutura de cada template:**
- Cabeçalho com versão + status (SEMPRE STAGING ONLY até assinatura) + Bloqueio LGPD correspondente
- Seção "Cross-References" no final (linka RIPD Tratamento + consent Item + privacy Seção + AUDITORIA_BLOCKERS)
- Assinaturas com testemunhas + reconhecimento de firmas + Apostila de Haia (se跨境)
- Histórico de versões (Conventional Commits style)

**3 templates criados (2026-06-23):**
1. `docs/lgpd/dpa_deepseek_template.md` (11.5KB) — China, 15 cláusulas completas, mecanismo duplo art. 33 II+I
2. `docs/lgpd/dpa_opencode_go_template.md` (8.5KB) — Gateway, 15 cláusulas simplificadas, sem armazenamento PII
3. `docs/lgpd/dpa_evolution_api_template.md` (9.5KB) — BR, 15 cláusulas, base legal art. 7 II obrig. legal, sem跨境

**Diferenciação por tipo de sub-processor:**
- **跨境 (China):** DPA completo + SCC + consentimento específico + auditoria presencial + seguro R$ 5M
- **Gateway:** DPA simplificado (sem armazenamento, sem treinamento, sem跨境 própria) — complementar ao DPA do sub-processor primário
- **BR:** DPA médio — sem跨境, sem SCC, base legal pode ser art. 7 II (obrigação legal) em vez de consentimento

**Cross-project:** esse template e reusable para QUALQUER projeto B2B com sub-processors. Adaptar:
- Sub-processors SaaS EUA: mecanismo art. 33 II (SCC) + I (consent) se EU/US sem Privacy Shield equivalente
- Sub-processors BR: sem跨境, base legal varia
- Sub-processors UE: GDPR adequacy (art. 33 I) — DPA mais simples

**Estimativa de esforço juridico externo (Doneda/Patricia Peck):**
- Parecer: 8-16h
- Adaptação por provedor: 2-4h cada
- Negociação: 2-6 semanas por provedor
- Total: 1-2 meses do kickoff à assinatura

**Regra:** NUNCA começar a enviar dado real para sub-processor sem DPA assinado E armazenado em `docs/lgpd/dpa_<provider>.pdf`. Template é ponto de partida, NAO contrato.
