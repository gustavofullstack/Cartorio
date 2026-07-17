# Webhook HMAC Rotation — 90 dias (G7.10.T3)

**Secrets cobertos**

| Secret | Header | Validator |
|--------|--------|-----------|
| `EVOLUTION_WEBHOOK_SECRET` (+ `_PREV`) | `X-Signature` / `X-Hub-Signature-256` | `validate_evolution_signature` |
| `TELEGRAM_WEBHOOK_SECRET` | `X-Telegram-Bot-Api-Secret-Token` | `hmac.compare_digest` em telegram.py |
| `CARTORIO_API_KEY` | `X-API-Key` | inter-service N8N↔API |
| `AUDIT_HMAC_KEY` | (server-side) | `AuditService._compute_hmac` — **rotação com cuidado** (chain) |

---

## Rotação Evolution (zero-downtime)

1. Gerar novo secret: `openssl rand -hex 32`
2. Easypanel / env:
   - `EVOLUTION_WEBHOOK_SECRET_PREV=<valor_atual>`
   - `EVOLUTION_WEBHOOK_SECRET=<novo>`
3. Redeploy API (grace: ambos secrets aceitos).
4. Atualizar Evolution Manager / webhook config com o **novo** secret.
5. Smoke: enviar msg teste ou curl assinado.
6. Após 24–72h estável: limpar `EVOLUTION_WEBHOOK_SECRET_PREV`.
7. Audit log: `action=secrets.rotated` (manual entry DPO se aplicável).

**Cadência:** 90 dias (ADR-017 credential rotation).

---

## Rotação Telegram

1. BotFather não rota secret_token sozinho — gerar novo e `setWebhook` com `secret_token`.
2. Atualizar env API **antes** do setWebhook (ou downtime curto).
3. Validar `GET /api/v1/telegram/webhook/info`.

---

## O que NÃO fazer

- Nunca commitar secrets (pre-commit `secrets_scan.py`).
- Nunca rotacionar `AUDIT_HMAC_KEY` sem plano de dual-key verify (quebra chain verify se misturar eras).
- Nunca logar signature headers ou secrets.

---

## Testes

```bash
cd backend && uv run pytest -q --no-cov tests/test_evolution_hmac.py
```

Cobertura: válido / inválido / ausente / `sha256=` prefix / **PREV rotation** / prev-only.

---

**Modified by Gustavo Almeida + cartorio-security — G7 Wave 16**
