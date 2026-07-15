# Postman — Cartorio API v1

> Collection Postman v2.1.0 + Environment production + Newman CLI.
> Missao F6 [P2] / Squad cartorio-front / 2026-07-15.

## Arquivos

- `Cartorio_API_v1.postman_collection.json` — 73 endpoints catalogados em `.brain/api-specs/catalog.py`.
- `Cartorio_Env.production.postman_environment.json` — Variaveis production (base_url, tokens, API keys). **Todos os secrets sao placeholders**.
- Este `README.md` — Guia de import + Newman CLI.

## Importar no Postman (UI)

### Passo 1 — Collection

1. Abrir Postman (v9+).
2. File > Import.
3. Selecionar arquivo `Cartorio_API_v1.postman_collection.json`.
4. Confirmar import (modo default = Collection v2.1.0).
5. Collection aparece em sidebar esquerda como "Cartorio API v1" com 16 folders:
   - Health (10)
   - Telegram (5)
   - WhatsApp (4)
   - LGPD (11)
   - Audit (4)
   - Brain (6)
   - OpenClaw (9)
   - Protocolo (6)
   - Cliente (4)
   - Emolumento (3)
   - Atendimento (4)
   - Auth (2)
   - Integrations (5)
   - Webhooks (2)
   - Observability (2)
   - Admin (4)
   - API v2 alpha (4)

### Passo 2 — Environment

1. File > Import.
2. Selecionar arquivo `Cartorio_Env.production.postman_environment.json`.
3. Environment aparece em Environments (sidebar esquerda).
4. **Selecionar** o environment "Cartorio Env - Production" no dropdown superior direito.

### Passo 3 — Configurar secrets (LOCAL only)

1. Clicar no olhinho (eye icon) ao lado do environment dropdown > Edit.
2. Substituir cada `REPLACE_WITH_*` pelo valor real (vault/Supabase/env).
3. **NAO commitar** este environment modificado.

## Newman CLI (CI / automated runs)

### Install

```bash
npm install -g newman
# ou
npx newman --version
```

### Rodar contra production

```bash
newman run postman/Cartorio_API_v1.postman_collection.json \
  --environment postman/Cartorio_Env.production.postman_environment.json \
  --reporters cli,html \
  --reporter-html-export postman/newman-report.html
```

### Rodar subset (folder LGPD)

```bash
newman run postman/Cartorio_API_v1.postman_collection.json \
  --environment postman/Cartorio_Env.production.postman_environment.json \
  --folder LGPD \
  --reporters cli
```

### Rodar contra local dev

```bash
newman run postman/Cartorio_API_v1.postman_collection.json \
  --env-var "base_url=http://localhost:8000" \
  --folder Health
```

## Seguranca

- **NUNCA** commitar valores reais de `telegram_bot_token`, `x_api_key_dpo`, `x_api_key_n8n`, `openclaw_gateway_token`, `jwt_dpo`.
- Todos os secrets do environment estao marcados como `type: "secret"` no Postman (mascarados na UI).
- O `scripts/check_no_literal_keys.py` (raiz do repo) bloqueia commits com chaves literais (`sk-*`, `lin_api_*`, etc).
- Para revogar: rotacionar env vars no Easypanel + invalidar JWT DPO via `POST /api/v1/auth/login`.

## Cobertura

| Categoria | Endpoints | Auth |
|-----------|-----------|------|
| Health | 10 | Publico |
| Telegram | 5 | Webhook: HMAC / Admin: X-API-Key |
| WhatsApp | 4 | Webhook: Publico / Test send: X-API-Key |
| LGPD | 11 | X-API-Key + JWT DPO |
| Audit | 4 | X-API-Key |
| Brain | 6 | Publico (dev tooling) |
| OpenClaw | 9 | Bearer token gateway / Admin RPC: X-API-Key |
| Protocolo | 6 | POST: X-API-Key / GET: Publico |
| Cliente | 4 | POST/PATCH/DELETE: X-API-Key |
| Emolumento | 3 | Publico |
| Atendimento | 4 | POST: X-API-Key / GET: Publico |
| Auth | 2 | Publico (login/refresh) |
| Integrations | 5 | X-API-Key |
| Webhooks | 2 | Publico (HMAC verify) |
| Observability | 2 | Prometheus: Publico / N8N: X-API-Key |
| Admin | 4 | X-API-Key |
| API v2 alpha | 4 | X-API-Key (cursor Relay) |

**Total**: 73 endpoints.

Modified by Gustavo Almeida.