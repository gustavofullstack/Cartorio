# LobeChat — Runbook de Produção (F4 [P1] RETRY 2026-07-15 14:45 BRT)

> Guia operacional para colocar o LobeChat em produção roteando para o **OpenClaw Gateway** (em vez do placeholder `OPENAI_API_KEY=sk-xxxx`).
> Cross-ref: `STATUS.md` (snapshot F4 RETRY) · `SETUP.md` (UI import) · Lesson 170 (CORS/timeout fix) · Lesson 177 (OpenClaw E8 catalog) · Lesson 179 (DNS runbook F4 SRE) · Lesson 178 (esta missão).

---

## TL;DR

LobeChat hoje está **UP** mas com `OPENAI_API_KEY=sk-xxxx` (placeholder) → qualquer chamada de chat retorna **401 Unauthorized** ou mensagem de erro. Para entrar em produção real, precisamos:

1. Apontar LobeChat para o **OpenClaw Gateway** (`https://agent.2notasudi.com.br/v1`)
2. Trocar o bearer (`@Techno832466` → operator token novo)
3. Importar o agente "Cartório 2º Notas de Uberlândia" via UI (5 cliques)
4. Expor DNS público branded (`lobe.2notasudi.com.br`)
5. Ativar monitor Uptime Kuma (já configurado — `monitors.json`)

> **Escopo desta doc**: documentação + templates. NÃO mexe em backend Python. NÃO rotaciona chaves. NÃO roda SSH no VPS.

---

## Arquitetura target

```
Cliente (escrevente)
       │
       ▼ HTTPS
lobe.2notasudi.com.br ───► Traefik ───► LobeChat container (:3210)
                                              │
                                              │ Custom OpenAI provider
                                              ▼
                              agent.2notasudi.com.br/v1 ───► OpenClaw Gateway
                                                                  │
                                                                  ▼
                                                          LiteLLM Proxy
                                                          (7 free providers)
```

**Importante**: LobeChat é independente do OpenClaw. Eles conversam via protocolo **OpenAI-compatible**. Não há registry compartilhado — o que aparece em LobeChat é o que foi **manualmente configurado na UI** (Settings → LLM Providers → + Add Provider).

---

## 3 passos para Gustavo (deploy real)

### Passo 1 — Gerar operator token OpenClaw

```bash
# SSH no VPS (alternativa: OpenClaw Control UI)
ssh deploy@100.99.172.84
docker exec -it openclaw-gateway /bin/sh

# Dentro do container:
openclaw operator create --name lobechat --scopes chat:write,models:read
# Output: bearer_token = "<novo-token-seguro>"
```

**Ação**: salvar o token num password manager (1Password / Bitwarden). O token atual `@Techno832466` será revogado após deploy.

> **Cross-ref**: Lesson 177 (`lesson-177-openclaw-e8-finalize-2026-07-14.md`) — operator token atual tem `hello-ok.auth.scopes=[]` (health-only). Para Gustavo ter permissões de `agents.list/create` + `models.list`, precisa gerar token com scopes corretos via `openclaw.json` no `/home/node/.openclaw/`.

---

### Passo 2 — Atualizar env vars no EasyPanel

1. Acesse o painel EasyPanel: `https://easypanel.2notasudi.com.br`
2. Projeto: **cartorio** → serviço: **lobechat**
3. Aba **Environment** → edite as variáveis:

| Variável | Valor novo |
|----------|------------|
| `OPENAI_API_KEY` | `<novo-operator-token-do-passo-1>` |
| `OPENAI_PROXY_URL` | `https://agent.2notasudi.com.br/v1` |
| `OPENAI_MODEL_LIST` | `openclaw,openclaw/default,openclaw/main` |

4. **Save** → EasyPanel vai disparar **restart automático** do container.

---

### Passo 3 — Importar o agente "Cartório 2º Notas de Uberlândia"

Seguir o guia `infra/lobechat/SETUP.md` (5 passos UI):

1. Login em `https://cartorio-lobechat.dfgdxq.easypanel.host/chat` (ou branded `lobe.2notasudi.com.br` após DNS)
2. Settings → LLM Providers → + Add Provider (Custom OpenAI) com base URL `https://agent.2notasudi.com.br/v1` e API key do Passo 1
3. Settings → Agents → Import from JSON → anexar `infra/lobechat/agent_cartorio_import.json`
4. Validar: New Chat → selecionar modelo `openclaw/main` → enviar `oi`
5. Smoke tests (A: emolumento, B: agendamento, C: PII handoff, D: jurídica handoff) — ver SETUP.md seção "Testes adicionais"

---

## Expor DNS público (Traefik router YAML)

> **Esta seção é referência para F4 SRE/dev**. Gustavo executa Passo A (DNS); SRE ou dev commita o YAML em `infra/traefik/dynamic/lobe.yml`.

### Opção A — Subdomínio `lobe.2notasudi.com.br` (recomendado, curto)

**Pré-requisito**: Gustavo criar **A record** no Cloudflare:

```
Tipo: A
Nome: lobe
Conteúdo: 187.77.236.77
Proxy: DNS only (cinza, não laranja — Traefik faz TLS)
TTL: Auto
```

> **Runbook DNS UI**: ver `infra/dns/CLOUDFLARE_RUNBOOK.md` (F4 SRE Lesson 179) — 5min de UI. Padrão idêntico ao que foi usado para chatwoot/n8n/supabase.

Depois, commitar em `infra/traefik/dynamic/lobe.yml`:

```yaml
http:
  routers:
    lobe:
      rule: "Host(`lobe.2notasudi.com.br`)"
      service: lobe
      tls:
        certResolver: letsencrypt
      entryPoints:
        - websecure
      middlewares:
        - secure-headers@file
        - rate-limit-public@file
  services:
    lobe:
      loadBalancer:
        servers:
          - url: "http://lobechat:3210"
        passHostHeader: true
```

Aplicar:

```bash
ssh deploy@100.99.172.84
docker exec traefik traefik --configFile=/etc/traefik/traefik.yml --check
# se OK, recarregar config dinamica
curl -X POST http://localhost:8080/api/loadconfig  # se hot-reload habilitado
# OU restart limpo
docker service update --force traefik_traefik
```

### Opção B — Subdomínio `lobechat.2notasudi.com.br`

Mesmo YAML acima, trocar `lobe` → `lobechat` na rule + nome do service.

**Decisão fica com Gustavo** (curto / longo / com/sem hyphen). Recomendação: `lobe` (matches Lesson 170 monitor URL).

---

## [HOLD-GUSTAVO] Checklist pré-deploy

- [ ] DNS decidido (`lobe` ou `lobechat`)
- [ ] A record Cloudflare criado → `187.77.236.77` (proxy DNS only)
- [ ] Operator token OpenClaw gerado (com scopes `chat:write,models:read`)
- [ ] Env EasyPanel atualizado (`OPENAI_API_KEY`, `OPENAI_PROXY_URL`, `OPENAI_MODEL_LIST`)
- [ ] Container LobeChat reiniciado e validando `OPENAI_API_KEY` no `/api/health`
- [ ] Provider Custom OpenAI registrado na UI (base URL `agent.2notasudi.com.br/v1`)
- [ ] Agente "Cartório 2º Notas" importado via JSON
- [ ] Smoke test `oi → saudação cartorária` passou
- [ ] Traefik router commitado em `infra/traefik/dynamic/lobe.yml`
- [ ] Monitor Uptime Kuma ativo (ver `monitors.json`)
- [ ] SUI_CHECKLIST atualizado: "SUI4: LobeChat production deploy" ✅

---

## Monitoramento

Já integrado ao stack Uptime Kuma (`infra/lobechat/monitors.json`):

- **HTTP probe** `https://lobe.2notasudi.com.br/api/health` (esperado 200)
- **Fallback**: `https://cartorio-lobechat.dfgdxq.easypanel.host/api/health`
- **Alertas Telegram** para Gustavo (`TELEGRAM_CHAT_ID_DPO=6682284055`) em caso de DOWN > 2min
- **Interval**: 60s · **Retry**: 30s · **Max retries**: 3 · **Timeout**: 10s

Para validar após deploy:

```bash
curl -fsS https://lobe.2notasudi.com.br/api/health
# Esperado: {"status":"ok"}
```

---

## Troubleshooting

| Sintoma | Causa | Ação |
|---------|-------|------|
| 401 Unauthorized no chat | `OPENAI_API_KEY` placeholder ou expirado | Verificar env EasyPanel, ver Passo 2 |
| Model `openclaw/main` não aparece | `OPENAI_MODEL_LIST` faltando | Adicionar env var |
| LobeChat abre mas não responde | OpenClaw upstream offline | `curl https://agent.2notasudi.com.br/v1/models` |
| Erro CORS no console | OpenClaw allow-origin faltando lobe domain | Adicionar em OpenClaw env `ALLOWED_ORIGINS` (já coberto por `.2notasudi.com.br` Lesson 170 fix) |
| DNS não resolve | Cloudflare A record não criado | Passo DNS Gustavo (runbook `infra/dns/CLOUDFLARE_RUNBOOK.md`) |
| TLS cert não emitido | Let's Encrypt rate-limit ou DNS não propagado | Aguardar 5min, ver logs Traefik |
| Latência > 30s | OpenClaw upstream timeout | Lesson 170 fix já tem 30s; verificar `agent.2notasudi.com.br` health |

---

## Cross-refs (mapa de navegação)

- [`infra/lobechat/STATUS.md`](file:///Users/gustavoalmeida/projetos/Cartorio/infra/lobechat/STATUS.md) — snapshot F4 RETRY 2026-07-15 14:45 BRT
- [`infra/lobechat/SETUP.md`](file:///Users/gustavoalmeida/projetos/Cartorio/infra/lobechat/SETUP.md) — passo-a-passo UI (5 cliques)
- [`infra/lobechat/agent_cartorio_import.json`](file:///Users/gustavoalmeida/projetos/Cartorio/infra/lobechat/agent_cartorio_import.json) — schema v1 export
- [`infra/lobechat/monitors.json`](file:///Users/gustavoalmeida/projetos/Cartorio/infra/lobechat/monitors.json) — Uptime Kuma monitor
- [`infra/openclaw-agent/workspace/SOUL.md`](file:///Users/gustavoalmeida/projetos/Cartorio/infra/openclaw-agent/workspace/SOUL.md) — persona source
- [`infra/dns/CLOUDFLARE_RUNBOOK.md`](file:///Users/gustavoalmeida/projetos/Cartorio/infra/dns/CLOUDFLARE_RUNBOOK.md) — DNS runbook (F4 SRE)
- [`infra/dns/CLOUDFLARE_DNS_RECORDS.md`](file:///Users/gustavoalmeida/projetos/Cartorio/infra/dns/CLOUDFLARE_DNS_RECORDS.md) — DNS canonico 10 hosts
- [`infra/traefik/ROUTERS_PENDENTES.yaml`](file:///Users/gustavoalmeida/projetos/Cartorio/infra/traefik/ROUTERS_PENDENTES.yaml) — Traefik routers template
- [`backend/app/api/v1/telegram.py`](file:///Users/gustavoalmeida/projetos/Cartorio/backend/app/api/v1/telegram.py) — handler Telegram (não mexe)
- [`.harness/memory/lesson-170-lobechat-agent-fix-2026-07-14.md`](file:///Users/gustavoalmeida/projetos/Cartorio/.harness/memory/lesson-170-lobechat-agent-fix-2026-07-14.md) — CORS+timeout fix
- [`.harness/memory/lesson-177-openclaw-e8-finalize-2026-07-14.md`](file:///Users/gustavoalmeida/projetos/Cartorio/.harness/memory/lesson-177-openclaw-e8-finalize-2026-07-14.md) — OpenClaw E8 catalog
- [`.harness/memory/lesson-179-dns-cloudflare-fixos-2026-07-15.md`](file:///Users/gustavoalmeida/projetos/Cartorio/.harness/memory/lesson-179-dns-cloudflare-fixos-2026-07-15.md) — DNS runbook F4 SRE
- [`.harness/memory/lesson-178-lobechat-telegram-snapshot-2026-07-15.md`](file:///Users/gustavoalmeida/projetos/Cartorio/.harness/memory/lesson-178-lobechat-telegram-snapshot-2026-07-15.md) — esta missão F4 RETRY
- [`.harness/SUI_CHECKLIST.md`](file:///Users/gustavoalmeida/projetos/Cartorio/.harness/SUI_CHECKLIST.md) — go-live checklist

---

Modified by Gustavo Almeida — 2026-07-15 14:45 BRT — F4 [P1] RETRY