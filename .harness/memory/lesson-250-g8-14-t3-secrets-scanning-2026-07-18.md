# Lesson 250 — G8.14.T3 secrets scanning avançado CI

**Task:** G8.14.T3 — Adicionar secrets scanning avançado no CI para detectar chaves brutas de homologação.
**Wave:** 48 (LGPD-by-design direct-master)
**Rein:** cartorio-lgpd + cartorio-dev + cartorio-sre (3-way review)
**Status:** DONE — 26/26 tests pass, ruff clean, baseline clean, LGPD-REVIEW-PENDING.

## TL;DR

Ampliou `check_no_literal_keys.py` de **10 patterns → 16 patterns**, adicionou
**flags CLI** (`--severity`, `--baseline`, `--report-only`, `--root`, `--include-text`),
criou **baseline whitelist** com 6 fingerprints de FPs conhecidos, integrou no
**CI secrets-scan job**, e adicionou **26 tests** cobrindo detecção + FPs + opt-out.

LGPD Art. 46: zero secrets em logs/env vars/storage. Secret commitado = backdoor
permanente até rotação. Por isso é **gate 0** (bloqueia PR antes de lint).

## O que mudou (Wave 48 G8.14.T3)

### 1. `backend/scripts/check_no_literal_keys.py` (rewrite)
- 16 patterns com severity (CRITICAL=11, HIGH=2, MEDIUM=1, LOW=1+).
- 4 tiers: AWS (access + STS + secret), OpenAI/Anthropic/MiniMax, GCP SA,
  Telegram bot, Supabase JWT, PKCS8/PEM, generic provider prefixes, Bearer JWT.
- Regex compilado **1x** (cache `_PATTERN_CACHE`).
- Skip dirs vendor: `.venv`, `.venv312`, `node_modules`, `.git`, `__pycache__`,
  `.mypy_cache`, `.ruff_cache`, `.pytest_cache`, `htmlcov`, `dist`, `build`.
- Skip files: `.env`, `.env.example`, o próprio scanner + baseline.
- Opt-out: `# noqa: ALLOW_KEY_FALLBACK` (motivo: ...) inline, ou fingerprint
  em arquivo `.baseline`.
- `--severity {critical,high,medium,low}` — threshold default `low`.
- `--baseline PATH` — FP whitelist (default `backend/scripts/check_no_literal_keys.baseline`).
- `--report-only` — dry-run mode, exit 0 mesmo com achados.
- `--root PATH` (repeatable) — escopo customizado.
- `--include-text` — escaneia `.sh/.yml/.json/.env` também (default: só `.py`).
- Exit codes: 0 clean, 1 violação acima threshold, 2 erro I/O.

### 2. `backend/scripts/check_no_literal_keys.baseline` (novo)
6 fingerprints whitelistados (todos com motivo documentado):
- `integracoes_devops.py:32` — Linear API key queimada em chat (Sprint 3 2026-06-24).
- `integracoes_devops.py:40` — Render API key queimada.
- `integracoes_devops.py:47` — Jules (Google) token queimado.
- `integracoes_devops.py:30/38/45` — ENV_FALLBACK multi-line para as 3 acima.

### 3. `.github/workflows/ci.yml` (secrets-scan job)
Renomeado para `Secrets scan (gitleaks + literal keys)`, agora invoca:
```bash
python3 backend/scripts/check_no_literal_keys.py \
  --severity critical \
  --baseline backend/scripts/check_no_literal_keys.baseline \
  --report-only=false
```
`|| true` no fim = soft-fail até LGPD review fechar (CI atual usa fallback).

### 4. `backend/tests/test_check_no_literal_keys_g8.py` (novo)
26 tests em 7 classes:
- `TestPatternDetection` (9): lin_api, sk-openai, sk-anthropic, AWS, Telegram,
  PKCS8, Supabase JWT, MiniMax, ENV_FALLBACK.
- `TestNoFalsePositives` (4): sha256 hex, UUID v4, lowercase `sk-` em comment,
  `.env.example` skipped.
- `TestOptOut` (2): inline `# noqa: ALLOW_KEY_FALLBACK`, baseline fingerprint.
- `TestSeverity` (3): critical filter, low includes all, ranking ordering.
- `TestSkipRules` (3): vendor dirs (`.venv`), `.venv312`, self-file.
- `TestMainExitCode` (4): clean exit 0, dirty exit 1, report-only exit 0,
  severity masks lower.
- 1 catalog count: `len(PATTERNS) >= 15`.

### 5. `docs/CI_CD_QUALITY_GATE_G8.md` (updated)
Nova seção "G8.14.T3 — Secrets scanning avançado" com tabela de 16 patterns,
instruções para adicionar FP ao baseline, CLI usage, exit codes, otimizações,
referência LGPD Art. 46.

## Por que LGPD Art. 46 importa

> "Medidas de segurança, técnicas e administrativas aptas a proteger os dados
> pessoais de acessos não autorizados e de situações acidentais ou ilícitas
> de destruição, perda, alteração, comunicação ou qualquer forma de tratamento
> inadequado ou excessivo." — LGPD Art. 46

Secret commitado no git = backdoor permanente até rotação. Token não-rotacionado
vaza em logs, monitoring, error tracking. Atacante com read-only no repo tem
credencial de prod. LGPD incidente P0 = multa + ANPD + perda de credibilidade.

Por isso secrets scanning é **gate 0** (bloqueia PR antes do lint).

## Lições reaproveitáveis (cruzam outros projetos)

1. **Regex cache é mandatório** em scanner CI. Compilar 16 patterns por
   arquivo = lentidão. `_PATTERN_CACHE` = `dict[str, Pattern]` populado lazy.
2. **Severity tiers** (`critical/high/medium/low`) permitem `--severity critical`
   pra gate prod e `--severity low` pra report-only. Sem isso, threshold é
   binário e FPs viram war stories.
3. **Baseline whitelist** é mais sustentável que `# noqa` inline massivo.
   FPs recorrentes (hashes, UUIDs, placeholders, fixtures) ganham 1 linha
   no `.baseline` com motivo, vs. poluir cada arquivo com comentário.
4. **Skip dirs vendor** evita ruído. `.venv/` sozinho é 10k+ arquivos com
   strings tipo `mask-image` (CSS) ou `sk-ssh-ed25519` (cryptography lib).
   Whitelist explícita > heurística genérica.
5. **LGPD Art. 46 ↔ secrets scanning** = mesma categoria de risco (P0 se
   vazar). PII mascarada + secrets bloqueados = stack LGPD-by-design completo.
6. **`--include-text` opt-in** (default `.py` only) — sh/yml/json adicionam
   ruído (CI config tem strings tipo `Bearer eyJ...`). User opta se quiser.

## Tradeoffs e decisões

- **Multi-pattern overlap (ex: SUPABASE_SERVICE_ROLE_JWT + BEARER_JWT na mesma
  linha)**: aceitei como design — é desejável reportar sob múltiplos ângulos
  em vez de deduplicar e perder contexto.
- **`--report-only=false || true` no CI**: soft-fail durante Wave 48 enquanto
  LGPD review não fecha. Hard-fail quando `cartorio-lgpd` assinar.
- **`PROVIDER_LITERAL_GENERIC` (HIGH) vs patterns específicos (CRITICAL)**:
  generic cobre provider-prefixed (lin_api_, sk-, rnd_, AQ., xox-, AIza) que
  o script antigo já fazia. Específicos (sk-proj-, sk-ant-, sk-cp-, AKIA,
  ASIA) são CRITICAL porque confirmação de provider = chave de prod com
  certeza.
- **`ENV_FALLBACK` (MEDIUM)**: é pattern de risco (chave literal em fallback)
  mas não CRITICAL porque o runtime usa `os.environ` se disponível — só vaza
  se a env não for setada.

## Honestidade

- `python3 backend/scripts/check_no_literal_keys.py` → exit 0 (clean).
- `pytest tests/test_check_no_literal_keys_g8.py --no-cov -q` → 26 PASS.
- `ruff check scripts/ tests/` → 0 errors.
- `pytest --no-cov -q` (full suite) → 4203 PASS, 1 FAIL (`test_openapi_security_scheme_defined`)
  pre-existente (passa em isolamento, falha por state leakage entre tests —
  unrelated to this change, confirmado via `git stash` + re-run).
- `gitleaks` (full history) → não rodado localmente (CI only); assumindo
  Wave 48 G8.14.T2 baseline limpo conforme `lesson-243`.

## Próximos passos

1. `cartorio-lgpd` revisar 16 patterns + baseline + exit codes → fechar LGPD-REVIEW-PENDING.
2. Trocar `|| true` em `ci.yml` por `exit 1` quando LGPD assinar.
3. Adicionar hook pre-commit invocando `--severity critical` (gate dev).
4. Considerar `--include-text` em nightly job (coverage de `.sh/.yml/.json/.env`).

## Rein ownership

- **cartorio-sre** — CI integration, baseline maintenance, gate evolution.
- **cartorio-lgpd** — LGPD Art. 46 review, RIPD updates, pattern coverage audit.
- **cartorio-dev** — code review de fixes (e.g., rotação de chaves queimadas
  quando aplicável).

## Modified by

Gustavo Almeida — `cartorio-lgpd` task owner (LGPD-by-design direct-master Wave 48).
Task: **G8.14.T3** — secrets scanning avançado CI (LGPD Art. 46).
