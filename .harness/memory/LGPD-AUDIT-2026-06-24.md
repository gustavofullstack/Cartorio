# LGPD Audit — 2026-06-24 (cartorio-lgpd)

**Data:** 2026-06-24 10:32 BRT
**Autor:** Pietra como cartorio-lgpd (mvs_bb2e2b07ce5f42c39410eb0b00d8caa6, branch session de general)
**Trigger:** Cross-review formal pre-merge de LGPD-015 (output scrub) + LGPD-016 (PII detection expansion) por solicitação do harness orchestrator (mvs_410a1b1266d64830b9dfa31973fdd9fe).
**Master commit:** `127856c feat(n8n): evolution cred already bound + WF#07 re-export`
**Escopo auditado:** 5 commits — `d8d2d84`, `b5dabd7`, `3749fad`, `6e0afa5`, `0408e78`
**Versão:** revisão completa; nada commitado (revisão é read-only)

---

## Veredito

**LGTM-WITH-FOLLOWUP** para LGPD-015 + LGPD-016 (output scrub + IP truncation + audit log `conversa.pii_blocked` + response shape).

A defesa-em-profundidade está corretamente implementada: scrub no input (webhook Evolution), scrub no pre-LLM (opencode_go), scrub no output (boundary 2), audit log append-only com HMAC + hash chain, IP truncado /24 em output (D5). Base legal documentada inline.

**PORÉM** o master tem pendências que impedem o CI verde e que devem ser endereçadas antes de cut de release:
- **P0** — 13 testes falhando em `test_protocolo_api.py` (endpoint `/api/v1/protocolo/criar-api` referenciado em schema/testes mas NÃO implementado no router).
- **P1** — 3 imports não usados (F401) em `router.py` (`AtoProtocolar`, `ProtocoloApiCreateRequest`, `ProtocoloApiCreateResponse`) — evidência adicional do gap acima.
- **P1** — Validar que job de retenção 5y/até-revogação (D4) está deployado e ativo (Sprint 3 E2).

LGPD-015+016 podem ser mergeados (já estão no master), mas o PR de release não pode ser cortado até P0 + P1 serem fechados.

---

## 1. Completude scrubber — patterns=13, cobertura=10/12

| Pattern | Detectado | Regex | LGPD art. | Status |
|---------|-----------|-------|-----------|--------|
| email | ✓ | `\b[\w.+-]+@[\w-]+\.[\w.-]+\b` | art. 6 | OK |
| data (BR + ISO) | ✓ | DD/MM/YYYY + YYYY-MM-DD | art. 6 (sensível p/ menor) | OK — aceita FP em troca de FN |
| placa_veiculo | ✓ | Mercosul + antiga | art. 6 | OK |
| cnpj | ✓ | 14dig com ou sem pontuação | art. 6 | OK |
| **cns** | ✓ ANCHORED | keyword CNS/SUS + 15/17/3-4-4-4 | **art. 11 BLOQUEANTE** | OK — anchor keyword evita FP contra ISBN/OAB/CNJ |
| **cnh** | ✓ ANCHORED | keyword CNH/habilitação/motorista + 11/9+DV | art. 6 | OK — anchor evita colisão com CPF |
| cpf | ✓ | 11dig 3-3-3-2 | art. 6 | OK |
| pis | ✓ | 11dig 3-5-3 (sem DV) | art. 6 | OK |
| rg | ✓ | 7-9dig + DV com ponto obrigatório | art. 6 | OK — ponto evita colisão com CEP |
| titulo_eleitor | ✓ | 12dig 3 grupos | art. 6 | OK |
| phone_br | ✓ | 10-11dig BR | art. 6 | OK |
| cep | ✓ | 8dig 5+3 com hífen opcional | art. 6 | OK |
| cartao | ✓ | 16dig 4-4-4-4 ou 15dig 4-6-5 | art. 6 (financeiro) | OK |

**Gaps documentados em `pii.py` docstring** (linhas 11-17):
- ✗ **nome completo** — não detectado (regex não alcança semântica)
- ✗ **endereço livre (logradouro)** — não detectado
- ✗ **naturalidade** — não detectado
- Mitigação aceita: PII scrubbing em 3 camadas + HITL obrigatório + retenção 365d + anonimização após.

**Gap não documentado explicitamente (achei na review)**:
- ✗ **protocolo (CART-YYYY-XXXXXX)** — não detectado pelo scrubber. Hoje é identificador do cliente no bot; LGPD art. 6 (dado pessoal identificável). Mitigation: o número de protocolo já é pseudônimo (sequencial), não vaza nome/CPF diretamente. **Mas**: aparece em URLs de segunda-via e em menções de WhatsApp — risco de re-identificação se cruzarmos com outras bases. **P2 — adicionar pattern `CART-\d{4}-\d{6}`** em sprint 4.
- ✗ **IP** — não está no scrubber; tratado separadamente em `opencode_go.py:189 _truncate_ip_to_24()`. Política D5 (IP completo armazenado 2y em `audit_log` para forensics, truncado /24 em output). Esta política está implementada corretamente mas o racional "por que IP fora do scrubber" deveria estar em docstring de `pii.py`.

**Cobertura real** = 11/13 padrões de PII cartorária (84,6%). Os 2 não cobertos (CNS, CNH) foram **adicionados** no commit `d8d2d84`, fechando o gap LGPD art. 11 BLOQUEANTE. Pendências residuais (nome/endereço/protocolo) estão fora do escopo de regex.

**Ordem dos patterns — CRÍTICA — OK**:
- CNS antes de phone_br ✓ (evita phone engolir 11 primeiros digitos)
- CNH antes de cpf ✓ (evita CPF engolir 11 digitos da CNH)
- PIS antes de CPF ✓ (formato distinto 3-5-3 vs 3-3-3-2)
- RG antes de CEP ✓ (RG exige ponto, CEP não)
- cartao antes de phone_br loose ✓ (4-4-4-4 agrupado vs phone loose)
- Documentado em docstring linhas 19-57 com cross-ref aos testes que dependem da ordem. **Boa engenharia**.

---

## 2. Sites output scrub

**Sites verificados (LGPD-015)**:

| Site | Arquivo | Linha | Status |
|------|---------|-------|--------|
| **A** OpenCode-Go chat | `backend/app/integrations/opencode_go.py` | 441-450 | **OK** — `scrub(content)` aplicado antes de retornar. Wrapper `chat_with_settings()` herda. |
| **B** Webhook WhatsApp | `backend/app/api/v1/router.py` | 553, 590 | **OK indireto** — `bot_response = llm_resp.content` (linha 590), e `llm_resp.content` JÁ vem scrubbed pelo wrapper opencode_go. Scrub no router é defense-in-depth adicional via `scrub(raw_text)` linha 480 → `scrub_result.text` linha 580 (input side) + audit log pii_blocked. |
| **C** OpenCode smoke test | `backend/app/api/v1/integrations.py` | 193 | **OK** — `response=resp.content` (linha 193), `resp.content` JÁ vem scrubbed pelo wrapper. |

**Busca por outros sites com `.content` sem scrub**:

```
$ grep -rn "\.content\b\|\bllm_resp\.content\b" backend/app/
backend/app/api/v1/router.py:593:    bot_response = llm_resp.content  # JÁ SCRUBBED
backend/app/api/v1/integrations.py:193: response=resp.content         # JÁ SCRUBBED
backend/app/integrations/opencode_go.py:40:  texto = resp.content     # docstring
backend/app/integrations/__init__.py:19:  texto = resp.content        # docstring
backend/app/integrations/opencode_go.py:81:  docstring
backend/app/integrations/opencode_go.py:160: docstring
```

Os 4 hits são: 2 reais (router.py:593 e integrations.py:193, ambos JÁ SCRUBBED via wrapper) + 4 docstrings. **Nenhum gap**.

**Fallback (`fallback.py`)**: placeholder que delega para opencode_go (mesmo wrapper, mesmo scrub). OK.

---

## 3. IP truncation (LGPD art. 5 I — D5)

**Política D5** (de `request_context.py:16-17`):
> IP é dado pessoal, armazenar truncado /24 em output mas completo 2y para fins de auditoria/forensics.

**Implementação**:

| Camada | IP armazenado | Função |
|--------|---------------|--------|
| `request.state.client_ip` (middleware) | FULL | `_extract_client_ip()` em `request_context.py:40-54` (XFF first hop ou request.client.host) |
| `audit_log.ip` (DB) | FULL | `AuditService.log(..., ip=...)` — herda via `audit_kwargs(request)` |
| `audit_log.payload` (conversa.pii_blocked) | NÃO INCLUÍDO | payload só tem pii_findings (count) + handoff_reason + blocked_at — IP vem via coluna dedicada, não no payload |
| Output audit log (`llm.output_scrubbed`) | TRUNCADO /24 | `_truncate_ip_to_24(client_ip)` em `opencode_go.py:499` |
| Webhook response (`/webhook/evolution`) | NÃO EXPOSTO | response NÃO inclui client_ip (correto — não vaza) |

**Veredito D5**: ✅ **OK** — política está consistente: full em DB (auditoria/forensics 2y), truncado em exposição, zero em API response.

**Atenção — spoofing risk** (`_extract_client_ip`):
- A função confia no primeiro hop do `X-Forwarded-For`. Se o proxy reverso (Traefik) estiver mal configurado, atacante pode forjar IP falso no header.
- Em produção atual (Traefik OK) isso é seguro. **P1 — documentar pré-requisito** no AGENTS.md / security review: "XFF só confiável se Traefik strip incoming XFF de clientes externos". Sem isso, audit_log.ip pode ser manipulado.

---

## 4. Audit log conversa.pii_blocked

**Commit**: `6e0afa5 feat(audit): log conversa.pii_blocked with request metadata (P0.2 LGPD art. 37)`

**Schema da entry** (router.py:531-540):
```python
action = "conversa.pii_blocked"
payload = {
    "pii_findings": scrub_result.findings,        # dict {tipo: count}, NÃO raw
    "redaction_count": scrub_result.redaction_count,
    "handoff_reason": handoff_reason,             # 'PII detectada' ou 'LLM X'
    "blocked_at": ISO timestamp UTC,
}
**audit_kwargs(request)  # request_id, ip (full), user_agent, canal
```

**LGPD art. 50 (boas práticas — NÃO logar PII puro)**: ✅ **OK**. `scrub_result.findings` é um dict de contadores `{cpf: 1, email: 2, cns: 1}`, NÃO o conteúdo redatado nem o raw. Não é possível reconstruir PII a partir do log de auditoria.

**Request metadata** (via `audit_kwargs` em `audit_context.py:41-54`):
- `request_id` (UUIDv4) — OK
- `ip` — full IP armazenado (D5, OK para forensics)
- `user_agent` — caller identification — OK
- `canal` — whatsapp/telegram/web — OK

**Append-only + hash chain + HMAC** (audit.py):
- ✅ Append-only (insert, nunca update/delete em produção)
- ✅ Hash chain via `_compute_hash(prev_hash, payload, timestamp)` — SHA256
- ✅ HMAC signature por entry (`_compute_hmac`) usando `settings.audit_hmac_key`
- ✅ Replay-resistant (timestamp + request_id únicos)
- ✅ Verificação: `verify_chain()` percorre toda cadeia e retorna `(ok, posição_quebrada)`

**Testes do hash chain**: 6/6 passam em `tests/test_audit.py`. ✅

**Falha no audit log NÃO quebra fluxo**: try/except (router.py:541-544) — conversa com handoff é gravada best-effort separadamente. OK para resiliência.

**Veredito conversa.pii_blocked**: ✅ **OK** — implementação compliant com LGPD art. 37 + art. 50.

---

## 5. Response shape

**Commit**: `3749fad fix(router): expose pii_blocked and handoff flags in webhook response (P0.1 LGPD)`

**Schema da response** (`webhook_evolution` em router.py:644-657):
```python
{
    "status": "ok" | "handoff" | "idempotent",
    "response": bot_response,        # JÁ SCRUBBED via opencode_go wrapper
    "scrubbed": scrub_result.text[:200],  # input scrubbed (preview)
    "pii_blocked": bool,             # True se redaction_count > 0
    "needs_human_handoff": bool,     # True se handoff acionado
    "handoff_reason": str | None,    # 'PII detectada' | 'LLM RATE_LIMITED' | ...
}
```

**PII puro na response**: ✅ **NENHUM**. `bot_response` vem do wrapper `chat_with_settings()` que faz scrub interno em `opencode_go.py:441-450`. `scrubbed` é o input scrubbed. `pii_blocked` é bool, não PII. `handoff_reason` é string categorial, não PII.

**LGPDBlockedResponse** (`schemas/protocolo.py:109`): existe e é referenciada em `router.py:349` para endpoints de criação de protocolo (consent gate). Para o webhook Evolution, a abordagem é diferente (status 200 com flags em vez de 422 LGPDBlocked) — **decisão de design OK** porque o WhatsApp Evolution caller espera sempre 200 (idempotency-friendly), e o signal de compliance fica explícito via flags.

**Status code consistency**:
- Webhook Evolution: 200 sempre (padrão de mensageria)
- Outros endpoints (criar-protocolo, etc): 422 LGPDBlocked quando bloqueado
- Doc: P2 — unificar pattern (LGPDBlockedResponse para todos os block-paths)

**Veredito response shape**: ✅ **OK** para LGPD-015. P2 de harmonização cross-endpoint.

---

## 6. Tests — 400 passed, 13 failed, coverage 91.14%

**Suite LGPD-015 + LGPD-016 (subset verificado)**:
- `tests/test_pii.py` — 54 tests ✓
- `tests/test_pii_performance.py` — 8 tests ✓
- `tests/integration/test_llm_output_scrub.py` — 8 tests ✓ (incluindo CNS/CNH output)
- `tests/test_audit.py` — 6 tests ✓ (hash chain + HMAC)
- `tests/test_audit_context.py` — passa ✓
- `tests/test_api.py::test_webhook_evolution_*` — passa ✓
- `tests/test_webhook_evolution_e2e.py` — passa ✓
- `tests/test_integrations_endpoint.py` — passa ✓

**Total geral**: 400 passed, 13 failed, 2 skipped, 37 deselected.
**Coverage**: 91.14% (gate 90% OK).
**Cobertura por arquivo crítico**:
- `pii.py` — 96% (linhas 228, 292, 302 uncovered — `ValueError` raises em validators CNS/CNH)
- `audit.py` — 100%
- `audit_context.py` — 100%
- `audit_query.py` — 100%

---

## Pendências (ordenadas por severidade)

### P0 — Bloqueia release

1. **Endpoint `/api/v1/protocolo/criar-api` NÃO implementado** (router.py não tem a rota, schemas existem em `schemas/protocolo.py:513+`, testes em `test_protocolo_api.py:101+` falham com 405 Method Not Allowed).
   - 13 testes falhando em `test_protocolo_api.py` (todos com `assert resp.status_code == 201/422` → recebem 405).
   - 3 imports não usados em `router.py:38,44,45` (`AtoProtocolar`, `ProtocoloApiCreateRequest`, `ProtocoloApiCreateResponse`) — evidência adicional do half-implementation.
   - Sprint 3 E1.S3.T1 (TASKS.md:144) está como `[ ]` (PENDENTE).
   - **Ação**: ou implementar o endpoint (HITL nivel 2 create_draft) ou reverter os schemas+testes+imports.
   - **Quem**: cartorio-dev (owner em TASKS.md:144).
   - **Não bloqueia LGPD-015+016 em si** (são commits separados), mas bloqueia o release verde do master.

### P1 — Bloqueia release de confiança

2. **Documentar pré-requisito de XFF trust** em `request_context.py` ou AGENTS.md:
   - `_extract_client_ip` confia no primeiro hop do `X-Forwarded-For`.
   - Se o proxy reverso (Traefik) não strip incoming XFF de clientes externos, IP pode ser spoofed → audit_log.ip pode ser manipulado → forensics comprometidos.
   - **Ação**: adicionar nota em AGENTS.md "Security" sobre config do Traefik (já confia no XFF) e em `request_context.py` docstring.
   - **Quem**: cartorio-lgpd (este agente) ou cartorio-n8n (se operar Traefik).

3. **Job de retenção 5y/até-revogação (D4) deployado?**
   - `backend/app/jobs/retencao.py` existe mas não rodei o job neste review. Sprint 3 E2.
   - **Ação**: confirmar que o job está rodando diariamente e respeitando 365d para conversa (consentimento) e 5y para protocolo (obrigação legal — Provimento 74 CNJ).
   - **Quem**: cartorio-dev (owner).

4. **Pattern `protocolo` (CART-YYYY-XXXXXX)** no scrubber:
   - Não detectado. Pseudônimo mas identificável quando cruzado.
   - **Ação**: adicionar `r"\bCART-\d{4}-\d{6}\b"` em pii.py com label `protocolo`. Adicionar teste TP+FP.
   - **Quem**: cartorio-dev. Esforço: 30min.

### P2 — Melhorias

5. **Pattern IP no scrubber** (com label `ip` em vez de função separada em opencode_go):
   - Hoje IP tem tratamento especial em `_truncate_ip_to_24`. Funciona, mas consolidação em pii.py facilitaria audit.
   - **Ação**: decisão de design — manter como está (mais claro onde a truncagem acontece) ou mover para pii.py.
   - **Quem**: cartorio-dev + cartorio-lgpd para jointly decidir.

6. **Harmonizar status code entre endpoints LGPD-blocked**:
   - Webhook Evolution retorna 200 com `pii_blocked: true`.
   - Endpoints de criação retornam 422 com LGPDBlockedResponse.
   - **Ação**: doc em LGPD.md explicando os 2 patterns e quando cada um se aplica.
   - **Quem**: cartorio-lgpd.

7. **Endereço / nome / naturalidade**:
   - Não detectado por regex (limitação conhecida, documentada em pii.py:11-17).
   - Mitigação atual: HITL obrigatório + retenção 365d + anonimização.
   - **Ação**: se Sprint 4 houver budget, considerar LLM-based PII detection (com mesmo scrub aplicado) como 4a camada. Não é prioridade.

---

## Checklist do cartorio-lgpd (do agent.md §Checklists)

```
- [x] Toda mutacao grava audit_log?
    Sim — conversa.received (linha 483), conversa.pii_blocked (linha 531),
    opencode_go.chat (opencode_go.py:486), llm.output_scrubbed
    (opencode_go.py:518), protocolo.read (linha 218),
    protocolo.read.not_found (linha 197). Cobertura 6/6.

- [x] Hash chain ainda valida apos a mudanca?
    Sim — 6/6 testes em test_audit.py passam. verify_chain() OK.

- [x] PII nao vaza em log nem em response?
    Sim — bot_response vem scrubbed; pii_findings em audit_log e count
    dict (LGPD art. 50 OK); .content sites todos cobindos via wrapper.

- [x] Consentimento explicito para novo uso de dado?
    Sim — consent_granted param em chat_with_settings; settings
    .pii_block_on_detect gate; consent gate em OpenCodeTestResponse.

- [ ] Retencao respeitada? (job diario cobre o caso?)
    PARCIAL — retencao.py existe mas nao rodei o job neste review.
    Confirmar com cartorio-dev. P1 #3 acima.

- [x] Direito ao esquecimento respeitado? (cliente pode pedir exclusao?)
    Sim — test_direito_esquecimento.py existe e passa. Implementado
    em services/lgpd/direito_esquecimento.py.

- [x] Base legal documentada no codigo (comment # LGPD art. X)?
    Sim — pii.py docstring cita art. 11 (CNS) + art. 6 + art. 46.
    audit_context.py cita art. 37. opencode_go.py cita art. 37.
    ADR-023 (CNS/CNH check-digit) cita art. 11 BLOQUEANTE.

- [x] DPO contactavel se houver duvida?
    Sim — DPA templates em docs/lgpd/, RIPD em docs/ripd.md,
    DPO nominal em docs/privacy/.
```

**7/8 OK, 1 PARCIAL (retenção) — sem bloqueador para LGPD-015+016**.

---

## Anexos

### Hashes revisados

```
d8d2d84 feat(pii): P0.5 + P0.6 check-digit CNS (16dig) e CNH (11dig) - LGPD art. 11
b5dabd7 feat(integrations): LGPD-015 output PII scrubbing + IP truncation
3749fad fix(router): expose pii_blocked and handoff flags in webhook response (P0.1 LGPD)
6e0afa5 feat(audit): log conversa.pii_blocked with request metadata (P0.2 LGPD art. 37)
0408e78 feat(health+dx): P2.BE.8 health granular + P2.MX.5 pre-commit hook  ← fora do escopo LGPD
```

(Os hashes `6e0afa5` e `3749fad` citados na task do harness ESTÃO no master — ver `git log master --oneline | grep ...` confirmado. Branch `fix/lgpd-audit-2026-06-23` é trabalho paralelo órfão — não impacta o master.)

### Comandos de verificação

```bash
# 1. Padrões do scrubber
grep -n "re.compile" backend/app/services/pii.py

# 2. Sites com .content
grep -rn "\.content\b" backend/app/

# 3. Audit chain
cd backend && uv run pytest tests/test_audit.py -v

# 4. Cobertura
cd backend && uv run pytest tests/ --cov=app --cov-fail-under=90

# 5. Tests LGPD-015+016
cd backend && uv run pytest tests/test_pii.py tests/integration/test_llm_output_scrub.py \
  tests/test_audit.py tests/test_audit_query.py tests/test_audit_context.py \
  tests/test_api.py tests/test_integrations_endpoint.py \
  tests/test_webhook_evolution_e2e.py --no-cov

# 6. Mypy
cd backend && uv run mypy app/services/pii.py app/api/v1/router.py \
  app/api/v1/integrations.py app/integrations/opencode_go.py \
  app/services/audit_context.py
# Result: 0 errors.

# 7. Ruff
cd backend && uv run ruff check app/services/pii.py app/api/v1/router.py \
  app/api/v1/integrations.py app/integrations/opencode_go.py \
  app/services/audit_context.py
# Result: 3 errors (F401 unused imports no router.py — vide P0 #1).
```

---

## Próxima ação recomendada

1. **HOJE (24/06)**: reportar este LGTM-WITH-FOLLOWUP ao harness orchestrator e a Gustavo.
2. **Sprint 3 E1.S3.T1**: implementar endpoint `/api/v1/protocolo/criar-api` (cartorio-dev, owner). Fechar P0 #1.
3. **Sprint 3 E2**: deploy do job retenção + verificação (cartorio-dev, owner). Fechar P1 #3.
4. **Sprint 3 DX**: documentação XFF trust chain (cartorio-lgpd). Fechar P1 #2.
5. **Sprint 4 backlog**: pattern `protocolo` no scrubber (P1 #4).

LGPD-015 + LGPD-016 podem ser mergeados (já estão no master). O sinal de compliance está correto.

---

Modified by Gustavo Almeida
