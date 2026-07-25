# Segurança — Trust Boundaries e Gates

Documento curto dos controles de segurança ativos na borda da API (E3.03/E3.04/E3.05, G9).
Para o modelo completo de ameaças LGPD, ver `docs/ARCHITECTURE.md` e `.harness/AGENTS.md`.

## 1. Trust boundary X-Forwarded-For (E3.04)

O IP do cliente define identidade para rate limit, logs e auditoria — portanto a
borda **nunca confia em header enviado pelo cliente**.

- `app/middleware/trusted_proxy.py` (`TrustedProxyMiddleware`) resolve o IP efetivo
  **somente** quando o peer direto pertence a uma rede confiável
  (`127.0.0.1/32`, `::1/128`, `10.0.0.0/8`, `172.16.0.0/12`, `187.77.236.77/32`).
- Conexão **direta** (peer fora das redes): o header XFF é **ignorado** — o peer
  TCP é a identidade. Um cliente nunca escolhe o próprio IP.
- Proxy confiável com XFF: percorre a cadeia **da direita para a esquerda** e
  ancora no primeiro hop **não confiável** (rightmost-untrusted). Cadeia só com
  hops confiáveis é **fail-closed**: preserva o peer direto.
- IPv4 e IPv6 suportados; XFF malformado é ignorado hop a hop (sem exceção).
- Consumidores downstream (`RateLimitByKeyMiddleware`, request context, deps de
  integrações) leem **apenas** `request.client.host` já resolvido — é proibido
  ler o header `X-Forwarded-For` diretamente (rate limit não é bypassável por
  XFF forjado: o bucket deriva sempre do IP real).
- Cobertura: `backend/tests/test_trusted_proxy_middleware.py` (mapa dos 9
  cenários no docstring) + `backend/tests/test_trusted_proxy.py`.

## 2. Registry de tiers de API key (E3.05)

`app/services/rate_limit_by_key.py` aplica 3 tiers de rate limit por `X-API-Key`:

| Tier    | Limite   | Como eleva                                             |
|---------|----------|--------------------------------------------------------|
| `n8n`   | 600/min  | Match exato com `settings.cartorio_api_key`            |
| `dpo`   | 60/min   | Match exato com `settings.cartorio_dpo_api_key`        |
| `padrao`| 30/min   | Default fail-secure (sem key / key desconhecida)       |

Regras anti-spoofing (E2.03 H4):

- Elevação de tier exige **match exato** da key registrada, comparado em
  **constant-time** (`hmac.compare_digest`) — nunca `==`.
- **Prefixo NUNCA eleva tier** (`n8n-*`, `dpo-*`, `admin-*` forjados caem em
  `padrao`). Prefixo/tamanho são controlados pelo caller, logo spoofable.
- Key vazia/ausente, near-miss (1 char), unicode malformada ou string longa
  aleatória → `padrao`.
- Sem key, o bucket é hash SHA-256 do IP (LGPD-safe, não reversível). Camadas
  adicionais por IP: DDoS fixed-window 100/min + sliding window (A7).
- Webhook Telegram (`/api/v1/telegram/webhook`) não usa este registry: autentica
  por `X-Telegram-Bot-Api-Secret-Token` no próprio router.
- Cobertura: `backend/tests/test_rate_limit_by_key.py` +
  `backend/tests/test_g9_s5_security_gates.py`.

## 3. CI gate de secrets (E3.03)

`backend/scripts/check_no_literal_keys.py` (LGPD Art. 46) — 20 patterns
(AWS, OpenAI, Anthropic, Telegram, Supabase JWT, MiniMax, GCP SA, PKCS8,
hex-64 webhook/HMAC, etc.) com severity + baseline + opt-out
(`# noqa: ALLOW_KEY_FALLBACK (motivo: ...)`). **Nunca imprime valores** de
match — apenas `path:lineno` + regra + `[valor redigido]`.

Três gates no job `secrets-scan` de `.github/workflows/ci.yml`:

1. **Gitleaks** — scan de repo (histórico sob demanda).
2. **Gate full** em `backend/app` + `backend/scripts` com
   `--severity critical --baseline ...` — falha em qualquer critical novo nos
   diretórios de código.
3. **Gate incremental (E3.03)** — `--changed-since <base>` em PR e push:
   escaneia **somente linhas adicionadas** do diff (`git diff -U0`), portanto
   **falha em secret NOVO em qualquer arquivo tracked** sem ser bloqueado por
   achados legados. Uso local equivalente: `--staged` (linhas no index).

Inventário de achados legados em arquivos tracked roda separado
(`--tracked-files --report-only`, G7.22.T4) — nunca bloqueia CI e serve de
fila de remediação. Candidatos a secret real NÃO são baselinados
silenciosamente: exigem decisão do dono (rotação) antes de whitelist.

Exit codes do scanner: `0` clean (ou `--report-only`), `1` violação ≥ threshold
(gate fail), `2` erro de I/O/argumento/git. Cobertura:
`backend/tests/test_check_no_literal_keys_g8.py`.
