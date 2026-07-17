# Traefik Edge Rate-Limit — Optional (G7.13.T4)

| Campo | Valor |
|-------|--------|
| **Task** | G7.13.T4 — rate-limit edge optional |
| **Wave** | G7 Wave 27 |
| **Agente** | cartorio-sre |
| **Config template** | [`infra/traefik/middleware-rate-limit-optional.yaml`](../infra/traefik/middleware-rate-limit-optional.yaml) |
| **Status deploy** | **HOLD** — docs + template only; não aplicar sem GO Gustavo |
| **Draft irmão** | [`infra/firewall/traefik-middleware/cartorio-middlewares.yml`](../infra/firewall/traefik-middleware/cartorio-middlewares.yml) (FASE 2, também HOLD) |

---

## 0. TL;DR

- **App-layer** rate limit já existe e é a fonte de verdade para tiers (N8N/DPO/default) e DDoS por IP.
- **Edge** (Traefik middleware) é **opcional**, defesa em profundidade: corta abuso **antes** de chegar nos workers Uvicorn.
- Template versionado em `infra/traefik/middleware-rate-limit-optional.yaml` — **não é o dynamic config ativo**.
- Deploy = HOLD-GUSTAVO (mesmo boundary de middlewares FASE 2).

---

## 1. Camadas de rate limit (ordem conceitual)

```
Cliente
  │
  ▼
Cloudflare (opcional WAF / rate rules)     ← fora deste repo
  │
  ▼
Traefik rateLimit middleware (EDGE)        ← ESTE doc / template (opcional)
  │  429 se average/burst estourar
  ▼
FastAPI middleware chain                   ← OBRIGATÓRIO em prod
  │  RequestContext → Idempotency
  │  → RateLimitByKey (tiers + DDoS IP 100/min)
  │  → RateLimit (sliding window ~60/min IP)
  │  → SlowLog → CORS
  ▼
Handlers / DB / Redis
```

### 1.1 App (já implementado)

| Camada | Onde | Limite típico | Fail mode |
|--------|------|---------------|-----------|
| DDoS por IP | `RateLimitByKeyMiddleware._check_ip_ddos` | **100 req/min** por IP | **fail-open** se Redis cair |
| Sliding window IP | `RateLimit` / A7 | **~60 req/min** por IP | fail-open |
| Tier API key | `RateLimitByKey` | N8N **600**/min, DPO **60**, default **30** | fail-open |
| ADR | [`docs/adr/022-rate-limit-ddos-by-ip.md`](adr/022-rate-limit-ddos-by-ip.md) | — | — |

### 1.2 Edge (opcional — template)

| Middleware `@file` | average | burst | period | Uso sugerido |
|--------------------|---------|-------|--------|--------------|
| `rate-limit-public` | 30/s | 60 | 1s | APIs/UIs públicas |
| `rate-limit-public-strict` | 5/s | 10 | 1s | login / auth forms |
| `rate-limit-anon` | 20/s | 40 | 1s | alias ROUTERS_PENDENTES (chatwoot) |
| `rate-limit-authenticated` | 50/s | 100 | 1s | n8n UI host |
| `rate-limit-internal` | 200/s | 400 | 1s | tráfego swarm / alto volume |
| `rate-limit-webhook` | 100/s | 250 | 1s | Telegram / Evolution webhooks |

> Unidades Traefik: `average` é taxa média **por source** no `period` (default 1s).  
> Não é o mesmo modelo “N/min” do Redis sliding window — calibre com teste.

---

## 2. Recomendações por superfície

| Superfície | FQDN / path | Edge? | Middleware sugerido | Notas |
|------------|-------------|-------|---------------------|-------|
| API pública | `api.2notasudi.com.br` | Opcional | `rate-limit-public` | App já cobre; edge evita flood TCP/TLS |
| Health | `/health`, `/ready` | **Não** ou alto | — / internal | Probes k8s/swarm não devem 429 |
| Webhooks TG/Evo | paths webhook | Cautela | `rate-limit-webhook` | Bursts legítimos; testar com carga real |
| N8N UI | `flow.*` | Opcional | `rate-limit-authenticated` | Admin UI |
| N8N → API | internal | Evitar strict | `rate-limit-internal` ou **sem** edge | Tier N8N 600/min no app |
| Chatwoot | `chat.*` | Opcional | `rate-limit-anon` | Ver ROUTERS_PENDENTES |
| EasyPanel | `easypanel.*` | Preferir IP allow / auth | strict + não público | Não depender só de rate limit |
| Admin / DPO | rotas sensíveis | Preferir Tailscale allowlist | ver FASE 2 draft | `ip-allow-tailscale` |

### 2.1 Público vs interno (resumo)

| | Público (internet) | Interno (swarm / N8N / Tailscale) |
|--|--------------------|-----------------------------------|
| Objetivo edge | Cortar bot/scraper | Teto anti-loop só |
| average | baixo–médio (5–30/s) | alto (100–200/s) ou ausente |
| Risco principal | falso positivo em NAT/CGNAT | matar cron N8N legítimo |
| Preferência | edge + app | **app only** (tiers) |

---

## 3. Fail-open vs fail-closed

| Camada | Se Redis/store cair | Comportamento |
|--------|---------------------|---------------|
| **App** RateLimit* | Redis down | **fail-open** (permite request; log warning) — design cartório |
| **Traefik** rateLimit | middleware in-memory | Continua limitando por IP em memória do processo Traefik; **não** depende Redis |
| **Traefik** se middleware YAML inválido | parse fail | Traefik pode recusar reload do dynamic file — **risco de config** |

Implicações:

1. Edge rate-limit **não herda** o fail-open do app — ele é sempre “enforced” enquanto o middleware estiver anexado.
2. Por isso o deploy é **HOLD**: um average baixo demais em rota de webhook = incidente de canal.
3. Se Redis cair e o app fail-open, o **edge** ainda protege contra flood bruto — benefício principal da camada.

---

## 4. Relação com Cloudflare

- Se o host estiver **Proxied** (laranja), o IP visto pelo Traefik pode ser o do CF edge, não o cliente.
- Sem `forwardedHeaders` / `trustedIPs` corretos, **todo o mundo** pode compartilhar o mesmo bucket de rate limit (ou o bucket vira o IP do proxy).
- Antes de ativar em hosts proxied:
  1. Confirmar `entryPoints.websecure.forwardedHeaders.trustedIPs` com ranges Cloudflare **ou**
  2. Usar rate rules no Cloudflare e **não** duplicar edge no Traefik para esse host.

---

## 5. Como aplicar (quando GO)

```bash
# 1) Backup dynamic config na VPS (HOLD-GUSTAVO / SSH autorizado)
cp /etc/traefik/dynamic/main.yaml{,.bak-$(date +%Y%m%d)}

# 2) Copiar template
# scp infra/traefik/middleware-rate-limit-optional.yaml vps:/etc/traefik/dynamic/

# 3) Anexar middleware só em 1 router de teste (ex. staging host)
#    middlewares: [rate-limit-public-strict@file]

# 4) Validar sintaxe / reload (método depende do static config EasyPanel)

# 5) Smoke 429
for i in $(seq 1 40); do
  curl -sk -o /dev/null -w "%{http_code}\n" "https://HOST_DE_TESTE/"
done
# Esperado: sequência de 200 depois 429 (se average baixo o bastante)

# 6) Rollback
# rm middleware file ou desanexar labels; reload Traefik
```

EasyPanel UI path: Service → Labels →  
`traefik.http.routers.<name>.middlewares=rate-limit-public@file`  
(requer middleware já no provider file).

---

## 6. Verificação / métricas

| Check | Como |
|-------|------|
| Middleware carregado | Traefik API local (se exposta só em loopback): `/api/http/middlewares` |
| 429 edge vs 429 app | Header / body: app costuma mandar problem+json + `X-RateLimit-*`; Traefik 429 é genérico |
| Falso positivo N8N | `docker service logs cartorio_n8n` + métricas rate_limit no `/metrics` da API |
| Acesso log | Ver backend ainda saudável em [`TRAEFIK_ACCESS_LOG_DEBUG_G7.md`](TRAEFIK_ACCESS_LOG_DEBUG_G7.md) |

Prometheus (se disponível): `traefik_service_requests_total` filtrado por code 429.

---

## 7. O que NÃO fazer

- Não copiar `average: 10` do draft FASE 2 em **webhooks** de produção.
- Não aplicar edge rate-limit em `/health` / `/ready` / radar probes sem exceção.
- Não commitar secrets ou IPs de clientes neste template.
- Não tratar edge como substituto de PII scrubbing ou auth.

---

## 8. Cross-refs

| Doc / código | Papel |
|--------------|-------|
| `infra/traefik/middleware-rate-limit-optional.yaml` | Template middlewares |
| `infra/firewall/traefik-middleware/cartorio-middlewares.yml` | Draft FASE 2 (headers + IP allow + rate) |
| `infra/traefik/ROUTERS_PENDENTES.yaml` | Já referencia `rate-limit-anon@file` / `rate-limit-authenticated@file` |
| `backend/app/services/rate_limit_by_key.py` | Tiers + DDoS IP |
| `backend/app/services/sliding_window.py` | A7 sliding window |
| ADR-022 | Decisão DDoS by IP |

**Modified by Gustavo Almeida — G7 Wave 27 cartorio-sre**
