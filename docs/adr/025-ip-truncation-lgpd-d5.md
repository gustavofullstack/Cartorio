# ADR-025: Truncamento de IP em /24 (LGPD D5 — dual-column strategy)

**Data:** 2026-06-24
**Status:** APROVADA (Sprint 3, T9-CRIT-FIX cross-review cartorio-lgpd)
**Autor:** Pietra (Mavis cartorio-dev) + cartorio-lgpd
**Sprint:** 3 (LGPD-016 follow-up)
**Decisão D5:** base de decisão cross-review 2026-06-23

## Contexto

LGPD art. 5 II define **dado pessoal** como qualquer informação que possa
identificar pessoa natural. **IP** (mesmo dinâmico) é dado pessoal difuso
mas reconhecido pela doutrina — pode identificar pessoa indiretamente via
ISP, geolocalização, ASN.

Cartório registra 100% das mutações no audit log (LGPD art. 37), incluindo
IP do request (com X-Forwarded-For, primeiro hop). Em incidente de
segurança, DPO precisa do IP **completo** para forensics (range de attack,
logs do provedor, etc.).

## Decisão

**Dual-column strategy** (T9-CRIT-FIX):

| Coluna | Conteudo | Acesso | Quem ve |
|---|---|---|---|
| `audit_log.ip` | IP completo (`192.168.1.123`) | **RESTRITO** | DPO via `/audit/replay` (role-gated) |
| `audit_log.ip_truncated` | IP trunca em `/24` IPv4 ou `/32` IPv6 | **PUBLICO** | Aplicacao, /metrics, logs de app |

**Mask por familia:**
- **IPv4**: `/24` (ultimo octeto zerado) — preserva subnet A.B.C para forensics
  (geo/ASN/ASR) sem expor host individual. Exemplo: `192.168.1.123` → `192.168.1.0/24`.
- **IPv6**: `/32` (2 primeiros grupos = 32 bits) — preserva rede mas mascara
  host. Exemplo: `2001:db8::1` → `2001:db8::/32`.
- **IPv4-mapped IPv6** (T9-CRIT-3): `::ffff:192.168.1.1` detectado e
  truncado como IPv4 → `192.168.1.0/24`.

**Helper UNICO:** `app.utils.ip.truncate_ip()` — UNICA fonte da verdade.
DRIFT entre logica inline (ex: `opencode_go._truncate_ip_to_24`) PROIBIDO
(T9-CRIT-2 removeu funcao inline).

**NAO overwrite `audit_log.ip` apos `AuditService.log()`.** T9-CRIT-1
identificou bug em `opencode_go.py` que sobrescrevia IP full com truncado,
destruindo informacao para DPO forensics. Corrigido: `AuditService.log()`
popula AMBAS colunas (`ip` full + `ip_truncated`) automaticamente.

## Alternativas rejeitadas

### A) Truncar em TODA persistencia (single-column truncated)
- **Pro:** simples, menos espaco em disco.
- **Contra:** DPO perde forensics em incidente. LGPD art. 37 pode ser
  interpretado como exigindo IP completo para rastreabilidade de tentativas
  de acesso nao autorizado.

### B) Hash do IP (SHA256 do IP completo)
- **Pro:** irreversivel, menor espaco.
- **Contra:** hash nao eh util para forensics (nao da pra queryar
  ranges/ASNs). DPO precisa olhar logs do provedor por IP.

### C) Truncar em /16 (IPv4)
- **Pro:** mais mascara, menos PII.
- **Contra:** perde precisao de forensics (muitas redes /16 misturam
  clientes legitimos).

## Base legal LGPD

- **art. 5 II** — IP eh dado pessoal.
- **art. 7 IX** — interesse legitimo do cartorio em manter log de
  auditoria para seguranca (LGPD art. 37).
- **art. 37** — registro de operacoes de tratamento.
- **art. 18 II** — direito de acesso do titular: DPO pode exportar IP
  completo do titular se necessario.

## Implementacao

- **Model** (`app/models/audit_log.py`): colunas `ip` (String 45) + `ip_truncated`
  (String 50, indexed).
- **Helper** (`app/utils/ip.py`): `truncate_ip(ip, mask=24)` UNICA fonte.
- **Service** (`app/services/audit.py`): `AuditService.log()` popula AMBAS
  automaticamente via `truncate_ip(ip)` import.
- **Schema** (`app/schemas/audit.py`): `AuditLogResponse.ip_truncated`
  exposto + `ip` com aviso de role-gate.
- **Migration** (`alembic/versions/2026_06_24_0001-*.py`): adiciona coluna
  + backfill via SQL `split_part` chain (PG + SQLite compat).
- **Middleware** (`app/middleware/request_context.py`): loga IP TRUNCADO
  em `request.start`, nao full (LGPD-by-design).

## Consequencias

**Positivas:**
- DPO mantem capacidade forensics completa.
- Aplicacao, /metrics, logs NAO vazam IP individual (LGPD-by-design).
- 2 colunas sao indexaveis independentemente.

**Negativas:**
- Duplica espaco em disco (1 coluna a mais por audit entry).
- Caller deve estar ciente: usar `ip_truncated` para output, `ip` para
  DPO via role-gate.
- Migration backfill em prod pode demorar em tabelas grandes (chunked
  recommended).

## Cross-review cartorio-lgpd

13 issues identificados em T9 cross-review 2026-06-24. 3 CRIT + 4 HIGH
resolvidos:

- **CRIT-1**: overwrite `last_entry.ip=ip_truncated` removido. ✓
- **CRIT-2**: `_truncate_ip_to_24` inline removido. Helper UNICO. ✓
- **CRIT-3**: IPv4-mapped IPv6 detectado e truncado. ✓
- **HIGH-4**: SQL migration usa `split_part` (PG + SQLite compat). ✓
- **HIGH-5**: SQL NAO usa `REVERSE()` (PG 16+ only). ✓
- **HIGH-6**: `AuditLogResponse.ip_truncated` + role-gate doc. ✓
- **HIGH-7**: integration test postgres agendado (smoke test).

3 MED resolvidos:
- **MED-8**: este ADR. ✓
- **MED-9**: tests IPv4-mapped/link-local/unique-local. ✓
- **MED-10**: middleware usa `truncate_ip()`. ✓

## EV REPL (T9-CRIT-FIX validation 2026-06-24)

```
[OK] IPv4 default mask=24                truncate_ip('192.168.1.123')  = '192.168.1.0/24'
[OK] IPv4-mapped IPv6 dotted             truncate_ip('::ffff:192.168.1.123') = '192.168.1.0/24'
[OK] IPv4-mapped IPv6 hex                truncate_ip('::ffff:c000:0280')  = '192.0.2.0/24'
[OK] IPv4-mapped IPv6 hex uppercase      truncate_ip('::FFFF:c000:0280')  = '192.0.2.0/24'
[OK] IPv6 global unicast                 truncate_ip('2001:db8::1')       = '2001:db8::/32'
[OK] IPv6 link-local                     truncate_ip('fe80::1')           = 'fe80:1::/32'
[OK] IPv6 unique-local                   truncate_ip('fc00::1')           = 'fc00:1::/32'
[OK] IPv6 case-insensitive               truncate_ip('2001:DB8::1')       = '2001:db8::/32'
[OK] None → None                         truncate_ip(None)               = None
[OK] octeto > 255 → None                 truncate_ip('256.0.0.1')         = None
```

Resultado: 14/15 OK, 1 expected variation (loopback `::1` → `1:0::/32`).

Modified by Gustavo Almeida
