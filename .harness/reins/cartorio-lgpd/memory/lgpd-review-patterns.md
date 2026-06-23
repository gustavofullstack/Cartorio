---
description: 5 decisões duráveis de LGPD PR review (LGPDBlockedResponse copy, retenção por base legal, IP middleware, soft delete LGPD-aware, status 422) + checklist LLM wrapper (7 itens) + heurística "test softened to match limited regex" + estado da task LGPD-014 (DPA DeepSeek P0). Carrega quando revisar PR que toca PII/auditoria/consentimento, ou auditar wrapper de LLM, ou classificar blocker LGPD.
---

# LGPD review patterns — decisões duráveis

## 1. As 5 decisões duráveis de PR review

### Decisão 1: LGPDBlockedResponse / erro de consentimento — copy defensável

Sempre incluir no body do erro:
- Citação do art. + inciso + parágrafo (não só a lei) — ex: "LGPD art. 7º, I e art. 8º, § 5º"
- Contato DPO (art. 41)
- Link da política de privacidade (art. 9 + art. 50)
- Como remediar (consentimento=true ou contato DPO)
- Direito à revogação (art. 8 § 5º)

**Status HTTP: 422** (Unprocessable Entity) — defensável: request compreendido, falha de precondição regulatória.

### Decisão 2: Retenção separada por base legal

NÃO tratar "tudo" como 5 anos ou "tudo" como até-revogação. Separar:

| Base legal | Retenção | Exemplo |
|------------|----------|---------|
| art. 7º II (obrigação legal) | MÍNIMA obrigatória = regra do setor | Cartório = 5y (Provimento CNJ 74); outros setores = norma específica |
| art. 7º I (consentimento) | ATÉ REVOGAÇÃO ou cessar finalidade | Conversa de bot sem protocolo |

**Cartório especificamente:**
- Cliente COM protocolo = 5y (anonimizar após)
- Cliente SEM protocolo = até revogação (deletar)
- Job retenção deve distinguir os 2 caminhos.

### Decisão 3: IP é dado pessoal (LGPD art. 5º I) — capturar via middleware + truncar

- Middleware FastAPI captura `request.client.host` (fallback `X-Forwarded-For` se atrás de proxy)
- Persistência completa com retenção curta (2 anos) — IP perde relevância operacional depois
- Exibição no painel admin: truncar /24 (IPv4) ou /48 (IPv6)
- Audit log: incluir `request_ip` em toda entrada (não só `actor_id`)
- Consentimento IP: registrar em coluna `consentimento_ip` (separado do IP de log) — base legal art. 37 + art. 8 § 2º

**Implementação canônica:** ver `pii-scrubbing-helpers.md`.

### Decisão 4: Soft delete LGPD-aware — coluna `motivo_encerramento` ENUM

Não basta ter `deleted_at`. Distinguir:
- `revogacao_consentimento` (cliente pediu pra sair — LGPD art. 18 IX)
- `retencao_5y` (job automático após prazo legal)
- `exercicio_direito_titular` (LGPD art. 18 IV — anonimização/bloqueio)
- `outros` (auditoria manual)

Cada caminho tem obrigação regulatória diferente. Sem distinção, vira caixa-preta em auditoria.

### Decisão 5: Status 422 vs 403 vs 400 — semântica regulatória

| Código | Significado |
|--------|-------------|
| 400 | Request malformado (sintaxe) |
| 403 | Autenticado mas sem permissão |
| **422** | Request OK sintaticamente, mas falha de precondição SEMÂNTICA/REGULATÓRIA ← **LGPDBlocked entra aqui** |
| 412 | Precondição de header falhou (não usar) |

Audit log da tentativa bloqueada (LGPD art. 37 — registro de tratamento).

## 2. Checklist de LLM wrapper (7 itens)

Quando revisar QUALQUER wrapper de API LLM (OpenAI, Anthropic, DeepSeek, OpenClaw, etc):

1. `pii.scrub()` em cada `message["content"]` internamente (defense-in-depth — caller pode esquecer)
2. `AuditService.log()` com hash do payload (request + response) — LGPD art. 37
3. Validar `consent.granted=true` antes de chamar — LGPD art. 7º I
4. Fallback para provider alternativo (LiteLLM) com mesmo scrubbing
5. Teste de regressão (`test_*_no_pii.py`) com mock httpx que falha se payload bruto chegar
6. Rate limit por sessão/usuário
7. Docstring + RIPD + config devem declarar o MESMO modelo (não deepseek vs minimax)

### Severidade

- PII scrubbing interno = CRÍTICO (não ALTO) — é a ÚNICA barreira real contra leak
- Audit log = ALTO (art. 37)
- Consent gate = ALTO (art. 7º I)
- Teste de regressão = ALTO
- Fallback/rate limit/modelo = MÉDIO

### Sinal verde (manter, não exigir mudança)

- Bearer auth via header (não query string)
- Timeout 30s
- Não loga payload bruto
- `raw=None` por padrão (response pode ecoar PII)
- Erros tipados sem leak
- Docstring dizendo que caller DEVE scrubar (boa intenção, mas insuficiente sem scrubbing interno)

## 3. Heurística "test softened to match limited regex"

Contexto: commit `a8581fe` "consertou" test PII trocando sample de PIS formato 3-6-2 para 3-5-3 com dash, **e suavizou o test removendo asserções de `body["status"]=="pii_blocked"`**. Teste passou, MAS o regex bug original (3-6-2 não-casa) e o gap de mascaramento foram silenciados.

### As 3 perguntas ao revisar QUALQUER PR que toca detecção PII/scrubbing

- **Q1:** Test passou porque regex MELHOROU ou porque a FIXTURE foi adaptada ao regex limitado?
- **Q2:** Response da API ainda carrega o sinal de compliance (`status=pii_blocked`, `needs_human_handoff`) ou foi silenciada?
- **Q3:** Audit log distingue DETECÇÃO de BLOQUEIO, ou só registra o primeiro?

### Quando desconfiar (heurística "test is too easy to pass")

- 50 amostras passou em <1 tentativa
- Sample foi trocado de formato sem justificativa regulatória
- Asserções de status/flag foram removidas em commit subsequente

**→ PROVAVELMENTE há gap de detecção mascarado. Investigar sempre.**

### P0 gaps típicos ao auditar PII service

1. Webhook response SEMPRE retorna `status="ok"` mesmo quando PII detectada+handoff (sistema de monitoramento externo perde sinal) — viola art. 9, 46, 50
2. Audit log grava DETECÇÃO mas NÃO grava BLOQUEIO/HANDOFF separadamente — viola art. 37
3. CNH (11 díg) NÃO detectada como CNH — casa como CPF (falso positivo perigoso)
4. CNS (15 díg, SENSÍVEL art. 5 II) NÃO detectado — vazamento de dado de saúde para LLM externa = violação GRAVE

## 4. LGPD-014 task state — DPA DeepSeek P0 BLOQUEADOR

**Status (2026-06-23):** P0 BLOQUEADOR — backend em STAGING ONLY até DPA assinado OU troca de provedor.

### Auditoria confirmou

- `opencode_go.py` usa `deepseek-v4-flash` (DeepSeek chinês) — LGPD art. 33 (transferência internacional sem adequação ANPD)
- Nenhum arquivo DPA no repo (`docs/lgpd/dpa_*.pdf` inexistente)
- 12 blockers LGPD identificados — 8 resolvidos, 4 abertos (#9, #10, #11, #12)
- Decisor: Gustavo (escalado 2026-06-23 18:39 via parent mvs_c2508947...)

### Templates prontos (ver `lgpd-dpa-templates.md`)

3 sub-processors: DeepSeek, OpenCode-Go, Evolution API.

### Esforço jurídico externo (Doneda/Patricia Peck)

- Parecer: 8-16h
- Adaptação por provedor: 2-4h cada
- Negociação: 2-6 semanas
- Total: 1-2 meses

### Alternativa estratégica

Trocar para OpenAI/Anthropic (DPA template público, país com adequação, custo +10-30x).

### Quem implementa

- Jurídico externo (contratação)
- Gustavo (decisão estratégica)
- DPO (assinatura)
- cartorio-lgpd (revisão final)

### References

- `docs/ripd.md` v1.3 (atualizado nesta sessão)
- `docs/lgpd/AUDITORIA_BLOCKERS.md` (Bloqueio #6 e #7)
- Report 2035 do parent session
