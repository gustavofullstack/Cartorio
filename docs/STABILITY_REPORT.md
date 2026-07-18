# Stability Report — G8.16.T4

Script `scripts/stability_report.py` que gera um relatório de estabilidade
operacional ao final de cada wave do loop G8. Owner: **cartorio-dev** (Wave 44).

## Quick start

```bash
# Padrão: últimas 24h, markdown em stdout
python3 scripts/stability_report.py --offline --window 24h

# Janela maior + persistir em arquivo (modo offline-safe)
python3 scripts/stability_report.py --offline --window 72h \
  --output docs/last_report.md

# JSON estruturado para pipelines
python3 scripts/stability_report.py --offline --window 24h --json \
  --output /tmp/report.json

# Modo live: probes HTTP reais aos serviços (sem DB)
python3 scripts/stability_report.py --window 1h
```

## O que ele coleta

| Seção | Origem | Fail-soft |
|-------|--------|-----------|
| 1. Serviços (API/N8N/Evolution/OpenClaw/Chatwoot/Supabase/Redis/Traefik/LiteLLM/EasyPanel/Tailscale) | `urllib` stdlib + `ThreadPoolExecutor` | ✅ status 🔴/🟡/🟢/⚪ |
| 2. Métricas de entrega | `git log`, `.pytest_cache`, `coverage`, `.harness/memory/`, `ruff`, `mypy` | ✅ ausente → `—` |
| 3. Sinais LGPD | `audit_log.position` via SQLAlchemy ou `state/last.json` | ✅ `unavailable` |
| 4. Sinais HITL | `protocolo.status='DRAFT'` via SQLAlchemy | ✅ `unavailable` |
| 5. Progresso do SUPER_PLANO_G8_100_TASKS.md | `re.findall` em checkboxes | ✅ counts 0 se arquivo ausente |
| Próxima wave | primeiro `W##` com `[ ]` no WAVE MAP | ✅ `None` se tudo `[x]` |

## Modos

- **`--offline`** (default em CI/dev): não chama HTTP nem DB. Ideal para laptops
  isolados e para rodar no master-loop sem martelar serviços prod.
- **modo live** (sem flag): `urllib` probes em paralelo (8 workers) com
  timeout 3s; DB opcional via `app.db.SessionLocal` (SQLAlchemy).
- **`--json`**: serializa `StabilityReport` em JSON.
- **`--since ISO`**: override da janela para timestamp explícito.

## LGPD & segurança

- **PII scrubbing automático**: padrões CPF / RG / telefone / email /
  `protocolo N` / `escritura N` são mascarados para `[REDACTED]` antes de
  qualquer string entrar no output.
- **Fail-soft absoluto**: cada coletor é `try/except Exception: return default`;
  nenhum serviço caído derruba o script. Sempre sai com `exit 0` (exceto
  erro de I/O → `exit 2`).
- **Sem deps externas**: só stdlib (`urllib`, `subprocess`, `concurrent.futures`,
  `dataclasses`, `argparse`, `re`, `pathlib`). Opcionalmente usa
  `coverage` se disponível.

## Integração com master-loop

Adicionar no `master-loop-v25.sh` (depois do bloco que fecha o wave):

```bash
# No final de cmd_run_wave, após update state:
python3 scripts/stability_report.py --offline --window "${WAVE_WINDOW:-24h}" \
  --output ".harness/loop-engineer/state/wave-${wave_num}-report.md"
```

E copiar para `docs/STABILITY_REPORT_<WAVE>.md` quando o relatório subir
para o PR. Hook opcional: `.harness/hooks/post-wave.sh` se preferir.

## Saída de exemplo (modo offline)

```
# Stability Report — Cartório 2º Notas
- **Gerado em:** 2026-07-18T14:23:12+00:00
- **Janela:** `24h` (since 2026-07-17T14:23:12+00:00 → until 2026-07-18T14:23:12+00:00)
- **Modo:** `offline`

## 1. Serviços
| Status | Serviço | Host | Latência | Detalhe |
|--------|---------|------|---------:|---------|
| ⚪ | API FastAPI | `api.2notasudi.com.br` | — | offline mode — skip HTTP probe |
| ⚪ | N8N Workflows | `flow.2notasudi.com.br` | — | offline mode — skip HTTP probe |
... (11 linhas)

## 2. Métricas de entrega
- **git_commits** (na janela): 27
- **git_last_sha**: `fa40504ae267` — feat(g8): wire ProcessingHostMiddleware (Cartorio CI)
- **lesson_count**: 81
- **ruff**: — · **mypy**: —

## 3. Sinais LGPD
- **chain_position=?**
- **audit_log.create_recent** (na janela): ?
- **source**: `unavailable`

## 5. Progresso do SUPER_PLANO_G8_100_TASKS.md
- **[x] done**: 45
- **[~] partial**: 1
- **[ ] pending**: 57
```

## Testes

```bash
cd backend && uv run pytest tests/test_stability_report_g8.py -v --no-cov
# 16 passed (5 obrigatórios + 11 extras — fail-soft, PII, gate, CLI)
```

Cobre: parse de wave progress, scrubbing de PII, fail-soft com todos os
serviços caídos, janelas 1h/6h/24h/72h/7d, formato `chain_position=N`,
CLI file/JSON.

## Lições relacionadas

- **Lesson 213/214/215** (G8.16 → Wave 32-34): padrões DLQ já provaram o
  valor do fail-soft — replicado aqui.
- **AGENTS.md §Security**: audit log é append-only; este relatório **lê**
  `audit_log.position` mas nunca escreve. Não toca a chain.
- **AGENTS.md §Datasensitive**: PII scrubbing 3-camadas continua sendo
  Pydantic field validators → Sentry `before_send` → log `MaskingFilter`;
  este script é a **4ª camada** (output-side).

_Modified by Gustavo Almeida — G8 Wave 44 / Squad 16 (cartorio-dev)._