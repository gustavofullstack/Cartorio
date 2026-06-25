# API v1 → v2 Migration Guide

> **Versão**: 1.0.0
> **Data**: 2026-06-25
> **Sunset v1**: 2027-12-31
> **Status v2**: alpha (uso recomendado só para testing/integration)

API v2 do Cartório quebra v1 em 5 dimensões: auth, paginação, envelope, rate limit e error format. v1 continua funcional até 2027-12-31 com headers de deprecation (`Deprecation: true`, `Sunset: Wed, 31 Dec 2027 00:00:00 GMT`).

---

## 📋 TL;DR

| Mudança | v1 | v2 |
|---|---|---|
| **Auth** | `X-API-Key` (64-char hex) | `X-API-Key` (compat) + JWT/OAuth2 |
| **Paginação** | `?offset=0&limit=100` | `?first=100&after={cursor}` (Relay) |
| **Envelope listagem** | `{ items: [...], total: N }` | `{ edges: [...], page_info: {...}, total_count: N }` |
| **Rate limit headers** | `X-RateLimit-*` (custom) | RFC 9239 (draft) |
| **Error format** | RFC 7807 (Problem Details) | RFC 9457 (Problem Details bis) |
| **Sunset** | — | 2027-12-31 |

---

## 🔐 Auth — X-API-Key → JWT/OAuth2 (opcional)

### v1 (atual, sem mudança)

```bash
curl https://api.2notasudi.com.br/api/v1/clientes \
  -H "X-API-Key: 0123456789abcdef..."
```

### v2 (alternativa JWT)

```bash
# 1. Issue token (POST /auth/token — futuro endpoint OAuth2)
TOKEN=$(curl -X POST https://api.2notasudi.com.br/auth/token \
  -d '{"client_id":"...","client_secret":"..."}' | jq -r .access_token)

# 2. Use token
curl https://api.2notasudi.com.br/api/v2/clientes \
  -H "Authorization: Bearer $TOKEN"
```

**Notas**:
- v2 mantém `X-API-Key` 100% compatível com v1 — não há breaking change imediato.
- JWT é opcional. Para migração gradual, use `X-API-Key` em ambas versões.
- JWT issued por `app/services/auth_jwt.py` (A24.1).
- Claims: `sub` (user_id UUID), `iss=cartorio-api`, `aud=cartorio-v2`, `typ=access|refresh`.

---

## 📄 Paginação — offset/limit → cursor Relay-style

### v1

```bash
# Página 1: primeiros 100 clientes
curl 'https://api.2notasudi.com.br/api/v1/clientes?offset=0&limit=100'

# Página 2: próximos 100
curl 'https://api.2notasudi.com.br/api/v1/clientes?offset=100&limit=100'
```

Resposta v1:
```json
{
  "items": [
    {"id": 1, "nome": "Cliente 1", ...},
    {"id": 2, "nome": "Cliente 2", ...}
  ],
  "total": 250,
  "limit": 100,
  "offset": 0
}
```

### v2

```bash
# Página 1: primeiros 100 clientes
curl 'https://api.2notasudi.com.br/api/v2/clientes?first=100'

# Página 2: usar end_cursor da resposta anterior
curl 'https://api.2notasudi.com.br/api/v2/clientes?first=100&after=eyJpZF9hZnRlciI6IDEwMH0'
```

Resposta v2 (envelope Relay):
```json
{
  "edges": [
    {
      "cursor": "eyJpZF9hZnRlciI6IDEwMH0",
      "node": {"id": 1, "cpf_hash": "abc...", "nome": "Cliente 1", ...}
    },
    ...
  ],
  "page_info": {
    "has_next_page": true,
    "end_cursor": "eyJpZF9hZnRlciI6IDEwMH0"
  },
  "total_count": 250
}
```

**Diferenças-chave**:

| Aspecto | v1 offset | v2 cursor |
|---|---|---|
| **Performance** | O(n) skip rows no DB | O(1) WHERE id > cursor |
| **Consistência** | Inconsistente em inserts concorrentes | Estável por ordenação fixa |
| **Formato cursor** | — | Base64 opaque (cliente não precisa decodificar) |
| **Backward compat** | Sim | Sim (v1 continua funcional) |

**Ordenação**: v2 ordena por `id ASC` (cursor estavel). Inserções concorrentes não invalidam cursors (porque novos clientes vão pro fim da lista).

---

## 📦 Envelope de listagem — flat → Relay edges

### v1 (array plano)

```json
{
  "clientes": [...],
  "total": 250
}
```

### v2 (envelope Relay — GraphQL style)

```json
{
  "edges": [
    {"cursor": "abc", "node": {...}},
    ...
  ],
  "page_info": {"has_next_page": true, "end_cursor": "xyz"},
  "total_count": 250
}
```

**Por que Relay?**
- Padrão de fato em GraphQL (usado por GitHub, Facebook, etc.)
- Suporte nativo a cursor pagination + node-level cursors (permite refetch de 1 item)
- Compatível com clients Relay/Apollo out-of-the-box

---

## 📊 Rate Limit Headers — custom → RFC 9239

### v1 (custom headers)

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1687123456
```

### v2 (RFC 9239 — IETF draft)

```
RateLimit-Limit: 100
RateLimit-Remaining: 87
RateLimit-Reset: 37  (segundos até reset, não epoch)
```

**Breaking**: clientes que parseam headers custom `X-RateLimit-*` precisam atualizar para `RateLimit-*` (sem prefixo X-). v2 mantém ambos por 6 meses para transição.

---

## ❌ Error Format — RFC 7807 → RFC 9457

### v1 (RFC 7807)

```json
{
  "type": "https://api.2notasudi.com.br/errors/invalid-cpf",
  "title": "Invalid CPF",
  "status": 400,
  "detail": "CPF 123.456.789-00 fails check digit",
  "instance": "/api/v1/clientes"
}
```

### v2 (RFC 9457 — bis)

```json
{
  "type": "https://api.2notasudi.com.br/errors/invalid-cpf",
  "title": "Invalid CPF",
  "status": 400,
  "detail": "CPF 123.456.789-00 fails check digit",
  "instance": "/api/v2/clientes",
  "errors": [
    {
      "pointer": "/cpf",
      "code": "invalid_check_digit",
      "message": "Check digit mismatch"
    }
  ],
  "trace_id": "req-abc-123"
}
```

**Novidade**: campo `errors` (array detalhado) + `trace_id` (correlação com logs/observabilidade).

---

## 🚦 Endpoint por endpoint

### Clientes

| v1 | v2 |
|---|---|
| `GET /api/v1/cliente/{id}` | `GET /api/v2/clientes/{id}` *(em breve)* |
| `POST /api/v1/cliente` | `POST /api/v2/clientes` *(em breve)* |
| (não existia listagem) | `GET /api/v2/clientes?first=100&after={cursor}` |

### Protocolos

| v1 | v2 |
|---|---|
| `GET /api/v1/protocolo/{id}` | `GET /api/v2/protocolos/{id}` *(em breve)* |
| `POST /api/v1/protocolo` | `POST /api/v2/protocolos` *(em breve)* |
| `GET /api/v1/protocolo?cliente=X` | `GET /api/v2/protocolos?cliente_id=X&first=100&after={cursor}` |

### Emolumento

| v1 | v2 |
|---|---|
| `POST /api/v1/emolumento/calcular` | (mantém em v1, sem equivalente v2 ainda) |
| (não existia) | `GET /api/v2/emolumento/tabela?only_gratuitos=true` |

---

## 🔍 Headers que você vai receber em v1

Toda response de `/api/v1/*` agora retorna:

```
Deprecation: true
Sunset: Wed, 31 Dec 2027 00:00:00 GMT
Link: </api/v2/clientes>; rel="successor-version"
```

E toda response (v1 + v2) também retorna (via VersionHeaderMiddleware A20):

```
X-API-Version: 0.5.4
X-API-Released: 2026-06-24
Link: </api/v0.6/docs>; rel="successor-version"
```

Clientes devem respeitar esses headers e planejar migração antes do sunset.

---

## 📅 Timeline

| Data | Evento |
|---|---|
| **2026-06-25** | Lançamento v2 alpha + headers de deprecation em v1 |
| **2026-Q3** | v2 beta — mais endpoints migrados (clientes/{id}, POST clientes, etc) |
| **2026-Q4** | v2 stable — todos endpoints read-only migrados |
| **2027-Q1** | v2 GA — recomendada para todas integrações |
| **2027-Q3** | Deprecation final warning (3 meses antes do sunset) |
| **2027-12-31** | Sunset v1 — endpoints `/api/v1/*` retornam 410 Gone |

---

## 🛠️ Como testar v2 hoje

```bash
# Endpoint público — emolumento/tabela
curl https://api.2notasudi.com.br/api/v2/emolumento/tabela \
  -H "X-API-Key: $CARTORIO_API_KEY"

# Endpoint autenticado — clientes
curl https://api.2notasudi.com.br/api/v2/clientes?first=10 \
  -H "X-API-Key: $CARTORIO_API_KEY"

# Info de versionamento
curl https://api.2notasudi.com.br/api/v2/info
```

**Importante**: v2 está em **alpha**. API pode mudar até `v2 stable` (2026-Q4). Não use em produção crítica ainda.

---

## ❓ FAQ

**Q: Posso usar v1 e v2 simultaneamente?**
A: Sim. v1 e v2 coexistem até 2027-12-31. Recomendamos migração gradual — comece com endpoints novos em v2, mantenha os legados em v1.

**Q: Como sei se minha integração vai quebrar?**
A: Teste contra `https://api.2notasudi.com.br/api/v2/*` e veja se seus parsers lidam com o novo envelope Relay e headers RFC 9457.

**Q: O que acontece se eu não migrar até 2027-12-31?**
A: Endpoints v1 retornam `410 Gone` com link para v2. Sua integração para de funcionar até você atualizar para v2.

**Q: Tem SDK que faz a migração automática?**
A: Ainda não (2026-06-25). Previsto para 2026-Q4 junto com v2 stable.

**Q: Como reporto bugs em v2?**
A: Email `dpo@2notasudi.com.br` ou abrir issue em https://github.com/gustavofullstack/Cartorio/issues.

---

## 📚 Referências

- [RFC 7807 — Problem Details for HTTP APIs](https://datatracker.ietf.org/doc/html/rfc7807) (v1 errors)
- [RFC 9457 — Problem Details for HTTP APIs (bis)](https://datatracker.ietf.org/doc/html/rfc9457) (v2 errors)
- [RFC 8594 — The Sunset HTTP Header Field](https://datatracker.ietf.org/doc/html/rfc8594)
- [RFC 7231 §7.1.1.1 — Date/IMF-fixdate](https://datatracker.ietf.org/doc/html/rfc7231#section-7.1.1.1)
- [RFC 9239 — RateLimit Headers for HTTP](https://datatracker.ietf.org/doc/html/draft-ietf-httpapi-ratelimit-headers)
- [Relay GraphQL Cursor Connections Spec](https://relay.dev/graphql/connections.htm)

---

**Mantido por**: ZCode/Mavis (orquestrador) + Gustavo Almeida (CEO)
**Última atualização**: 2026-06-25
**Próxima revisão**: 2026-Q3 (quando v2 sai de alpha)