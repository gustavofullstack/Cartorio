# LGPD PR Review Checklist — TDD obrigatório para cartorio-dev

> **Para**: cartorio-dev (mvs_6cd75d5f...) ao implementar D26-D32
> **De**: cartorio-lgpd (Pietra) — gatekeeper
> **Aplicar**: EM CADA PR que toca `audit.py`, `pii.py`, `consentimento`, `retencao`, ou endpoints D26-D32
> **Base**: Lei 13.709/2018 + Provimento 74/2018 CNJ

## Regra de ferro

> Quem revisa compliance **NÃO implementa** o que revisa. SoD obrigatória.
> cartorio-dev implementa. cartorio-lgpd revisa. Mavis aprova.

---

## Checklist PR Review (audit/pii/consentimento/retencao)

```
## Pré-merge — marcar TODOS antes de pedir review

### LGPD art. 37 — Audit chain
- [ ] Toda mutação grava `AuditService.log()`?
- [ ] Hash chain ainda válida após a mudança? (rodar `pytest tests/test_audit_chain.py -v`)
- [ ] `verify_chain()` passa em CI?
- [ ] Campos obrigatórios: actor_id, actor_type, action, resource, payload, ip, user_agent, request_id, canal
- [ ] `request_id` presente (propagar via `request.state.request_id`)
- [ ] `canal` preenchido corretamente ("api_v1" para /api/v1/lgpd/*, "whatsapp", "telegram", etc.)

### LGPD art. 50 — Boas práticas (PII)
- [ ] PII NÃO vaza em log (`logger.info(f"...{cpf}...")` é BLOQUEIO P0)
- [ ] PII NÃO vaza em response (verificar Pydantic models — não retornar campos PII)
- [ ] `pii.scrub()` aplicado em TODO texto antes de LLM externa
- [ ] IP truncado (`/24` IPv4, `/48` IPv6) em response ao titular (D32)
- [ ] `cpf_hash` (não CPF puro) onde o hash é suficiente (D29)

### LGPD art. 7º I + 8º — Consentimento
- [ ] Consentimento explícito para novo uso de dado?
- [ ] Finalidade ESPECÍFICA (não genérica "para melhorar o serviço")
- [ ] Canal de coleta registrado (whatsapp/telegram/web/presencial/email)
- [ ] Direito de revogação comunicado na response (copy jurídica)

### LGPD art. 16 — Retenção
- [ ] Política de retenção respeitada (ver `LGPD-retention-policy.md`)?
- [ ] Job diário cobre o caso? (verificar `app/jobs/retention.py`)
- [ ] Soft delete > hard delete quando há retenção legal (D28)

### LGPD art. 18 — Direitos do titular
- [ ] Direito ao esquecimento respeitado? (cliente pode pedir exclusão via D28)
- [ ] Export portável funciona? (D29 retorna JSON estruturado art. 19)
- [ ] Correção com whitelist? (D30 — não deixa alterar cpf_hash, id, deleted_at)
- [ ] Revogação effective immediately? (D31 — side effects aplicados)
- [ ] Transparência permite titular ver próprio histórico? (D32)

### LGPD art. 33 — Transferência internacional
- [ ] Sub-processor com DPA assinado em `docs/lgpd/dpa_*.pdf`?
- [ ] Se STAGING ONLY (LGPD-014 DeepSeek pendente), flag no response?

### LGPD art. 41 — DPO
- [ ] DPO contactável se houver dúvida? (dpo@2notasudi.com.br)
- [ ] Endpoints administrativos restritos a DPO role? (D26)
- [ ] `require_dpo_role()` aplicado corretamente?

### Código
- [ ] Base legal documentada no código (comment `# LGPD art. X`)
- [ ] Conventional Commits; mensagem termina com `Modified by Gustavo Almeida`
- [ ] mypy 0 errors
- [ ] ruff check + ruff format limpos
- [ ] pytest coverage >= 90.18%
- [ ] OpenAPI docstring com LGPD art. + DPO contact
```

---

## Checklist LLM wrapper (se o endpoint toca LLM)

```
## Aplicar se endpoint chama LiteLLM/OpenClaw/OpenCode-Go

- [ ] Boundary 1 (input): `pii.scrub()` ANTES de `httpx.post(...)` ou `openai.ChatCompletion.create(...)`
- [ ] Boundary 2 (output): `scrub_llm_output(llm_resp.content)` ANTES de gravar/enviar ao cliente
- [ ] docstring diz "caller DEVE scrubar output também"
- [ ] response tem `output_pii_redacted_count: int`
- [ ] audit log tem `action='llm.output_scrubbed'` quando output passa por scrub
- [ ] testes mockam LLM ecoando CPF e assertam response NÃO contém CPF puro
```

---

## Heurística "test softened to match limited regex"

Suspeitar quando:
- 50 amostras de PII passam em <1 tentativa
- Asserções removidas (pytest fica verde sem testar o que importa)
- Regex de detecção fica mais fraco para o teste passar (ao invés de teste adaptar para regex forte)

Ações:
1. Verificar regex MELHOROU (não teste adaptado)
2. Verificar response carrega sinal de compliance (campo PII truncado?)
3. Verificar audit log distingue DETECÇÃO de BLOQUEIO

---

## Audit chain — estrutura obrigatória

```python
AuditService.log(
    db,
    actor_id="...",         # WHO (sem PII — usar user_id/cliente_id/escrevente:hash)
    actor_type="...",       # cliente | dpo | escrevente | system | bot
    action="...",           # WHAT (formato: domain.entity.verb)
    resource="...",         # ON WHAT (formato: entity:id ou entity:id:sub)
    payload={...},          # CONTEXT (dict, NUNCA string com PII puro)
    ip="...",               # request.client.host (completo, truncado auto)
    user_agent="...",       # request.headers.get("user-agent")
    request_id="...",       # request.state.request_id (propagar do middleware)
    canal="...",            # api_v1 | whatsapp | telegram | web
)
```

**Validações automáticas (CI)**:
```python
def test_audit_entry_no_pii_in_actor_id():
    """actor_id NUNCA contém CPF/RG/email/telefone."""
    for entry in audit_log_entries:
        assert not re.search(r"\d{3}\.\d{3}\.\d{3}-\d{2}", entry.actor_id)
        assert "@" not in entry.actor_id  # email
```

---

## Checklist retenção (referência rápida)

| Dado | Retenção | Ver |
|---|---|---|
| Consentimento | enquanto relação + 5y | `LGPD-retention-policy.md §3` |
| Audit log | 5 anos | `LGPD-retention-policy.md §4` |
| Payload export D29 | até revogação + TTL 90d download | `LGPD-retention-policy.md §5` |
| Conversa scrubbed | 365 dias | `LGPD-retention-policy.md §6` |
| IP completo | 2 anos, depois trunca | `LGPD-retention-policy.md §7` |

---

## Checklist incident (se PR é bug fix de incidente)

```
- [ ] Detectar (alerta, reclamação, auditoria)
- [ ] Conter (parar vazamento — bloquear endpoint, rotacionar secret)
- [ ] Avaliar (que dados, quantos titulares, qual severidade)
- [ ] Notificar DPO + Gustavo em até 24h
- [ ] Se risco >= médio: notificar ANPD em até 72h (LGPD art. 48)
- [ ] Notificar titulares afetados
- [ ] Remediar (deploy fix)
- [ ] Documentar timeline + lição + memória
```

---

## Quem aprova o quê

| PR toca | Implementa | Revisa | Aprova |
|---|---|---|---|
| `audit.py`, `pii.py`, `consentimento`, `retencao`, D26-D32 | cartorio-dev | **cartorio-lgpd** | Mavis |
| Workflow N8N com PII | cartorio-n8n | **cartorio-lgpd** | Mavis |
| Texto de política/copy jurídica | cartorio-lgpd | (auto) | Mavis |
| Mudança em DPA | cartorio-lgpd + jurídico externo | Gustavo | Gustavo |

Modified by cartorio-lgpd (Pietra root mvs_97612f6bb1824cbdaf7c134fa34bf057)