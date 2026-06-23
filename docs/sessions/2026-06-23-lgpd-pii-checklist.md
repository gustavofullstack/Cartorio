# LGPD Review Checklist - 7 PII Workflows E6.S2

> Pre-fill para cartorio-lgpd (mvs_d4fa1b1a) review 24h pos-merge cartorio-dev PR LGPD-015/016.
> Generated 2026-06-23 19:32 BRT by cartorio-n8n.

## WFs PII (7) — gate activate=true

| # | WF | ID N8N | Trigger | PII data flow | Status |
|---|----|--------|---------|---------------|--------|
| 13 | OpenClaw Chat Bridge | 0cw3YxcB0msB0KRC | webhook `/openclaw-in` | OpenClaw msg -> PII scrub inline -> API /webhook/evolution (com pii_blocked flag) | draft |
| 15 | Session Sync | h7Qf9AnmUkvAfnmO | cron 5min | API GET /sessao/list-active (cliente_id) -> sync DB | draft |
| 17 | Prospeccao Send WhatsApp | LIsYz9xOm8InBTlG | cron 09:00 diario | Supabase leads (telefone) -> msg WhatsApp com opt-out PARAR/SAIR | draft |
| 19 | Cliente Criado | Iw2bxvzhTlUVA3qA | webhook `/cliente-criado` | novo cliente -> boas-vindas LGPD (SIM/NAO/PARAR) + Chatwoot se sem consent | draft |
| 20 | Protocolo Criado | yAGQZUyMimSEatXn | webhook `/protocolo-criado` | protocolo -> WhatsApp notify + Chatwoot escrevente + audit log | draft |
| 23 | LGPD Esqueci | TtD6qS6LCexwhMke | webhook `/lgpd-esqueci` | cliente_id -> DELETE /cliente/{id} (LGPD art 18 VI) + cascade + audit | draft |
| 27 | Welcome First Time | NlGoGgAlY9ln8T0s | webhook `/welcome-first` | primeira msg -> boas-vindas LGPD (SIM/NAO/PARAR) + log Supabase | draft |

## LGPD-by-design checks por WF

### Padrão PII Scrub (todos os 7)
- Code node JS PII Scrubber inline (espelho de `backend/app/services/pii.py`)
- Regex: cpf, rg, phone_br, email, cnpj, placa, data, pis, titulo_eleitor, cep, cartao
- Output: `{scrubbed, pii_blocked, pii_redaction_count, pii_findings}`
- Nunca passa msg original (raw) para API ou LLM

### Padrão X-API-Key auth (todos os 7)
- Header `X-API-Key: {{ $env.CARTORIO_API_KEY }}`
- Cred `cartorio-api-key` (ADNkyTP2e6uYskUZ) — type httpHeaderAuth
- Se 401, no-op silencioso (não vaza dados)

### Padrão Audit Log (todos os 7)
- POST /api/v1/audit/log com `actor: n8n-wf{N}`, `action: {wf-specific}`, `target: {cliente_id/protocolo}`
- RequestContextMiddleware (request_id, ip /24, user_agent, X-Canal) é backend-side; WF nao precisa duplicar

### Padrão PII touchpoints por WF
- **#13 OpenClaw Chat Bridge**: msg body (PII scrub inline) + sender phone
- **#15 Session Sync**: cliente_id (PII), sessao_id (synthetic, OK)
- **#17 Prospeccao Send WhatsApp**: telefone (PII) + msg body (public data only, sem PII)
- **#19 Cliente Criado**: cliente_id (PII) + telefone (PII) + consent_granted
- **#20 Protocolo Criado**: cliente_id (PII) + telefone (PII) + protocolo numero (publico)
- **#23 LGPD Esqueci**: cliente_id (PII) + motivo (categorical, no PII)
- **#27 Welcome First Time**: telefone (PII) + nome (PII optional)

## Compliance checklist pre-merge

### Backend deps (cartorio-dev) — REQUIRED pre-activate
- [ ] LGPD-015 (output scrub boundary) merged — eta 19:42 BRT
- [ ] LGPD-016 (CNS+CNH P0.4) merged — eta 19:42 BRT
- [ ] RequestContextMiddleware (116afe0) ativo em prod
- [ ] LGPDBlockedResponse copy juridica (116afe0) plugada
- [ ] DELETE /cliente/{id} endpoint deployed (ea24216) — para WF #23
- [ ] Audit log middleware (116afe0) gravando 100% mutacoes

### N8N deps (cartorio-n8n) — DONE
- [x] 18 E6 WFs criados em flow.2notasudi.com.br
- [x] 11 non-PII ATIVOS
- [x] 7 PII DRAFT (este checklist)
- [x] Creds: cartorio-api-key, opencode-go, supabase-rest, redis-cartorio, openclaw-gateway OK
- [x] $env.X (zero hardcoded secrets) — auditoria limpa
- [x] Chatwoot via httpRequest (workaround ate node oficial funcionar)
- [x] Evolution via httpRequest (idem)

### Reviewers (cartorio-lgpd mvs_d4fa1b1a) — TODO
- [ ] Confirmar padrao PII scrub inline JS = match backend/app/services/pii.py
- [ ] Confirmar 7 WFs PII tem defense-in-depth (scrub + audit + X-API-Key)
- [ ] Confirmar WF #17 opt-out PARAR/SAIR keyword handling
- [ ] Confirmar WF #19/27 LGPD consent capture (SIM/NAO/PARAR)
- [ ] Confirmar WF #23 LGPD art 18 VI direito ao esquecimento (hard delete sem protocolo, soft delete com)
- [ ] Cross-coord com cartorio-dev pra confirmar endpoints deployed (DELETE /cliente, sessao APIs)

## Riscos residuais (post-activate)

1. **Opencode-Go API key**: WF #14 fallback depende de key real no env. Se Gustavo nao configurar ate Sprint E6.S10, WF #14 fica em "degraded" (responde mas com 401).
2. **chatwoot-api cred type**: Atualmente GENERICA httpHeaderAuth, ideal seria ChatWootApi type (pendente Gustavo UI).
3. **Evolution instance cartorio-2notas**: PROVISIONED mas QR scan so Sprint E6.S10.T1. WFs 17/18/19/20/27 vao falhar envio ate QR scan.
4. **IF node main[1] empty array**: pre-existing bug em 25-protocolo-concluido-pdf.json (nao E6), nao bloqueia 7 PII.

## Activation sequence (pos cartorio-lgpd GO)

```
1. cartorio-lgpd (mvs_d4fa1b1a) review 7 WFs (24h) -> GO
2. cartorio-n8n: 7x POST /workflows/{id}/activate (sem body)
3. Smoke test: webhook health check em cada um
4. Notify parent: 7 PII WFs ATIVOS
5. Update .harness/TASKS.md E6.S2.T1-T18 [x]
6. Cross-coord com ceo-assistant pra prospeccao Wave 1 (#16/17/18)
```

Modified by Gustavo Almeida (via cartorio-n8n 19:33 BRT)
