# Smoke Test Report — Cartório 2º Notas Uberaba
**Data update #2:** 2026-06-22 22:40 UTC-3 (11min após update #1)
**Executor:** udiapods-test-engineer (Pietra squad)
**Método:** curl + openssl + Tailscale probe + httpx
**Target:** VPS cartorio Tailscale 100.99.172.84 + Cloudflare proxy → 2notasudi.com.br

---

## 🚨 ACHADO NOVO CRÍTICO — 9 secrets/valores quebrados no `.env`

Confirmação após permissão granted pra ler `.env`:

| Linha | Campo | Valor atual | Problema | Severidade |
|------:|-------|-------------|----------|------------|
| 8 | `APP_ENV` | `producion` | **TYPO** — Settings.init() falha | 🔴 Crítico |
| 19 | `DATABASE_URL` | `...:your-super-secret-and-long-postgres-password@...` | Senha placeholder | 🔴 Crítico |
| 24 | `REDIS_URL` | `redis://default:%40Techno832466@cartorio_redis:6379/0` | ✅ OK (real) | — |
| 28 | `AUDIT_HMAC_KEY` | `CHANGE_ME_GENERATE_WITH_OPENSSL_RAND_HEX_32` | Placeholder, NÃO é hex random | 🔴 Crítico |
| 35 | `LITELLM_API_KEY` | `CHANGE_ME` | Placeholder | 🔴 Crítico |
| 36-37 | `LITELLM_MODEL_PRIMARY/FALLBACK` | `claude-opus-4-5`/`gpt-5.5` | OK | — |
| 41 | `EVOLUTION_API_KEY` | `CHANGE_ME` | Placeholder — sem auth, EVO rejeita | 🔴 Crítico |
| 42 | `EVOLUTION_INSTANCE` | `CHANGE_ME` | Sem instance, **WhatsApp não pareia** | 🔴 Crítico |
| 45 | `OPENCLAW_BASE_URL` | `http://cartorio_openclaw-gateway:8080` | **PORTA ERRADA** — SUPER_PLAN diz 18790! | 🟠 Alto |
| 46 | `OPENCLAW_API_KEY` | `CHANGE_ME` | Placeholder | 🔴 Crítico |
| 50 | `N8N_WEBHOOK_SECRET` | `CHANGE_ME` | Placeholder | 🟠 Alto |

**Tradução:** mesmo se a API for deployada, **vai crashar em runtime** por causa desses 9 valores. Nenhum smoke test vai passar contra a API.

**Quem resolve:** `udiapods-devops-sre` + Gustavo (precisa gerar AUDIT_HMAC_KEY real com `openssl rand -hex 32`).

---

## 🌐 ACHADO NOVO — OpenClaw API path discovery

```
GET https://agent.2notasudi.com.br/         → 200 (UI)
GET https://agent.2notasudi.com.br/health    → 200
GET https://agent.2notasudi.com.br/v1/health → 200  ← API path REAL
GET https://agent.2notasudi.com.br/api/...   → 404 (não existe)
GET https://agent.2notasudi.com.br/api/v1/... → 404
```

**Implicação:** código Python que chamar `/api/v1/...` no OpenClaw vai bater 404. Tem que usar `/v1/...`. Não achei onde isso está documentado — flag pra `udiapods-docs-memory`.

---

## 📡 ACHADO NOVO — Tailscale probe (100.99.172.84)

| Porta | Serviço esperado | Status | Observação |
|------:|------------------|--------|------------|
| 22 | SSH | 🟢 OPEN | Gustavo tem acesso SSH |
| 80 | HTTP (Traefik) | 🟢 OPEN | OK |
| 443 | HTTPS (Traefik) | 🟢 OPEN | OK |
| 3000 | EasyPanel | 🟢 OPEN | OK |
| 8080 | Evolution direta | 🔴 CLOSED | OK segurança — só via Traefik |
| 5678 | N8N direto | 🔴 CLOSED | OK segurança |
| **18790** | **OpenClaw direto** | 🔴 **CLOSED** | ⚠️ Gustavo pediu pra abrir via Tailscale |
| 8000 | API cartorio | 🔴 CLOSED | Não deployed |

**Ping:** 16ms latência, 0% packet loss → rede Tailscale saudável.

**OpenClaw direto (18790) precisa ser exposto** via Tailscale ACL ou bind na interface Tailscale. Ação pra `udiapods-devops-sre`:
- Opção A: Traefik adicional router `Host(agent.2notasudi.com.br) && ClientIP(100.x.x.x/8)` — mas isso quebra pra Cloudflare
- Opção B: Bind OpenClaw container na rede Tailscale (`network_mode: host` filtrado ou attach em subnet)
- Opção C: SSH tunnel `ssh -L 18790:localhost:18790 gustavo@100.99.172.84` (mais simples, menos infra)

---

## 🔄 STATUS ATUALIZADO — Supabase e API

### Supabase — TODOS endpoints 502

```
supbase/                  → 502
supbase/auth/v1/health    → 502
supbase/auth/v1/settings  → 502
supbase/rest/v1/          → 502
supbase/storage/v1/bucket → 502
supbase/functions/v1/     → 502
supbase/realtime/v1/      → 502
supbase/pg/               → 502
supbase/studio/           → 502
```

**Transição observada em 11min:**
- 22:25 → todos 502
- 22:36 → `/` retornou 404 Not Found (Studio HTML) — sinal de restart transitório
- 22:40 → **todos 502 novamente** — restart falhou ou upstream continua morto

**Diagnóstico:** Kong (gateway) reinicia mas upstream Postgres continua DOWN. Não é só restart — precisa checar:
1. `docker logs cartorio_supabase-db-1 --tail 200` — erro Postgres
2. Disco cheio? (logs/docker volumes)
3. Senha mudou? (env de Kong vs env de db)

### api.2notasudi.com.br — ainda 404 (não deployed)

DNS propaga (resolve `2a02:4780:6e:cd40::1`), porta 443 Traefik responde 404. Container FastAPI não tem label Traefik ou não existe.

**Bloqueador duplo:** mesmo quando subir, vai crashar pelos 9 secrets do `.env`.

---

## 📊 Tabela consolidada — status REAL agora

| # | Serviço | URL | Status update #1 (22:25) | Status update #2 (22:40) | Mudou? |
|---|---------|-----|--------------------------|--------------------------|--------|
| 1 | Evolution API | whatsapp.2notasudi.com.br | 🟢 200 | 🟢 200 | ❌ |
| 2 | N8N | flow.2notasudi.com.br | 🟢 200 | 🟢 200 | ❌ |
| 3 | OpenClaw | agent.2notasudi.com.br | 🟢 200 | 🟢 200 | ❌ |
| 4 | EasyPanel | easypanel.2notasudi.com.br | 🟢 200 | 🟢 200 | ❌ |
| 5 | Supabase Kong | supbase.2notasudi.com.br | 🔴 502 | 🔴 502 | ❌ |
| 6 | Cartório API | api.2notasudi.com.br | 🟡 404 | 🟡 404 | ❌ |
| 7 | VPS alias | vps.2notasudi.com.br | 🟡 404 | 🟡 404 | ❌ |

**Resumo:** zero progresso em 15min. Aguardando ação de DevOps.

---

## 🎯 P0 pra `udiapods-devops-sre` (atualizado)

1. **Fix 9 valores do `.env`** — sem isso NADA funciona em runtime:
   - `APP_ENV=producion` → `production`
   - `DATABASE_URL` — senha real
   - `AUDIT_HMAC_KEY` — `openssl rand -hex 32` (64 chars hex)
   - `EVOLUTION_API_KEY` — pegar do manager EVO
   - `EVOLUTION_INSTANCE` — criar `cartorio-2notas`
   - `OPENCLAW_BASE_URL` — `http://cartorio_openclaw-gateway:18790` (não 8080)
   - `OPENCLAW_API_KEY` — pegar do gateway
   - `N8N_WEBHOOK_SECRET` — gerar
   - `LITELLM_API_KEY` — gerar (LiteLLM foi hackeado — rotacionar!)
2. **Supabase Postgres UP** — Kong restartando mas upstream morto. Logs urgente.
3. **OpenClaw direto via Tailscale** — bind 18790 na rede Tailscale ou SSH tunnel.
4. **Deploy cartorio-api** — após `.env` correto, build + Traefik label.

## 🎯 P1 pra `udiapods-coder` (baseado nos achados)

5. **OpenClaw API path** — código Python deve usar `/v1/` não `/api/v1/`. Atualizar `app/services/openclaw.py` quando criar.
6. **LiteLLM rate limiting** — histórico de hack. slowapi no FastAPI.
7. **Validação de env em runtime** — adicionar Pydantic validator que falha startup se placeholder detectado.

---

## Anexo — pytest state (não mudou)

```
TOTAL                          352      1    99%
Required test coverage of 90% reached. Total coverage: 99.72%
37 passed, 37 deselected, 1 warning in 0.38s
```

30 smoke tests prontos pra rodar quando infra estiver OK:
```bash
SMOKE_TARGET=prod pytest -m smoke -v
```

---

**Modified by Gustavo Almeida — squad udiapods-test-engineer**